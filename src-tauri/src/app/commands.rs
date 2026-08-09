//! The commands the UI invokes, plus the shared actions the tray reuses.

use serde::Serialize;
use tauri::{AppHandle, Manager, WebviewWindow};
use tauri_plugin_autostart::ManagerExt;
use tauri_plugin_updater::UpdaterExt;

use crate::core::models::Geometry;
use crate::core::themes::{all_themes, get_theme, Theme};

use super::state::AppContext;
use super::{tray, windows};

/// Everything a freshly opened window needs to render itself.
#[derive(Serialize, Clone)]
pub struct Bootstrap {
    window_id: String,
    title: String,
    editor_text: String,
    theme: &'static Theme,
    themes: &'static [Theme],
    opacity: f64,
    total_enabled: bool,
    always_on_top: bool,
    window_mode: String,
    startup_enabled: bool,
    version: String,
}

#[derive(Serialize, Clone)]
pub struct Evaluation {
    results: Vec<String>,
    total: Option<String>,
}

#[derive(Serialize, Clone)]
pub struct UpdateSummary {
    version: String,
    current_version: String,
    notes: Option<String>,
}

fn window_id_of(window: &WebviewWindow) -> Result<String, String> {
    windows::window_id_from_label(window.label())
        .map(str::to_string)
        .ok_or_else(|| format!("Not a calculator window: {}", window.label()))
}

#[tauri::command]
pub fn bootstrap(app: AppHandle, window: WebviewWindow) -> Result<Bootstrap, String> {
    let window_id = window_id_of(&window)?;
    let context = app.state::<AppContext>();
    let workspace = context.workspace();

    let title = workspace
        .window_title(&window_id)
        .unwrap_or_else(|| "Calculator".to_string());

    Ok(Bootstrap {
        editor_text: workspace.window_text(&window_id).unwrap_or_default(),
        title,
        window_id,
        theme: get_theme(&workspace.theme_id),
        themes: all_themes(),
        opacity: workspace.window_opacity,
        total_enabled: workspace.total_enabled,
        always_on_top: workspace.always_on_top,
        window_mode: workspace.window_mode.clone(),
        startup_enabled: app.autolaunch().is_enabled().unwrap_or(false),
        version: app.package_info().version.to_string(),
    })
}

/// Async so the blocking currency lookup never runs on the UI thread.
#[tauri::command]
pub async fn evaluate(
    app: AppHandle,
    window: WebviewWindow,
    text: String,
) -> Result<Evaluation, String> {
    let window_id = window_id_of(&window)?;
    let context = app.state::<AppContext>();
    let mut workspace = context.workspace();
    let results = workspace.evaluate_window(&window_id, &text);
    let total = workspace.total_for(&results);
    drop(workspace);
    context.save_soon();
    Ok(Evaluation { results, total })
}

/// Re-run the text a window already holds. Unlike [`evaluate`] this does not
/// touch the command history, so refreshing after a settings change cannot
/// duplicate entries.
#[tauri::command]
pub async fn recompute(app: AppHandle, window: WebviewWindow) -> Result<Evaluation, String> {
    let window_id = window_id_of(&window)?;
    let context = app.state::<AppContext>();
    let workspace = context.workspace();
    let results = workspace
        .evaluate_window_text(&window_id)
        .ok_or_else(|| format!("Unknown window: {window_id}"))?;
    let total = workspace.total_for(&results);
    Ok(Evaluation { results, total })
}

#[tauri::command]
pub fn set_theme(app: AppHandle, theme_id: String) {
    apply_theme(&app, &theme_id);
}

pub fn apply_theme(app: &AppHandle, theme_id: &str) {
    let resolved = {
        let context = app.state::<AppContext>();
        let resolved = context.workspace().set_theme(theme_id);
        context.save_soon();
        resolved
    };
    windows::broadcast(app, "theme-changed", get_theme(&resolved));
    tray::rebuild_menu(app);
}

#[tauri::command]
pub fn set_opacity(app: AppHandle, opacity: f64) -> f64 {
    let context = app.state::<AppContext>();
    let resolved = context.workspace().set_window_opacity(opacity);
    context.save_soon();
    windows::broadcast(&app, "opacity-changed", resolved);
    resolved
}

#[tauri::command]
pub fn set_total_enabled(app: AppHandle, enabled: bool) -> bool {
    let context = app.state::<AppContext>();
    let resolved = context.workspace().set_total_enabled(enabled);
    context.save_soon();
    windows::broadcast(&app, "total-changed", resolved);
    resolved
}

