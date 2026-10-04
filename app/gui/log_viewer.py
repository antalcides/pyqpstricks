import os
from typing import List

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.compiler import LaTeXError

class LaTeXLogViewer(QTabWidget):
    """Bottom panel displaying compilation logs and structured errors list."""

    line_selected = Signal(int)  # Emits line number when double-clicked

    def __init__(self, parent=None, is_dark: bool = True):
        super().__init__(parent)
        self.is_dark = is_dark

        # Tab 1: Error List
        self.list_errors = QListWidget(self)
        self.list_errors.itemDoubleClicked.connect(self._on_error_double_clicked)

        # Tab 2: Raw Console Log
        self.txt_raw_log = QTextEdit(self)
        self.txt_raw_log.setReadOnly(True)
        font = QFont("Consolas" if os.name == "nt" else "Monospace", 9)
        self.txt_raw_log.setFont(font)

        self.addTab(self.list_errors, "Errors & Warnings (0)")
        self.addTab(self.txt_raw_log, "Compilation Log")

        self.set_theme(is_dark)

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark

    def clear(self):
        self.list_errors.clear()
        self.txt_raw_log.clear()
        self.setTabText(0, "Errors & Warnings (0)")

    def append_log(self, text: str):
        self.txt_raw_log.append(text.rstrip())

    def set_errors(self, errors: List[LaTeXError]):
        self.list_errors.clear()
        self.setTabText(0, f"Errors & Warnings ({len(errors)})")

        for err in errors:
            item_text = f"Line {err.line_number}: {err.message}"
            if err.context:
                item_text += f" -> ({err.context})"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, err.line_number)
            item.setForeground(QColor("#F44336") if self.is_dark else QColor("#D32F2F"))
            self.list_errors.addItem(item)

        if errors:
            self.setCurrentIndex(0)

    def _on_error_double_clicked(self, item: QListWidgetItem):
        line_num = item.data(Qt.ItemDataRole.UserRole)
        if line_num:
            self.line_selected.emit(line_num)
