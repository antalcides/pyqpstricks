import json
import os
from typing import Dict, List

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

class SnippetsDockWidget(QDockWidget):
    """Dockable side panel with categorized PSTricks snippets."""

    snippet_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__("PSTricks Snippets Library", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self.container = QWidget(self)
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(4, 4, 4, 4)

        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("Filter snippets...")
        self.txt_search.textChanged.connect(self._filter_snippets)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout.addWidget(self.txt_search)
        layout.addWidget(self.tree)

        self.setWidget(self.container)

        self.load_snippets()

    def load_snippets(self):
        res_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources")
        json_path = os.path.join(res_dir, "snippets.json")

        if not os.path.exists(json_path):
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data: Dict[str, List[dict]] = json.load(f)

            self.tree.clear()
            for category, items in data.items():
                cat_item = QTreeWidgetItem(self.tree, [category])
                cat_item.setExpanded(True)
                for item in items:
                    sub_item = QTreeWidgetItem(cat_item, [item["name"]])
                    sub_item.setData(0, Qt.ItemDataRole.UserRole, item["code"])

        except Exception as e:
            print(f"Error loading snippets.json: {e}")

    def _filter_snippets(self, text: str):
        search = text.lower()
        for i in range(self.tree.topLevelItemCount()):
            cat_item = self.tree.topLevelItem(i)
            cat_visible = False
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                matches = search in child.text(0).lower()
                child.setHidden(not matches)
                if matches:
                    cat_visible = True
            cat_item.setHidden(not cat_visible)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        code = item.data(0, Qt.ItemDataRole.UserRole)
        if code:
            self.snippet_selected.emit(code)
