//! Persisted application state and its normalisation rules.

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use super::themes::DEFAULT_THEME_ID;

pub const MAX_HISTORY_ITEMS: usize = 500;
pub const MIN_OPACITY: f64 = 0.25;
pub const MAX_OPACITY: f64 = 1.0;

pub const WINDOW_MODE_PREVIOUS: &str = "previous";
pub const WINDOW_MODE_NEW: &str = "new";
pub const WINDOW_MODE_BOTH: &str = "both";
pub const DEFAULT_WINDOW_MODE: &str = WINDOW_MODE_BOTH;

/// Out-of-range or unparseable opacities snap back to fully opaque, matching
/// the Python behaviour that treated any bad value as "no transparency".
pub fn normalize_opacity(value: f64) -> f64 {
    if value.is_nan() || !(MIN_OPACITY..=MAX_OPACITY).contains(&value) {
        return MAX_OPACITY;
    }
    value
}

pub fn normalize_window_mode(value: &str) -> String {
    match value {
        WINDOW_MODE_PREVIOUS | WINDOW_MODE_NEW | WINDOW_MODE_BOTH => value.to_string(),
        _ => DEFAULT_WINDOW_MODE.to_string(),
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WindowState {
    pub window_id: String,
    pub title: String,
    #[serde(default)]
    pub editor_text: String,
}

/// Position and size of a window, in physical pixels.
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct Geometry {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

/// Accepts both the current object form and the `[x, y, width, height]` array
/// the PySide6 version wrote, so an existing install keeps its layout.
impl<'de> Deserialize<'de> for Geometry {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        #[derive(Deserialize)]
        #[serde(untagged)]
        enum Stored {
            Object {
                x: i32,
                y: i32,
                width: u32,
                height: u32,
            },
            Legacy(i32, i32, u32, u32),
        }

        Ok(match Stored::deserialize(deserializer)? {
            Stored::Object {
                x,
                y,
                width,
                height,
            } => Geometry {
                x,
                y,
                width,
                height,
            },
            Stored::Legacy(x, y, width, height) => Geometry {
                x,
                y,
                width,
                height,
            },
        })
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct AppState {
    pub windows: Vec<WindowState>,
    pub history: Vec<String>,
    pub theme_id: String,
    pub startup_initialized: bool,
    pub window_opacity: f64,
    pub window_mode: String,
    pub last_active_window_id: Option<String>,
    pub window_geometries: HashMap<String, Geometry>,
    pub total_enabled: bool,
    pub always_on_top: bool,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            windows: Vec::new(),
            history: Vec::new(),
            theme_id: DEFAULT_THEME_ID.to_string(),
            startup_initialized: false,
            window_opacity: MAX_OPACITY,
            window_mode: DEFAULT_WINDOW_MODE.to_string(),
            last_active_window_id: None,
            window_geometries: HashMap::new(),
            total_enabled: true,
            always_on_top: true,
        }
    }
}

impl AppState {
    /// Clamp every field into its valid range after loading untrusted JSON.
    pub fn normalized(mut self) -> Self {
        self.window_opacity = normalize_opacity(self.window_opacity);
        self.window_mode = normalize_window_mode(&self.window_mode);
        self.history.retain(|item| !item.trim().is_empty());
        if self.history.len() > MAX_HISTORY_ITEMS {
            self.history = self.history[self.history.len() - MAX_HISTORY_ITEMS..].to_vec();
        }
        self.window_geometries
            .retain(|_, geometry| geometry.width > 0 && geometry.height > 0);
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn opacity_stays_within_range() {
        assert_eq!(normalize_opacity(0.5), 0.5);
        assert_eq!(normalize_opacity(MIN_OPACITY), MIN_OPACITY);
        assert_eq!(normalize_opacity(MAX_OPACITY), MAX_OPACITY);
    }

    #[test]
    fn out_of_range_opacity_falls_back_to_opaque() {
        assert_eq!(normalize_opacity(0.0), MAX_OPACITY);
        assert_eq!(normalize_opacity(1.5), MAX_OPACITY);
        assert_eq!(normalize_opacity(-1.0), MAX_OPACITY);
        assert_eq!(normalize_opacity(f64::NAN), MAX_OPACITY);
    }

    #[test]
    fn window_mode_accepts_only_known_values() {
        assert_eq!(normalize_window_mode("previous"), "previous");
        assert_eq!(normalize_window_mode("new"), "new");
        assert_eq!(normalize_window_mode("both"), "both");
        assert_eq!(normalize_window_mode("nonsense"), DEFAULT_WINDOW_MODE);
        assert_eq!(normalize_window_mode(""), DEFAULT_WINDOW_MODE);
    }

    #[test]
    fn default_state_is_usable() {
        let state = AppState::default();
        assert_eq!(state.theme_id, DEFAULT_THEME_ID);
        assert_eq!(state.window_opacity, MAX_OPACITY);
        assert_eq!(state.window_mode, DEFAULT_WINDOW_MODE);
        assert!(state.total_enabled);
        assert!(state.always_on_top);
        assert!(state.windows.is_empty());
    }

    #[test]
    fn geometry_reads_both_the_new_and_the_legacy_shape() {
        let modern: Geometry =
            serde_json::from_str(r#"{"x":5,"y":6,"width":620,"height":340}"#).unwrap();
        let legacy: Geometry = serde_json::from_str("[5, 6, 620, 340]").unwrap();
        assert_eq!(modern, legacy);
        assert_eq!(
            modern,
            Geometry {
                x: 5,
                y: 6,
                width: 620,
                height: 340
            }
        );
    }

    #[test]
    fn a_pyside_state_file_still_loads() {
        // Field-for-field what the Python version wrote, geometry arrays and all.
        let json = r#"{
            "windows": [{"window_id": "abc", "title": "Calculator 1", "editor_text": "1+1"}],
            "history": ["1+1"],
            "theme_id": "nord",
            "startup_initialized": true,
            "window_opacity": 0.96,
            "window_mode": "previous",
            "last_active_window_id": "abc",
            "window_geometries": {"abc": [1043, 58, 760, 589]},
            "total_enabled": false
        }"#;
        let state: AppState = serde_json::from_str::<AppState>(json).unwrap().normalized();
        assert_eq!(state.windows.len(), 1);
        assert_eq!(state.history, vec!["1+1".to_string()]);
        assert_eq!(state.theme_id, "nord");
        assert_eq!(state.window_opacity, 0.96);
        assert!(!state.total_enabled);
        assert_eq!(
            state.window_geometries["abc"],
            Geometry {
                x: 1043,
                y: 58,
                width: 760,
                height: 589
            }
        );
        // Not present in the old file, so it takes the default.
        assert!(state.always_on_top);
    }

    #[test]
    fn normalisation_trims_history_and_bad_geometry() {
        let mut state = AppState {
            history: (0..MAX_HISTORY_ITEMS + 25).map(|n| n.to_string()).collect(),
            ..AppState::default()
        };
        state.history.push("   ".to_string());
        state.window_geometries.insert(
            "broken".to_string(),
            Geometry {
                x: 0,
                y: 0,
                width: 0,
                height: 100,
            },
        );
        state.window_geometries.insert(
            "fine".to_string(),
            Geometry {
                x: 10,
                y: 20,
                width: 620,
                height: 340,
            },
        );

        let state = state.normalized();
        assert_eq!(state.history.len(), MAX_HISTORY_ITEMS);
        assert_eq!(state.history.last().unwrap(), "524");
        assert!(!state.window_geometries.contains_key("broken"));
        assert!(state.window_geometries.contains_key("fine"));
    }
}
