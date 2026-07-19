from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QSplitter
)
from PyQt6.QtCore import Qt
import json
import os


class OKFDashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("OKF Dashboard")
        title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Ontology Knowledge Framework - Symbol knowledge graph explorer")
        subtitle.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(subtitle)

        # Splitter: tree left, details right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Knowledge tree
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.knowledge_tree = QTreeWidget()
        self.knowledge_tree.setHeaderLabel("Symbol Ontology")
        self.knowledge_tree.setStyleSheet("""
            QTreeWidget { background: #16213e; color: #ccc; border: 1px solid #1a1a3e;
                          border-radius: 6px; font-size: 12px; }
            QTreeWidget::item:hover { background: #1a1a3e; }
        """)
        self.knowledge_tree.itemClicked.connect(self._on_item_clicked)
        left_layout.addWidget(self.knowledge_tree)

        load_btn = QPushButton("Load Knowledge Base")
        load_btn.clicked.connect(self._load_knowledge)
        left_layout.addWidget(load_btn)

        splitter.addWidget(left)

        # Right: details
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.detail_display = QTextEdit()
        self.detail_display.setReadOnly(True)
        self.detail_display.setStyleSheet("""
            QTextEdit { background: #0f3460; color: #e0e0e0; border: 1px solid #1a1a3e;
                        border-radius: 6px; padding: 15px; font-size: 13px; }
        """)
        self.detail_display.setPlaceholderText("Select a symbol to view details...")
        right_layout.addWidget(self.detail_display)

        splitter.addWidget(right)
        splitter.setSizes([300, 400])

        layout.addWidget(splitter, 1)

        # Load automatically
        self._load_knowledge()

    def _load_knowledge(self):
        self.knowledge_tree.clear()
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base, "assets", "legend_classification.json")

        if not os.path.exists(json_path):
            self.detail_display.setText("Knowledge base not found. Place legend_classification.json in assets/")
            return

        with open(json_path, 'r') as f:
            data = json.load(f)

        classes = data.get("legend_classification", {}).get("classes", {})
        root = QTreeWidgetItem(self.knowledge_tree)
        root.setText(0, "P&ID Symbols")
        root.setExpanded(True)

        for parent_name, info in classes.items():
            subclasses = info.get("subclasses", [])
            parent_item = QTreeWidgetItem(root)
            parent_item.setText(0, f"{parent_name} ({len(subclasses)})")
            parent_item.setExpanded(False)
            for sub in subclasses:
                child = QTreeWidgetItem(parent_item)
                child.setText(0, sub.replace("_", " "))
                child.setData(0, Qt.ItemDataRole.UserRole, {"parent": parent_name, "subclass": sub})

        self.detail_display.setText(f"Loaded {len(classes)} parent classes.\nClick a symbol to view details.")

    def _on_item_clicked(self, item, col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.detail_display.setText(
                f"<b>Parent Class:</b> {data['parent']}<br>"
                f"<b>Subclass:</b> {data['subclass']}<br><br>"
                f"<i>DINOv2 embeddings available for reclassification.</i>"
            )
        else:
            self.detail_display.setText(f"<b>{item.text(0)}</b>")
