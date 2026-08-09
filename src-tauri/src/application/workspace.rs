//! Multi-window workspace: which windows exist, what they contain, the shared
//! command history and the user's preferences. Platform-independent, so the
//! Tauri layer only has to render what it says.

use std::collections::HashMap;

use uuid::Uuid;

use crate::core::calculator::CalculatorEvaluator;
use crate::core::models::{
    normalize_opacity, normalize_window_mode, AppState, Geometry, WindowState, MAX_HISTORY_ITEMS,
    WINDOW_MODE_NEW, WINDOW_MODE_PREVIOUS,
};
use crate::core::themes::{get_theme, DEFAULT_THEME_ID};

pub struct WorkspaceService {
    evaluator: CalculatorEvaluator,
    windows: HashMap<String, WindowState>,
    window_order: Vec<String>,
    focus_history: Vec<String>,
    window_counter: usize,

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

impl WorkspaceService {
    pub fn new(evaluator: CalculatorEvaluator, initial_state: AppState) -> Self {
        let state = initial_state.normalized();
        let mut workspace = Self {
            evaluator,
            windows: HashMap::new(),
            window_order: Vec::new(),
            focus_history: Vec::new(),
            window_counter: 0,
            history: state.history,
            theme_id: if state.theme_id.is_empty() {
                DEFAULT_THEME_ID.to_string()
            } else {
                get_theme(&state.theme_id).theme_id.to_string()
            },
            startup_initialized: state.startup_initialized,
            window_opacity: normalize_opacity(state.window_opacity),
            window_mode: normalize_window_mode(&state.window_mode),
            last_active_window_id: state.last_active_window_id,
            window_geometries: state.window_geometries,
            total_enabled: state.total_enabled,
            always_on_top: state.always_on_top,
        };

        if state.windows.is_empty() {
            workspace.create_window();
        } else {
            // Seed the counter past the restored titles so the next window
            // does not reuse "Calculator 1".
            workspace.window_counter = state.windows.len();
            for window in state.windows {
                workspace.register_window(window);
            }
        }

        workspace
    }

    fn register_window(&mut self, window: WindowState) {
        let title = if window.title.is_empty() {
            self.next_window_title()
        } else {
            window.title
        };
        let window = WindowState {
            window_id: window.window_id,
            title,
            editor_text: window.editor_text,
        };
        if !self.window_order.contains(&window.window_id) {
            self.window_order.push(window.window_id.clone());
        }
        self.windows.insert(window.window_id.clone(), window);
    }

    fn next_window_title(&mut self) -> String {
        self.window_counter += 1;
        format!("Calculator {}", self.window_counter)
    }

    pub fn create_window(&mut self) -> WindowState {
        let window_id: String = Uuid::new_v4()
            .simple()
            .to_string()
            .chars()
            .take(10)
            .collect();
        let window = WindowState {
            window_id,
            title: self.next_window_title(),
            editor_text: String::new(),
        };
        let id = window.window_id.clone();
        self.register_window(window);
        self.windows[&id].clone()
    }

    pub fn window_states(&self) -> Vec<WindowState> {
        self.window_order
            .iter()
            .filter_map(|id| self.windows.get(id).cloned())
            .collect()
    }

    pub fn window_title(&self, window_id: &str) -> Option<String> {
        self.windows
            .get(window_id)
            .map(|window| window.title.clone())
    }

    pub fn window_text(&self, window_id: &str) -> Option<String> {
        self.windows
            .get(window_id)
            .map(|window| window.editor_text.clone())
    }

    /// Store the text, fold it into the history and evaluate it.
    pub fn evaluate_window(&mut self, window_id: &str, editor_text: &str) -> Vec<String> {
        if let Some(window) = self.windows.get_mut(window_id) {
            window.editor_text = editor_text.to_string();
        }
        let lines: Vec<String> = editor_text.lines().map(str::to_string).collect();
        self.record_history(&lines);
        self.evaluator.evaluate_lines(&lines)
    }

