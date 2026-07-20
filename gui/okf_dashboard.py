from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QSplitter
)
from PyQt6.QtCore import Qt
import os
import yaml


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

        subtitle = QLabel("Open Knowledge Format - P&ID symbol knowledge bundle explorer")
        subtitle.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(subtitle)

        # Splitter: tree left, details right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Knowledge tree
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.knowledge_tree = QTreeWidget()
        self.knowledge_tree.setHeaderLabel("Symbol Knowledge Bundle")
        self.knowledge_tree.setStyleSheet("""
            QTreeWidget { background: #16213e; color: #ccc; border: 1px solid #1a1a3e;
                          border-radius: 6px; font-size: 12px; }
            QTreeWidget::item:hover { background: #1a1a3e; }
        """)
        self.knowledge_tree.itemClicked.connect(self._on_item_clicked)
        left_layout.addWidget(self.knowledge_tree)

        load_btn = QPushButton("Load Knowledge Bundle")
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
        okf_dir = os.path.join(base, "okf")

        if not os.path.isdir(okf_dir):
            self.detail_display.setText("OKF bundle not found. Place okf/ in project root.")
            return

        root = QTreeWidgetItem(self.knowledge_tree)
        root.setText(0, "P&ID Symbols")
        root.setExpanded(True)

        classes_dir = os.path.join(okf_dir, "classes")
        if not os.path.isdir(classes_dir):
            self.detail_display.setText("No classes/ directory in OKF bundle.")
            return

        count = 0
        for fname in sorted(os.listdir(classes_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(classes_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()

            # Parse frontmatter
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    try:
                        meta = yaml.safe_load(parts[1]) or {}
                    except yaml.YAMLError:
                        meta = {}
                    body = parts[2].strip()
                else:
                    meta = {}
                    body = text
            else:
                meta = {}
                body = text

            title = meta.get("title", fname.replace(".md", ""))
            subclasses = []
            in_list = False
            for line in body.split("\n"):
                if line.strip() == "## Subclasses":
                    in_list = True
                    continue
                if in_list and line.startswith("- "):
                    subclasses.append(line[2:].strip())
                elif in_list and line.startswith("#"):
                    break

            parent_item = QTreeWidgetItem(root)
            parent_item.setText(0, f"{title} ({len(subclasses)})")
            parent_item.setExpanded(False)
            parent_item.setData(0, Qt.ItemDataRole.UserRole, {"meta": meta, "body": body})

            for sub in subclasses:
                child = QTreeWidgetItem(parent_item)
                child.setText(0, sub)
                child.setData(0, Qt.ItemDataRole.UserRole, {"parent": title, "subclass": sub})
            count += 1

        self.detail_display.setText(f"Loaded {count} parent classes from OKF bundle.\nClick a symbol to view details.")

    def _on_item_clicked(self, item, col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and "subclass" in data:
            self.detail_display.setText(
                f"<b>Parent Class:</b> {data['parent']}<br>"
                f"<b>Subclass:</b> {data['subclass']}<br><br>"
                f"<i>DINOv2 embeddings available for reclassification.</i>"
            )
        elif data and "meta" in data:
            meta = data["meta"]
            self.detail_display.setText(
                f"<b>{meta.get('title', item.text(0))}</b><br>"
                f"<b>Type:</b> {meta.get('type', 'N/A')}<br>"
                f"<b>Description:</b> {meta.get('description', 'N/A')}<br>"
                f"<b>Tags:</b> {', '.join(meta.get('tags', []))}"
            )
        else:
            self.detail_display.setText(f"<b>{item.text(0)}</b>")
