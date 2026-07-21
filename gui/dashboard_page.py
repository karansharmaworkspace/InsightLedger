import torch
import cv2
import os
import sys
import json
import traceback
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QStatusBar, QFileDialog, QTextEdit, QTableWidget,
    QTableWidgetItem, QLabel, QPushButton, QProgressBar,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QMessageBox, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsRectItem, QTabWidget, QLineEdit,
    QGridLayout, QScrollArea, QSpinBox, QApplication
)
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QRectF, QTimer
from PyQt6.QtGui import QAction, QFont, QColor, QPalette, QPixmap, QImage, QPen

from core.universal_engine import UniversalEngine
from core.groq_client import GroqChat
from utils.translations import tr_class, tr_gui, tr_parent, tr_header, get_ocr_lang, CLASS_NAMES, SUPPORTED_LANGUAGES, GOOGLE_LANG_MAP, prewarm_language, available_language_count
from utils.graphml_formatter import GraphMLFormatter

# Reuse existing classes from dashboard.py
from gui.dashboard import (
    CropGraphicsView, ProcessingThread, ChatThread, ReclassifySidebar
)


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lang = "en"
        self.model_path = os.getenv("PT_MODEL_PATH", "models/32class.pt")
        self.chat_engine = GroqChat()
        self.latest_result = None
        self.cropped_image_path = None
        self.output_dir = "output"
        self.node_rects = {}
        self._current_glow = None
        self._chat_streaming = False
        self._realtime_items = []
        self._realtime_nodes = {}
        self.image_path = None
        os.makedirs(self.output_dir, exist_ok=True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Toolbar ---
        toolbar = QFrame()
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet("background: #111827; border-bottom: 1px solid #334155;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 0, 8, 0)
        tb_layout.setSpacing(4)

        def tb_btn(text, slot=None, enabled=True):
            b = QPushButton(text)
            b.setEnabled(enabled)
            b.setStyleSheet("""
                QPushButton { background: #1E293B; color: #F8FAFC; border: 1px solid #334155;
                              padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; }
                QPushButton:hover { background: #253449; border-color: #3B82F6; }
                QPushButton:disabled { background: #111827; color: #64748B; border-color: #1E293B; }
            """)
            if slot:
                b.clicked.connect(slot)
            return b

        self.btn_open = tb_btn("Open Diagram", self.open_image)
        self.btn_crop = tb_btn("Crop P&ID", self._start_crop, False)
        self.btn_crop_confirm = tb_btn("Confirm Crop", self._confirm_crop, False)
        self.btn_crop_cancel = tb_btn("Cancel Crop", self._cancel_crop, False)
        self.btn_run = tb_btn("Run Digitization", self.run_engine, False)
        self.btn_export_json = tb_btn("Export DEXPI", self.export_json)
        self.btn_export_gml = tb_btn("Export GraphML", self.export_graphml)

        self.tile_size = QSpinBox()
        self.tile_size.setRange(320, 1920)
        self.tile_size.setSingleStep(64)
        self.tile_size.setValue(640)
        self.tile_size.setFixedWidth(70)
        self.tile_size.setStyleSheet("background: #1E293B; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 2px;")

        self.lang_combo = QtWidgets.QComboBox()
        for _code, name in SUPPORTED_LANGUAGES:
            self.lang_combo.addItem(name)
        self.lang_combo.setFixedWidth(140)
        self.lang_combo.setStyleSheet("QComboBox { background: #1E293B; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 2px 6px; } QComboBox::drop-down { border: none; } QComboBox QAbstractItemView { background: #1E293B; color: #F8FAFC; selection-background-color: #3B82F6; }")
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)

        for w in [self.btn_open, None, self.btn_crop, self.btn_crop_confirm, self.btn_crop_cancel,
                  None, self.btn_run, None, self.btn_export_json, self.btn_export_gml,
                  None]:
            if w is None:
                tb_layout.addSpacing(6)
            else:
                tb_layout.addWidget(w)

        tb_layout.addStretch()
        tb_layout.addWidget(QLabel("Tile:"))
        tb_layout.addWidget(self.tile_size)
        tb_layout.addSpacing(8)
        tb_layout.addWidget(self.lang_combo)

        layout.addWidget(toolbar)

        # --- Main content splitter ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # Left: image view
        self.scene = QGraphicsScene()
        self.view = CropGraphicsView(self.scene)
        self.view.crop_confirmed.connect(self._on_crop_confirmed)
        self.view.right_click_symbol.connect(self._on_reclassify_request)
        self.scene.addText("Load a P&ID diagram to begin...").setDefaultTextColor(QColor("#555"))
        splitter.addWidget(self.view)

        # Right: tabs (hierarchy + chat)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: none; background: #1E293B; } QTabBar::tab { background: #111827; color: #94A3B8; padding: 7px 14px; font-weight: 600; } QTabBar::tab:selected { background: #1E293B; color: #3B82F6; }")

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Topology Explorer")
        self.tree.setStyleSheet("background-color: #1E293B; color: #E2E8F0; border: none;")
        self.tabs.addTab(self.tree, "Hierarchy")

        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 10px; padding: 10px; font-size: 13px;")
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask AI Assistant...")
        self.chat_input.setStyleSheet("background-color: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 15px; padding: 8px 15px; margin-top: 5px;")
        self.chat_input.returnPressed.connect(self.send_chat)
        chat_layout.addWidget(self.chat_display)
        chat_layout.addWidget(self.chat_input)
        self.tabs.addTab(chat_container, "AI Assistant")

        right_layout.addWidget(self.tabs)
        splitter.addWidget(right_panel)
        splitter.setSizes([700, 350])

        layout.addWidget(splitter, 1)

        # --- Bottom panels (table + console) ---
        bottom_tabs = QTabWidget()
        bottom_tabs.setFixedHeight(180)
        bottom_tabs.setStyleSheet("QTabWidget::pane { border: none; background: #1E293B; } QTabBar::tab { background: #111827; color: #94A3B8; padding: 5px 10px; font-size: 11px; font-weight: 600; } QTabBar::tab:selected { background: #1E293B; color: #3B82F6; }")

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Class", "Labels", "Coordinates"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: #1E293B; color: #E2E8F0; gridline-color: #334155; font-size: 11px;")
        bottom_tabs.addTab(self.table, "Detection Metadata")

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 10))
        self.console.setStyleSheet("background-color: #0F172A; color: #10B981; border: none; padding: 6px;")
        bottom_tabs.addTab(self.console, "Neural Console")

        layout.addWidget(bottom_tabs)

    # ---- Image loading ----

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open P&ID", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            if self.view.crop_active:
                self._cancel_crop()
            self.image_path = path
            self.cropped_image_path = None
            self.console.append(f"[SYSTEM] Loading: {os.path.basename(path)}")

            self.scene.clear()
            self.pixmap_item = QGraphicsPixmapItem(QPixmap(path))
            self.scene.addItem(self.pixmap_item)
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

            self.btn_crop.setEnabled(True)
            self.btn_run.setEnabled(False)
            self.console.append("[SYSTEM] Use 'Crop P&ID' to select the diagram region.")

    # ---- Crop ----

    def _start_crop(self):
        self.console.append("[CROP] Draw a rectangle around the P&ID area.")
        self.view.enter_crop_mode()
        self.btn_crop.setEnabled(False)
        self.btn_crop_confirm.setEnabled(False)
        self.btn_crop_cancel.setEnabled(True)
        try:
            self.view.crop_rect_changed.disconnect(self._on_crop_rect_changed)
        except TypeError:
            pass
        self.view.crop_rect_changed.connect(self._on_crop_rect_changed)

    def _on_crop_rect_changed(self):
        rect = self.view.get_crop_rect()
        self.btn_crop_confirm.setEnabled(rect is not None)

    def _confirm_crop(self):
        rect = self.view.get_crop_rect()
        if rect:
            self._on_crop_confirmed(*rect)

    def _cancel_crop(self):
        self.view.exit_crop_mode()
        self.btn_crop.setEnabled(True)
        self.btn_crop_confirm.setEnabled(False)
        self.btn_crop_cancel.setEnabled(False)
        self.console.append("[CROP] Cancelled.")
        try:
            self.view.crop_rect_changed.disconnect(self._on_crop_rect_changed)
        except TypeError:
            pass

    def _on_crop_confirmed(self, x1, y1, x2, y2):
        self.view.exit_crop_mode()
        self.btn_crop.setEnabled(True)
        self.btn_crop_confirm.setEnabled(False)
        self.btn_crop_cancel.setEnabled(False)
        try:
            self.view.crop_rect_changed.disconnect(self._on_crop_rect_changed)
        except TypeError:
            pass
        self.console.append(f"[CROP] Region: ({x1},{y1}) -> ({x2},{y2})")

        img = cv2.imread(self.image_path)
        if img is None:
            self.console.append("[ERROR] Failed to read image for cropping.")
            return

        cropped = img[y1:y2, x1:x2]
        crop_dir = os.path.join(self.output_dir, "crops")
        os.makedirs(crop_dir, exist_ok=True)
        crop_path = os.path.join(crop_dir, f"cropped_{os.path.basename(self.image_path)}")
        cv2.imwrite(crop_path, cropped)
        self.cropped_image_path = crop_path

        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(QPixmap(crop_path))
        self.scene.addItem(self.pixmap_item)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.console.append("[CROP] P&ID isolated. Ready for digitization.")
        self.btn_run.setEnabled(True)

    # ---- Engine ----

    def run_engine(self):
        target_path = self.cropped_image_path if self.cropped_image_path else self.image_path
        self.console.append(f"[ENGINE] Starting digitization on: {os.path.basename(target_path)}")
        self._clear_boxes()
        self._clear_realtime_items()
        self._current_glow = None

        self.thread = ProcessingThread(
            image_path=target_path,
            model_path=self.model_path,
            lang=self.lang,
            sahi_tile_size=self.tile_size.value()
        )
        self.thread.log.connect(lambda t: self.console.append(f"[LOG] {t}"))
        self.thread.new_box.connect(self._draw_live_box)
        self.thread.new_node.connect(self._store_realtime_node)
        self.thread.new_realtime_line.connect(self._draw_realtime_line)
        self.thread.new_realtime_edge.connect(self._draw_realtime_edge)
        self.thread.new_ocr_bbox.connect(self._draw_ocr_bbox)
        self.thread.finished.connect(self._on_finished)
        self.thread.error.connect(self._on_engine_error)
        self.thread.start()

    def _on_engine_error(self, error_msg):
        self.console.append(f"[ENGINE ERROR] {error_msg}")
        QMessageBox.critical(self, "Engine Error", f"Digitization failed:\n\n{error_msg[:500]}")

    def _on_finished(self, data):
        self.console.append("[SUCCESS] Digitization Complete.")
        try:
            with open(data["path"], "r") as f:
                result = json.load(f)
            self.latest_result = result
            self.chat_engine.index_result(result)
            nodes = result.get('nodes', [])
            edges = result.get('edges', [])
            self.console.append(f"\n[DEXPI OUTPUT] {len(nodes)} nodes, {len(edges)} edges")
        except Exception as e:
            self.console.append(f"[ERROR] Failed to load results: {e}")
            return

        self.table.setRowCount(0)
        self.table.setRowCount(len(nodes))
        headers = tr_header(self.lang)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        try:
            self.table.cellClicked.disconnect(self._highlight_node)
        except TypeError:
            pass
        self.table.cellClicked.connect(self._highlight_node)

        self.node_rects.clear()
        root = QTreeWidgetItem(self.tree)

        for i, node in enumerate(nodes):
            type_key = node.get('type_key', node.get('type', 'unknown'))
            display_type = tr_class(type_key, self.lang)
            fine_label = node.get('attrs', {}).get('fine_class', '')
            ocr_label = node.get('attrs', {}).get('Labels', 'N/A')
            x1 = node['attrs'].get('xmin', 0)
            y1 = node['attrs'].get('ymin', 0)
            x2 = node['attrs'].get('xmax', 0)
            y2 = node['attrs'].get('ymax', 0)

            if fine_label:
                display = f"{display_type} -> {fine_label} ({ocr_label})"
            else:
                display = f"{display_type} ({ocr_label}): {node['id']}"
            QTreeWidgetItem(root, [display])

            self.table.setItem(i, 0, QTableWidgetItem(node['id']))
            self.table.setItem(i, 1, QTableWidgetItem(display_type))
            self.table.setItem(i, 2, QTableWidgetItem(fine_label if fine_label else ''))
            self.table.setItem(i, 3, QTableWidgetItem(ocr_label))
            self.table.setItem(i, 4, QTableWidgetItem(f"{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}"))

            rect = self.scene.addRect(QRectF(x1, y1, x2-x1, y2-y1), QPen(QColor(0, 255, 0), 3))
            rect.setToolTip(node['id'])
            self.node_rects[node['id']] = rect

        self.tree.expandAll()
        self.console.append(f"[REPORT] {len(nodes)} nodes, {len(edges)} connections finalized.")

    # ---- Drawing helpers ----

    def _draw_live_box(self, box_data):
        x1, y1, x2, y2, label = box_data
        rect = self.scene.addRect(QRectF(x1, y1, x2-x1, y2-y1), QPen(QColor(255, 0, 0), 1))
        rect.setToolTip(f"Proposal: {label}")

    def _draw_realtime_line(self, x1, y1, x2, y2, line_type):
        color_map = {
            "process": QColor(255, 0, 0), "signal": QColor(0, 0, 255),
            "utility": QColor(0, 200, 200), "software": QColor(0, 200, 0),
            "mechanical": QColor(0, 255, 255), "heat_trace": QColor(255, 0, 255)
        }
        pen = QPen(color_map.get(line_type, QColor(255, 0, 0)), 2)
        if line_type == "signal":
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setDashPattern([6, 4])
        elif line_type == "utility":
            pen.setStyle(Qt.PenStyle.DotLine)
        elif line_type == "software":
            pen.setStyle(Qt.PenStyle.DashDotDotLine)
        elif line_type == "mechanical":
            pen.setStyle(Qt.PenStyle.DashDotLine)
        line = self.scene.addLine(x1, y1, x2, y2, pen)
        line.setZValue(1)
        self._realtime_items.append(line)

    def _draw_realtime_edge(self, src_id, tgt_id, line_type):
        src_bbox = self._realtime_nodes.get(src_id)
        tgt_bbox = self._realtime_nodes.get(tgt_id)
        if not src_bbox or not tgt_bbox:
            return
        smx, smy = (src_bbox[0]+src_bbox[2])/2.0, (src_bbox[1]+src_bbox[3])/2.0
        tmx, tmy = (tgt_bbox[0]+tgt_bbox[2])/2.0, (tgt_bbox[1]+tgt_bbox[3])/2.0
        pen = QPen(QColor(255, 0, 0), 3)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([8, 5])
        line = self.scene.addLine(smx, smy, tmx, tmy, pen)
        line.setZValue(2)
        self._realtime_items.append(line)

    def _store_realtime_node(self, node_id, bbox):
        self._realtime_nodes[node_id] = bbox

    def _draw_ocr_bbox(self, x1, y1, x2, y2, text, conf):
        rect = self.scene.addRect(QRectF(x1, y1, x2-x1, y2-y1), QPen(QColor(0, 255, 255), 2, Qt.PenStyle.DashLine))
        rect.setZValue(1.5)
        text_item = self.scene.addText(f"{text} ({conf:.0%})", QFont("Arial", 7))
        text_item.setDefaultTextColor(QColor(0, 255, 255))
        text_item.setPos(x1, y1 - 18)
        text_item.setZValue(1.5)
        self._realtime_items.extend([rect, text_item])

    def _clear_realtime_items(self):
        for item in self._realtime_items:
            if item in self.scene.items():
                self.scene.removeItem(item)
        self._realtime_items.clear()
        self._realtime_nodes.clear()

    def _clear_boxes(self):
        for item in list(self.scene.items()):
            if isinstance(item, QGraphicsRectItem):
                self.scene.removeItem(item)

    # ---- Node highlight ----

    def _highlight_node(self, row, col):
        node_id = self.table.item(row, 0).text()
        rect = self.node_rects.get(node_id)
        if not rect:
            return
        if self._current_glow and self._current_glow in self.node_rects:
            self.node_rects[self._current_glow].setPen(QPen(QColor(0, 255, 0), 3))
        rect.setPen(QPen(QColor(255, 200, 0), 5))
        self._current_glow = node_id
        self.view.fitInView(rect.rect(), Qt.AspectRatioMode.KeepAspectRatio)

    # ---- Reclassify ----

    def _on_reclassify_request(self, node_id):
        if not self.latest_result:
            return
        nodes = self.latest_result.get('nodes', [])
        node = next((n for n in nodes if n['id'] == node_id), None)
        if not node:
            return

        x1, y1 = int(node['attrs'].get('xmin', 0)), int(node['attrs'].get('ymin', 0))
        x2, y2 = int(node['attrs'].get('xmax', 0)), int(node['attrs'].get('ymax', 0))

        crop = None
        target = self.cropped_image_path or self.image_path
        if target:
            img = cv2.imread(target)
            if img is not None:
                crop = img[y1:y2, x1:x2].copy()

        if not hasattr(self, 'reclassify_sidebar') or self.reclassify_sidebar is None:
            self.reclassify_sidebar = ReclassifySidebar()
            self.reclassify_sidebar.class_selected.connect(
                lambda cls, parent: self._apply_reclassify(
                    self.reclassify_sidebar._current_node_id, cls, parent))
            self.reclassify_sidebar.setWindowFlags(
                Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)

        self.reclassify_sidebar.show_for_node(node_id, crop)
        self.reclassify_sidebar._current_node_id = node_id
        self.reclassify_sidebar.show()

    def _apply_reclassify(self, node_id, new_class, parent_class):
        if not self.latest_result:
            return
        nodes = self.latest_result.get('nodes', [])
        target_node = next((n for n in nodes if n['id'] == node_id), None)
        if not target_node:
            return

        old_class = target_node.get('attrs', {}).get('fine_class', '') or target_node.get('attrs', {}).get('label', 'unknown')
        count = 0
        for node in nodes:
            node_class = node.get('attrs', {}).get('fine_class', '') or node.get('attrs', {}).get('label', 'unknown')
            if node_class == old_class:
                node['attrs']['fine_class'] = new_class
                node['attrs']['label'] = new_class
                count += 1
                rect = self.node_rects.get(node['id'])
                if rect:
                    rect.setPen(QPen(QColor(0, 200, 255), 4))
                for i in range(self.table.rowCount()):
                    if self.table.item(i, 0) and self.table.item(i, 0).text() == node['id']:
                        self.table.setItem(i, 2, QTableWidgetItem(new_class))
                        break

        self.console.append(f"[RECLASSIFY] {old_class} -> {new_class} ({count} symbols updated)")

    # ---- Chat ----

    def send_chat(self):
        query = self.chat_input.text().strip()
        if not query or self._chat_streaming:
            return
        self.chat_input.clear()
        self.chat_display.append(
            f"<div style='margin-bottom:8px;padding:8px 10px;background:#1E293B;border-radius:8px;'>"
            f"<b style='color:#3B82F6;'>You:</b> <span style='color:#F8FAFC;'>{query}</span></div>"
        )
        self.chat_display.append(
            "<div style='margin-bottom:8px;padding:8px 10px;background:#0F172A;border-radius:8px;'>"
            "<b style='color:#10B981;'>AI:</b> <span id='ai-text' style='color:#F8FAFC;'></span>"
            "<span style='color:#10B981;'>|</span></div>"
        )
        self._chat_streaming = True
        self._chat_full_response = ""
        self.chat_input.setEnabled(False)

        self.chat_thread = ChatThread(self.chat_engine, query, self.latest_result)
        self.chat_thread.chunk_received.connect(self._on_chat_chunk)
        self.chat_thread.finished.connect(self._on_chat_finished)
        self.chat_thread.error.connect(self._on_chat_error)
        self.chat_thread.start()

    def _on_chat_chunk(self, chunk):
        self._chat_full_response += chunk
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.chat_display.ensureCursorVisible()

    def _on_chat_finished(self, full_response):
        self._chat_streaming = False
        self.chat_input.setEnabled(True)
        self.chat_input.setFocus()

    def _on_chat_error(self, error_msg):
        self._chat_streaming = False
        self.chat_input.setEnabled(True)
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"\n\n[ERROR] {error_msg}")

    # ---- Export ----

    def export_json(self):
        if not self.latest_result:
            QMessageBox.warning(self, "Export", "No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save DEXPI JSON", self.output_dir, "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.latest_result, f, indent=2)
            self.console.append(f"[EXPORT] DEXPI JSON saved to {path}")

    def export_graphml(self):
        if not self.latest_result:
            QMessageBox.warning(self, "Export", "No results to export.")
            return
        nodes = self.latest_result.get("nodes", [])
        edges = self.latest_result.get("edges", [])
        if not nodes:
            QMessageBox.warning(self, "Export", "No nodes to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save GraphML", self.output_dir, "GraphML (*.graphml)")
        if path:
            GraphMLFormatter.export(nodes, edges, path)
            self.console.append(f"[EXPORT] GraphML saved to {path}")

    # ---- Language ----

    def _on_language_changed(self, idx):
        self.lang = SUPPORTED_LANGUAGES[idx][0]
        prewarm_language(self.lang)
