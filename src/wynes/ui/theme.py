"""Application-wide Qt stylesheet.

Design language: black / white / gray only. No accent colors, gradients,
glow effects or animations — a restrained, professional diagnostic tool.
"""
from __future__ import annotations

C_BG = "#17181a"
C_PANEL = "#1e2023"
C_CARD = "#232529"
C_BORDER = "#33363c"
C_TEXT = "#e8e9eb"
C_MUTED = "#9aa0a6"

APP_QSS = f"""
QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-size: 13px;
}}
QToolTip {{
    background-color: {C_PANEL};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    padding: 4px;
}}

/* ---- navigation list ---- */
QListWidget#nav {{
    background-color: {C_PANEL};
    border: none;
    outline: none;
    padding: 6px 0;
}}
QListWidget#nav::item {{
    padding: 9px 18px;
    color: {C_MUTED};
}}
QListWidget#nav::item:hover {{
    color: {C_TEXT};
}}
QListWidget#nav::item:selected {{
    background-color: {C_CARD};
    color: {C_TEXT};
    border-left: 3px solid #c8c9cb;
}}

/* ---- headers and muted text ---- */
QLabel[role="h1"] {{ font-size: 20px; font-weight: 600; }}
QLabel[role="h2"] {{ font-size: 15px; font-weight: 600; }}
QLabel[role="muted"] {{ color: {C_MUTED}; }}

/* ---- cards ---- */
QFrame[card="true"] {{
    background-color: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
}}
QFrame[rule="true"] {{
    background-color: {C_BORDER};
    max-height: 1px;
    border: none;
}}

/* ---- status dots ---- */
QLabel[dot="ok"]      {{ color: #d7d9dc; }}
QLabel[dot="planned"] {{ color: #6c7075; }}
QLabel[dot="warn"]    {{ color: #d9c08b; }}
QLabel[dot="error"]   {{ color: #d98b8b; }}

/* ---- input widgets ---- */
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background-color: #191b1d;
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 7px 9px;
    selection-background-color: #3a3e44;
}}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid #5a5f66;
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    background-color: #191b1d;
    border: 1px solid {C_BORDER};
    border-radius: 3px;
}}
QCheckBox::indicator:checked {{
    background-color: #d7d9dc;
    border: 1px solid #d7d9dc;
}}

/* ---- buttons ---- */
QPushButton {{
    background-color: #2c2f34;
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 8px 18px;
}}
QPushButton:hover {{ background-color: #35393f; }}
QPushButton:pressed {{ background-color: #26292d; }}
QPushButton:disabled {{ color: #6d7176; background-color: #26292d; }}
QPushButton[primary="true"] {{
    background-color: #d7d9dc;
    color: #17181a;
    font-weight: 600;
    border: none;
}}
QPushButton[primary="true"]:hover {{ background-color: #ffffff; }}
QPushButton[primary="true"]:disabled {{
    background-color: #3a3d42;
    color: #6d7176;
}}

/* ---- scroll areas ---- */
QScrollArea {{ border: none; }}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #3a3e44;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #4a4f56; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #3a3e44;
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---- combo boxes and spin boxes ---- */
QComboBox {{
    padding: 6px 9px;
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox QAbstractItemView {{
    background-color: {C_PANEL};
    border: 1px solid {C_BORDER};
    selection-background-color: {C_CARD};
    selection-color: {C_TEXT};
    outline: none;
}}
QSpinBox {{
    padding: 6px 9px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: #26292d;
    border: none;
    width: 20px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: #2f3338;
}}

/* ---- tables (result sections) ---- */
QTreeWidget {{
    background-color: #191b1d;
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    alternate-background-color: #1d1f22;
    show-decoration-selected: 0;
}}
QTreeWidget::item {{
    padding: 3px 4px;
}}
QTreeWidget::item:selected {{
    background-color: #2c2f34;
}}
QHeaderView::section {{
    background-color: {C_PANEL};
    color: {C_MUTED};
    border: none;
    border-bottom: 1px solid {C_BORDER};
    padding: 6px 8px;
    font-weight: 600;
}}

/* ---- notice cards (warnings, info banners) ---- */
QFrame[notice="true"] {{
    background-color: #26221c;
    border: 1px solid #4d4030;
    border-radius: 6px;
}}
QFrame[notice="true"] QLabel {{
    background-color: transparent;
}}

/* ---- version chip ---- */
QLabel[chip="true"] {{
    background-color: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 9px;
    padding: 2px 10px;
    color: {C_MUTED};
}}

/* ---- status bar ---- */
QStatusBar {{ background-color: {C_PANEL}; color: {C_MUTED}; }}
"""
