//! Creating, restoring and tracking the calculator windows.
//!
//! Every window is a frameless, transparent webview whose label encodes the
//! workspace window id, so the UI can identify itself with nothing more than
//! `getCurrentWindow().label`.

use serde::Serialize;
use tauri::{
    AppHandle, Emitter, LogicalSize, Manager, PhysicalPosition, PhysicalSize, WebviewUrl,
    WebviewWindow, WebviewWindowBuilder, WindowEvent,
};

use crate::core::models::Geometry;

use super::state::AppContext;
use super::tray;

const LABEL_PREFIX: &str = "calc-";
const DEFAULT_WIDTH: f64 = 620.0;
const DEFAULT_HEIGHT: f64 = 340.0;
const MIN_WIDTH: f64 = 380.0;
const MIN_HEIGHT: f64 = 220.0;

pub fn label_for(window_id: &str) -> String {
    format!("{LABEL_PREFIX}{window_id}")
}

pub fn window_id_from_label(label: &str) -> Option<&str> {
    label.strip_prefix(LABEL_PREFIX)
}

/// Emit an event to every calculator window.
pub fn broadcast<S: Serialize + Clone>(app: &AppHandle, event: &str, payload: S) {
    let _ = app.emit(event, payload);
}

pub fn create(app: &AppHandle, window_id: &str, title: &str, visible: bool) -> tauri::Result<()> {
    let label = label_for(window_id);
    if app.get_webview_window(&label).is_some() {
        return Ok(());
    }

    let always_on_top = {
        let context = app.state::<AppContext>();
        let workspace = context.workspace();
        workspace.always_on_top
    };

    let window = WebviewWindowBuilder::new(app, &label, WebviewUrl::App("index.html".into()))
        .title(title)
        .inner_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        .min_inner_size(MIN_WIDTH, MIN_HEIGHT)
        .decorations(false)
        .transparent(true)
        .always_on_top(always_on_top)
        .skip_taskbar(false)
        .visible(false)
        .build()?;

    restore_geometry(app, &window, window_id);
    attach_events(app, &window, window_id);

    if visible {
        let _ = window.show();
        let _ = window.set_focus();
    }
    Ok(())
}

fn restore_geometry(app: &AppHandle, window: &WebviewWindow, window_id: &str) {
    let context = app.state::<AppContext>();
    let saved = context.workspace().get_window_geometry(window_id);
    let Some(geometry) = saved else {
        return;
    };

    let minimum = window
        .scale_factor()
        .map(|scale| LogicalSize::new(MIN_WIDTH, MIN_HEIGHT).to_physical::<u32>(scale))
        .unwrap_or(PhysicalSize::new(MIN_WIDTH as u32, MIN_HEIGHT as u32));
    if geometry.width < minimum.width || geometry.height < minimum.height {
        return;
    }
    if !is_on_screen(window, geometry) {
        return;
    }

    let _ = window.set_position(PhysicalPosition::new(geometry.x, geometry.y));
    let _ = window.set_size(PhysicalSize::new(geometry.width, geometry.height));
}

/// Windows saved on a monitor that is no longer attached would open off-screen.
fn is_on_screen(window: &WebviewWindow, geometry: Geometry) -> bool {
    let Ok(monitors) = window.available_monitors() else {
        return true;
    };
    if monitors.is_empty() {
        return true;
    }
    monitors.iter().any(|monitor| {
        let position = monitor.position();
        let size = monitor.size();
        let right = position.x + size.width as i32;
        let bottom = position.y + size.height as i32;
        geometry.x + geometry.width as i32 > position.x
            && geometry.x < right
            && geometry.y + geometry.height as i32 > position.y
            && geometry.y < bottom
    })
}

