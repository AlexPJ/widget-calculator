from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget

from widget_calc.domain.themes import Theme


class TitleBar(QWidget):
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()
    double_clicked = Signal()

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(32)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(0)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("titleBarTitle")
        self._subtitle_label = QLabel("")
        self._subtitle_label.setObjectName("titleBarSubtitle")

        layout.addWidget(self._title_label, stretch=1)
        layout.addWidget(self._subtitle_label, stretch=0)

        self._min_button = QToolButton(self)
        self._min_button.setObjectName("titleBarButton")
        self._min_button.setText("\u2014")  # em dash
        self._min_button.setToolTip("Minimize")
        self._min_button.setFixedSize(32, 32)
        self._min_button.clicked.connect(self.minimize_clicked)

        self._max_button = QToolButton(self)
        self._max_button.setObjectName("titleBarButton")
        self._max_button.setText("\u25A1")  # white square
        self._max_button.setToolTip("Maximize")
        self._max_button.setFixedSize(32, 32)
        self._max_button.clicked.connect(self.maximize_clicked)

        self._close_button = QToolButton(self)
        self._close_button.setObjectName("titleBarButton#titleBarCloseButton")
        self._close_button.setText("\u2715")  # multiplication x
        self._close_button.setToolTip("Close")
        self._close_button.setFixedSize(32, 32)
        self._close_button.clicked.connect(self.close_clicked)

        layout.addWidget(self._min_button)
        layout.addWidget(self._max_button)
        layout.addWidget(self._close_button)

        self._drag_offset: QPoint | None = None

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        self._subtitle_label.setText(subtitle)

    def set_maximized(self, maximized: bool) -> None:
        self._max_button.setText("\u2750" if maximized else "\u25A1")
        self._max_button.setToolTip("Restore" if maximized else "Maximize")

    def apply_theme(self, theme: Theme) -> None:  # noqa: ARG002
        # QSS handles theming; this hook stays for symmetry.
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_offset is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        window = self.window()
        window_handle = window.windowHandle() if window is not None else None
        if window_handle is not None:
            window_handle.startSystemMove()
            self._drag_offset = None
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
