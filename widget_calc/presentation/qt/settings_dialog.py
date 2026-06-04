from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from widget_calc.domain.models import (
    MAX_OPACITY,
    MIN_OPACITY,
    WINDOW_MODE_BOTH,
    WINDOW_MODE_NEW,
    WINDOW_MODE_PREVIOUS,
)
from widget_calc.domain.themes import Theme, all_themes

from .theme_styles import build_stylesheet


class SettingsDialog(QDialog):
    theme_requested = Signal(str)
    startup_requested = Signal(bool)
    always_on_top_requested = Signal(bool)
    opacity_requested = Signal(float)
    new_window_requested = Signal()
    show_history_requested = Signal()
    about_requested = Signal()
    help_requested = Signal()
    window_mode_requested = Signal(str)

    def __init__(
        self,
        current_theme_id: str,
        current_opacity: float,
        current_startup: bool,
        current_always_on_top: bool,
        current_window_mode: str = WINDOW_MODE_BOTH,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("Settings")
        self.setMinimumSize(380, 0)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        header = QLabel("Settings")
        header.setObjectName("settingsHeader")
        root.addWidget(header)

        # --- Theme group ---
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setContentsMargins(10, 12, 10, 10)
        theme_layout.setSpacing(6)
        self._theme_buttons: dict[str, QRadioButton] = {}
        for theme in all_themes():
            radio = QRadioButton(theme.name)
            if theme.theme_id == current_theme_id:
                radio.setChecked(True)
            radio.toggled.connect(self._on_theme_toggled(theme.theme_id))
            self._theme_buttons[theme.theme_id] = radio
            theme_layout.addWidget(radio)
        root.addWidget(theme_group)

        # --- Appearance group ---
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        appearance_layout.setContentsMargins(10, 12, 10, 10)
        appearance_layout.setSpacing(10)

        opacity_row = QHBoxLayout()
        opacity_label = QLabel("Opacity")
        opacity_label.setObjectName("settingsHint")
        opacity_row.addWidget(opacity_label)
        self._opacity_value_label = QLabel(f"{int(current_opacity * 100)}%")
        self._opacity_value_label.setObjectName("settingsHint")
        self._opacity_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        opacity_row.addWidget(self._opacity_value_label)
        appearance_layout.addLayout(opacity_row)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setMinimum(int(MIN_OPACITY * 100))
        self._opacity_slider.setMaximum(int(MAX_OPACITY * 100))
        self._opacity_slider.setSingleStep(1)
        self._opacity_slider.setPageStep(5)
        self._opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._opacity_slider.setTickInterval(25)
        self._opacity_slider.setValue(int(current_opacity * 100))
        self._opacity_slider.valueChanged.connect(self._on_slider_moved)
        appearance_layout.addWidget(self._opacity_slider)

        self._always_on_top = QCheckBox("Always on top")
        self._always_on_top.setChecked(current_always_on_top)
        self._always_on_top.toggled.connect(self.always_on_top_requested.emit)
        appearance_layout.addWidget(self._always_on_top)

        root.addWidget(appearance_group)

        # --- Startup group ---
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)
        startup_layout.setContentsMargins(10, 12, 10, 10)
        startup_layout.setSpacing(6)
        self._startup_checkbox = QCheckBox("Start when Windows boots")
        self._startup_checkbox.setChecked(current_startup)
        self._startup_checkbox.toggled.connect(self.startup_requested.emit)
        startup_layout.addWidget(self._startup_checkbox)
        root.addWidget(startup_group)

        # --- Window management group ---
        windows_group = QGroupBox("Windows")
        windows_layout = QVBoxLayout(windows_group)
        windows_layout.setContentsMargins(10, 12, 10, 10)
        windows_layout.setSpacing(6)
        self._window_mode_buttons: dict[str, QRadioButton] = {}
        for mode_id, label in (
            (WINDOW_MODE_PREVIOUS, "Keep previous window only"),
            (WINDOW_MODE_NEW, "Start fresh each time"),
            (WINDOW_MODE_BOTH, "Keep all open windows"),
        ):
            radio = QRadioButton(label)
            if mode_id == current_window_mode:
                radio.setChecked(True)
            radio.toggled.connect(self._on_window_mode_toggled(mode_id))
            self._window_mode_buttons[mode_id] = radio
            windows_layout.addWidget(radio)
        root.addWidget(windows_group)

        # --- Quick actions ---
        actions_group = QGroupBox("Quick actions")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setContentsMargins(10, 12, 10, 10)
        actions_layout.setSpacing(6)
        new_window_btn = QPushButton("New calculator window")
        new_window_btn.setObjectName("settingsAction")
        new_window_btn.clicked.connect(self.new_window_requested.emit)
        actions_layout.addWidget(new_window_btn)
        self._new_window_button = new_window_btn

        history_btn = QPushButton("Show command history")
        history_btn.setObjectName("settingsAction")
        history_btn.clicked.connect(self.show_history_requested.emit)
        actions_layout.addWidget(history_btn)
        self._history_button = history_btn
        root.addWidget(actions_group)

        # --- Help row ---
        help_row = QHBoxLayout()
        about_btn = QPushButton("About")
        about_btn.clicked.connect(self.about_requested.emit)
        help_btn = QPushButton("Help")
        help_btn.clicked.connect(self.help_requested.emit)
        help_row.addWidget(about_btn)
        help_row.addWidget(help_btn)
        help_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        help_row.addWidget(close_btn)
        root.addLayout(help_row)

        self._opacity_debounce = QTimer(self)
        self._opacity_debounce.setSingleShot(True)
        self._opacity_debounce.setInterval(120)
        self._opacity_debounce.timeout.connect(self._emit_opacity)

    def _on_theme_toggled(self, theme_id: str) -> Callable[[bool], None]:
        def handler(checked: bool) -> None:
            if checked:
                self.theme_requested.emit(theme_id)

        return handler

    def _on_window_mode_toggled(self, mode_id: str) -> Callable[[bool], None]:
        def handler(checked: bool) -> None:
            if checked:
                self.window_mode_requested.emit(mode_id)

        return handler

    def _on_slider_moved(self, value: int) -> None:
        self._opacity_value_label.setText(f"{value}%")
        self._opacity_debounce.start()

    def _emit_opacity(self) -> None:
        value = self._opacity_slider.value() / 100.0
        self.opacity_requested.emit(value)

    def set_startup_state(self, enabled: bool) -> None:
        self._startup_checkbox.blockSignals(True)
        self._startup_checkbox.setChecked(enabled)
        self._startup_checkbox.blockSignals(False)

    def set_always_on_top_state(self, enabled: bool) -> None:
        self._always_on_top.blockSignals(True)
        self._always_on_top.setChecked(enabled)
        self._always_on_top.blockSignals(False)

    def set_theme_state(self, theme_id: str) -> None:
        button = self._theme_buttons.get(theme_id)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(True)
        button.blockSignals(False)

    def set_window_mode_state(self, mode_id: str) -> None:
        button = self._window_mode_buttons.get(mode_id)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(True)
        button.blockSignals(False)

    def set_opacity_value(self, opacity: float) -> None:
        self._opacity_slider.blockSignals(True)
        self._opacity_slider.setValue(int(opacity * 100))
        self._opacity_slider.blockSignals(False)
        self._opacity_value_label.setText(f"{int(opacity * 100)}%")

    def apply_theme(self, theme: Theme) -> None:
        self.setStyleSheet(build_stylesheet(theme))
        for theme_obj in all_themes():
            btn = self._theme_buttons.get(theme_obj.theme_id)
            if btn is not None:
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        for child in self.findChildren(QFrame):
            child.style().unpolish(child)
            child.style().polish(child)
