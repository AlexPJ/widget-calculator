from __future__ import annotations

from widget_calc.domain.themes import Theme


def build_stylesheet(theme: Theme) -> str:
    return f"""
    QMainWindow#calculatorWindow {{
        background: {theme.window_bg};
        color: {theme.text};
    }}
    QFrame#rootPanel {{
        background: {theme.window_bg};
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        border-bottom-left-radius: 10px;
        border-bottom-right-radius: 10px;
    }}

    /* Custom title bar */
    QWidget#titleBar {{
        background: {theme.surface_bg};
        border: none;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }}
    QLabel#titleBarTitle {{
        color: {theme.text};
        font-size: 11pt;
        font-weight: 600;
        padding-left: 10px;
    }}
    QLabel#titleBarSubtitle {{
        color: {theme.muted_text};
        font-size: 9pt;
        padding-right: 4px;
    }}
    QToolButton#titleBarButton {{
        background: transparent;
        color: {theme.muted_text};
        border: none;
        padding: 0;
        font-size: 10pt;
        font-family: "Segoe MDL2 Assets", "Segoe Fluent Icons", sans-serif;
        border-radius: 4px;
    }}
    QToolButton#titleBarButton:hover {{
        background: {theme.selection};
        color: {theme.text};
    }}
    QToolButton#titleBarButton#titleBarCloseButton:hover {{
        background: {theme.danger};
        color: #ffffff;
    }}

    /* Editor panes (input + results) */
    QFrame#inputPane {{
        background: {theme.window_bg};
    }}
    QFrame#resultPane {{
        background: {theme.window_bg};
        border: 1px solid {theme.border};
        border-radius: 10px;
    }}
    QPlainTextEdit#inputEditor {{
        background: {theme.editor_bg};
        color: {theme.text};
        border: 1px solid {theme.border};
        border-radius: 10px;
        padding: 8px 4px;
        selection-background-color: {theme.selection};
    }}
    QPlainTextEdit#resultEditor {{
        background: {theme.results_bg};
        color: {theme.accent};
        border: none;
        border-radius: 0;
        padding: 8px 4px;
        selection-background-color: {theme.selection};
    }}

    /* Total bar inside the result pane */
    QFrame#totalBar {{
        background: {theme.results_bg};
        border: none;
    }}

    /* Splitter handle - nearly invisible, shows a 1px dot on hover */
    QSplitter#mainSplitter::handle {{
        background: transparent;
    }}
    QSplitter#mainSplitter::handle:horizontal {{
        width: 6px;
        background: transparent;
    }}
    QSplitter#mainSplitter::handle:horizontal:hover {{
        background: {theme.border};
    }}

    /* Engine (gear) icon overlay */
    QWidget#engineIcon {{
        background: {theme.surface_bg};
        border: 1px solid {theme.border};
        border-radius: 11px;
    }}
    QWidget#engineIcon:hover {{
        border: 1px solid {theme.accent};
    }}

    /* Menus */
    QMenuBar {{
        background: {theme.surface_bg};
        color: {theme.text};
        border-bottom: 1px solid {theme.border};
        padding: 1px 4px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 2px 10px;
    }}
    QMenuBar::item:selected {{
        background: {theme.selection};
        border-radius: 4px;
    }}
    QMenu {{
        background: {theme.surface_bg};
        color: {theme.text};
        border: 1px solid {theme.border};
        padding: 4px 0;
    }}
    QMenu::item {{
        padding: 6px 24px 6px 18px;
    }}
    QMenu::item:selected {{
        background: {theme.selection};
    }}
    QMenu::separator {{
        height: 1px;
        background: {theme.border};
        margin: 4px 8px;
    }}

    /* Buttons */
    QPushButton {{
        background: {theme.accent};
        color: #101010;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        background: {theme.accent_hover};
    }}

    /* Settings dialog controls */
    QDialog#settingsDialog {{
        background: {theme.window_bg};
        color: {theme.text};
    }}
    QLabel#settingsHeader {{
        color: {theme.text};
        font-size: 13pt;
        font-weight: 700;
    }}
    QLabel#settingsSection {{
        color: {theme.accent};
        font-size: 10pt;
        font-weight: 600;
        padding-top: 6px;
    }}
    QLabel#settingsHint {{
        color: {theme.muted_text};
        font-size: 9pt;
    }}
    QFrame#settingsGroup {{
        background: {theme.surface_bg};
        border: 1px solid {theme.border};
        border-radius: 10px;
    }}
    QGroupBox {{
        border: 1px solid {theme.border};
        border-radius: 8px;
        margin-top: 14px;
        padding: 10px 8px 8px 8px;
        color: {theme.muted_text};
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
        color: {theme.accent};
    }}
    QRadioButton, QCheckBox {{
        color: {theme.text};
        spacing: 8px;
    }}
    QRadioButton::indicator, QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        background: {theme.editor_bg};
        border: 1px solid {theme.border};
        border-radius: 3px;
    }}
    QRadioButton::indicator {{
        border-radius: 7px;
    }}
    QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
        background: {theme.accent};
        border: 1px solid {theme.accent};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {theme.border};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {theme.accent};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {theme.text};
        border: 1px solid {theme.border};
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {theme.accent_hover};
    }}

    /* Tooltips */
    QToolTip {{
        background: {theme.surface_bg};
        color: {theme.text};
        border: 1px solid {theme.border};
        padding: 4px 6px;
    }}
    """
