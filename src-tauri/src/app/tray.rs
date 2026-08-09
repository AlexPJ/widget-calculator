//! System tray icon and its menu. The menu is rebuilt whenever the list of
//! windows or the selected theme changes, since Tauri menus are immutable.

use tauri::menu::{CheckMenuItem, Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager, Wry};
use tauri_plugin_autostart::ManagerExt;

use crate::core::themes::all_themes;

use super::state::AppContext;
use super::windows;

const TRAY_ID: &str = "main-tray";

pub fn build(app: &AppHandle) -> tauri::Result<()> {
    let menu = build_menu(app)?;
    TrayIconBuilder::with_id(TRAY_ID)
        .icon(
            app.default_window_icon()
                .cloned()
                .ok_or_else(|| tauri::Error::AssetNotFound("default window icon".into()))?,
        )
        .tooltip("Widget Calculator")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(handle_menu_event)
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                toggle_primary_window(tray.app_handle());
            }
        })
        .build(app)?;
    Ok(())
}

/// Rebuild the menu in place so the Windows and Themes submenus stay current.
pub fn rebuild_menu(app: &AppHandle) {
    let Some(tray) = app.tray_by_id(TRAY_ID) else {
        return;
    };
    if let Ok(menu) = build_menu(app) {
        let _ = tray.set_menu(Some(menu));
    }
}

fn build_menu(app: &AppHandle) -> tauri::Result<Menu<Wry>> {
    let (window_states, theme_id) = {
        let context = app.state::<AppContext>();
        let workspace = context.workspace();
        (workspace.window_states(), workspace.theme_id.clone())
    };

    let new_window = MenuItem::with_id(app, "new", "New calculator window", true, None::<&str>)?;
    let settings = MenuItem::with_id(app, "settings", "Settings...", true, None::<&str>)?;

    let show_all = MenuItem::with_id(app, "windows:all", "Show all windows", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let mut window_items: Vec<MenuItem<Wry>> = Vec::new();
    for state in &window_states {
        window_items.push(MenuItem::with_id(
            app,
            format!("window:{}", state.window_id),
            &state.title,
            true,
            None::<&str>,
        )?);
    }
    let mut window_refs: Vec<&dyn tauri::menu::IsMenuItem<Wry>> = vec![&show_all, &separator];
    for item in &window_items {
        window_refs.push(item);
    }
    let windows_menu = Submenu::with_items(app, "Windows", true, &window_refs)?;

    let mut theme_items: Vec<CheckMenuItem<Wry>> = Vec::new();
    for theme in all_themes() {
        theme_items.push(CheckMenuItem::with_id(
            app,
            format!("theme:{}", theme.theme_id),
            theme.name,
            true,
            theme.theme_id == theme_id,
            None::<&str>,
        )?);
    }
    let theme_refs: Vec<&dyn tauri::menu::IsMenuItem<Wry>> = theme_items
        .iter()
        .map(|item| item as &dyn tauri::menu::IsMenuItem<Wry>)
        .collect();
    let themes_menu = Submenu::with_items(app, "Themes", true, &theme_refs)?;

    let history = MenuItem::with_id(app, "history", "Show command history", true, None::<&str>)?;
    let startup = CheckMenuItem::with_id(
        app,
        "startup",
        "Start when Windows boots",
        true,
        app.autolaunch().is_enabled().unwrap_or(false),
        None::<&str>,
    )?;
    let update = MenuItem::with_id(app, "update", "Check for updates", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

    Menu::with_items(
        app,
        &[
            &new_window,
            &settings,
            &windows_menu,
            &themes_menu,
            &PredefinedMenuItem::separator(app)?,
            &history,
            &startup,
            &update,
            &PredefinedMenuItem::separator(app)?,
            &quit,
        ],
    )
}

fn handle_menu_event(app: &AppHandle, event: tauri::menu::MenuEvent) {
    let id = event.id.as_ref();

    if let Some(window_id) = id.strip_prefix("window:") {
        windows::show(app, window_id);
        return;
    }
    if let Some(theme_id) = id.strip_prefix("theme:") {
        super::commands::apply_theme(app, theme_id);
        return;
    }

    match id {
        "new" => {
            let _ = windows::open_new(app);
        }
        "settings" => notify_focused(app, "menu:settings"),
        "history" => notify_focused(app, "menu:history"),
        "update" => notify_focused(app, "menu:check-updates"),
        "windows:all" => windows::show_all(app),
        "startup" => {
            let enabled = app.autolaunch().is_enabled().unwrap_or(false);
            super::commands::apply_startup(app, !enabled);
        }
        "quit" => super::commands::quit_app(app),
        _ => {}
    }
}

/// Bring a window forward and tell its UI to open a panel.
fn notify_focused(app: &AppHandle, event: &str) {
    let Some(window) = primary_window(app) else {
        return;
    };
    let _ = window.unminimize();
    let _ = window.show();
    let _ = window.set_focus();
    let _ = window.emit(event, ());
}

/// The window the user most recently used, falling back to any open window.
pub fn primary_window(app: &AppHandle) -> Option<tauri::WebviewWindow> {
    let last_active = {
        let context = app.state::<AppContext>();
        let workspace = context.workspace();
        workspace.last_active_window_id.clone()
    };
    if let Some(window_id) = last_active {
        if let Some(window) = app.get_webview_window(&windows::label_for(&window_id)) {
            return Some(window);
        }
    }
    app.webview_windows()
        .into_iter()
        .find(|(label, _)| windows::window_id_from_label(label).is_some())
        .map(|(_, window)| window)
}

fn toggle_primary_window(app: &AppHandle) {
    let Some(window) = primary_window(app) else {
        return;
    };
    if window.is_visible().unwrap_or(false) {
        let _ = window.hide();
    } else {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}
