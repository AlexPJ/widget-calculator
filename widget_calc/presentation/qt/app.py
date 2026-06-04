from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QEvent, QObject, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeyEvent
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from widget_calc.application.workspace import WorkspaceService
from widget_calc.domain.calculator import CalculatorEvaluator
from widget_calc.domain.models import WINDOW_MODE_NEW
from widget_calc.domain.themes import Theme, all_themes, get_theme
from widget_calc.infrastructure.currency_api import OpenExchangeRateCurrencyConverter
from widget_calc.infrastructure.startup_registry import WindowsStartupRegistry
from widget_calc.infrastructure.state_store import JsonStateStore

from .calculator_icon import cached_app_icon
from .menu_bar import MenuActions, build_menu_bar
from .settings_dialog import SettingsDialog
from .window import CalculatorWindow

EVALUATE_DEBOUNCE_MS = 120
SAVE_DEBOUNCE_MS = 250


class AltKeyFilter(QObject):
    """Global event filter that shows/hides the active window's menu bar on Alt."""

    def __init__(self, controller: MultiWindowAppController) -> None:
        super().__init__()
        self._controller = controller

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if isinstance(event, QKeyEvent):
            if event.key() != Qt.Key.Key_Alt:
                return super().eventFilter(obj, event)
            window = self._controller._active_window()  # noqa: SLF001
            if window is None:
                return super().eventFilter(obj, event)
            if event.type() == QEvent.Type.KeyPress:
                window.show_menu_bar()
                return True
            if event.type() == QEvent.Type.KeyRelease:
                window.alt_released.emit()
                window._menu_hide_timer.start()  # noqa: SLF001
                return True
        return super().eventFilter(obj, event)


