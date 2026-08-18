#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;
mod application;
mod core;
mod infra;

use tauri_plugin_autostart::ManagerExt;

use app::state::AppContext;

/// Passed by the autostart entry so a boot-time launch stays in the tray.
const BACKGROUND_FLAG: &str = "--background";

fn main() {
    let start_hidden = std::env::args().any(|argument| argument == BACKGROUND_FLAG);

    tauri::Builder::default()
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec![BACKGROUND_FLAG]),
        ))
        .manage(AppContext::load())
        .invoke_handler(tauri::generate_handler![
            app::commands::bootstrap,
            app::commands::evaluate,
            app::commands::recompute,
            app::commands::set_theme,
            app::commands::set_opacity,
            app::commands::set_total_enabled,
            app::commands::set_always_on_top,
            app::commands::set_window_mode,
            app::commands::set_startup,
            app::commands::new_window,
            app::commands::show_all_windows,
            app::commands::get_history,
            app::commands::clear_history,
            app::commands::save_geometry,
            app::commands::store_text,
            app::commands::check_for_updates,
            app::commands::install_update,
            app::commands::quit,
        ])
        .setup(move |tauri_app| {
            let handle = tauri_app.handle().clone();

            configure_startup(&handle);
            app::windows::bootstrap(&handle, start_hidden)?;
            app::tray::build(&handle)?;
            app::state::spawn_state_writer(handle);

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("could not start Widget Calculator")
        .run(|_handle, event| {
            // Hiding the last window must not end the process: the tray icon
            // is what keeps the app reachable. An explicit quit carries an
            // exit code, and is allowed through.
            if let tauri::RunEvent::ExitRequested { code, api, .. } = event {
                if code.is_none() {
                    api.prevent_exit();
                }
            }
        });
}

/// Take over "start with Windows" from whatever was there before.
///
/// Retiring the PySide6 registry entry is driven by the registry itself rather
/// than a saved flag: finding the old entry is already proof the handover has
/// not happened, and removing it is what stops it happening twice. A flag would
/// only add a way for the two to disagree.
///
/// A fresh install is left opted *out*. Writing a `Run` entry nobody asked for
/// is both a surprise to the user and a heuristic that antivirus engines score
/// against unsigned binaries; the tray menu and the settings dialog are the
/// only things that turn it on.
fn configure_startup(app: &tauri::AppHandle) {
    if infra::legacy::remove_legacy_startup_entry()
        && !app.autolaunch().is_enabled().unwrap_or(false)
    {
        if let Err(error) = app.autolaunch().enable() {
            eprintln!("Could not carry the start-up setting over: {error}");
        }
    }
}