#[tauri::command]
pub fn set_always_on_top(app: AppHandle, enabled: bool) -> bool {
    let context = app.state::<AppContext>();
    let resolved = context.workspace().set_always_on_top(enabled);
    context.save_soon();
    windows::apply_always_on_top(&app, resolved);
    windows::broadcast(&app, "always-on-top-changed", resolved);
    resolved
}

#[tauri::command]
pub fn set_window_mode(app: AppHandle, mode: String) -> String {
    let context = app.state::<AppContext>();
    let resolved = context.workspace().set_window_mode(&mode);
    context.save_soon();
    windows::broadcast(&app, "window-mode-changed", resolved.clone());
    resolved
}

#[tauri::command]
pub fn set_startup(app: AppHandle, enabled: bool) -> bool {
    apply_startup(&app, enabled)
}

pub fn apply_startup(app: &AppHandle, enabled: bool) -> bool {
    let result = if enabled {
        app.autolaunch().enable()
    } else {
        app.autolaunch().disable()
    };
    if let Err(error) = result {
        eprintln!("Could not update the startup entry: {error}");
    }

    let actual = app.autolaunch().is_enabled().unwrap_or(false);
    {
        let context = app.state::<AppContext>();
        context.workspace().startup_initialized = true;
        context.save_soon();
    }
    windows::broadcast(app, "startup-changed", actual);
    tray::rebuild_menu(app);
    actual
}

#[tauri::command]
pub fn new_window(app: AppHandle) -> Result<(), String> {
    windows::open_new(&app).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn show_all_windows(app: AppHandle) {
    windows::show_all(&app);
}

#[tauri::command]
pub fn get_history(app: AppHandle) -> Vec<String> {
    let context = app.state::<AppContext>();
    let workspace = context.workspace();
    workspace.history.clone()
}

#[tauri::command]
pub fn clear_history(app: AppHandle) {
    let context = app.state::<AppContext>();
    context.workspace().clear_history();
    context.save_now();
    windows::broadcast(&app, "history-changed", Vec::<String>::new());
}

#[tauri::command]
pub fn save_geometry(app: AppHandle, window: WebviewWindow) -> Result<(), String> {
    let window_id = window_id_of(&window)?;
    let position = window.outer_position().map_err(|e| e.to_string())?;
    let size = window.inner_size().map_err(|e| e.to_string())?;
    let context = app.state::<AppContext>();
    context.workspace().set_window_geometry(
        &window_id,
        Geometry {
            x: position.x,
            y: position.y,
            width: size.width,
            height: size.height,
        },
    );
    context.save_soon();
    Ok(())
}

#[tauri::command]
pub async fn check_for_updates(app: AppHandle) -> Result<Option<UpdateSummary>, String> {
    let updater = app.updater().map_err(|error| error.to_string())?;
    let update = updater.check().await.map_err(|error| error.to_string())?;
    Ok(update.map(|update| UpdateSummary {
        version: update.version.clone(),
        current_version: update.current_version.clone(),
        notes: update.body.clone(),
    }))
}

#[tauri::command]
pub async fn install_update(app: AppHandle) -> Result<(), String> {
    let updater = app.updater().map_err(|error| error.to_string())?;
    let update = updater
        .check()
        .await
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "No update available".to_string())?;

    update
        .download_and_install(|_chunk, _total| {}, || {})
        .await
        .map_err(|error| error.to_string())?;

    {
        let context = app.state::<AppContext>();
        context.save_now();
    }
    app.restart()
}

#[tauri::command]
pub fn quit(app: AppHandle) {
    quit_app(&app);
}

pub fn quit_app(app: &AppHandle) {
    {
        let context = app.state::<AppContext>();
        for (label, window) in app.webview_windows() {
            let Some(window_id) = windows::window_id_from_label(&label) else {
                continue;
            };
            if let (Ok(position), Ok(size)) = (window.outer_position(), window.inner_size()) {
                context.workspace().set_window_geometry(
                    window_id,
                    Geometry {
                        x: position.x,
                        y: position.y,
                        width: size.width,
                        height: size.height,
                    },
                );
            }
        }
        context.save_now();
    }
    app.exit(0);
}

/// Push the current editor text into the workspace without evaluating, so a
/// window that is closing does not lose the last keystrokes.
#[tauri::command]
pub fn store_text(app: AppHandle, window: WebviewWindow, text: String) -> Result<(), String> {
    let window_id = window_id_of(&window)?;
    let context = app.state::<AppContext>();
    context.workspace().set_window_text(&window_id, &text);
    context.save_soon();
    Ok(())
}
