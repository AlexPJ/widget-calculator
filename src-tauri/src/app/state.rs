//! Shared runtime state, plus the debounced writer that keeps `state.json`
//! current without touching the disk on every keystroke.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, MutexGuard};
use std::time::Duration;

use crate::application::workspace::WorkspaceService;
use crate::core::calculator::CalculatorEvaluator;
use crate::infra::currency::OpenExchangeRateCurrencyConverter;
use crate::infra::state_store::JsonStateStore;

const SAVE_INTERVAL: Duration = Duration::from_millis(1500);

pub struct AppContext {
    workspace: Mutex<WorkspaceService>,
    store: JsonStateStore,
    dirty: AtomicBool,
}

impl AppContext {
    pub fn load() -> Self {
        let store = JsonStateStore::new();
        let state = store.load();
        let evaluator =
            CalculatorEvaluator::new(Arc::new(OpenExchangeRateCurrencyConverter::new()));
        Self {
            workspace: Mutex::new(WorkspaceService::new(evaluator, state)),
            store,
            dirty: AtomicBool::new(false),
        }
    }

    /// A poisoned lock would mean a panic while holding it; recovering the
    /// guard keeps the app usable instead of cascading the panic.
    pub fn workspace(&self) -> MutexGuard<'_, WorkspaceService> {
        self.workspace
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
    }

    /// Mark the state as needing a write; the background writer picks it up.
    pub fn save_soon(&self) {
        self.dirty.store(true, Ordering::Relaxed);
    }

    pub fn save_now(&self) {
        self.dirty.store(false, Ordering::Relaxed);
        let snapshot = self.workspace().snapshot();
        if let Err(error) = self.store.save(&snapshot) {
            eprintln!("Could not save state: {error}");
        }
    }

    fn flush_if_dirty(&self) {
        if self.dirty.swap(false, Ordering::Relaxed) {
            let snapshot = self.workspace().snapshot();
            if let Err(error) = self.store.save(&snapshot) {
                eprintln!("Could not save state: {error}");
            }
        }
    }
}

/// Start the background writer. It owns nothing but the app handle, so it
/// exits with the process.
pub fn spawn_state_writer(app: tauri::AppHandle) {
    std::thread::spawn(move || loop {
        std::thread::sleep(SAVE_INTERVAL);
        let context: tauri::State<'_, AppContext> = tauri::Manager::state(&app);
        context.flush_if_dirty();
    });
}
