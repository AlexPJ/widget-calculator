from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QMouseEvent, QPaintEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from widget_calc.domain.themes import Theme

from .toggle_switch import ToggleSwitch


class _ClickableLabel(QLabel):
    """QLabel that emits `clicked` on a short left-click."""

    clicked = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._press_pos: QPoint | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._press_pos is not None
            and (event.position().toPoint() - self._press_pos).manhattanLength() < 4
        ):
            self.clicked.emit()
        self._press_pos = None


class TotalBar(QFrame):
    """Bottom bar showing the running total of result lines.

    - A 1px divider at the top separates it from the result editor.
    - A bold "Total" label dims when the total is disabled.
    - The value label mirrors the value (or clears it) when toggled.
    - Clicking the value label copies it to the clipboard.
    - The toggle switch enables or disables the running total.
    """

    toggled = Signal(bool)
    value_copied = Signal(str)

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

        self._value = _ClickableLabel("", self)
        self._value.setObjectName("totalValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        value_font = QFont("Cascadia Mono")
        value_font.setStyleHint(QFont.StyleHint.Monospace)
        value_font.setBold(True)
        value_font.setPointSize(11)
        self._value.setFont(value_font)
        self._value.clicked.connect(self._copy_value)

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

    def _copy_value(self) -> None:
        if not self._value_text or not self._enabled:
            return
        QApplication.clipboard().setText(self._value_text)
        self.value_copied.emit(self._value_text)
        QToolTip.showText(QCursor.pos(), "Copied", self)

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