class MultiWindowAppController:
    def __init__(self, app: QApplication, start_hidden: bool) -> None:
        self.app = app
        self.state_store = JsonStateStore()
        initial_state = self.state_store.load()
        evaluator = CalculatorEvaluator(OpenExchangeRateCurrencyConverter())
        self.workspace = WorkspaceService(evaluator, initial_state)
        self.startup_registry = WindowsStartupRegistry()

        self.windows: dict[str, CalculatorWindow] = {}
        self.eval_timers: dict[str, QTimer] = {}
        self.theme_actions: dict[str, QAction] = {}
        self.window_menus: dict[str, MenuActions] = {}
        self.current_theme: Theme = get_theme(self.workspace.theme_id)
        self.current_opacity: float = self.workspace.window_opacity
        self.always_on_top: bool = True  # default for new windows
        self.window_mode: str = self.workspace.window_mode

        self._allow_close = False
        self._close_notice_shown = False
        self._settings_dialog: SettingsDialog | None = None

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._save_state)

        self._create_tray()
        self._bootstrap_windows(start_hidden)
        self._apply_theme(self.workspace.theme_id, persist=False)
        self._apply_startup_default()

        # Install Alt-key filter on the application
        self._alt_filter = AltKeyFilter(self)
        self.app.installEventFilter(self._alt_filter)

    def _active_window(self) -> CalculatorWindow | None:
        active = self.app.activeWindow()
        if isinstance(active, CalculatorWindow):
            return active
        for window in self.windows.values():
            if window.isActiveWindow():
                return window
        return next(iter(self.windows.values()), None)

    def _on_window_activated(self, window: CalculatorWindow) -> None:
        self.workspace.set_last_active_window(window.window_id)
        self._save_timer.start()

    def _on_geometry_changed(self, window: CalculatorWindow, x: int, y: int, w: int, h: int) -> None:
        self.workspace.set_window_geometry(window.window_id, x, y, w, h)
        self._save_timer.start()

    def _restore_geometry(self, window: CalculatorWindow) -> None:
        geom = self.workspace.get_window_geometry(window.window_id)
        if geom is None:
            return
        x, y, w, h = geom
        if w < window.minimumWidth() or h < window.minimumHeight():
            return
        if not self._is_geometry_on_screen(x, y, w, h):
            return
        window.setGeometry(QRect(x, y, w, h))

    def _is_geometry_on_screen(self, x: int, y: int, w: int, h: int) -> bool:
        app = QApplication.instance()
        if app is None or not isinstance(app, QApplication):
            return True
        screens = app.screens()
        if not screens:
            return True
        for screen in screens:
            screen_geom = screen.availableGeometry()
            if (
                x + w > screen_geom.x()
                and x < screen_geom.x() + screen_geom.width()
                and y + h > screen_geom.y()
                and y < screen_geom.y() + screen_geom.height()
            ):
                return True
        return False

    def _create_tray(self) -> None:
        icon = cached_app_icon()
        self.app.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon)
        self.tray.setToolTip("Widget Calculator")

        self.menu = QMenu()
        self.new_window_action = QAction("New calculator window", self.menu)
        self.new_window_action.triggered.connect(self._create_new_window)
        self.menu.addAction(self.new_window_action)

        self.open_settings_action = QAction("Settings...", self.menu)
        self.open_settings_action.triggered.connect(self._open_settings)
        self.menu.addAction(self.open_settings_action)

        self.windows_menu = self.menu.addMenu("Windows")
        self.themes_menu = self.menu.addMenu("Themes")
        self._build_theme_actions()

        self.menu.addSeparator()

        self.history_action = QAction("Show command history", self.menu)
        self.history_action.triggered.connect(self._show_history)
        self.menu.addAction(self.history_action)

        self.startup_action = QAction("Start when Windows boots", self.menu)
        self.startup_action.setCheckable(True)
        self.startup_action.triggered.connect(self._toggle_startup)
        self.menu.addAction(self.startup_action)

        self.menu.addSeparator()

        self.quit_action = QAction("Quit", self.menu)
        self.quit_action.triggered.connect(self._quit)
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _build_theme_actions(self) -> None:
        group = QActionGroup(self.themes_menu)
        group.setExclusive(True)
        self.theme_actions.clear()

        for theme in all_themes():
            action = QAction(theme.name, group)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked, theme_id=theme.theme_id: self._apply_theme(theme_id))
            self.themes_menu.addAction(action)
            self.theme_actions[theme.theme_id] = action

    def _bootstrap_windows(self, start_hidden: bool) -> None:
        self._close_all_windows()
        if self.window_mode == WINDOW_MODE_NEW:
            fresh = self.workspace.create_window()
            self.workspace.replace_windows_with(fresh)
            self._create_window_widget(
                fresh.window_id,
                fresh.title,
                fresh.editor_text,
                visible=not start_hidden,
            )
        else:
            for state in self.workspace.active_window_states(self.window_mode):
                self._create_window_widget(
                    state.window_id,
                    state.title,
                    state.editor_text,
                    visible=not start_hidden,
                )
        self._rebuild_windows_menu()

    def _create_window_widget(self, window_id: str, title: str, editor_text: str, visible: bool) -> None:
        if window_id in self.windows:
            return

        window = CalculatorWindow(
            window_id=window_id,
            title=title,
            on_open_settings=self._open_settings,
            initial_opacity=self.current_opacity,
        )
        if not self.always_on_top:
            window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
            window.show()  # re-apply flags
            window.hide()
        window.set_editor_text(editor_text)
        window.set_close_handler(self._handle_window_close)
        window.set_total_enabled(self.workspace.total_enabled)
        window.set_total_toggle_handler(self._on_total_toggled)
        window.editor_text_changed.connect(lambda window_ref=window_id: self._on_editor_text_changed(window_ref))
        window.window_activated.connect(lambda window_ref=window: self._on_window_activated(window_ref))
        window.geometry_changed.connect(
            lambda x, y, w, h, window_ref=window: self._on_geometry_changed(window_ref, x, y, w, h)
        )
        self._restore_geometry(window)

        # Build menu bar for this window
        _bar, actions = build_menu_bar(
            window=window,
            on_new_window=self._create_new_window,
            on_show_settings=self._open_settings,
            on_quit=self._quit,
            on_show_history=self._show_history,
            on_about=self._show_about,
            on_help=self._show_help,
        )
        self.window_menus[window_id] = actions

        window.apply_theme(self.current_theme)
        self.windows[window_id] = window

        eval_timer = QTimer(window)
        eval_timer.setSingleShot(True)
        eval_timer.setInterval(EVALUATE_DEBOUNCE_MS)
        eval_timer.timeout.connect(lambda window_ref=window_id: self._evaluate_window(window_ref))
        self.eval_timers[window_id] = eval_timer

        self._evaluate_window(window_id)
        if visible:
            window.show()
        else:
            window.hide()

    def _rebuild_windows_menu(self) -> None:
        self.windows_menu.clear()

        show_all_action = QAction("Show all windows", self.windows_menu)
        show_all_action.triggered.connect(self._show_all_windows)
        self.windows_menu.addAction(show_all_action)
        self.windows_menu.addSeparator()

        for state in self.workspace.window_states():
            action = QAction(state.title, self.windows_menu)
            action.triggered.connect(lambda _checked=False, window_id=state.window_id: self._show_window(window_id))
            self.windows_menu.addAction(action)

    def _on_editor_text_changed(self, window_id: str) -> None:
        if window_id in self.eval_timers:
            self.eval_timers[window_id].start()
        self._save_timer.start()

    def _evaluate_window(self, window_id: str) -> None:
        window = self.windows.get(window_id)
        if window is None:
            return

        results = self.workspace.evaluate_window(window_id, window.editor_text())
        window.set_results(results)
        self._apply_total(window_id, results)

    def _apply_total(self, window_id: str, results: list[str]) -> None:
        window = self.windows.get(window_id)
        if window is None:
            return
        if not self.workspace.total_enabled:
            window.set_total(None)
            return
        evaluator = self.workspace._evaluator  # noqa: SLF001
        total = evaluator.sum_results(results)
        if total is None:
            window.set_total(None)
        else:
            window.set_total(evaluator._format_number(total))  # noqa: SLF001

    def _on_total_toggled(self, enabled: bool) -> None:
        self.workspace.set_total_enabled(enabled)
        self._save_timer.start()
        for window_id in list(self.windows):
            results = self.workspace.evaluate_window_text(window_id) or []
            self._apply_total(window_id, results)

    def _show_window(self, window_id: str) -> None:
        window = self.windows.get(window_id)
        if window is None:
            return
        window.show()
        window.raise_()
        window.activateWindow()

    def _show_all_windows(self) -> None:
        for window in self.windows.values():
            window.show()
            window.raise_()

    def _show_history(self) -> None:
        anchor = self._active_window()
        if anchor is None:
            return
        anchor.show_history_dialog(self.workspace.history, self.current_theme)

    def _show_about(self) -> None:
        anchor = self._active_window()
        QMessageBox.information(
            anchor,
            "About Widget Calculator",
            "Widget Calculator\n\nA modern, resizable calculator widget for Windows with "
            "variables, unit conversions, currency rates, and themes.\n\n"
            "Built with PySide6 and Pint.",
        )

    def _show_help(self) -> None:
        anchor = self._active_window()
        QMessageBox.information(
            anchor,
            "Help",
            "Examples:\n"
            "  x = 1\n  y = 2\n  x + y\n"
            "  10 km to m\n"
            "  20 usd to eur\n"
            "  200 * 10%\n"
            "  sqrt(9)\n\n"
            "Press Alt to show the menu bar. Click a result line to copy it. "
            "Use the gear icon (bottom-right) for settings.",
        )

    def _create_new_window(self) -> None:
        if self.window_mode == WINDOW_MODE_NEW:
            for window in list(self.windows.values()):
                self._close_window_widget(window.window_id)
            fresh = self.workspace.create_window()
            self.workspace.replace_windows_with(fresh)
            self._create_window_widget(
                window_id=fresh.window_id,
                title=fresh.title,
                editor_text=fresh.editor_text,
                visible=True,
            )
            self._rebuild_windows_menu()
            self._save_timer.start()
            return

        window_state = self.workspace.create_window()
        self._create_window_widget(
            window_id=window_state.window_id,
            title=window_state.title,
            editor_text=window_state.editor_text,
            visible=True,
        )
        self._rebuild_windows_menu()
        self._save_timer.start()

    def _close_window_widget(self, window_id: str) -> None:
        window = self.windows.pop(window_id, None)
        if window is None:
            return
        self.eval_timers.pop(window_id, None)
        self.window_menus.pop(window_id, None)
        self._allow_close = True
        window.close()
        self._allow_close = False

    def _close_all_windows(self) -> None:
        for window_id in list(self.windows.keys()):
            self._close_window_widget(window_id)

    def _on_window_mode_changed(self, mode: str) -> None:
        resolved = self.workspace.set_window_mode(mode)
        self.window_mode = resolved
        if self._settings_dialog is not None:
            self._settings_dialog.set_window_mode_state(resolved)
        self._save_timer.start()

    def _apply_theme(self, theme_id: str, persist: bool = True) -> None:
        resolved = self.workspace.set_theme(theme_id)
        self.current_theme = get_theme(resolved)
        for window in self.windows.values():
            window.apply_theme(self.current_theme)
        if self._settings_dialog is not None:
            self._settings_dialog.apply_theme(self.current_theme)
            self._settings_dialog.set_theme_state(resolved)

        for known_theme_id, action in self.theme_actions.items():
            action.blockSignals(True)
            action.setChecked(known_theme_id == resolved)
            action.blockSignals(False)

        if persist:
            self._save_timer.start()

    def _apply_startup_default(self) -> None:
        if not self.workspace.startup_initialized:
            try:
                self.startup_registry.set_enabled(True)
                enabled = True
            except Exception as exc:
                enabled = False
                QMessageBox.warning(None, "Startup setup failed", f"Could not set startup: {exc}")

            self.workspace.startup_initialized = True
            self._save_timer.start()
        else:
            enabled = self.startup_registry.is_enabled()

        self.startup_action.blockSignals(True)
        self.startup_action.setChecked(enabled)
        self.startup_action.blockSignals(False)

    def _toggle_startup(self, checked: bool) -> None:
        try:
            self.startup_registry.set_enabled(checked)
            self.workspace.startup_initialized = True
            self._save_timer.start()
        except Exception as exc:
            QMessageBox.warning(None, "Startup update failed", f"Could not update startup: {exc}")
            checked = self.startup_registry.is_enabled()

        self.startup_action.blockSignals(True)
        self.startup_action.setChecked(checked)
        self.startup_action.blockSignals(False)

        if self._settings_dialog is not None:
            self._settings_dialog.set_startup_state(checked)

    def _open_settings(self) -> None:
        if self._settings_dialog is None:
            dialog = SettingsDialog(
                current_theme_id=self.workspace.theme_id,
                current_opacity=self.current_opacity,
                current_startup=self.startup_registry.is_enabled(),
                current_always_on_top=self.always_on_top,
                current_window_mode=self.workspace.window_mode,
                parent=self._active_window(),
            )
            dialog.theme_requested.connect(self._apply_theme)
            dialog.startup_requested.connect(self._toggle_startup)
            dialog.always_on_top_requested.connect(self._on_always_on_top_changed)
            dialog.opacity_requested.connect(self._on_opacity_changed)
            dialog.new_window_requested.connect(self._create_new_window)
            dialog.show_history_requested.connect(self._show_history)
            dialog.about_requested.connect(self._show_about)
            dialog.help_requested.connect(self._show_help)
            dialog.window_mode_requested.connect(self._on_window_mode_changed)
            dialog.apply_theme(self.current_theme)
            self._settings_dialog = dialog

        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _on_opacity_changed(self, value: float) -> None:
        resolved = self.workspace.set_window_opacity(value)
        self.current_opacity = resolved
        for window in self.windows.values():
            window.set_opacity(resolved)
        if self._settings_dialog is not None:
            self._settings_dialog.set_opacity_value(resolved)
        self._save_timer.start()

    def _on_always_on_top_changed(self, enabled: bool) -> None:
        self.always_on_top = enabled
        for window in self.windows.values():
            was_visible = window.isVisible()
            window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
            if was_visible:
                window.show()
        if self._settings_dialog is not None:
            self._settings_dialog.set_always_on_top_state(enabled)

    def _handle_window_close(self, window: CalculatorWindow) -> bool:
        if self._allow_close:
            return False

        self.workspace.release_window(window.window_id)
        window.hide()
        if not self._close_notice_shown:
            self.tray.showMessage(
                "Widget Calculator",
                "Still running in the background. Reopen windows from the tray menu.",
                QSystemTrayIcon.MessageIcon.Information,
                3500,
            )
            self._close_notice_shown = True
        self._save_timer.start()
        return True

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            first_window = next(iter(self.windows.values()), None)
            if first_window is None:
                return
            if first_window.isVisible():
                first_window.hide()
            else:
                self._show_window(first_window.window_id)

    def _save_state(self) -> None:
        for window_id, window in self.windows.items():
            self.workspace.set_window_text(window_id, window.editor_text())
        self.state_store.save(self.workspace.snapshot())

    def _quit(self) -> None:
        self._save_state()
        self._allow_close = True
        if self._settings_dialog is not None:
            self._settings_dialog.close()
        self.tray.hide()
        for window in self.windows.values():
            window.close()
        self.app.quit()


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--background", action="store_true", help="Start hidden in system tray")
    args = parser.parse_args(argv[1:])

    app = QApplication(argv)
    app.setQuitOnLastWindowClosed(False)

    _controller = MultiWindowAppController(app, start_hidden=args.background)
    return app.exec()


def cli() -> None:
    raise SystemExit(run(sys.argv))
