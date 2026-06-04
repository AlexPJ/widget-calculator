from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QEnterEvent, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from widget_calc.domain.themes import Theme


class EngineIconButton(QWidget):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("engineIcon")
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Settings")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self._accent = QColor("#a6e22e")
        self._bg = QColor("#1f2023")
        self._hovered = False
        self._pressed = False

    def apply_theme(self, theme: Theme) -> None:
        self._accent = QColor(theme.accent)
        self._bg = QColor(theme.surface_bg)
        self.update()

    def _set_hovered(self, hovered: bool) -> None:
        if self._hovered == hovered:
            return
        self._hovered = hovered
        self.update()

    def enterEvent(self, event: QEnterEvent) -> None:  # noqa: N802
        self._set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802
        self._set_hovered(False)
        self._pressed = False
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._pressed:
            self._pressed = False
            if self.rect().contains(event.pos()):
                self.clicked.emit()
                event.accept()
                return
        self._pressed = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2.0

        # Backing circle
        bg_color = QColor(self._bg)
        bg_color.setAlpha(220 if self._hovered or self._pressed else 200)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawEllipse(center, radius, radius)

        # Gear: 6-tooth using a star path
        gear_radius = radius * 0.55
        inner_radius = gear_radius * 0.62
        tooth_offset = radius * 0.10
        teeth = 6
        path = QPainterPath()
        for i in range(teeth * 2):
            angle = (math.pi * 2) * (i / (teeth * 2)) - math.pi / 2
            r = gear_radius + tooth_offset if i % 2 == 0 else gear_radius
            x = center.x() + r * math.cos(angle)
            y = center.y() + r * math.sin(angle)
            if i == 0:
                path.moveTo(QPointF(x, y))
            else:
                path.lineTo(QPointF(x, y))
        path.closeSubpath()

        # Inner hole
        hole = QPainterPath()
        hole.addEllipse(center, inner_radius, inner_radius)

        gear_path = path.subtracted(hole)

        accent = QColor(self._accent)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(accent))
        painter.drawPath(gear_path)

        # Subtle outline
        outline = QColor(self._accent)
        outline.setAlpha(120)
        painter.setPen(QPen(outline, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, gear_radius, gear_radius)
