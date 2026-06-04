from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_CORNER_RATIO = 0.18
_SCREEN_HEIGHT_RATIO = 0.22
_BUTTON_AREA_PADDING_RATIO = 0.20
_BUTTON_SPACING_RATIO = 0.18

_DEFAULT_LINE_WIDTHS: tuple[tuple[int, float], ...] = (
    (16, 1.4),
    (24, 1.6),
    (32, 1.8),
    (48, 2.0),
    (64, 2.4),
    (128, 3.0),
    (256, 4.0),
)


def _line_width_for_size(size: int) -> float:
    for threshold, width in _DEFAULT_LINE_WIDTHS:
        if size <= threshold:
            return width
    return _DEFAULT_LINE_WIDTHS[-1][1]


def draw_calculator_icon(painter: QPainter, rect: QRectF, color: QColor) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    size = min(rect.width(), rect.height())
    line_width = max(1.0, _line_width_for_size(int(size)))
    inset = line_width / 2.0
    body = rect.adjusted(inset, inset, -inset, -inset)

    radius = body.width() * _CORNER_RATIO
    body_path = QPainterPath()
    body_path.addRoundedRect(body, radius, radius)

    screen_h = body.height() * _SCREEN_HEIGHT_RATIO
    screen = QRectF(body.x(), body.y(), body.width(), screen_h)

    buttons_top = screen.bottom()
    buttons_bottom = body.bottom()
    buttons_rect = QRectF(body.x(), buttons_top, body.width(), buttons_bottom - buttons_top)

    pad = buttons_rect.width() * _BUTTON_AREA_PADDING_RATIO
    cell_w = (buttons_rect.width() - pad * 2) / 2
    cell_h = (buttons_rect.height() - pad * 2) / 2
    cell_size = min(cell_w, cell_h)
    grid_left = buttons_rect.left() + (buttons_rect.width() - cell_size * 2) / 2
    grid_top = buttons_rect.top() + (buttons_rect.height() - cell_size * 2) / 2

    cells = [
        (grid_left, grid_top),
        (grid_left + cell_size, grid_top),
        (grid_left, grid_top + cell_size),
        (grid_left + cell_size, grid_top + cell_size),
    ]

    pen = QPen(color, line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(body_path)

    painter.drawLine(QPointF(body.left(), screen.bottom()), QPointF(body.right(), screen.bottom()))

    glyph_inset = cell_size * 0.30
    plus = [
        (cells[0][0] + cell_size / 2, cells[0][1] + glyph_inset),
        (cells[0][0] + cell_size / 2, cells[0][1] + cell_size - glyph_inset),
    ]
    painter.drawLine(QPointF(*plus[0]), QPointF(*plus[1]))
    painter.drawLine(
        QPointF(cells[0][0] + glyph_inset, cells[0][1] + cell_size / 2),
        QPointF(cells[0][0] + cell_size - glyph_inset, cells[0][1] + cell_size / 2),
    )

    minus_y = cells[1][1] + cell_size / 2
    painter.drawLine(
        QPointF(cells[1][0] + glyph_inset, minus_y),
        QPointF(cells[1][0] + cell_size - glyph_inset, minus_y),
    )

    cross_inset = cell_size * 0.28
    cx_top = cells[2][0] + cell_size / 2
    cy_top = cells[2][1] + cell_size / 2
    painter.drawLine(
        QPointF(cx_top - cross_inset, cy_top - cross_inset),
        QPointF(cx_top + cross_inset, cy_top + cross_inset),
    )
    painter.drawLine(
        QPointF(cx_top - cross_inset, cy_top + cross_inset),
        QPointF(cx_top + cross_inset, cy_top - cross_inset),
    )

    eq_inset = cell_size * 0.30
    eq_x = cells[3][0]
    eq_y = cells[3][1] + cell_size / 2
    painter.drawLine(
        QPointF(eq_x + eq_inset, eq_y - cell_size * 0.14),
        QPointF(eq_x + cell_size - eq_inset, eq_y - cell_size * 0.14),
    )
    painter.drawLine(
        QPointF(eq_x + eq_inset, eq_y + cell_size * 0.14),
        QPointF(eq_x + cell_size - eq_inset, eq_y + cell_size * 0.14),
    )

    painter.restore()


def build_app_icon(color: QColor | None = None) -> QIcon:
    icon = QIcon()
    brush = color or QColor("#1f2023")

    for size in (16, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            draw_calculator_icon(painter, QRectF(0.0, 0.0, float(size), float(size)), brush)
        finally:
            painter.end()
        icon.addPixmap(pixmap)

    return icon


def cached_app_icon() -> QIcon:
    global _app_icon
    if _app_icon is not None:
        return _app_icon
    _app_icon = build_app_icon()
    return _app_icon


_app_icon: QIcon | None = None
