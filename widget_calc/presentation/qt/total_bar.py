from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPaintEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from widget_calc.domain.themes import Theme

from .toggle_switch import ToggleSwitch


class TotalBar(QFrame):
    """Bottom bar showing the running total of result lines.

    - A 1px divider at the top separates it from the result editor.
    - A bold "Total" label dims when the total is disabled.
    - The value label mirrors the value (or clears it) when toggled.
    - The toggle switch enables or disables the running total.
    """

    toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("totalBar")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(28)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._enabled = True
        self._value_text: str = ""

        self._accent = QColor("#a6e22e")
        self._foreground = QColor("#f8f8f2")
        self._muted = QColor("#a8a8a2")
        self._border = QColor("#3d3e42")
        self._background = QColor("#151619")

        self._label = QLabel("Total:", self)
        self._label.setObjectName("totalLabel")
        bold = QFont()
        bold.setBold(True)
        bold.setPointSize(11)
        self._label.setFont(bold)
        self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self._value = QLabel("", self)
        self._value.setObjectName("totalValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        value_font = QFont("Cascadia Mono")
        value_font.setStyleHint(QFont.StyleHint.Monospace)
        value_font.setBold(True)
        value_font.setPointSize(11)
        self._value.setFont(value_font)

        self._switch = ToggleSwitch(self)
        self._switch.setChecked(True)
        self._switch.toggled.connect(self._on_switch_toggled)

        row = QHBoxLayout()
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(12)
        row.addWidget(self._label)
        row.addWidget(self._value, stretch=1)
        row.addWidget(self._switch)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addLayout(row)

        self._apply_label_color()
        self._apply_value_color()

    def apply_theme(self, theme: Theme) -> None:
        self._accent = QColor(theme.accent)
        self._foreground = QColor(theme.text)
        self._muted = QColor(theme.muted_text)
        self._border = QColor(theme.border)
        self._background = QColor(theme.results_bg)
        self._switch.apply_theme(theme)
        self._apply_label_color()
        self._apply_value_color()
        self.update()

    def set_total(self, value: str | None) -> None:
        self._value_text = value or ""
        self._value.setText(self._value_text if self._enabled else "")

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool, *, emit: bool = False) -> None:
        if self._enabled == enabled and self._switch.isChecked() == enabled:
            return
        self._enabled = enabled
        self._switch.setChecked(enabled)
        self._apply_label_color()
        self._value.setText(self._value_text if enabled else "")
        self._apply_value_color()
        if emit:
            self.toggled.emit(enabled)

    def _on_switch_toggled(self, checked: bool) -> None:
        self._enabled = checked
        self._apply_label_color()
        self._value.setText(self._value_text if checked else "")
        self._apply_value_color()
        self.toggled.emit(checked)

    def _apply_label_color(self) -> None:
        color = self._foreground if self._enabled else self._border
        self._label.setStyleSheet(f"color: {color.name()}; background: transparent;")

    def _apply_value_color(self) -> None:
        if self._enabled:
            self._value.setStyleSheet(
                f"color: {self._accent.name()}; background: transparent;"
            )
        else:
            self._value.setStyleSheet(
                f"color: {self._border.name()}; background: transparent;"
            )

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        # Separator is handled by the stylesheet (border-top).
        super().paintEvent(event)
