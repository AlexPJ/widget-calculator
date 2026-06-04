from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import QMenuBar

if TYPE_CHECKING:
    from widget_calc.presentation.qt.window import CalculatorWindow


class MenuActions:
    def __init__(self) -> None:
        self.new_window: QAction
        self.new_window_shortcut: QShortcut
        self.settings: QAction
        self.quit: QAction
        self.undo: QAction
        self.redo: QAction
        self.copy: QAction
        self.paste: QAction
        self.cut: QAction
        self.show_history: QAction
        self.about: QAction
        self.help: QAction


def build_menu_bar(
    window: CalculatorWindow,
    on_new_window: Callable[[], None],
    on_show_settings: Callable[[], None],
    on_quit: Callable[[], None],
    on_show_history: Callable[[], None],
    on_about: Callable[[], None],
    on_help: Callable[[], None],
) -> tuple[QMenuBar, MenuActions]:
    bar = window.menuBar()
    bar.setNativeMenuBar(False)
    bar.setVisible(False)

    actions = MenuActions()

    file_menu = bar.addMenu("&File")
    actions.new_window = QAction("&New window", window)
    actions.new_window.setShortcut(QKeySequence("Ctrl+N"))
    actions.new_window.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    actions.new_window.triggered.connect(on_new_window)
    file_menu.addAction(actions.new_window)
    # Window-level shortcut fallback: works even when the menu bar is hidden
    new_window_shortcut = QShortcut(QKeySequence("Ctrl+N"), window)
    new_window_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
    new_window_shortcut.activated.connect(on_new_window)
    actions.new_window_shortcut = new_window_shortcut

    actions.settings = QAction("&Settings...", window)
    actions.settings.setShortcut(QKeySequence("Ctrl+,"))
    actions.settings.triggered.connect(on_show_settings)
    file_menu.addAction(actions.settings)

    file_menu.addSeparator()

    actions.quit = QAction("&Quit", window)
    actions.quit.setShortcut(QKeySequence("Ctrl+Q"))
    actions.quit.triggered.connect(on_quit)
    file_menu.addAction(actions.quit)

    edit_menu = bar.addMenu("&Edit")
    actions.undo = QAction("&Undo", window)
    actions.undo.setShortcut(QKeySequence.StandardKey.Undo)
    actions.undo.triggered.connect(window.editor.undo)
    edit_menu.addAction(actions.undo)

    actions.redo = QAction("&Redo", window)
    actions.redo.setShortcut(QKeySequence.StandardKey.Redo)
    actions.redo.triggered.connect(window.editor.redo)
    edit_menu.addAction(actions.redo)

    edit_menu.addSeparator()

    actions.cut = QAction("Cu&t", window)
    actions.cut.setShortcut(QKeySequence.StandardKey.Cut)
    actions.cut.triggered.connect(window.editor.cut)
    edit_menu.addAction(actions.cut)

    actions.copy = QAction("&Copy", window)
    actions.copy.setShortcut(QKeySequence.StandardKey.Copy)
    actions.copy.triggered.connect(window.editor.copy)
    edit_menu.addAction(actions.copy)

    actions.paste = QAction("&Paste", window)
    actions.paste.setShortcut(QKeySequence.StandardKey.Paste)
    actions.paste.triggered.connect(window.editor.paste)
    edit_menu.addAction(actions.paste)

    view_menu = bar.addMenu("&View")
    actions.show_history = QAction("Show &history", window)
    actions.show_history.setShortcut(QKeySequence("Ctrl+H"))
    actions.show_history.triggered.connect(on_show_history)
    view_menu.addAction(actions.show_history)

    help_menu = bar.addMenu("&Help")
    actions.about = QAction("&About", window)
    actions.about.triggered.connect(on_about)
    help_menu.addAction(actions.about)
    actions.help = QAction("&Help", window)
    actions.help.setShortcut(QKeySequence("F1"))
    actions.help.triggered.connect(on_help)
    help_menu.addAction(actions.help)

    return bar, actions
