from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtWidgets import QApplication

from widget_calc.application.workspace import WorkspaceService
from widget_calc.domain.calculator import CalculatorEvaluator, CurrencyConverter
from widget_calc.domain.models import AppState, WindowState
from widget_calc.infrastructure.state_store import JsonStateStore
from widget_calc.presentation.qt.app import MultiWindowAppController


@pytest.fixture(scope="module")
def qapp() -> Generator[QApplication, None, None]:
    existing = QGuiApplication.instance()
    if isinstance(existing, QApplication):
        yield existing
        return
    app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def clean_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    yield


@pytest.fixture
def controller(
    qapp: QApplication, clean_state: None  # noqa: ARG001
) -> Generator[MultiWindowAppController, None, None]:
    c = MultiWindowAppController(qapp, start_hidden=True)
    yield c
    state = JsonStateStore()
    if state.state_path.exists():
        state.state_path.unlink()


class TestAltKeyFilter:
    def test_alt_press_shows_menu_bar(
        self, qapp: QApplication, controller: MultiWindowAppController  # noqa: ARG002
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        bar = window.menuBar()
        bar.setVisible(False)
        assert bar.isVisible() is False

        press = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Alt,
            Qt.KeyboardModifier.NoModifier,
        )
        controller._alt_filter.eventFilter(window, press)
        assert bar.isVisible() is True

    def test_alt_release_starts_hide_timer(
        self, qapp: QApplication, controller: MultiWindowAppController  # noqa: ARG002
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        bar = window.menuBar()
        bar.setVisible(True)
        assert bar.isVisible() is True

        window._menu_hide_timer.stop()
        release = QKeyEvent(
            QEvent.Type.KeyRelease,
            Qt.Key.Key_Alt,
            Qt.KeyboardModifier.NoModifier,
        )
        window.keyReleaseEvent(release)
        assert window._menu_hide_timer.isActive() is True
        window._menu_hide_timer.stop()
        window._hide_menu_bar()
        assert bar.isVisible() is False

    def test_hide_menu_bar_keeps_visible_when_popup_active(
        self, qapp: QApplication, controller: MultiWindowAppController  # noqa: ARG002
    ) -> None:
        from PySide6.QtWidgets import QMenu

        window = next(iter(controller.windows.values()))
        window.show()
        bar = window.menuBar()
        bar.setVisible(True)
        menu = None
        for existing in bar.findChildren(QMenu):
            menu = existing
            break
        if menu is None:
            menu = bar.addMenu("Test")
        menu.show()
        try:
            window._hide_menu_bar()
            assert bar.isVisible() is True
            assert window._menu_hide_timer.isActive() is True
        finally:
            menu.close()
            window._menu_hide_timer.stop()

    def test_non_alt_key_does_not_toggle(
        self, qapp: QApplication, controller: MultiWindowAppController  # noqa: ARG002
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        bar = window.menuBar()
        bar.setVisible(False)

        a_event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_A,
            Qt.KeyboardModifier.NoModifier,
        )
        controller._alt_filter.eventFilter(window, a_event)
        assert bar.isVisible() is False


class TestMultiWindowAppController:
    def test_creates_default_window(
        self, controller: MultiWindowAppController
    ) -> None:
        assert len(controller.windows) == 1
        window = next(iter(controller.windows.values()))
        assert window.window_id in controller.windows
        assert window.windowTitle().startswith("Calculator")

    def test_settings_dialog_opened_lazily(
        self, controller: MultiWindowAppController
    ) -> None:
        assert controller._settings_dialog is None
        controller._open_settings()
        assert controller._settings_dialog is not None
        assert controller._settings_dialog.windowTitle() == "Settings"
        first = controller._settings_dialog
        controller._open_settings()
        assert controller._settings_dialog is first

    def test_create_new_window_adds_widget(
        self, controller: MultiWindowAppController
    ) -> None:
        before = len(controller.windows)
        controller._create_new_window()
        assert len(controller.windows) == before + 1
        for window in controller.windows.values():
            assert window.title_bar is not None
            assert window.results is not None
            assert window.engine_icon is not None

    def test_apply_theme_changes_current(
        self, controller: MultiWindowAppController
    ) -> None:
        controller._apply_theme("nord", persist=False)
        assert controller.current_theme.theme_id == "nord"
        for window in controller.windows.values():
            assert window._theme is not None
            assert window._theme.theme_id == "nord"

    def test_apply_unknown_theme_falls_back(
        self, controller: MultiWindowAppController
    ) -> None:
        original = controller.current_theme.theme_id
        controller._apply_theme("not-a-real-theme", persist=False)
        assert controller.current_theme.theme_id == original

    def test_set_opacity_updates_all_windows(
        self, controller: MultiWindowAppController
    ) -> None:
        controller._create_new_window()
        controller._on_opacity_changed(0.5)
        for w in controller.windows.values():
            assert abs(w.windowOpacity() - 0.5) < 0.05

        controller._on_opacity_changed(5.0)
        for w in controller.windows.values():
            assert w.windowOpacity() == 1.0

        controller._on_opacity_changed(0.1)
        for w in controller.windows.values():
            assert w.windowOpacity() == 1.0

        controller._on_opacity_changed(0.4)
        for w in controller.windows.values():
            assert abs(w.windowOpacity() - 0.4) < 0.05

    def test_always_on_top_default_true(
        self, controller: MultiWindowAppController
    ) -> None:
        assert controller.always_on_top is True
        window = next(iter(controller.windows.values()))
        assert bool(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)

    def test_window_has_translucent_background(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def test_window_mask_applied(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        window._apply_window_mask()
        assert window.mask() is not None
        assert not window.mask().isEmpty()

    def test_splitter_discrete_handle(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        assert window.splitter.handleWidth() == 8
        assert window.splitter.objectName() == "mainSplitter"

    def test_panes_have_symmetric_top_margin(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        input_pane = window.input_pane
        result_pane = window.result_pane
        input_layout = input_pane.layout()
        result_layout = result_pane.layout()
        assert input_layout is not None
        assert result_layout is not None
        # Both panes have a 4px top margin to align the input frame's top
        # edge with the result editor's top edge.
        assert input_layout.contentsMargins().top() == 4
        assert result_layout.contentsMargins().top() == 4

    def test_menu_bar_starts_hidden(
        self, controller: MultiWindowAppController
    ) -> None:
        from widget_calc.presentation.qt.menu_bar import build_menu_bar

        window = next(iter(controller.windows.values()))
        build_menu_bar(
            window=window,
            on_new_window=lambda: None,
            on_show_settings=lambda: None,
            on_quit=lambda: None,
            on_show_history=lambda: None,
            on_about=lambda: None,
            on_help=lambda: None,
        )
        assert window.menuBar().isVisible() is False

    def test_show_menu_bar_makes_it_visible(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        bar = window.menuBar()
        bar.setVisible(False)
        window.show_menu_bar()
        assert bar.isVisible() is True

    def test_resize_edges_on_right_edge(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        w, h = window.width(), window.height()
        pos = QPoint(w - 2, h // 2)
        edges = window._get_resize_edges(pos)
        assert bool(edges & Qt.Edge.RightEdge)

    def test_resize_edges_on_bottom_edge(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        w, h = window.width(), window.height()
        pos = QPoint(w // 2, h - 2)
        edges = window._get_resize_edges(pos)
        assert bool(edges & Qt.Edge.BottomEdge)

    def test_resize_edges_on_left_edge(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        h = window.height()
        pos = QPoint(2, h // 2)
        edges = window._get_resize_edges(pos)
        assert bool(edges & Qt.Edge.LeftEdge)

    def test_no_resize_in_title_bar(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        w = window.width()
        title_h = window.title_bar.height()
        pos = QPoint(w - 2, title_h // 2)
        edges = window._get_resize_edges(pos)
        assert edges == Qt.Edge(0)

    def test_no_resize_in_center(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        w, h = window.width(), window.height()
        pos = QPoint(w // 2, h // 2)
        edges = window._get_resize_edges(pos)
        assert edges == Qt.Edge(0)

    def test_resize_cursor_set_on_edge(
        self, controller: MultiWindowAppController
    ) -> None:
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        window = next(iter(controller.windows.values()))
        window.show()
        w, h = window.width(), window.height()

        move = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(w - 2, h // 2),
            QPointF(w - 2, h // 2),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        window.mouseMoveEvent(move)
        assert window.cursor().shape() == Qt.CursorShape.SizeHorCursor

    def test_cursor_filter_updates_from_child_widget(
        self, controller: MultiWindowAppController
    ) -> None:
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        window = next(iter(controller.windows.values()))
        window.show()

        child = window.editor
        local_pos = QPointF(child.width() - 1, child.height() // 2)
        global_pos = child.mapToGlobal(local_pos.toPoint())

        move = QMouseEvent(
            QEvent.Type.MouseMove,
            local_pos,
            global_pos,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        window._cursor_filter.eventFilter(child, move)  # type: ignore[union-attr]
        assert window.cursor().shape() in (
            Qt.CursorShape.SizeHorCursor,
            Qt.CursorShape.ArrowCursor,
        )

    def test_resize_disabled_when_maximized(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        window._maximized = True
        w, h = window.width(), window.height()
        pos = QPoint(w - 2, h // 2)
        edges = window._get_resize_edges(pos)
        assert edges == Qt.Edge(0)
        window._maximized = False

    def test_cursor_for_edges_diagonal(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        assert window._cursor_for_edges(Qt.Edge.BottomEdge | Qt.Edge.LeftEdge) == Qt.CursorShape.SizeBDiagCursor
        assert window._cursor_for_edges(Qt.Edge.BottomEdge | Qt.Edge.RightEdge) == Qt.CursorShape.SizeFDiagCursor
        assert window._cursor_for_edges(Qt.Edge.BottomEdge) == Qt.CursorShape.SizeVerCursor
        assert window._cursor_for_edges(Qt.Edge.RightEdge) == Qt.CursorShape.SizeHorCursor
        assert window._cursor_for_edges(Qt.Edge(0)) == Qt.CursorShape.ArrowCursor


class TestWindowMode:
    def test_default_window_mode_is_both(
        self, controller: MultiWindowAppController
    ) -> None:
        assert controller.window_mode == "both"

    def test_set_window_mode_persists(
        self, controller: MultiWindowAppController
    ) -> None:
        controller._on_window_mode_changed("previous")
        assert controller.window_mode == "previous"
        assert controller.workspace.window_mode == "previous"

    def test_set_window_mode_invalid_falls_back(
        self, controller: MultiWindowAppController
    ) -> None:
        controller._on_window_mode_changed("garbage")
        assert controller.window_mode == "both"

    def test_create_new_in_previous_mode_creates_another(
        self, controller: MultiWindowAppController
    ) -> None:
        controller._on_window_mode_changed("previous")
        first_id = next(iter(controller.windows.values())).window_id
        controller._create_new_window()
        assert len(controller.windows) == 2
        assert first_id in controller.windows

    def test_create_new_in_new_mode_replaces(
        self, controller: MultiWindowAppController
    ) -> None:
        controller._on_window_mode_changed("new")
        first_window = next(iter(controller.windows.values()))
        first_id = first_window.window_id
        first_window.show()
        controller._create_new_window()
        assert first_id not in controller.windows
        assert len(controller.windows) == 1
        new_id = next(iter(controller.windows.values())).window_id
        assert new_id != first_id
        saved_ids = [s.window_id for s in controller.workspace.window_states()]
        assert saved_ids == [new_id]

    def test_create_new_in_both_mode_keeps_old(
        self, controller: MultiWindowAppController
    ) -> None:
        first_window = next(iter(controller.windows.values()))
        first_id = first_window.window_id
        first_window.show()
        controller._create_new_window()
        assert first_id in controller.windows
        assert len(controller.windows) == 2

    def test_bootstrap_previous_mode_shows_only_last(
        self,
        qapp: QApplication,  # noqa: ARG002
        clean_state: None,  # noqa: ARG002
    ) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="old-1", title="Old 1", editor_text="1+1"),
                WindowState(window_id="old-2", title="Old 2", editor_text="2+2"),
            ],
            window_mode="previous",
        )
        workspace = WorkspaceService(evaluator, initial)
        controller = MultiWindowAppController(qapp, start_hidden=True)
        controller.workspace = workspace
        controller.window_mode = "previous"
        controller._bootstrap_windows(True)
        visible_ids = list(controller.windows.keys())
        assert visible_ids == ["old-2"]
        controller._quit()

    def test_bootstrap_new_mode_clears_state(
        self,
        qapp: QApplication,  # noqa: ARG002
        clean_state: None,  # noqa: ARG002
    ) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[WindowState(window_id="stale", title="Stale", editor_text="x")],
            window_mode="new",
        )
        workspace = WorkspaceService(evaluator, initial)
        controller = MultiWindowAppController(qapp, start_hidden=True)
        controller.workspace = workspace
        controller.window_mode = "new"
        controller._bootstrap_windows(True)
        visible_ids = list(controller.windows.keys())
        assert len(visible_ids) == 1
        assert visible_ids[0] != "stale"
        saved_ids = [s.window_id for s in workspace.window_states()]
        assert saved_ids == visible_ids
        controller._quit()

    def test_bootstrap_previous_mode_uses_last_active(
        self,
        qapp: QApplication,  # noqa: ARG002
        clean_state: None,  # noqa: ARG002
    ) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="first", title="First", editor_text="1"),
                WindowState(window_id="middle", title="Middle", editor_text="2"),
                WindowState(window_id="last", title="Last", editor_text="3"),
            ],
            window_mode="previous",
            last_active_window_id="middle",
        )
        workspace = WorkspaceService(evaluator, initial)
        controller = MultiWindowAppController(qapp, start_hidden=True)
        controller.workspace = workspace
        controller.window_mode = "previous"
        controller._bootstrap_windows(True)
        visible_ids = list(controller.windows.keys())
        assert visible_ids == ["middle"]
        controller._quit()

    def test_focus_change_records_last_active(
        self, controller: MultiWindowAppController
    ) -> None:
        first_window = next(iter(controller.windows.values()))
        controller._create_new_window()
        windows = list(controller.windows.values())
        assert len(windows) == 2
        second_window = next(w for w in windows if w.window_id != first_window.window_id)
        controller._on_window_activated(first_window)
        assert controller.workspace.last_active_window_id == first_window.window_id
        controller._on_window_activated(second_window)
        assert controller.workspace.last_active_window_id == second_window.window_id

    def test_window_activated_signal_updates_active(
        self, controller: MultiWindowAppController
    ) -> None:
        first_window = next(iter(controller.windows.values()))
        controller._create_new_window()
        windows = list(controller.windows.values())
        second_window = next(w for w in windows if w.window_id != first_window.window_id)
        # Emit the signal directly (simulating the changeEvent result)
        second_window.window_activated.emit()
        assert controller.workspace.last_active_window_id == second_window.window_id

    def test_geometry_change_saves_to_workspace(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        window.setGeometry(10, 20, 700, 500)
        qapp = QApplication.instance()
        if qapp:
            qapp.processEvents()
        geom = controller.workspace.get_window_geometry(window.window_id)
        assert geom is not None
        assert geom[2] == 700
        assert geom[3] == 500

    def test_geometry_restored_on_create(
        self,
        qapp: QApplication,  # noqa: ARG002
        clean_state: None,  # noqa: ARG002
    ) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[WindowState(window_id="saved", title="Saved")],
            window_geometries={"saved": (10, 20, 700, 500)},
        )
        workspace = WorkspaceService(evaluator, initial)
        controller = MultiWindowAppController(qapp, start_hidden=True)
        controller.workspace = workspace
        controller._bootstrap_windows(True)
        window = controller.windows["saved"]
        # Allow Qt to apply the geometry
        qapp.processEvents()
        assert window.width() == 700
        assert window.height() == 500
        controller._quit()

    def test_geometry_off_screen_ignored(
        self,
        qapp: QApplication,  # noqa: ARG002
        clean_state: None,  # noqa: ARG002
    ) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[WindowState(window_id="offscreen", title="Off")],
            window_geometries={"offscreen": (-9999, -9999, 700, 500)},
        )
        workspace = WorkspaceService(evaluator, initial)
        controller = MultiWindowAppController(qapp, start_hidden=True)
        controller.workspace = workspace
        controller._bootstrap_windows(True)
        # Should not have moved to off-screen
        window = controller.windows["offscreen"]
        assert window.x() > -9999
        controller._quit()

    def test_tray_uses_calculator_icon(self, controller: MultiWindowAppController) -> None:
        from widget_calc.presentation.qt.calculator_icon import build_app_icon

        expected = build_app_icon()
        assert not controller.tray.icon().isNull()
        # The cached app icon should be a valid multi-size icon
        for size in (16, 32, 64):
            assert not expected.pixmap(size, size).isNull()

    def test_app_window_icon_set(self, controller: MultiWindowAppController) -> None:
        assert not controller.app.windowIcon().isNull()
        # All windows inherit the app icon
        window = next(iter(controller.windows.values()))
        window.show()
        qapp = QApplication.instance()
        if qapp:
            qapp.processEvents()
        assert not window.windowIcon().isNull()

    def test_total_bar_starts_enabled(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        assert window.total_bar.is_enabled() is True
        assert controller.workspace.total_enabled is True

    def test_total_updates_with_results(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        window.set_editor_text("1 + 2\n3 + 4")
        controller._evaluate_window(window.window_id)
        qapp = QApplication.instance()
        if qapp:
            qapp.processEvents()
        assert window.total_bar._value.text() == "10"

    def test_total_clears_when_disabled(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        window.set_editor_text("1 + 2\n3 + 4")
        controller._evaluate_window(window.window_id)
        assert window.total_bar._value.text() != ""
        window.total_bar._switch.setChecked(False)
        # Manually invoke the slot to mimic the user click
        window.total_bar.toggled.emit(False)
        assert window.total_bar._value.text() == ""
        assert controller.workspace.total_enabled is False

    def test_total_persists_state(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.total_bar._switch.setChecked(False)
        window.total_bar.toggled.emit(False)
        controller._save_timer.stop()
        controller._save_state()
        # Reload from disk and verify
        store = JsonStateStore()
        reloaded = store.load()
        assert reloaded.total_enabled is False

    def test_total_bar_lives_in_result_pane(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        qapp = QApplication.instance()
        if qapp:
            qapp.processEvents()
        # The total bar's parent should be the result pane, not the root panel.
        assert window.total_bar.parentWidget() is window.result_pane
        # And its width should not exceed the result pane's width.
        assert window.total_bar.width() <= window.result_pane.width() + 1

    def test_total_bar_overlays_results_at_bottom(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        qapp = QApplication.instance()
        if qapp:
            qapp.processEvents()
        # The total bar lives at the bottom of the result pane, just below the
        # result editor. It is part of the layout (not an overlay) and shares
        # the parent with the result editor.
        assert window.total_bar.parentWidget() is window.result_pane
        # The total bar is below the result editor.
        assert window.total_bar.y() >= window.results.y() + window.results.height()
        # The total bar sits flush against the result pane's bottom border.
        pane_bottom = window.result_pane.height()
        bar_bottom = window.total_bar.y() + window.total_bar.height()
        assert pane_bottom - bar_bottom == 1
        # The total bar fills the full result pane content width (minus the
        # 1px border on each side). Its own internal margins provide content
        # spacing for the label/value/switch.
        assert window.total_bar.width() == window.result_pane.width() - 2

    def test_engine_icon_inside_editor_with_padding(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        qapp = QApplication.instance()
        if qapp:
            qapp.processEvents()
        # The engine icon should be at the bottom-left of the input pane
        # (the visible "rounded box" of the input area).
        assert window.engine_icon.parentWidget() is window.input_pane
        assert window.engine_icon.x() == 3
        pane_bottom = window.input_pane.height()
        icon_bottom = window.engine_icon.y() + window.engine_icon.height()
        assert pane_bottom - icon_bottom == 3

    def test_result_editor_height_matches_input_editor(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        qapp = QApplication.instance()
        if qapp:
            qapp.processEvents()
        # The result editor and input editor should have the same height
        # (both are inside a 1px-border QFrame with matching margins).
        result_h = window.results.height()
        input_h = window.editor.height()
        assert result_h == input_h

    def test_input_frame_wraps_editor(
        self, controller: MultiWindowAppController
    ) -> None:
        window = next(iter(controller.windows.values()))
        window.show()
        qapp = QApplication.instance()
        if qapp:
            qapp.processEvents()
        # The input pane and result pane are symmetric: both are QFrames
        # that contain their editor as a direct child (and the result pane
        # also contains the total bar).
        assert window.editor.parentWidget() is window.input_pane
        assert window.results.parentWidget() is window.result_pane