    /// Re-evaluate what a window already holds, without touching the history.
    pub fn evaluate_window_text(&self, window_id: &str) -> Option<Vec<String>> {
        let window = self.windows.get(window_id)?;
        let lines: Vec<String> = window.editor_text.lines().map(str::to_string).collect();
        Some(self.evaluator.evaluate_lines(&lines))
    }

    pub fn total_for(&self, results: &[String]) -> Option<String> {
        if !self.total_enabled {
            return None;
        }
        self.evaluator
            .sum_results(results)
            .map(crate::core::value::format_number)
    }

    pub fn set_window_text(&mut self, window_id: &str, editor_text: &str) {
        if let Some(window) = self.windows.get_mut(window_id) {
            window.editor_text = editor_text.to_string();
        }
    }

    pub fn set_theme(&mut self, theme_id: &str) -> String {
        self.theme_id = get_theme(theme_id).theme_id.to_string();
        self.theme_id.clone()
    }

    pub fn set_window_opacity(&mut self, opacity: f64) -> f64 {
        self.window_opacity = normalize_opacity(opacity);
        self.window_opacity
    }

    pub fn set_window_mode(&mut self, mode: &str) -> String {
        self.window_mode = normalize_window_mode(mode);
        self.window_mode.clone()
    }

    pub fn set_total_enabled(&mut self, enabled: bool) -> bool {
        self.total_enabled = enabled;
        enabled
    }

    pub fn set_always_on_top(&mut self, enabled: bool) -> bool {
        self.always_on_top = enabled;
        enabled
    }

    /// Which windows should be on screen for the given start-up mode:
    /// `previous` restores the last focused one, `new` starts empty, `both`
    /// restores everything.
    pub fn active_window_states(&self, mode: Option<&str>) -> Vec<WindowState> {
        let effective = match mode {
            Some(mode) => normalize_window_mode(mode),
            None => self.window_mode.clone(),
        };
        if effective == WINDOW_MODE_NEW {
            return Vec::new();
        }
        let ordered = self.window_states();
        if effective == WINDOW_MODE_PREVIOUS {
            if ordered.is_empty() {
                return Vec::new();
            }
            if let Some(active) = &self.last_active_window_id {
                if let Some(window) = ordered.iter().find(|w| &w.window_id == active) {
                    return vec![window.clone()];
                }
            }
            return ordered[ordered.len() - 1..].to_vec();
        }
        ordered
    }

    pub fn set_last_active_window(&mut self, window_id: Option<&str>) {
        if let Some(id) = window_id {
            if !self.windows.contains_key(id) {
                return;
            }
            if Some(id) != self.last_active_window_id.as_deref() {
                self.focus_history.retain(|known| known != id);
                self.focus_history.insert(0, id.to_string());
            }
        }
        self.last_active_window_id = window_id.map(str::to_string);
    }

    /// Drop a window from the focus history; if it was the active one, fall
    /// back to whatever was focused before it.
    pub fn release_window(&mut self, window_id: &str) {
        self.focus_history.retain(|known| known != window_id);
        if self.last_active_window_id.as_deref() == Some(window_id) {
            self.last_active_window_id = Some(
                self.focus_history
                    .first()
                    .cloned()
                    .unwrap_or_else(|| window_id.to_string()),
            );
        }
    }

    /// Forget a window entirely: its text, its place in the order and its
    /// saved geometry. Unlike [`release_window`](Self::release_window) this is
    /// the "closed for good" path, and it is what stops the saved list growing
    /// forever the way it did under the PySide6 version.
    pub fn remove_window(&mut self, window_id: &str) {
        self.windows.remove(window_id);
        self.window_order.retain(|known| known != window_id);
        self.focus_history.retain(|known| known != window_id);
        self.window_geometries.remove(window_id);
        if self.last_active_window_id.as_deref() == Some(window_id) {
            self.last_active_window_id = self.focus_history.first().cloned();
        }
    }

    pub fn window_count(&self) -> usize {
        self.windows.len()
    }

    pub fn get_window_geometry(&self, window_id: &str) -> Option<Geometry> {
        self.window_geometries.get(window_id).copied()
    }

