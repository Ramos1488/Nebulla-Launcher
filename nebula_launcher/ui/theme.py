"""A dark, flat, PolyMC/MultiMC-flavoured Qt stylesheet."""

ACCENT = "#8a5cf6"       # nebula purple
ACCENT_HOVER = "#a179ff"
BG = "#1e1f26"
BG_PANEL = "#26272f"
BG_TILE = "#2d2e38"
BORDER = "#3a3b46"
TEXT = "#e7e7ee"
TEXT_DIM = "#9a9aa8"

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 10.5pt;
}}
QMainWindow, QDialog {{
    background-color: {BG};
}}
#Sidebar {{
    background-color: {BG_PANEL};
    border-right: 1px solid {BORDER};
}}
#Toolbar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
}}
QPushButton {{
    background-color: {BG_TILE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: white;
}}
QPushButton:pressed {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#Primary {{
    background-color: {ACCENT};
    color: white;
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    background-color: {ACCENT_HOVER};
}}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: {BG_TILE};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 8px;
}}
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    background-color: {BG_TILE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin: 6px;
    padding: 10px;
}}
QListWidget::item:selected {{
    border: 1px solid {ACCENT};
    background-color: #34293f;
}}
QLabel#Dim {{
    color: {TEXT_DIM};
}}
QLabel#Title {{
    font-size: 15pt;
    font-weight: 700;
}}
QProgressBar {{
    background-color: {BG_TILE};
    border: 1px solid {BORDER};
    border-radius: 5px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}
QScrollBar:vertical {{
    background: {BG};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
}}
QPlainTextEdit#Console {{
    background-color: #14151a;
    color: #c9c9d4;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 9.5pt;
}}
"""
