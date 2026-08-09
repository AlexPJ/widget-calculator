//! Persistence for the whole workspace.
//!
//! Keeps the Python version's location and JSON shape
//! (`%APPDATA%/WidgetCalculatorWidget/state.json`) so an existing install
//! carries its windows, history and theme straight over.

use std::path::PathBuf;

use crate::core::models::AppState;

const APP_DIR_NAME: &str = "WidgetCalculatorWidget";
const STATE_FILE_NAME: &str = "state.json";

pub struct JsonStateStore {
    state_path: PathBuf,
}

impl JsonStateStore {
    pub fn new() -> Self {
        Self::with_base_dir(default_dir())
    }

    pub fn with_base_dir(base_dir: PathBuf) -> Self {
        let _ = std::fs::create_dir_all(&base_dir);
        Self {
            state_path: base_dir.join(STATE_FILE_NAME),
        }
    }

    #[cfg(test)]
    pub fn path(&self) -> &std::path::Path {
        &self.state_path
    }

    /// Never fails: an unreadable or corrupt file yields the default state.
    pub fn load(&self) -> AppState {
        std::fs::read(&self.state_path)
            .ok()
            .and_then(|bytes| serde_json::from_slice::<AppState>(&bytes).ok())
            .unwrap_or_default()
            .normalized()
    }

    /// Written to a sibling temp file first so a crash mid-write cannot leave
    /// a truncated state behind.
    pub fn save(&self, state: &AppState) -> Result<(), String> {
        let json = serde_json::to_vec_pretty(state).map_err(|error| error.to_string())?;
        let temp_path = self.state_path.with_extension("tmp");
        std::fs::write(&temp_path, json).map_err(|error| error.to_string())?;
        std::fs::rename(&temp_path, &self.state_path).map_err(|error| error.to_string())
    }
}

impl Default for JsonStateStore {
    fn default() -> Self {
        Self::new()
    }
}

fn default_dir() -> PathBuf {
    dirs::config_dir()
        .or_else(dirs::home_dir)
        .unwrap_or_else(|| PathBuf::from("."))
        .join(APP_DIR_NAME)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::models::{Geometry, WindowState, MAX_OPACITY};

    fn temp_store(name: &str) -> JsonStateStore {
        let dir = std::env::temp_dir().join(format!("widget-calc-test-{name}"));
        let _ = std::fs::remove_dir_all(&dir);
        JsonStateStore::with_base_dir(dir)
    }

    #[test]
    fn missing_file_loads_defaults() {
        let store = temp_store("missing");
        let state = store.load();
        assert_eq!(state, AppState::default());
    }

    #[test]
    fn corrupt_file_loads_defaults() {
        let store = temp_store("corrupt");
        std::fs::write(store.path(), b"{not json").unwrap();
        assert_eq!(store.load(), AppState::default());
    }

    #[test]
    fn round_trips_a_full_state() {
        let store = temp_store("roundtrip");
        let mut state = AppState {
            windows: vec![WindowState {
                window_id: "abc".to_string(),
                title: "Calculator 1".to_string(),
                editor_text: "1 + 1".to_string(),
            }],
            history: vec!["1 + 1".to_string()],
            theme_id: "nord".to_string(),
            startup_initialized: true,
            window_opacity: 0.8,
            window_mode: "previous".to_string(),
            last_active_window_id: Some("abc".to_string()),
            total_enabled: false,
            always_on_top: false,
            ..AppState::default()
        };
        state.window_geometries.insert(
            "abc".to_string(),
            Geometry {
                x: 5,
                y: 6,
                width: 620,
                height: 340,
            },
        );

        store.save(&state).unwrap();
        assert_eq!(store.load(), state);
    }

    #[test]
    fn partial_json_fills_in_defaults() {
        let store = temp_store("partial");
        std::fs::write(store.path(), br#"{"theme_id":"graphite"}"#).unwrap();
        let state = store.load();
        assert_eq!(state.theme_id, "graphite");
        assert_eq!(state.window_opacity, MAX_OPACITY);
        assert!(state.total_enabled);
    }

    #[test]
    fn loading_normalises_bad_values() {
        let store = temp_store("normalise");
        std::fs::write(
            store.path(),
            br#"{"window_opacity":9.0,"window_mode":"sideways","history":["a","  "]}"#,
        )
        .unwrap();
        let state = store.load();
        assert_eq!(state.window_opacity, MAX_OPACITY);
        assert_eq!(state.window_mode, "both");
        assert_eq!(state.history, vec!["a".to_string()]);
    }

    #[test]
    fn saving_leaves_no_temp_file_behind() {
        let store = temp_store("temp-cleanup");
        store.save(&AppState::default()).unwrap();
        assert!(store.path().exists());
        assert!(!store.path().with_extension("tmp").exists());
    }
}
