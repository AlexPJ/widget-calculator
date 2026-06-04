from __future__ import annotations

from collections.abc import Generator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMainWindow

from widget_calc.domain.models import MAX_OPACITY, MIN_OPACITY
from widget_calc.domain.themes import all_themes
from widget_calc.presentation.qt.calculator_icon import (
    build_app_icon,
    cached_app_icon,
    draw_calculator_icon,
)
from widget_calc.presentation.qt.engine_icon import EngineIconButton
from widget_calc.presentation.qt.result_editor import ResultEditor
from widget_calc.presentation.qt.settings_dialog import SettingsDialog
from widget_calc.presentation.qt.title_bar import TitleBar
from widget_calc.presentation.qt.toggle_switch import ToggleSwitch
from widget_calc.presentation.qt.total_bar import TotalBar


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
def result_editor(qapp: QApplication) -> Generator[ResultEditor, None, None]:  # noqa: ARG001
    editor = ResultEditor()
    editor.resize(400, 200)
    yield editor
    editor.close()
    editor.deleteLater()


@pytest.fixture
def engine_icon(qapp: QApplication) -> Generator[EngineIconButton, None, None]:  # noqa: ARG001
    icon = EngineIconButton()
    yield icon
    icon.close()
    icon.deleteLater()


@pytest.fixture
def settings_dialog(qapp: QApplication) -> Generator[SettingsDialog, None, None]:  # noqa: ARG001
    dialog = SettingsDialog(
        current_theme_id="monokai",
        current_opacity=1.0,
        current_startup=False,
        current_always_on_top=False,
    )
    yield dialog
    dialog.close()
    dialog.deleteLater()


@pytest.fixture
def title_bar(qapp: QApplication) -> Generator[TitleBar, None, None]:  # noqa: ARG001
    bar = TitleBar("Test")
    yield bar
    bar.close()
    bar.deleteLater()


