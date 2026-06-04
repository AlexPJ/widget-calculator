from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QTextOption
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QToolTip, QWidget


class ResultEditor(QPlainTextEdit):
    line_copied = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultEditor")
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)

        monospace = QFont("Cascadia Mono")
        monospace.setStyleHint(QFont.StyleHint.Monospace)
        monospace.setPointSize(11)
        self.setFont(monospace)

        self._press_pos: QPointF | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._press_pos is not None
            and (event.position() - self._press_pos).manhattanLength() < 4
        ):
            self._copy_line_at(event.position())
        self._press_pos = None

    def _copy_line_at(self, position: QPointF) -> None:
        cursor = self.cursorForPosition(position.toPoint())
        block = cursor.block()
        text = block.text()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.line_copied.emit(text)
        global_pos = self.mapToGlobal(position.toPoint())
        QToolTip.showText(global_pos, "Copied", self)
