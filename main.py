#!/usr/bin/env python3
"""PyQPSTricks Studio — Live PSTricks / pdftricks editor & previewer."""

import sys
import os

# Ensure the package root is on sys.path when launched as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PyQPSTricks Studio")
    app.setOrganizationName("PyQPSTricks")
    app.setApplicationVersion("1.0.0")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
