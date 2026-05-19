"""
Teknofest fork — sabit CAD geometrisi, değişken: balast + yay.

Çalıştırma (proje kökünden):
    python -m teknofest.main
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from teknofest.ui import TeknofestMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    font = QFont("Inter", 11)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    cad_arg = sys.argv[1] if len(sys.argv) > 1 else None
    window = TeknofestMainWindow(cad_arg)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
