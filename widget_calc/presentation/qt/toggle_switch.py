from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget

from widget_calc.domain.themes import Theme


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    TRACK_HEIGHT_RATIO = 0.55
    KNOB_INSET = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("toggleSwitch")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(38, 22)

        self._checked = False
        self._accent = QColor("#a6e22e")
        self._track_off = QColor("#3b3d42")
        self._knob = QColor("#f8f8f2")
        self._foreground: QColor = QColor("#f8f8f2")

    def apply_theme(self, theme: Theme) -> None:
        self._accent = QColor(theme.accent)
        self._track_off = QColor(theme.surface_bg)
        self._knob = QColor(theme.text)
        self._foreground = QColor(theme.text)
        self.update()

    def isChecked(self) -> bool:  # noqa: N802 - Qt naming
        return self._checked

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        if self._checked == checked:
            return
        self._checked = checked
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self._checked = not self._checked
            self.toggled.emit(self._checked)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _track_rect(self) -> QRectF:
        height = self.height() * self.TRACK_HEIGHT_RATIO
        y = (self.height() - height) / 2
        return QRectF(0.0, y, float(self.width()), height)

    def _knob_rect(self) -> QRectF:
        diameter = self.height() - self.KNOB_INSET * 2
        x = self.width() - diameter - self.KNOB_INSET if self._checked else self.KNOB_INSET
        return QRectF(x, float(self.KNOB_INSET), diameter, diameter)

    def paintEvent(self, event: QEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            track = self._track_rect()
            radius = track.height() / 2

            color = QColor(self._accent) if self._checked else QColor(self._track_off)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(track, radius, radius)

            knob = self._knob_rect()
            knob_radius = knob.width() / 2
            painter.setBrush(QBrush(self._knob))
            painter.drawEllipse(knob.center(), knob_radius, knob_radius)
        finally:
            painter.end()
