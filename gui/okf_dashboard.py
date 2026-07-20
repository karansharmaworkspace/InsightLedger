"""3D Knowledge Visualization Dashboard — all documents, entities, and relationships."""
from __future__ import annotations

import math
import os
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import yaml
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSplitter, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)
from pyqtgraph.opengl import (
    GLGridItem, GLLinePlotItem, GLScatterPlotItem, GLViewWidget,
)


# ── Theme ────────────────────────────────────────────────────────────
BG_DARK = "#1a1a2e"
BG_CARD = "#16213e"
BG_INPUT = "#0f3460"
ACCENT = "#0078d4"
TEXT = "#e0e0e0"
TEXT_DIM = "#888"
BORDER = "#1a1a3e"

ENTITY_COLORS: dict[str, tuple[int, int, int, int]] = {
    "equipment_tag":  (52, 152, 219, 255),
    "personnel":      (46, 204, 113, 255),
    "regulatory_ref": (231, 76, 60, 255),
    "date":           (243, 156, 18, 255),
    "parameter":      (155, 89, 182, 255),
    "work_order":     (26, 188, 156, 255),
    "failure_mode":   (230, 126, 34, 255),
    "location":       (52, 73, 94, 255),
    "okf_class":      (0, 200, 255, 255),
    "okf_symbol":     (0, 150, 200, 180),
    "unknown":        (149, 165, 166, 255),
}

EDGE_COLOR = (100, 100, 100, 60)
DOC_COLOR = (255, 255, 255, 180)

CARD_STYLE = (
    f"QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER}; "
    f"border-radius: 6px; }}"
)


def _parse_okf_file(fpath: str) -> tuple[dict[str, Any], list[str]]:
    text = open(fpath, "r", encoding="utf-8").read()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                meta = {}
            body = parts[2]
        else:
            meta, body = {}, text
    else:
        meta, body = {}, text
    subs: list[str] = []
    in_list = False
    for line in body.split("\n"):
        if line.strip() == "## Subclasses":
            in_list = True
            continue
        if in_list and line.startswith("- "):
            subs.append(line[2:].strip())
        elif in_list and line.startswith("#"):
            break
    return meta, subs


# ── 3D viewport ──────────────────────────────────────────────────────
class Scene3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = GLViewWidget()
        self.view.setBackgroundColor(26, 26, 46)
        self.view.setCameraPosition(distance=40, elevation=25, azimuth=45)

        grid = GLGridItem()
        grid.setSize(40, 40)
        grid.setSpacing(2, 2)
        self.view.addItem(grid)

        self.scatter: GLScatterPlotItem | None = None
        self.lines: GLLinePlotItem | None = None
        self.label_items: list[tuple[np.ndarray, str]] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)

    def render_scene(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        sizes: np.ndarray,
        edges: list[tuple[int, int]],
        node_labels: list[str],
    ):
        if self.scatter is not None:
            self.view.removeItem(self.scatter)
        if self.lines is not None:
            self.view.removeItem(self.lines)

        self.scatter = GLScatterPlotItem(
            pos=positions,
            color=colors,
            size=sizes,
            pxMode=True,
        )
        self.view.addItem(self.scatter)

        if edges:
            edge_verts = []
            for a, b in edges:
                edge_verts.append(positions[a])
                edge_verts.append(positions[b])
            edge_arr = np.array(edge_verts)
            self.lines = GLLinePlotItem(
                pos=edge_arr,
                color=EDGE_COLOR,
                width=1,
                mode="lines",
            )
            self.view.addItem(self.lines)

        self.label_items = list(zip(positions, node_labels))

    def freeze(self):
        self.view.update()


