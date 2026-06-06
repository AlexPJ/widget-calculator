from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QCursor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QMoveEvent,
    QPainterPath,
    QResizeEvent,
    QTextOption,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from widget_calc.domain.models import MAX_OPACITY, MIN_OPACITY
from widget_calc.domain.themes import Theme

from .calculator_icon import cached_app_icon
from .engine_icon import EngineIconButton
from .result_editor import ResultEditor
from .theme_styles import build_stylesheet
from .title_bar import TitleBar
from .total_bar import TotalBar

WINDOW_RADIUS = 10
MENU_HIDE_DELAY_MS = 250
RESIZE_MARGIN = 6
SPLITTER_HANDLE_WIDTH = 2
PANE_BORDER = 1
ENGINE_ICON_PADDING = 4
INPUT_PANE_LEFT_MARGIN = 8


class _ResizeCursorFilter(QObject):
    """App-level event filter that updates the cursor over resize edges.

    Catches mouse moves on child widgets and re-points the cursor at the
    parent window when the mouse is over a resize area.
    """

    def __init__(self, window: CalculatorWindow) -> None:
        super().__init__()
        self._window: CalculatorWindow | None = window

    def detach(self) -> None:
        self._window = None

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        window = self._window
        if window is None:
            return super().eventFilter(obj, event)
        try:
            if not isinstance(obj, QWidget) or not window.isAncestorOf(obj):
                return super().eventFilter(obj, event)
        except RuntimeError:
            return super().eventFilter(obj, event)

        etype = event.type()
        if etype == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
            try:
                local_pos = event.position().toPoint() if hasattr(event, "position") else QPoint(event.pos())
                global_pos = obj.mapToGlobal(local_pos)
                window_pos = window.mapFromGlobal(global_pos)
                window._update_cursor_for_pos(window_pos)  # noqa: SLF001
            except RuntimeError:
                self.detach()
        elif etype in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
            try:
                inside = window.rect().contains(window.mapFromGlobal(QCursor.pos()))
                if inside:
                    window._update_cursor_for_pos(window.mapFromGlobal(QCursor.pos()))  # noqa: SLF001
                else:
                    window._reset_cursor()  # noqa: SLF001
            except RuntimeError:
                self.detach()
        return super().eventFilter(obj, event)


