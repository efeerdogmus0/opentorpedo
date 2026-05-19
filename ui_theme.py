"""
ui_theme.py — Flat technical UI theme (engineering / lab tool style).
"""

from PyQt6.QtWidgets import QLabel


# Plot & visualizer
VIZ_BACKGROUND = "#121212"
PLOT_BACKGROUND = "#121212"
PLOT_GRID_ALPHA = 0.25
PLOT_TRAJECTORY = "#d4d4d8"
PLOT_VELOCITY = "#93c5fd"
PLOT_START_MARKER = "#4ade80"

# Cross-section view
BODY_FILL = "#52525b"
BODY_STROKE = "#71717a"
NOSE_FILL = "#71717a"
FIN_FILL = "#3f3f46"
CAD_FILL = "#404040"
CAD_STROKE = "#a3a3a3"

COG_COLOR = "#f87171"
COB_COLOR = "#60a5fa"
CP_COLOR = "#4ade80"


STYLESHEET = """
QMainWindow, QWidget {
    background-color: #181818;
    color: #e5e5e5;
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 12px;
}
QLabel#panelTitle {
    color: #9ca3af;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 0 4px 0;
}
QLabel#readoutPanel {
    background: #1f1f1f;
    border: 1px solid #333333;
    padding: 8px;
    font-size: 11px;
    color: #a3a3a3;
}
QMenuBar {
    background: #181818;
    color: #e5e5e5;
    border-bottom: 1px solid #333333;
    padding: 2px;
}
QMenuBar::item:selected { background: #2a2a2a; }
QMenu {
    background: #1f1f1f;
    color: #e5e5e5;
    border: 1px solid #333333;
}
QMenu::item:selected { background: #2d3748; }
QSplitter::handle { background: #333333; width: 1px; }
QTabWidget::pane {
    border: 1px solid #333333;
    background: #181818;
    top: -1px;
}
QTabBar::tab {
    background: #1f1f1f;
    color: #9ca3af;
    padding: 6px 14px;
    border: 1px solid #333333;
    border-bottom: none;
    margin-right: -1px;
}
QTabBar::tab:selected {
    background: #181818;
    color: #e5e5e5;
    border-bottom: 1px solid #181818;
}
QGroupBox {
    border: 1px solid #333333;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    font-weight: 600;
    color: #d4d4d4;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #9ca3af;
}
QListWidget {
    background: #1f1f1f;
    border: 1px solid #333333;
    padding: 2px;
    outline: none;
}
QListWidget::item { padding: 4px 6px; }
QListWidget::item:selected {
    background: #2d3748;
    color: #f5f5f5;
}
QDoubleSpinBox, QSpinBox, QComboBox {
    background: #1f1f1f;
    border: 1px solid #404040;
    padding: 3px 6px;
    color: #e5e5e5;
    min-height: 20px;
}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #525252;
}
QComboBox QAbstractItemView {
    background: #1f1f1f;
    color: #e5e5e5;
    selection-background-color: #2d3748;
    border: 1px solid #333333;
}
QPushButton {
    background: #2a2a2a;
    color: #e5e5e5;
    border: 1px solid #404040;
    padding: 5px 12px;
    min-height: 22px;
}
QPushButton:hover { background: #333333; border-color: #525252; }
QPushButton:pressed { background: #262626; }
QPushButton:disabled { color: #6b7280; background: #1f1f1f; }
QPushButton#btnPrimary {
    background: #1e3a5f;
    border-color: #2563eb;
    color: #f5f5f5;
}
QPushButton#btnPrimary:hover { background: #1e40af; }
QPushButton#btnDanger {
    background: #1f1f1f;
    border-color: #7f1d1d;
    color: #fca5a5;
}
QPushButton#btnDanger:hover { background: #2a1515; }
QPushButton#btnSecondary {
    background: #1f1f1f;
    border-color: #404040;
}
QTableWidget {
    background: #1f1f1f;
    border: 1px solid #333333;
    color: #e5e5e5;
    gridline-color: #2a2a2a;
}
QHeaderView::section {
    background: #1a1a1a;
    color: #9ca3af;
    border: none;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
    padding: 4px 6px;
    font-weight: 600;
    font-size: 11px;
}
QProgressBar {
    background: #1f1f1f;
    border: 1px solid #333333;
    text-align: center;
    color: #9ca3af;
    max-height: 16px;
}
QProgressBar::chunk { background: #2563eb; }
QScrollArea { border: none; background: transparent; }
QGraphicsView#profileView {
    background: #121212;
    border: 1px solid #333333;
}
QCheckBox { spacing: 6px; color: #d4d4d4; }
"""


def panel_title(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("panelTitle")
    return lbl


def readout_style() -> str:
    return ""  # use objectName readoutPanel via setObjectName