# ── Main dashboard ───────────────────────────────────────────────────
class OKFDashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._positions: np.ndarray = np.empty((0, 3))
        self._colors: np.ndarray = np.empty((0, 4))
        self._sizes: np.ndarray = np.empty(0)
        self._node_labels: list[str] = []
        self._edge_idx: list[tuple[int, int]] = []
        self._node_meta: list[dict[str, Any]] = []
        self._type_filter: dict[str, bool] = {k: True for k in ENTITY_COLORS}
        self._setup_ui()
        self._load_all()

    # ── UI ───────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Left panel ───────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        title = QLabel("3D Knowledge Explorer")
        title.setStyleSheet(f"color: #fff; font-size: 20px; font-weight: bold;")
        left.addWidget(title)

        # Stats
        self.stats_lbl = QLabel("")
        self.stats_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        self.stats_lbl.setWordWrap(True)
        left.addWidget(self.stats_lbl)

        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter nodes...")
        self.search.setStyleSheet(
            f"QLineEdit {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER}; "
            f"border-radius: 5px; padding: 6px 10px; font-size: 12px; }}"
        )
        self.search.textChanged.connect(self._apply_filter)
        left.addWidget(self.search)

        # Type filters
        filters_frame = QFrame()
        filters_frame.setStyleSheet(CARD_STYLE)
        flay = QVBoxLayout(filters_frame)
        flay.setContentsMargins(8, 6, 8, 6)
        flay.setSpacing(2)
        self._filter_checks: dict[str, QCheckBox] = {}
        for etype in ENTITY_COLORS:
            cb = QCheckBox(etype.replace("_", " ").title())
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
            cb.stateChanged.connect(self._apply_filter)
            self._filter_checks[etype] = cb
            flay.addWidget(cb)
        left.addWidget(filters_frame)

        left.addStretch()

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Nodes")
        self.tree.setMaximumWidth(260)
        self.tree.setStyleSheet(
            f"QTreeWidget {{ background: {BG_CARD}; color: #ccc; border: 1px solid {BORDER}; "
            f"font-size: 11px; }}"
            f"QTreeWidget::item:selected {{ background: {ACCENT}; color: #fff; }}"
        )
        self.tree.itemClicked.connect(self._on_tree_click)
        left.addWidget(self.tree, 1)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(280)

        root.addWidget(left_widget)

        # ── Right: 3D + detail ───────────────────────────────────────
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self.scene3d = Scene3D()
        right_splitter.addWidget(self.scene3d)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(200)
        self.detail.setStyleSheet(
            f"QTextEdit {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; padding: 12px; font-size: 12px; }}"
        )
        self.detail.setPlaceholderText("Click a node in the 3D scene or tree to view details...")
        right_splitter.addWidget(self.detail)

        right_splitter.setSizes([500, 200])
        root.addWidget(right_splitter, 1)

    # ── Data loading ─────────────────────────────────────────────────
    def _load_all(self):
        positions: list[list[float]] = []
        colors: list[list[int]] = []
        sizes: list[float] = []
        labels: list[str] = []
        meta: list[dict[str, Any]] = []
        edges: list[tuple[int, int]] = []
        idx_map: dict[str, int] = {}

        def _add_node(nid: str, etype: str, value: str, size: float = 8.0, extra: dict | None = None):
            if nid in idx_map:
                return idx_map[nid]
            i = len(positions)
            idx_map[nid] = i
            positions.append([0, 0, 0])
            rgba = ENTITY_COLORS.get(etype, ENTITY_COLORS["unknown"])
            colors.append(list(rgba))
            sizes.append(size)
            labels.append(value)
            m: dict[str, Any] = {"id": nid, "type": etype, "value": value}
            if extra:
                m.update(extra)
            meta.append(m)
            return i

        # ── Load knowledge graph ─────────────────────────────────────
        try:
            from core.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            for nid, node in kg.nodes.items():
                _add_node(nid, node.get("type", "unknown"), node.get("value", nid))
            for edge in kg.edges:
                s = edge.get("source")
                t = edge.get("target")
                if s in idx_map and t in idx_map:
                    edges.append((idx_map[s], idx_map[t]))
        except Exception:
            pass

        # ── Load OKF classes + symbols ───────────────────────────────
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        okf_dir = os.path.join(base, "okf", "classes")
        if os.path.isdir(okf_dir):
            for fname in sorted(os.listdir(okf_dir)):
                if not fname.endswith(".md"):
                    continue
                meta_okf, subs = _parse_okf_file(os.path.join(okf_dir, fname))
                title = meta_okf.get("title", fname.replace(".md", ""))
                class_id = f"okf:{title}"
                ci = _add_node(class_id, "okf_class", title, size=14.0, extra={"count": len(subs)})
                for si, sub in enumerate(subs):
                    sub_id = f"okf:{title}:{sub}"
                    _add_node(sub_id, "okf_symbol", sub, size=5.0, extra={"parent": title})
                    edges.append((ci, idx_map[sub_id]))

        # ── Layout: arrange by type in 3D ────────────────────────────
        type_groups: dict[str, list[int]] = defaultdict(list)
        for i, m in enumerate(meta):
            type_groups[m["type"]].append(i)

        n_types = len(type_groups)
        for ti, (etype, indices) in enumerate(type_groups.items()):
            angle = 2 * math.pi * ti / max(n_types, 1)
            radius = 8.0 if etype.startswith("okf") else 6.0
            cx = radius * math.cos(angle)
            cy = radius * math.sin(angle)
            cz = 0.0

            ni = len(indices)
            for ii, idx in enumerate(indices):
                phi = 2 * math.pi * ii / max(ni, 1)
                r = 2.0 + (ni % 5) * 0.5
                positions[idx] = [
                    cx + r * math.cos(phi),
                    cy + r * math.sin(phi),
                    cz + (ii % 3 - 1) * 1.5,
                ]

        self._positions = np.array(positions, dtype=np.float32) if positions else np.zeros((0, 3), dtype=np.float32)
        self._colors = np.array(colors, dtype=np.float32) / 255.0 if colors else np.zeros((0, 4), dtype=np.float32)
        self._sizes = np.array(sizes, dtype=np.float32) if sizes else np.zeros(0, dtype=np.float32)
        self._node_labels = labels
        self._edge_idx = edges
        self._node_meta = meta

        # Stats
        n_nodes = len(meta)
        n_edges = len(edges)
        n_docs = len({m.get("source", "") for m in meta if m.get("source")})
        self.stats_lbl.setText(
            f"Nodes: {n_nodes}  |  Edges: {n_edges}  |  "
            f"Types: {len(type_groups)}  |  OKF classes: {len([k for k in type_groups if k == 'okf_class'])}"
        )

        # Populate tree
        self.tree.clear()
        for etype in sorted(type_groups.keys()):
            titem = QTreeWidgetItem(self.tree)
            titem.setText(0, f"{etype.replace('_', ' ').title()} ({len(type_groups[etype])})")
            titem.setExpanded(False)
            for idx in type_groups[etype][:200]:
                child = QTreeWidgetItem(titem)
                child.setText(0, meta[idx]["value"][:40])
                child.setData(0, Qt.ItemDataRole.UserRole, idx)
            if len(type_groups[etype]) > 200:
                child = QTreeWidgetItem(titem)
                child.setText(0, f"... +{len(type_groups[etype]) - 200} more")

        self.scene3d.render_scene(self._positions, self._colors, self._sizes, edges, labels)

    # ── Filtering ────────────────────────────────────────────────────
    def _apply_filter(self):
        q = self.search.text().lower().strip()
        active_types = {k for k, v in self._type_filter.items() if v}
        for k, cb in self._filter_checks.items():
            self._type_filter[k] = cb.isChecked()
            active_types = {k2 for k2, v in self._type_filter.items() if v}

        mask = np.zeros(len(self._node_meta), dtype=bool)
        for i, m in enumerate(self._node_meta):
            if m["type"] not in active_types:
                continue
            if q and q not in m.get("value", "").lower():
                continue
            mask[i] = True

        vis_colors = self._colors.copy()
        vis_sizes = self._sizes.copy()
        vis_colors[~mask] = [0.1, 0.1, 0.15, 0.1]
        vis_sizes[~mask] = 1.0

        self.scene3d.render_scene(self._positions, vis_colors, vis_sizes, self._edge_idx, self._node_labels)

    # ── Tree selection ───────────────────────────────────────────────
    def _on_tree_click(self, item, _col):
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        if idx is None or idx >= len(self._node_meta):
            return
        m = self._node_meta[idx]
        html = (
            f"<b style='font-size:14px;'>{m.get('value', '')}</b><br><br>"
            f"<b>Type:</b> {m.get('type', '—')}<br>"
            f"<b>ID:</b> {m.get('id', '—')}<br>"
        )
        for k in ("source", "confidence", "parent", "count", "sources"):
            if k in m and m[k]:
                html += f"<b>{k.title()}:</b> {m[k]}<br>"
        self.detail.setHtml(html)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    w = OKFDashboardPage()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