class CalculatorWindow(QMainWindow):
    editor_text_changed = Signal()
    alt_pressed = Signal()
    alt_released = Signal()
    window_activated = Signal()
    geometry_changed = Signal(int, int, int, int)

    def __init__(
        self,
        window_id: str,
        title: str,
        on_open_settings: Callable[[], None],
        initial_opacity: float = MAX_OPACITY,
    ) -> None:
        super().__init__()
        self.window_id = window_id
        self._close_handler: Callable[[CalculatorWindow], bool] | None = None
        self._history_dialog: QDialog | None = None
        self._theme: Theme | None = None
        self._on_open_settings = on_open_settings
        self._maximized = False

        self.setObjectName("calculatorWindow")
        self.setWindowTitle(title)
        self.setMinimumSize(380, 220)
        self.resize(620, 340)

        # Frameless, always on top, with our own custom title bar.
        # WindowSystemMenuHint keeps the taskbar icon visible on Windows
        # even though we draw our own title bar.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.WindowSystemMenuHint, True)
        self.setWindowIcon(cached_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self.title_bar = TitleBar(title, self)
        self.editor = QPlainTextEdit()
        self.results = ResultEditor(self)
        self.engine_icon = EngineIconButton(self)
        self.total_bar = TotalBar(self)
        self._total_enabled: bool = True
        self._on_total_toggled: Callable[[bool], None] | None = None

        self._build_layout()

        self.editor.setObjectName("inputEditor")
        self.editor.setPlaceholderText("x = 1\ny = 1\nx + y\n10 km to m\n20 usd to eur\nnow('UTC')")
        self.editor.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        editor_font = QFont("Cascadia Mono")
        editor_font.setStyleHint(QFont.StyleHint.Monospace)
        editor_font.setPointSize(11)
        self.editor.setFont(editor_font)

        self._link_scrollbars()

        self.title_bar.minimize_clicked.connect(self._on_minimize)
        self.title_bar.maximize_clicked.connect(self._on_toggle_maximize)
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.double_clicked.connect(self._on_toggle_maximize)
        self.engine_icon.clicked.connect(self._on_open_settings)
        self.editor.textChanged.connect(self.editor_text_changed.emit)
        self.total_bar.toggled.connect(self._on_total_toggle_requested)

        self._menu_hide_timer = QTimer(self)
        self._menu_hide_timer.setSingleShot(True)
        self._menu_hide_timer.setInterval(MENU_HIDE_DELAY_MS)
        self._menu_hide_timer.timeout.connect(self._hide_menu_bar)

        self._cursor_filter: _ResizeCursorFilter | None = _ResizeCursorFilter(self)
        app_instance = QApplication.instance()
        if app_instance is not None and self._cursor_filter is not None:
            app_instance.installEventFilter(self._cursor_filter)

        self._apply_opacity(initial_opacity)
        self._apply_window_mask()

    def _build_layout(self) -> None:
        root = QFrame()
        root.setObjectName("rootPanel")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 4)
        root_layout.setSpacing(0)

        root_layout.addWidget(self.title_bar)

        self.input_pane = QFrame()
        self.input_pane.setObjectName("inputPane")
        input_pane_layout = QVBoxLayout(self.input_pane)
        # Symmetric layout with the result pane: no left/right margin so the
        # editor fills the full pane width. The editor's own internal padding
        # (8px 4px) provides the text spacing from the rounded border.
        input_pane_layout.setContentsMargins(0, 4, 0, 0)
        input_pane_layout.setSpacing(0)
        input_pane_layout.addWidget(self.editor, stretch=1)

        self._input_spacer = QWidget()
        self._input_spacer.setFixedHeight(self.total_bar.height())
        self._input_spacer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        input_pane_layout.addWidget(self._input_spacer)

        self.result_pane = QFrame()
        self.result_pane.setObjectName("resultPane")
        result_pane_layout = QVBoxLayout(self.result_pane)
        # No left/right/bottom margin so the total bar fills the full pane
        # width and sits flush against the bottom border. The total bar's
        # own internal margins (12px) provide content spacing.
        result_pane_layout.setContentsMargins(0, 4, 0, 0)
        result_pane_layout.setSpacing(0)
        result_pane_layout.addWidget(self.results, stretch=1)
        result_pane_layout.addWidget(self.total_bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("mainSplitter")
        self.splitter.addWidget(self.input_pane)
        self.splitter.addWidget(self.result_pane)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([390, 230])
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)

        root_layout.addWidget(self.splitter, stretch=1)

        self.setCentralWidget(root)

        self.engine_icon.setParent(self.input_pane)
        self.engine_icon.raise_()
        self._position_engine_icon()
        self.input_pane.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if obj is self.input_pane and event.type() == QEvent.Type.Resize:
            self._position_engine_icon()
        return super().eventFilter(obj, event)

    def _position_engine_icon(self) -> None:
        if self.input_pane is None:
            return
        # Place the icon at the bottom-left of the input pane (the visible
        # rounded box), just inside the 1px border with a small padding.
        x = PANE_BORDER + ENGINE_ICON_PADDING
        y = (
            self.input_pane.height()
            - PANE_BORDER
            - self.engine_icon.height()
        )
        self.engine_icon.move(max(0, x), max(0, y))

    def _get_resize_edges(self, pos: QPoint) -> Qt.Edge:
        edges = Qt.Edge(0)
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        if self._maximized:
            return edges
        title_h = self.title_bar.height() if self.title_bar is not None else 0
        if y < title_h:
            return edges
        on_left = x < RESIZE_MARGIN
        on_right = x >= w - RESIZE_MARGIN
        on_bottom = y >= h - RESIZE_MARGIN
        if on_left:
            edges |= Qt.Edge.LeftEdge
        if on_right:
            edges |= Qt.Edge.RightEdge
        if on_bottom:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _cursor_for_edges(self, edges: Qt.Edge) -> Qt.CursorShape:
        has_left = bool(edges & Qt.Edge.LeftEdge)
        has_right = bool(edges & Qt.Edge.RightEdge)
        has_bottom = bool(edges & Qt.Edge.BottomEdge)
        if has_bottom and has_left:
            return Qt.CursorShape.SizeBDiagCursor
        if has_bottom and has_right:
            return Qt.CursorShape.SizeFDiagCursor
        if has_left or has_right:
            return Qt.CursorShape.SizeHorCursor
        if has_bottom:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def _update_cursor_for_pos(self, pos: QPoint) -> None:
        edges = self._get_resize_edges(pos)
        if edges:
            cursor_shape = self._cursor_for_edges(edges)
            if self.cursor().shape() != cursor_shape:
                self.setCursor(QCursor(cursor_shape))
        else:
            self._reset_cursor()

    def _reset_cursor(self) -> None:
        if self.cursor().shape() != Qt.CursorShape.ArrowCursor:
            self.unsetCursor()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._update_cursor_for_pos(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._get_resize_edges(event.position().toPoint())
            handle = self.windowHandle()
            if edges and handle is not None:
                handle.startSystemResize(edges)
                event.accept()
                return
        super().mousePressEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802
        self._reset_cursor()
        super().leaveEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_engine_icon()
        self._apply_window_mask()
        self._emit_geometry()

    def moveEvent(self, event: QMoveEvent) -> None:  # noqa: N802
        super().moveEvent(event)
        self._emit_geometry()

    def _emit_geometry(self) -> None:
        if self.isMaximized() or self.isMinimized() or self.isFullScreen():
            return
        self.geometry_changed.emit(self.x(), self.y(), self.width(), self.height())

    def _apply_window_mask(self) -> None:
        if self._maximized:
            self.clearMask()
            return
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0.0, 0.0, float(self.width()), float(self.height())),
            WINDOW_RADIUS,
            WINDOW_RADIUS,
        )
        self.setMask(path.toFillPolygon(QTransform()).toPolygon())

    def _link_scrollbars(self) -> None:
        editor_scroll = self.editor.verticalScrollBar()
        results_scroll = self.results.verticalScrollBar()
        editor_scroll.valueChanged.connect(results_scroll.setValue)
        results_scroll.valueChanged.connect(editor_scroll.setValue)

    def _on_minimize(self) -> None:
        self.showMinimized()

    def _on_toggle_maximize(self) -> None:
        if self._maximized:
            self.showNormal()
            self._maximized = False
        else:
            self.showMaximized()
            self._maximized = True
        self.title_bar.set_maximized(self._maximized)
        self._apply_window_mask()

    def apply_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.title_bar.apply_theme(theme)
        self.engine_icon.apply_theme(theme)
        self.total_bar.apply_theme(theme)
        self.setStyleSheet(build_stylesheet(theme))
        if self._history_dialog is not None:
            self._history_dialog.setStyleSheet(build_stylesheet(theme))

    def set_total(self, value: str | None) -> None:
        self.total_bar.set_total(value)

    def set_total_enabled(self, enabled: bool) -> None:
        if self._total_enabled == enabled:
            self.total_bar.set_enabled(enabled)
            return
        self._total_enabled = enabled
        self.total_bar.set_enabled(enabled)

    def set_total_toggle_handler(self, handler: Callable[[bool], None]) -> None:
        self._on_total_toggled = handler

    def _on_total_toggle_requested(self, enabled: bool) -> None:
        if self._on_total_toggled is not None:
            self._on_total_toggled(enabled)

    def set_results(self, lines: list[str]) -> None:
        self.results.blockSignals(True)
        self.results.setPlainText("\n".join(lines))
        self.results.blockSignals(False)

    def editor_text(self) -> str:
        return self.editor.toPlainText()

    def set_editor_text(self, text: str) -> None:
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)

    def set_close_handler(self, handler: Callable[[CalculatorWindow], bool]) -> None:
        self._close_handler = handler

    def set_opacity(self, value: float) -> None:
        self._apply_opacity(value)

    def _apply_opacity(self, value: float) -> None:
        clamped = min(MAX_OPACITY, max(MIN_OPACITY, float(value)))
        self.setWindowOpacity(clamped)

    def set_title_text(self, title: str) -> None:
        self.title_bar.set_title(title)

    def set_subtitle_text(self, subtitle: str) -> None:
        self.title_bar.set_subtitle(subtitle)

    def show_history_dialog(self, history_items: list[str], theme: Theme) -> None:
        if self._history_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Command History")
            dialog.resize(520, 360)

            history_box = QPlainTextEdit(dialog)
            history_box.setObjectName("historyBox")
            history_box.setReadOnly(True)
            history_box.setWordWrapMode(QTextOption.WrapMode.NoWrap)

            close_button = QPushButton("Close", dialog)
            close_button.clicked.connect(dialog.close)

            body = QVBoxLayout(dialog)
            body.addWidget(history_box)
            body.addWidget(close_button)

            self._history_dialog = dialog

        self._history_dialog.setStyleSheet(build_stylesheet(theme))
        found_box: QPlainTextEdit | None = self._history_dialog.findChild(QPlainTextEdit, "historyBox")
        if found_box is not None:
            found_box.setPlainText("\n".join(history_items) if history_items else "No commands yet.")

        self._history_dialog.show()
        self._history_dialog.raise_()
        self._history_dialog.activateWindow()

    def show_menu_bar(self) -> None:
        self._menu_hide_timer.stop()
        bar = self.menuBar()
        if not bar.isVisible():
            bar.setVisible(True)
            self.title_bar.set_menu_visible(True)
            bar.setFocus()

    def has_active_menu_popup(self) -> bool:
        bar = self.menuBar()
        return any(menu.isVisible() for menu in bar.findChildren(QMenu))

    def _hide_menu_bar(self) -> None:
        if self.has_active_menu_popup():
            self._menu_hide_timer.start()
            return
        self.menuBar().setVisible(False)
        self.title_bar.set_menu_visible(False)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Alt:
            self.alt_pressed.emit()
            self.show_menu_bar()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Alt:
            self.alt_released.emit()
            self._menu_hide_timer.start()
        super().keyReleaseEvent(event)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        if event.type() == QEvent.Type.WindowStateChange:
            self._maximized = bool(self.windowState() & Qt.WindowState.WindowMaximized)
            self.title_bar.set_maximized(self._maximized)
            self._apply_window_mask()
        elif event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.window_activated.emit()
        super().changeEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._close_handler and self._close_handler(self):
            event.ignore()
            return
        if hasattr(self, "_cursor_filter") and self._cursor_filter is not None:
            self._cursor_filter.detach()
            self._cursor_filter = None
        super().closeEvent(event)