    pub fn set_window_geometry(&mut self, window_id: &str, geometry: Geometry) {
        if !self.windows.contains_key(window_id) {
            return;
        }
        self.window_geometries
            .insert(window_id.to_string(), geometry);
    }

    pub fn cleanup_window_geometries(&mut self) {
        let saved = std::mem::take(&mut self.window_geometries);
        self.window_geometries = saved
            .into_iter()
            .filter(|(id, _)| self.windows.contains_key(id))
            .collect();
    }

    /// Drop every saved window and keep a single replacement, used by the
    /// "start fresh each time" window mode.
    pub fn replace_windows_with(&mut self, window: WindowState) {
        self.windows.clear();
        self.window_order.clear();
        self.focus_history.clear();
        let id = window.window_id.clone();
        self.register_window(window);
        self.last_active_window_id = Some(id);
    }

    fn record_history(&mut self, lines: &[String]) {
        for line in lines {
            let command = line.trim();
            if command.is_empty() {
                continue;
            }
            if self.history.last().map(String::as_str) == Some(command) {
                continue;
            }
            self.history.push(command.to_string());
        }
        if self.history.len() > MAX_HISTORY_ITEMS {
            self.history = self.history[self.history.len() - MAX_HISTORY_ITEMS..].to_vec();
        }
    }

    pub fn clear_history(&mut self) {
        self.history.clear();
    }

