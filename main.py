#!/usr/bin/env python3
"""
main.py — Entry point for the OpenTorpedo desktop application.

Run with:
    python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from torpedo_model import create_default_torpedo
from config_manager import load_last_session
from ui_components import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    # Set a nicer default font
    font = QFont("Inter", 11)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Try to restore last session, otherwise use default
    session = load_last_session()
    if session is not None:
        torpedo, sim_params, env_params = session
        window = MainWindow(torpedo)
        window._set_sim_params(sim_params)
        window._set_env_params(env_params)
    else:
        torpedo = create_default_torpedo()
        window = MainWindow(torpedo)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