fn attach_events(app: &AppHandle, window: &WebviewWindow, window_id: &str) {
    let handle = app.clone();
    let id = window_id.to_string();
    let tracked = window.clone();

    window.on_window_event(move |event| match event {
        WindowEvent::CloseRequested { api, .. } => {
            let context = handle.state::<AppContext>();
            if context.workspace().window_count() <= 1 {
                // The last window only hides: its contents survive and the
                // tray still has something to reopen.
                api.prevent_close();
                let _ = tracked.hide();
                context.workspace().release_window(&id);
                context.save_soon();
            } else {
                // Any other window closes for good, so the saved list cannot
                // grow without bound.
                context.workspace().remove_window(&id);
                context.save_now();
                tray::rebuild_menu(&handle);
            }
        }
        WindowEvent::Focused(true) => {
            let context = handle.state::<AppContext>();
            context.workspace().set_last_active_window(Some(&id));
            context.save_soon();
        }
        WindowEvent::Moved(_) | WindowEvent::Resized(_) => {
            if tracked.is_minimized().unwrap_or(false) || tracked.is_maximized().unwrap_or(false) {
                return;
            }
            let (Ok(position), Ok(size)) = (tracked.outer_position(), tracked.inner_size()) else {
                return;
            };
            let context = handle.state::<AppContext>();
            context.workspace().set_window_geometry(
                &id,
                Geometry {
                    x: position.x,
                    y: position.y,
                    width: size.width,
                    height: size.height,
                },
            );
            context.save_soon();
        }
        _ => {}
    });
}

pub fn show(app: &AppHandle, window_id: &str) {
    if let Some(window) = app.get_webview_window(&label_for(window_id)) {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

pub fn show_all(app: &AppHandle) {
    for window in app.webview_windows().values() {
        let _ = window.unminimize();
        let _ = window.show();
    }
}

/// Recreate the windows the workspace says should be on screen at start-up.
pub fn bootstrap(app: &AppHandle, start_hidden: bool) -> tauri::Result<()> {
    let (mode, windows) = {
        let context = app.state::<AppContext>();
        let workspace = context.workspace();
        (
            workspace.window_mode.clone(),
            workspace.active_window_states(None),
        )
    };

    if mode == crate::core::models::WINDOW_MODE_NEW {
        let fresh = {
            let context = app.state::<AppContext>();
            let mut workspace = context.workspace();
            let fresh = workspace.create_window();
            workspace.replace_windows_with(fresh.clone());
            fresh
        };
        create(app, &fresh.window_id, &fresh.title, !start_hidden)?;
    } else {
        for window in windows {
            create(app, &window.window_id, &window.title, !start_hidden)?;
        }
    }

    {
        let context = app.state::<AppContext>();
        context.workspace().cleanup_window_geometries();
        context.save_soon();
    }
    Ok(())
}

/// Open a brand new calculator window. In "start fresh each time" mode this
/// replaces whatever was open, mirroring the previous behaviour.
pub fn open_new(app: &AppHandle) -> tauri::Result<()> {
    let mode = {
        let context = app.state::<AppContext>();
        let workspace = context.workspace();
        workspace.window_mode.clone()
    };

    if mode == crate::core::models::WINDOW_MODE_NEW {
        for (label, window) in app.webview_windows() {
            if window_id_from_label(&label).is_some() {
                let _ = window.destroy();
            }
        }
        let fresh = {
            let context = app.state::<AppContext>();
            let mut workspace = context.workspace();
            let fresh = workspace.create_window();
            workspace.replace_windows_with(fresh.clone());
            fresh
        };
        create(app, &fresh.window_id, &fresh.title, true)?;
    } else {
        let fresh = {
            let context = app.state::<AppContext>();
            let mut workspace = context.workspace();
            workspace.create_window()
        };
        create(app, &fresh.window_id, &fresh.title, true)?;
    }

    tray::rebuild_menu(app);
    let context = app.state::<AppContext>();
    context.save_soon();
    Ok(())
}

/// Apply the always-on-top preference to every open window.
pub fn apply_always_on_top(app: &AppHandle, enabled: bool) {
    for window in app.webview_windows().values() {
        let _ = window.set_always_on_top(enabled);
    }
}