    pub fn snapshot(&self) -> AppState {
        AppState {
            windows: self.window_states(),
            history: self.history.clone(),
            theme_id: self.theme_id.clone(),
            startup_initialized: self.startup_initialized,
            window_opacity: self.window_opacity,
            window_mode: self.window_mode.clone(),
            last_active_window_id: self.last_active_window_id.clone(),
            window_geometries: self.window_geometries.clone(),
            total_enabled: self.total_enabled,
            always_on_top: self.always_on_top,
        }
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use super::*;
    use crate::core::calculator::CurrencyConverter;

    struct NoCurrency;

    impl CurrencyConverter for NoCurrency {
        fn convert(&self, _amount: f64, _from: &str, _to: &str) -> Result<f64, String> {
            Err("offline".to_string())
        }
    }

    fn make_workspace(state: AppState) -> WorkspaceService {
        WorkspaceService::new(CalculatorEvaluator::new(Arc::new(NoCurrency)), state)
    }

    fn saved_window(id: &str, title: &str, text: &str) -> WindowState {
        WindowState {
            window_id: id.to_string(),
            title: title.to_string(),
            editor_text: text.to_string(),
        }
    }

    #[test]
    fn starts_with_one_window_when_state_is_empty() {
        let workspace = make_workspace(AppState::default());
        let windows = workspace.window_states();
        assert_eq!(windows.len(), 1);
        assert_eq!(windows[0].title, "Calculator 1");
    }

    #[test]
    fn restores_saved_windows_in_order() {
        let workspace = make_workspace(AppState {
            windows: vec![
                saved_window("a", "First", "1+1"),
                saved_window("b", "Second", "2+2"),
            ],
            ..AppState::default()
        });
        let titles: Vec<String> = workspace
            .window_states()
            .into_iter()
            .map(|window| window.title)
            .collect();
        assert_eq!(titles, vec!["First", "Second"]);
    }

    #[test]
    fn new_windows_do_not_reuse_restored_titles() {
        let mut workspace = make_workspace(AppState {
            windows: vec![
                saved_window("a", "Calculator 1", ""),
                saved_window("b", "Calculator 2", ""),
            ],
            ..AppState::default()
        });
        assert_eq!(workspace.create_window().title, "Calculator 3");
    }

    #[test]
    fn evaluating_a_window_stores_its_text() {
        let mut workspace = make_workspace(AppState::default());
        let id = workspace.window_states()[0].window_id.clone();
        let results = workspace.evaluate_window(&id, "x = 2\nx * 3");
        assert_eq!(results, vec!["", "6"]);
        assert_eq!(workspace.window_text(&id).unwrap(), "x = 2\nx * 3");
    }

    #[test]
    fn history_records_commands_without_consecutive_duplicates() {
        let mut workspace = make_workspace(AppState::default());
        let id = workspace.window_states()[0].window_id.clone();
        workspace.evaluate_window(&id, "1 + 1\n\n1 + 1\n2 + 2");
        assert_eq!(workspace.history, vec!["1 + 1", "2 + 2"]);
    }

    #[test]
    fn history_is_capped() {
        let mut workspace = make_workspace(AppState {
            history: (0..MAX_HISTORY_ITEMS).map(|n| n.to_string()).collect(),
            ..AppState::default()
        });
        let id = workspace.window_states()[0].window_id.clone();
        workspace.evaluate_window(&id, "9991\n9992");
        assert_eq!(workspace.history.len(), MAX_HISTORY_ITEMS);
        assert_eq!(workspace.history.last().unwrap(), "9992");
    }

    #[test]
    fn clearing_history_empties_it() {
        let mut workspace = make_workspace(AppState {
            history: vec!["1 + 1".to_string()],
            ..AppState::default()
        });
        workspace.clear_history();
        assert!(workspace.history.is_empty());
    }

    #[test]
    fn totals_follow_the_toggle() {
        let mut workspace = make_workspace(AppState::default());
        let results = vec!["1".to_string(), "2".to_string()];
        assert_eq!(workspace.total_for(&results), Some("3".to_string()));
        workspace.set_total_enabled(false);
        assert_eq!(workspace.total_for(&results), None);
    }

    #[test]
    fn window_mode_new_shows_nothing_saved() {
        let workspace = make_workspace(AppState {
            windows: vec![saved_window("a", "First", "")],
            ..AppState::default()
        });
        assert!(workspace.active_window_states(Some("new")).is_empty());
    }

    #[test]
    fn window_mode_previous_prefers_the_last_active_window() {
        let workspace = make_workspace(AppState {
            windows: vec![
                saved_window("a", "First", ""),
                saved_window("b", "Second", ""),
            ],
            last_active_window_id: Some("a".to_string()),
            ..AppState::default()
        });
        let active = workspace.active_window_states(Some("previous"));
        assert_eq!(active.len(), 1);
        assert_eq!(active[0].window_id, "a");
    }

    #[test]
    fn window_mode_previous_falls_back_to_the_newest_window() {
        let workspace = make_workspace(AppState {
            windows: vec![
                saved_window("a", "First", ""),
                saved_window("b", "Second", ""),
            ],
            ..AppState::default()
        });
        let active = workspace.active_window_states(Some("previous"));
        assert_eq!(active[0].window_id, "b");
    }

    #[test]
    fn window_mode_both_shows_everything() {
        let workspace = make_workspace(AppState {
            windows: vec![
                saved_window("a", "First", ""),
                saved_window("b", "Second", ""),
            ],
            ..AppState::default()
        });
        assert_eq!(workspace.active_window_states(Some("both")).len(), 2);
    }

    #[test]
    fn releasing_the_active_window_falls_back_to_the_previous_focus() {
        let mut workspace = make_workspace(AppState {
            windows: vec![
                saved_window("a", "First", ""),
                saved_window("b", "Second", ""),
            ],
            ..AppState::default()
        });
        workspace.set_last_active_window(Some("a"));
        workspace.set_last_active_window(Some("b"));
        workspace.release_window("b");
        assert_eq!(workspace.last_active_window_id.as_deref(), Some("a"));
    }

    #[test]
    fn unknown_windows_never_become_active() {
        let mut workspace = make_workspace(AppState::default());
        workspace.set_last_active_window(Some("nope"));
        assert_eq!(workspace.last_active_window_id, None);
    }

    #[test]
    fn removing_a_window_forgets_everything_about_it() {
        let mut workspace = make_workspace(AppState {
            windows: vec![
                saved_window("a", "First", "1+1"),
                saved_window("b", "Second", "2+2"),
            ],
            ..AppState::default()
        });
        workspace.set_window_geometry(
            "b",
            Geometry {
                x: 1,
                y: 2,
                width: 620,
                height: 340,
            },
        );
        workspace.set_last_active_window(Some("a"));
        workspace.set_last_active_window(Some("b"));

        workspace.remove_window("b");

        assert_eq!(workspace.window_count(), 1);
        assert_eq!(workspace.window_states()[0].window_id, "a");
        assert_eq!(workspace.window_text("b"), None);
        assert_eq!(workspace.get_window_geometry("b"), None);
        // Focus falls back to the window that was active before it.
        assert_eq!(workspace.last_active_window_id.as_deref(), Some("a"));
        assert!(!workspace.snapshot().window_geometries.contains_key("b"));
    }

    #[test]
    fn removing_the_only_window_leaves_no_active_id() {
        let mut workspace = make_workspace(AppState::default());
        let id = workspace.window_states()[0].window_id.clone();
        workspace.set_last_active_window(Some(&id));
        workspace.remove_window(&id);
        assert_eq!(workspace.window_count(), 0);
        assert_eq!(workspace.last_active_window_id, None);
    }

    #[test]
    fn geometry_is_only_kept_for_live_windows() {
        let mut workspace = make_workspace(AppState::default());
        let id = workspace.window_states()[0].window_id.clone();
        let geometry = Geometry {
            x: 1,
            y: 2,
            width: 620,
            height: 340,
        };
        workspace.set_window_geometry(&id, geometry);
        workspace.set_window_geometry("ghost", geometry);
        assert_eq!(workspace.get_window_geometry(&id), Some(geometry));
        assert_eq!(workspace.get_window_geometry("ghost"), None);
    }

    #[test]
    fn cleanup_drops_geometry_for_vanished_windows() {
        let mut workspace = make_workspace(AppState::default());
        let geometry = Geometry {
            x: 1,
            y: 2,
            width: 620,
            height: 340,
        };
        workspace
            .window_geometries
            .insert("ghost".to_string(), geometry);
        workspace.cleanup_window_geometries();
        assert!(!workspace.window_geometries.contains_key("ghost"));
    }

    #[test]
    fn replacing_windows_leaves_exactly_one() {
        let mut workspace = make_workspace(AppState {
            windows: vec![
                saved_window("a", "First", ""),
                saved_window("b", "Second", ""),
            ],
            ..AppState::default()
        });
        workspace.replace_windows_with(saved_window("c", "Fresh", ""));
        let windows = workspace.window_states();
        assert_eq!(windows.len(), 1);
        assert_eq!(windows[0].window_id, "c");
        assert_eq!(workspace.last_active_window_id.as_deref(), Some("c"));
    }

    #[test]
    fn preferences_are_normalised_on_the_way_in_and_out() {
        let mut workspace = make_workspace(AppState::default());
        assert_eq!(workspace.set_theme("nope"), "monokai");
        assert_eq!(workspace.set_theme("nord"), "nord");
        assert_eq!(workspace.set_window_opacity(5.0), 1.0);
        assert_eq!(workspace.set_window_opacity(0.6), 0.6);
        assert_eq!(workspace.set_window_mode("sideways"), "both");
        assert_eq!(workspace.set_window_mode("new"), "new");
    }

    #[test]
    fn snapshot_round_trips_through_state() {
        let mut workspace = make_workspace(AppState::default());
        let id = workspace.window_states()[0].window_id.clone();
        workspace.evaluate_window(&id, "2 + 2");
        workspace.set_theme("graphite");
        workspace.set_window_opacity(0.7);

        let snapshot = workspace.snapshot();
        assert_eq!(snapshot.theme_id, "graphite");
        assert_eq!(snapshot.window_opacity, 0.7);
        assert_eq!(snapshot.windows[0].editor_text, "2 + 2");
        assert_eq!(snapshot.history, vec!["2 + 2"]);

        let restored = make_workspace(snapshot.clone());
        assert_eq!(restored.snapshot().windows, snapshot.windows);
        assert_eq!(restored.theme_id, "graphite");
    }
}