class TestResultEditor:
    def test_creates_with_correct_setup(self, result_editor: ResultEditor) -> None:
        assert result_editor.isReadOnly()
        assert result_editor.objectName() == "resultEditor"
        assert result_editor.focusPolicy() == Qt.FocusPolicy.NoFocus

    def test_click_copies_line(
        self, result_editor: ResultEditor, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _FakeClipboard:
            def __init__(self) -> None:
                self.text_value = ""

            def setText(self, text: str) -> None:  # noqa: N802
                self.text_value = text

            def text(self) -> str:
                return self.text_value

        fake = _FakeClipboard()
        monkeypatch.setattr(QGuiApplication, "clipboard", staticmethod(lambda: fake))

        result_editor.setPlainText("first\nsecond\nthird")
        received: list[str] = []
        result_editor.line_copied.connect(received.append)

        from PySide6.QtCore import QEvent, QPointF
        from PySide6.QtGui import QMouseEvent

        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(5.0, 5.0),
            QPointF(5.0, 5.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        result_editor.mousePressEvent(press)

        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(5.0, 5.0),
            QPointF(5.0, 5.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        result_editor.mouseReleaseEvent(release)

        assert received, "line_copied should be emitted on click"
        assert fake.text_value in {"first", "second", "third"}

    def test_drag_does_not_copy(self, result_editor: ResultEditor) -> None:
        result_editor.setPlainText("line one\nline two")
        received: list[str] = []
        result_editor.line_copied.connect(received.append)

        from PySide6.QtCore import QEvent, QPointF
        from PySide6.QtGui import QMouseEvent

        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(2.0, 2.0),
            QPointF(2.0, 2.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        result_editor.mousePressEvent(press)

        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(200.0, 2.0),
            QPointF(200.0, 2.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        result_editor.mouseReleaseEvent(release)

        assert received == []


class TestEngineIconButton:
    def test_creates_with_correct_setup(self, engine_icon: EngineIconButton) -> None:
        assert engine_icon.objectName() == "engineIcon"
        assert engine_icon.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_click_emits_signal(self, engine_icon: EngineIconButton) -> None:
        received: list[None] = []
        engine_icon.clicked.connect(lambda: received.append(None))

        from PySide6.QtCore import QEvent, QPointF
        from PySide6.QtGui import QMouseEvent

        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(5.0, 5.0),
            QPointF(5.0, 5.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        engine_icon.mousePressEvent(press)

        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(5.0, 5.0),
            QPointF(5.0, 5.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        engine_icon.mouseReleaseEvent(release)

        assert received, "clicked signal should be emitted"

    def test_apply_theme_updates_colors(self, engine_icon: EngineIconButton) -> None:
        themes = all_themes()
        theme = next(t for t in themes if t.theme_id == "nord")
        engine_icon.apply_theme(theme)
        assert engine_icon._accent.name().lower() == theme.accent.lower()
        assert engine_icon._bg.name().lower() == theme.surface_bg.lower()

    def test_paint_event_does_not_crash(
        self, engine_icon: EngineIconButton, qapp: QApplication
    ) -> None:  # noqa: ARG002
        engine_icon.show()
        qapp.processEvents()
        engine_icon.repaint()


class TestCalculatorIcon:
    def test_draw_calculator_icon_does_not_raise(self) -> None:
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor, QImage, QPainter

        for size in (16, 22, 24, 32, 64, 128, 256):
            image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(0)
            painter = QPainter(image)
            try:
                draw_calculator_icon(
                    painter, QRectF(0.0, 0.0, float(size), float(size)), QColor("#1f2023")
                )
            finally:
                painter.end()
            assert not image.isNull()

    def test_build_app_icon_provides_multiple_sizes(self) -> None:
        icon = build_app_icon()
        for size in (16, 24, 32, 48, 64, 128, 256):
            pixmap = icon.pixmap(size, size)
            assert not pixmap.isNull()
            # On HiDPI displays pixmap.width() may be scaled up; check it's at least the request
            assert pixmap.width() >= size
            assert pixmap.height() >= size

    def test_cached_app_icon_returns_same_instance(self) -> None:
        first = cached_app_icon()
        second = cached_app_icon()
        assert first is second
        assert not first.isNull()


class TestSettingsDialog:
    def test_creates_with_initial_values(self, settings_dialog: SettingsDialog) -> None:
        assert settings_dialog.windowTitle() == "Settings"
        assert settings_dialog._opacity_slider.value() == int(1.0 * 100)
        assert settings_dialog._always_on_top.isChecked() is False
        assert settings_dialog._startup_checkbox.isChecked() is False

    def test_emits_theme_request(self, settings_dialog: SettingsDialog) -> None:
        received: list[str] = []
        settings_dialog.theme_requested.connect(received.append)

        for theme_id, radio in settings_dialog._theme_buttons.items():
            if theme_id == "nord":
                radio.click()
                break

        assert received == ["nord"]

    def test_emits_always_on_top_request(self, settings_dialog: SettingsDialog) -> None:
        received: list[bool] = []
        settings_dialog.always_on_top_requested.connect(received.append)
        settings_dialog._always_on_top.click()
        assert received == [True]

    def test_emits_startup_request(self, settings_dialog: SettingsDialog) -> None:
        received: list[bool] = []
        settings_dialog.startup_requested.connect(received.append)
        settings_dialog._startup_checkbox.click()
        assert received == [True]

    def test_opacity_debounce_emits_value(self, settings_dialog: SettingsDialog) -> None:
        received: list[float] = []
        settings_dialog.opacity_requested.connect(received.append)
        settings_dialog._opacity_slider.setValue(int(MIN_OPACITY * 100))
        settings_dialog._emit_opacity()
        assert pytest.approx(received[-1]) == MIN_OPACITY

    def test_new_window_request(self, settings_dialog: SettingsDialog) -> None:
        received: list[None] = []
        settings_dialog.new_window_requested.connect(lambda: received.append(None))
        settings_dialog._new_window_button.click()
        assert received == [None]

    def test_show_history_request(self, settings_dialog: SettingsDialog) -> None:
        received: list[None] = []
        settings_dialog.show_history_requested.connect(lambda: received.append(None))
        settings_dialog._history_button.click()
        assert received == [None]

    def test_set_opacity_value(self, settings_dialog: SettingsDialog) -> None:
        settings_dialog.set_opacity_value(0.5)
        assert settings_dialog._opacity_slider.value() == 50

    def test_constructor_clamps_opacity(self, qapp: QApplication) -> None:  # noqa: ARG002
        dialog = SettingsDialog(
            current_theme_id="monokai",
            current_opacity=5.0,
            current_startup=False,
            current_always_on_top=False,
        )
        assert dialog._opacity_slider.value() == int(MAX_OPACITY * 100)
        dialog.close()
        dialog.deleteLater()

    def test_window_mode_buttons_present(self, settings_dialog: SettingsDialog) -> None:
        assert "previous" in settings_dialog._window_mode_buttons
        assert "new" in settings_dialog._window_mode_buttons
        assert "both" in settings_dialog._window_mode_buttons

    def test_window_mode_default_is_both(self, qapp: QApplication) -> None:  # noqa: ARG002
        dialog = SettingsDialog(
            current_theme_id="monokai",
            current_opacity=1.0,
            current_startup=False,
            current_always_on_top=False,
        )
        assert dialog._window_mode_buttons["both"].isChecked() is True
        dialog.close()
        dialog.deleteLater()

    def test_emits_window_mode_request(self, settings_dialog: SettingsDialog) -> None:
        received: list[str] = []
        settings_dialog.window_mode_requested.connect(received.append)
        settings_dialog._window_mode_buttons["new"].click()
        assert received == ["new"]

    def test_set_window_mode_state(self, settings_dialog: SettingsDialog) -> None:
        settings_dialog.set_window_mode_state("previous")
        assert settings_dialog._window_mode_buttons["previous"].isChecked() is True
        assert settings_dialog._window_mode_buttons["both"].isChecked() is False


class TestTitleBar:
    def test_buttons_are_square(self, title_bar: TitleBar) -> None:
        for button in (title_bar._min_button, title_bar._max_button, title_bar._close_button):
            assert button.width() == 32
            assert button.height() == 32

    def test_buttons_have_no_text_padding(self, title_bar: TitleBar) -> None:
        for button in (title_bar._min_button, title_bar._max_button, title_bar._close_button):
            assert button.text() != ""

    def test_layout_has_right_padding(self, title_bar: TitleBar) -> None:
        layout = title_bar.layout()
        assert layout is not None
        margins = layout.contentsMargins()
        assert margins.right() >= 4


class TestMenuBar:
    def test_ctrl_n_shortcut_registered(self, qapp: QApplication) -> None:  # noqa: ARG002
        from widget_calc.presentation.qt.menu_bar import build_menu_bar

        called: list[int] = []

        class _StubEditor:
            def undo(self) -> None: ...
            def redo(self) -> None: ...
            def copy(self) -> None: ...
            def paste(self) -> None: ...
            def cut(self) -> None: ...

        window = QMainWindow()
        window.editor = _StubEditor()  # type: ignore[attr-defined]
        try:
            _bar, actions = build_menu_bar(
                window=window,  # type: ignore[arg-type]
                on_new_window=lambda: called.append(1),
                on_show_settings=lambda: None,
                on_quit=lambda: None,
                on_show_history=lambda: None,
                on_about=lambda: None,
                on_help=lambda: None,
            )
            # The action has the shortcut
            assert actions.new_window.shortcut().toString().lower() == "ctrl+n"
            # The window-level QShortcut is also registered
            assert actions.new_window_shortcut.key().toString().lower() == "ctrl+n"
            # Activating the window-level shortcut directly invokes the callback
            actions.new_window_shortcut.activated.emit()
            assert called == [1]
        finally:
            window.close()
            window.deleteLater()


class TestToggleSwitch:
    def test_starts_unchecked(self, qapp: QApplication) -> None:  # noqa: ARG002
        switch = ToggleSwitch()
        assert switch.isChecked() is False

    def test_click_toggles_state(self, qapp: QApplication) -> None:  # noqa: ARG002
        from PySide6.QtCore import QEvent, QPointF
        from PySide6.QtGui import QMouseEvent

        switch = ToggleSwitch()
        received: list[bool] = []
        switch.toggled.connect(received.append)
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(10.0, 10.0),
            QPointF(10.0, 10.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        switch.mouseReleaseEvent(release)
        switch.mouseReleaseEvent(release)
        assert received == [True, False]

    def test_set_checked_does_not_emit(self, qapp: QApplication) -> None:  # noqa: ARG002
        switch = ToggleSwitch()
        received: list[bool] = []
        switch.toggled.connect(received.append)
        switch.setChecked(True)
        assert received == []
        assert switch.isChecked() is True

    def test_paint_does_not_crash(self, qapp: QApplication) -> None:  # noqa: ARG002
        switch = ToggleSwitch()
        switch.show()
        qapp.processEvents()
        switch.setChecked(True)
        switch.repaint()
        switch.setChecked(False)
        switch.repaint()


class TestTotalBar:
    def test_starts_enabled_with_empty_value(self) -> None:
        bar = TotalBar()
        assert bar.is_enabled() is True
        assert bar._value.text() == ""

    def test_set_total_displays_value(self) -> None:
        bar = TotalBar()
        bar.set_total("42")
        assert bar._value.text() == "42"

    def test_set_total_none_clears_value(self) -> None:
        bar = TotalBar()
        bar.set_total("42")
        bar.set_total(None)
        assert bar._value.text() == ""

    def test_disable_clears_value_but_keeps_buffer(self) -> None:
        bar = TotalBar()
        bar.set_total("15")
        bar.set_enabled(False)
        assert bar._value.text() == ""
        assert bar._value_text == "15"
        assert bar.is_enabled() is False

    def test_reenable_restores_value(self) -> None:
        bar = TotalBar()
        bar.set_total("15")
        bar.set_enabled(False)
        bar.set_enabled(True)
        assert bar._value.text() == "15"

    def test_toggle_signal_fires(self, qapp: QApplication) -> None:  # noqa: ARG002
        from PySide6.QtCore import QEvent, QPointF
        from PySide6.QtGui import QMouseEvent

        bar = TotalBar()
        received: list[bool] = []
        bar.toggled.connect(received.append)
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(5.0, 5.0),
            QPointF(5.0, 5.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        bar._switch.mouseReleaseEvent(release)
        bar._switch.mouseReleaseEvent(release)
        assert received == [False, True]
        assert bar._value.text() == ""

    def test_paint_does_not_crash(self, qapp: QApplication) -> None:  # noqa: ARG002
        bar = TotalBar()
        bar.show()
        bar.resize(400, 34)
        qapp.processEvents()
        bar.set_total("99")
        bar.repaint()
        bar.set_enabled(False)
        bar.repaint()
