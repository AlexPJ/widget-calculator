from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import QMenu, QMenuBar

if TYPE_CHECKING:
    from widget_calc.presentation.qt.window import CalculatorWindow


class MenuActions:
    def __init__(self) -> None:
        self.new_window: QAction
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
        self._shortcuts: list[QShortcut]


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
    actions._shortcuts = []

    def add_action(
        menu: QMenu,
        text: str,
        shortcut: QKeySequence | QKeySequence.StandardKey,
        slot: Callable[[], None],
    ) -> QAction:
        action = QAction(text, window)
        action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        # Window-level QShortcut fallback: QAction shortcuts only fire when
        # the action is in an active shortcut chain (visible menu/toolbar).
        # Since the menu bar is hidden by default, add a QShortcut so the
        # key binding works regardless of menu bar visibility.
        sc = QShortcut(shortcut, window)
        sc.setContext(Qt.ShortcutContext.WindowShortcut)
        sc.activated.connect(slot)
        actions._shortcuts.append(sc)
        return action

    file_menu = bar.addMenu("&File")
    actions.new_window = add_action(
        file_menu, "&New window", QKeySequence("Ctrl+N"), on_new_window
    )

    actions.settings = add_action(
        file_menu, "&Settings...", QKeySequence("Ctrl+,"), on_show_settings
    )

    file_menu.addSeparator()

    actions.quit = add_action(
        file_menu, "&Quit", QKeySequence("Ctrl+Q"), on_quit
    )

    edit_menu = bar.addMenu("&Edit")
    actions.undo = add_action(
        edit_menu, "&Undo", QKeySequence.StandardKey.Undo, window.editor.undo
    )

    actions.redo = add_action(
        edit_menu, "&Redo", QKeySequence.StandardKey.Redo, window.editor.redo
    )

    edit_menu.addSeparator()

    actions.cut = add_action(
        edit_menu, "Cu&t", QKeySequence.StandardKey.Cut, window.editor.cut
    )

    actions.copy = add_action(
        edit_menu, "&Copy", QKeySequence.StandardKey.Copy, window.editor.copy
    )

    actions.paste = add_action(
        edit_menu, "&Paste", QKeySequence.StandardKey.Paste, window.editor.paste
    )

    view_menu = bar.addMenu("&View")
    actions.show_history = add_action(
        view_menu, "Show &history", QKeySequence("Ctrl+H"), on_show_history
    )

    help_menu = bar.addMenu("&Help")
    actions.about = add_action(
        help_menu, "&About", QKeySequence(""), on_about
    )
    actions.help = add_action(
        help_menu, "&Help", QKeySequence("F1"), on_help
    )

    return bar, actions
