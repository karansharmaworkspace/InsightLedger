import torch
import cv2
import sys
import os
import time
import json
import traceback
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QFileDialog, QTextEdit, QTableWidget, 
    QTableWidgetItem, QLabel, QPushButton, QProgressBar, 
    QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QScrollArea, QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
    QTabWidget, QLineEdit, QGridLayout, QScrollArea as QScrollArea2,
    QSpinBox
)
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QRectF, QTimer
from PyQt6.QtGui import QAction, QFont, QColor, QPalette, QPixmap, QImage, QPen

from core.universal_engine import UniversalEngine
from core.groq_client import GroqChat
from utils.translations import tr_class, tr_gui, tr_parent, tr_header, get_ocr_lang, CLASS_NAMES, SUPPORTED_LANGUAGES, GOOGLE_LANG_MAP, prewarm_language, available_language_count
from utils.graphml_formatter import GraphMLFormatter

class ReclassifySidebar(QWidget):
    class_selected = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reclassify")
        self.setMinimumWidth(350)
        self.setMaximumWidth(450)
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #d4d4d4; }
            QTabWidget::pane { border: 1px solid #333; }
            QTabBar::tab { background: #333; color: #ccc; padding: 6px 10px; font-size: 11px; }
            QTabBar::tab:selected { background: #0078d4; }
            QLineEdit { background: #2d2d2d; color: #fff; border: 1px solid #444;
                         border-radius: 4px; padding: 5px; font-size: 12px; }
            QPushButton { background: #0078d4; color: white; border: none;
                          padding: 6px 14px; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1a8fe3; }
            QPushButton:disabled { background: #555; color: #999; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header = QLabel("Reclassify Symbol")
        header.setStyleSheet("color: #0078d4; font-size: 14px; font-weight: bold; padding: 4px;")
        layout.addWidget(header)

        self.crop_preview = QLabel()
        self.crop_preview.setFixedSize(120, 120)
        self.crop_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.crop_preview.setStyleSheet("background: #252526; border: 1px solid #333; border-radius: 4px;")
        self.crop_preview.setText("No symbol")
        layout.addWidget(self.crop_preview, alignment=Qt.AlignmentFlag.AlignCenter)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search classes...")
        self.search.textChanged.connect(self._filter_classes)
        layout.addWidget(self.search)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.selected_label = QLabel("No class selected")
        self.selected_label.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.selected_label)

        btn_row = QHBoxLayout()
        self.confirm_btn = QPushButton("Confirm")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._confirm_selection)
        btn_row.addStretch()
        btn_row.addWidget(self.confirm_btn)
        layout.addLayout(btn_row)

        self._selected_class = None
        self._selected_parent = None
        self._all_items = []
        self._current_node_id = None
        self._load_hierarchy()

    def show_for_node(self, node_id, crop_img=None):
        self._current_node_id = node_id
        self._selected_class = None
        self._selected_parent = None
        self.confirm_btn.setEnabled(False)
        self.selected_label.setText(f"Node: {node_id}")
        self.selected_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.search.clear()

        if crop_img is not None:
            import cv2
            rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            bytes_per_line = 3 * w
            from PyQt6.QtGui import QImage as QImg
            qimg = QImg(rgb.data, w, h, bytes_per_line, QImg.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.crop_preview.setPixmap(pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                                       Qt.TransformationMode.SmoothTransformation))
        else:
            self.crop_preview.setText("No image")

    def _load_hierarchy(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base, "assets", "legend_classification.json")
        gallery_dir = os.path.join(base, "assets", "class_gallery")

        if not os.path.exists(json_path):
            return

        with open(json_path, 'r') as f:
            data = json.load(f)

        classes = data.get("legend_classification", {}).get("classes", {})
        self._parent_classes = list(classes.keys())

        for parent_name, info in classes.items():
            subclasses = info.get("subclasses", [])
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setSpacing(2)
            tab_layout.setContentsMargins(2, 2, 2, 2)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; }")
            grid_widget = QWidget()
            grid_layout = QtWidgets.QGridLayout(grid_widget)
            grid_layout.setSpacing(4)
            grid_layout.setContentsMargins(2, 2, 2, 2)

            for i, cls_name in enumerate(subclasses):
                card = self._create_class_card(cls_name, parent_name, gallery_dir)
                row, col = divmod(i, 2)
                grid_layout.addWidget(card, row, col)
                self._all_items.append((card, cls_name, parent_name))

            scroll.setWidget(grid_widget)
            tab_layout.addWidget(scroll)
            self.tabs.addTab(tab, f"{parent_name} ({len(subclasses)})")

        self._add_create_new_tab()

    def _create_class_card(self, class_name, parent_name, gallery_dir):
        card = QFrame()
        card.setFixedSize(160, 70)
        card.setStyleSheet("QFrame { background: #252526; border: 1px solid #333; border-radius: 3px; }"
                           "QFrame:hover { border: 1px solid #0078d4; }")
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        img_label = QLabel()
        img_label.setFixedSize(32, 32)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_path = os.path.join(gallery_dir, f"{class_name}.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            img_label.setPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))
        else:
            img_label.setText("?")
        layout.addWidget(img_label)

        name_label = QLabel(class_name.replace("_", " "))
        name_label.setStyleSheet("color: #ccc; font-size: 10px;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        card.mousePressEvent = lambda e, cn=class_name, pn=parent_name: self._on_card_click(cn, pn)
        return card

    def _on_card_click(self, class_name, parent_name):
        self._selected_class = class_name
        self._selected_parent = parent_name
        self.selected_label.setText(f"Selected: {class_name}")
        self.selected_label.setStyleSheet("color: #0078d4; font-size: 11px; font-weight: bold;")
        self.confirm_btn.setEnabled(True)

    def _confirm_selection(self):
        if self._selected_class and self._selected_parent:
            self.class_selected.emit(self._selected_class, self._selected_parent)

    def _filter_classes(self, text):
        query = text.lower().strip()
        for card, class_name, parent_name in self._all_items:
            if not query or query in class_name.lower() or query in parent_name.lower():
                card.setVisible(True)
            else:
                card.setVisible(False)

    def _add_create_new_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("New Class")
        title.setStyleSheet("color: #0078d4; font-size: 12px; font-weight: bold;")
        layout.addWidget(title)

        self.new_class_input = QLineEdit()
        self.new_class_input.setPlaceholderText("Class name...")
        layout.addWidget(self.new_class_input)

        self.new_parent_combo = QtWidgets.QComboBox()
        self.new_parent_combo.addItems(self._parent_classes)
        layout.addWidget(self.new_parent_combo)

        self.create_btn = QPushButton("Create & Select")
        self.create_btn.setEnabled(False)
        self.create_btn.clicked.connect(self._create_new_class)
        layout.addWidget(self.create_btn)

        self.new_class_input.textChanged.connect(lambda t: self.create_btn.setEnabled(len(t.strip()) > 0))

        self.new_class_status = QLabel("")
        self.new_class_status.setStyleSheet("color: #aaa; font-size: 10px;")
        layout.addWidget(self.new_class_status)

        layout.addStretch()
        self.tabs.addTab(tab, "+ New")

    def set_current_crop(self, crop):
        self._current_crop = crop

    def _create_new_class(self):
        class_name = self.new_class_input.text().strip().replace(" ", "_")
        parent_name = self.new_parent_combo.currentText()
        if not class_name:
            return

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base, "assets", "legend_classification.json")
        gallery_dir = os.path.join(base, "assets", "class_gallery")
        os.makedirs(gallery_dir, exist_ok=True)

        if hasattr(self, '_current_crop') and self._current_crop is not None:
            import cv2
            img_path = os.path.join(gallery_dir, f"{class_name}.png")
            cv2.imwrite(img_path, self._current_crop)

        with open(json_path, 'r') as f:
            data = json.load(f)

        classes = data.get("legend_classification", {}).get("classes", {})
        if parent_name in classes:
            subs = classes[parent_name].get("subclasses", [])
            if class_name not in subs:
                subs.append(class_name)
                subs.sort()
                classes[parent_name]["subclasses"] = subs
                classes[parent_name]["subclass_count"] = len(subs)

        data["legend_classification"]["classes"] = classes
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        self._selected_class = class_name
        self._selected_parent = parent_name
        self.new_class_status.setText(f"Created: {class_name}")
        self.new_class_status.setStyleSheet("color: #00ff00; font-size: 10px;")
        self.confirm_btn.setEnabled(True)


class CropGraphicsView(QGraphicsView):
    crop_confirmed = pyqtSignal(int, int, int, int)
    crop_rect_changed = pyqtSignal()
    right_click_symbol = pyqtSignal(str)

    HANDLE_SIZE = 10
    MIN_CROP = 50

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.crop_active = False
        self.crop_origin = None
        self.crop_rect_item = None
        self.crop_handles = []       # [(QGraphicsRectItem, edge_type)]
        self.drag_handle = None      # edge_type being dragged, or 'move'
        self.drag_origin = None
        self.drag_start_rect = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setStyleSheet("background-color: #000; border: none;")

    # --- Mode control ---

    def enter_crop_mode(self):
        self.crop_active = True
        self.crop_origin = None
        self._clear_crop_items()
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def exit_crop_mode(self):
        self.crop_active = False
        self.crop_origin = None
        self.drag_handle = None
        self.drag_origin = None
        self.drag_start_rect = None
        self._clear_crop_items()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def get_crop_rect(self):
        """Return (x1, y1, x2, y2) of current selection, or None."""
        if not self.crop_rect_item:
            return None
        r = self.crop_rect_item.rect()
        return (int(r.left()), int(r.top()), int(r.right()), int(r.bottom()))

    # --- Item management ---

    def _clear_crop_items(self):
        scene = self.scene()
        if not scene:
            return
        if self.crop_rect_item and self.crop_rect_item in scene.items():
            scene.removeItem(self.crop_rect_item)
        self.crop_rect_item = None
        for item, _ in self.crop_handles:
            if item in scene.items():
                scene.removeItem(item)
        self.crop_handles.clear()

    def _redraw_with_handles(self, rect):
        self._clear_crop_items()
        if rect.width() < self.MIN_CROP or rect.height() < self.MIN_CROP:
            return

        pen = QPen(QColor(0, 150, 255), 2)
        fill = QColor(0, 120, 255, 25)
        self.crop_rect_item = self.scene().addRect(rect, pen, fill)

        x1, y1, x2, y2 = rect.left(), rect.top(), rect.right(), rect.bottom()
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0

        positions = {
            'tl': (x1, y1), 'tm': (cx, y1), 'tr': (x2, y1),
            'ml': (x1, cy),                          'mr': (x2, cy),
            'bl': (x1, y2), 'bm': (cx, y2), 'br': (x2, y2),
        }
        hp = QPen(QColor(0, 150, 255), 1)
        hb = QColor(255, 255, 255)
        half = self.HANDLE_SIZE / 2.0
        for edge, (hx, hy) in positions.items():
            hr = QRectF(hx - half, hy - half, self.HANDLE_SIZE, self.HANDLE_SIZE)
            item = self.scene().addRect(hr, hp, hb)
            self.crop_handles.append((item, edge))

    def _handle_at(self, scene_pos):
        for item, edge in self.crop_handles:
            if item.rect().contains(scene_pos):
                return edge
        return None

    # --- Mouse events ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            pos = self.mapToScene(event.pos())
            for item in self.scene().items():
                if isinstance(item, QGraphicsRectItem) and item.contains(pos):
                    node_id = item.toolTip()
                    if node_id:
                        self.right_click_symbol.emit(node_id)
                    break
            return

        if not self.crop_active or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pos = self.mapToScene(event.pos())

        handle = self._handle_at(pos)
        if handle:
            self.drag_handle = handle
            self.drag_origin = pos
            self.drag_start_rect = QRectF(self.crop_rect_item.rect())
            return

        if self.crop_rect_item and self.crop_rect_item.rect().contains(pos):
            self.drag_handle = 'move'
            self.drag_origin = pos
            self.drag_start_rect = QRectF(self.crop_rect_item.rect())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        self._clear_crop_items()
        self.crop_origin = pos
        self.drag_handle = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseMoveEvent(self, event):
        if not self.crop_active:
            super().mouseMoveEvent(event)
            return

        pos = self.mapToScene(event.pos())

        if self.drag_handle and self.drag_handle != 'move' and self.drag_start_rect:
            r = QRectF(self.drag_start_rect)
            sx, sy = self.drag_origin.x(), self.drag_origin.y()
            dx, dy = pos.x() - sx, pos.y() - sy
            eh = self.drag_handle

            new_r = QRectF(r)
            if 'l' in eh:
                new_r.setLeft(min(r.left() + dx, r.right() - self.MIN_CROP))
            if 'r' in eh:
                new_r.setRight(max(r.right() + dx, r.left() + self.MIN_CROP))
            if 't' in eh:
                new_r.setTop(min(r.top() + dy, r.bottom() - self.MIN_CROP))
            if 'b' in eh:
                new_r.setBottom(max(r.bottom() + dy, r.top() + self.MIN_CROP))

            self._redraw_with_handles(new_r)
            self.crop_rect_changed.emit()
            return

        if self.drag_handle == 'move' and self.drag_start_rect:
            dx = pos.x() - self.drag_origin.x()
            dy = pos.y() - self.drag_origin.y()
            new_r = QRectF(self.drag_start_rect).translated(dx, dy)
            self._redraw_with_handles(new_r)
            self.crop_rect_changed.emit()
            return

        if self.crop_origin:
            x1 = min(self.crop_origin.x(), pos.x())
            y1 = min(self.crop_origin.y(), pos.y())
            x2 = max(self.crop_origin.x(), pos.x())
            y2 = max(self.crop_origin.y(), pos.y())
            rect = QRectF(x1, y1, x2 - x1, y2 - y1)
            self._redraw_with_handles(rect)
            self.crop_rect_changed.emit()
            return

        if self.crop_rect_item:
            handle = self._handle_at(pos)
            if handle:
                if handle in ('tl', 'br'):
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif handle in ('tr', 'bl'):
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif handle in ('tm', 'bm'):
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                else:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif self.crop_rect_item.rect().contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseReleaseEvent(self, event):
        if not self.crop_active or event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        self.crop_origin = None
        if self.drag_handle == 'move':
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.drag_handle = None
        self.drag_origin = None
        self.drag_start_rect = None

        if self.crop_rect_item:
            r = self.crop_rect_item.rect()
            if r.width() < self.MIN_CROP or r.height() < self.MIN_CROP:
                self._clear_crop_items()
        self.crop_rect_changed.emit()


class ProcessingThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    log = pyqtSignal(str)
    new_box = pyqtSignal(list)
    new_node = pyqtSignal(str, list)
    new_realtime_line = pyqtSignal(float, float, float, float, str)
    new_realtime_edge = pyqtSignal(str, str, str)
    new_ocr_bbox = pyqtSignal(int, int, int, int, str, float)
    
    def __init__(self, image_path, model_path="models/32class.pt", lang="en", sahi_tile_size=640):
        super().__init__()
        self.image_path = image_path
        self.model_path = model_path
        self.lang = lang
        self.sahi_tile_size = sahi_tile_size
        
    def run(self):
        try:
            self.log.emit(f"Initializing Universal Engine for {os.path.basename(self.image_path)}...")
            
            from core.universal_engine import UniversalEngine
            
            engine = UniversalEngine(model_path=self.model_path, sahi_tile_size=self.sahi_tile_size)
            
            def box_cb(box): self.new_box.emit(box)
            
            def realtime_line_cb(p1, p2, line_type):
                self.new_realtime_line.emit(float(p1[0]), float(p1[1]), float(p2[0]), float(p2[1]), line_type)
            
            def realtime_edge_cb(src_id, tgt_id, line_type):
                self.new_realtime_edge.emit(src_id, tgt_id, line_type)
            
            def node_cb(node_id, bbox):
                self.new_node.emit(node_id, bbox)
            
            def ocr_bbox_cb(x1, y1, x2, y2, text, conf):
                self.new_ocr_bbox.emit(x1, y1, x2, y2, text, conf)
            
            result = engine.process(
                self.image_path, 
                callback=box_cb, 
                logger=self.log.emit, 
                lang=self.lang,
                on_line_found=realtime_line_cb,
                on_edge_found=realtime_edge_cb,
                on_node_found=node_cb,
                on_ocr_bbox=ocr_bbox_cb
            )
            
            self.log.emit(f"Topology complete: {len(result.get('lines', []))} segments, {len(result.get('edges', []))} connections.")
            
            temp_result = "output/temp_transfer.json"
            with open(temp_result, "w") as f: 
                json.dump(result.get('json', {}), f)
            
            self.finished.emit({
                "path": temp_result,
                "lines": result.get('lines', []),
                "detections": result.get('detections', [])
            })
        except Exception:
            err = traceback.format_exc()
            self.log.emit(f"CRITICAL THREAD ERROR:\n{err}")
            self.error.emit(str(err))

class ChatThread(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, engine, query, context):
        super().__init__()
        self.engine = engine
        self.query = query
        self.context = context

    def run(self):
        full_response = ""
        try:
            stream = self.engine.ask(self.query, self.context)
            if not stream:
                self.error.emit("Failed to connect to AI. Check GROQ_API_KEY.")
                return
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    self.chunk_received.emit(content)
            self.finished.emit(full_response)
        except Exception as e:
            self.error.emit(str(e))

class DPIDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "en"
        self.setWindowTitle("DPID AI - Universal Intelligence Engine")
        self.resize(1400, 900)
        _icon = QPixmap(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png"))
        if not _icon.isNull():
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(_icon))
        
        self.model_path = os.getenv("PT_MODEL_PATH", "models/32class.pt")
        self.chat_engine = GroqChat()
        self.latest_result = None
        self.cropped_image_path = None
        self.output_dir = "output"
        self.node_rects = {}       # node_id -> QGraphicsRectItem
        self._current_glow = None  # currently glowing node ID
        self._chat_streaming = False
        self._realtime_items = []
        self._realtime_nodes = {}
        os.makedirs(self.output_dir, exist_ok=True)
        
        self._init_theme()
        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()
        
    def _init_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#1e1e1e'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#d4d4d4'))
        palette.setColor(QPalette.ColorRole.Base, QColor('#1e1e1e'))
        palette.setColor(QPalette.ColorRole.Button, QColor('#333333'))
        palette.setColor(QPalette.ColorRole.Highlight, QColor('#0078d4'))
        self.setPalette(palette)
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")

    def _setup_ui(self):
        self.scene = QGraphicsScene()
        self.view = CropGraphicsView(self.scene)
        self.view.crop_confirmed.connect(self._on_crop_confirmed)
        self.view.right_click_symbol.connect(self._on_reclassify_request)
        self.setCentralWidget(self.view)
        
        self.scene.addText("Load a P&ID diagram to begin...").setDefaultTextColor(QColor("#555"))
        
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: none; } QTabBar::tab { background: #333; color: #ccc; padding: 5px; } QTabBar::tab:selected { background: #0078d4; }")
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Topology Explorer")
        self.tree.setStyleSheet("background-color: #252526; color: #ccc; border: none;")
        self.tabs.addTab(self.tree, "Hierarchy")
        
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #333; border-radius: 5px; padding: 10px; font-size: 13px;")
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask Digitwin AI Assistant...")
        self.chat_input.setStyleSheet("background-color: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 15px; padding: 8px 15px; margin-top: 5px;")
        self.chat_input.returnPressed.connect(self.send_chat)
        chat_layout.addWidget(self.chat_display)
        chat_layout.addWidget(self.chat_input)
        self.tabs.addTab(chat_container, "AI Assistant")
        
        dock_tree = QDockWidget("Topology & Intelligence", self)
        dock_tree.setWidget(self.tabs)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_tree)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Class", "Lables", "Coordinates"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: #1e1e1e; color: #bbb; gridline-color: #333;")
        dock_table = QDockWidget("Detection Metadata", self)
        dock_table.setWidget(self.table)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_table)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 10))
        self.console.setStyleSheet("background-color: #000; color: #00ff00; border: none;")
        dock_console = QDockWidget("Neural Console", self)
        dock_console.setWidget(self.console)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_console)
        self.tabifyDockWidget(dock_table, dock_console)

    def _setup_toolbar(self):
        bar = self.addToolBar("Controls")
        
        open_act = QAction("Open Diagram", self)
        open_act.triggered.connect(self.open_image)
        bar.addAction(open_act)
        
        bar.addSeparator()
        
        self.crop_act = QAction("Crop P&ID", self)
        self.crop_act.setEnabled(False)
        self.crop_act.triggered.connect(self._start_crop)
        bar.addAction(self.crop_act)
        
        self.crop_confirm_act = QAction("✓ Confirm Crop", self)
        self.crop_confirm_act.setEnabled(False)
        self.crop_confirm_act.triggered.connect(self._confirm_crop)
        bar.addAction(self.crop_confirm_act)
        
        self.crop_cancel_act = QAction("✕ Cancel Crop", self)
        self.crop_cancel_act.setEnabled(False)
        self.crop_cancel_act.triggered.connect(self._cancel_crop)
        bar.addAction(self.crop_cancel_act)
        
        bar.addSeparator()
        
        zoom_in = QAction("Zoom +", self)
        zoom_in.triggered.connect(lambda: self.view.scale(1.2, 1.2))
        bar.addAction(zoom_in)
        
        zoom_out = QAction("Zoom -", self)
        zoom_out.triggered.connect(lambda: self.view.scale(0.8, 0.8))
        bar.addAction(zoom_out)
        
        bar.addSeparator()
        
        tile_label = QLabel("  Tile:")
        tile_label.setStyleSheet("color: #aaa; font-size: 12px;")
        bar.addWidget(tile_label)
        self.tile_size = QSpinBox()
        self.tile_size.setRange(320, 1920)
        self.tile_size.setSingleStep(64)
        self.tile_size.setValue(640)
        self.tile_size.setToolTip("SAHI tile size (px) for tiled inference")
        self.tile_size.setStyleSheet("QSpinBox { background: #333; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 2px 4px; min-width: 70px; }")
        bar.addWidget(self.tile_size)
        
        self.run_act = QAction("Run Digitization", self)
        self.run_act.setEnabled(False)
        self.run_act.triggered.connect(self.run_engine)
        bar.addAction(self.run_act)
        
        export_act = QAction("Export DEXPI", self)
        export_act.triggered.connect(self.export_json)
        bar.addAction(export_act)

        export_graphml_act = QAction("Export GraphML", self)
        export_graphml_act.triggered.connect(self.export_graphml)
        bar.addAction(export_graphml_act)
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bar.addWidget(spacer)
        
        lang_label = QLabel("  🌐")
        lang_label.setStyleSheet("color: #aaa; font-size: 14px; margin-right: 2px;")
        bar.addWidget(lang_label)
        
        self.lang_combo = QtWidgets.QComboBox()
        for _code, name in SUPPORTED_LANGUAGES:
            self.lang_combo.addItem(name)
        self.lang_combo.setStyleSheet("QComboBox { background: #333; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 2px 6px; min-width: 140px; } QComboBox::drop-down { border: none; } QComboBox QAbstractItemView { background: #333; color: #ccc; selection-background-color: #0078d4; }")
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        bar.addWidget(self.lang_combo)
        
        logo_label = QLabel()
        _assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        logo_pixmap = QPixmap(os.path.join(_assets, "logo.png"))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation))
            logo_label.setStyleSheet("background: transparent; padding: 0; margin-right: 8px;")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText("DPID AI")
            logo_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-family: 'Segoe UI', sans-serif; font-size: 14px; letter-spacing: 1px; margin-right: 10px;")
        bar.addWidget(logo_label)

    def _setup_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.hide()
        self.status.addPermanentWidget(self.progress)
        self.status.showMessage("Ready")

    def _start_crop(self):
        """Enter crop mode — user draws rectangle on the image."""
        self.console.append("[CROP] Draw a rectangle around the P&ID diagram area.")
        self.view.enter_crop_mode()
        self.crop_act.setEnabled(False)
        self.crop_confirm_act.setEnabled(False)
        self.crop_cancel_act.setEnabled(True)
        try:
            self.view.crop_rect_changed.disconnect(self._on_crop_rect_changed)
        except TypeError:
            pass
        self.view.crop_rect_changed.connect(self._on_crop_rect_changed)

    def _on_crop_rect_changed(self):
        rect = self.view.get_crop_rect()
        self.crop_confirm_act.setEnabled(rect is not None)

    def _confirm_crop(self):
        rect = self.view.get_crop_rect()
        if rect:
            self._on_crop_confirmed(*rect)

    def _cancel_crop(self):
        self.view.exit_crop_mode()
        self.crop_act.setEnabled(True)
        self.crop_confirm_act.setEnabled(False)
        self.crop_cancel_act.setEnabled(False)
        self.console.append("[CROP] Cancelled.")
        try:
            self.view.crop_rect_changed.disconnect(self._on_crop_rect_changed)
        except TypeError:
            pass

    def _on_crop_confirmed(self, x1, y1, x2, y2):
        self.view.exit_crop_mode()
        self.crop_act.setEnabled(True)
        self.crop_confirm_act.setEnabled(False)
        self.crop_cancel_act.setEnabled(False)
        try:
            self.view.crop_rect_changed.disconnect(self._on_crop_rect_changed)
        except TypeError:
            pass
        self.console.append(f"[CROP] Region selected: ({x1},{y1}) → ({x2},{y2})")
        
        # Load original, crop, save as temp
        img = cv2.imread(self.image_path)
        if img is None:
            self.console.append("[ERROR] Failed to read image for cropping.")
            self.crop_act.setEnabled(True)
            return
        
        cropped = img[y1:y2, x1:x2]
        crop_dir = os.path.join(self.output_dir, "crops")
        os.makedirs(crop_dir, exist_ok=True)
        crop_path = os.path.join(crop_dir, f"cropped_{os.path.basename(self.image_path)}")
        cv2.imwrite(crop_path, cropped)
        self.cropped_image_path = crop_path
        
        # Update display to show only cropped region
        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(QPixmap(crop_path))
        self.scene.addItem(self.pixmap_item)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
        self.console.append(f"[CROP] P&ID isolated. Ready for digitization.")
        self.run_act.setEnabled(True)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open P&ID", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            if self.view.crop_active:
                self._cancel_crop()
            self.image_path = path
            self.cropped_image_path = None
            self.console.append(f"[SYSTEM] Loading High-Res Scene: {os.path.basename(path)}")
            
            self.scene.clear()
            self.pixmap_item = QGraphicsPixmapItem(QPixmap(path))
            self.scene.addItem(self.pixmap_item)
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            
            # Crop mandatory before digitization
            self.crop_act.setEnabled(True)
            self.run_act.setEnabled(False)
            self.console.append("[SYSTEM] Use 'Crop P&ID' to select the diagram region before digitization.")

    def _on_language_changed(self, idx):
        self.lang = SUPPORTED_LANGUAGES[idx][0]
        # Pre-warm cache with ALL strings in one batch API call (avoids rate limits)
        prewarm_language(self.lang)
        self._update_ui_language()
        # Re-translate any existing detection results
        if self.latest_result:
            self._retranslate_detections()

    def _update_ui_language(self):
        self.setWindowTitle(tr_gui("window_title", self.lang))
        self.tabs.setTabText(0, tr_gui("hierarchy", self.lang))
        self.tabs.setTabText(1, tr_gui("ai_assistant", self.lang))
        # Update dock widgets
        for dock in self.findChildren(QDockWidget):
            if dock.widget() == self.tabs:
                dock.setWindowTitle(tr_gui("topology_explorer", self.lang))
        # Find metadata dock
        for dock in self.findChildren(QDockWidget):
            if dock.widget() == self.table:
                dock.setWindowTitle(tr_gui("detection_metadata", self.lang))
        # Find console dock
        for dock in self.findChildren(QDockWidget):
            w = dock.widget()
            if isinstance(w, QTextEdit) and w != self.chat_display and w == self.console:
                dock.setWindowTitle(tr_gui("neural_console", self.lang))
        # Update table headers
        headers = tr_header(self.lang)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        # Update chat placeholder
        self.chat_input.setPlaceholderText(tr_gui("ask_placeholder", self.lang))
        # Update status
        self.status.showMessage(tr_gui("ready", self.lang))

    def _retranslate_detections(self):
        """Re-translate detection labels in table and tree when language changes."""
        nodes = self.latest_result.get('nodes', [])
        # Update tree
        self.tree.clear()
        root = QTreeWidgetItem(self.tree)
        seen_types = {}
        for node in nodes:
            type_key = node.get('type_key', node.get('type', 'unknown'))
            display_type = tr_class(type_key, self.lang)
            fine = node.get('attrs', {}).get('fine_class', '')
            ocr = node.get('attrs', {}).get('Labels', 'N/A')
            if fine:
                display = f"{display_type} → {fine} ({ocr})"
            else:
                display = f"{display_type} ({ocr}): {node['id']}"
            QTreeWidgetItem(root, [display])
        self.tree.expandAll()
        # Update table
        self.table.setRowCount(len(nodes))
        for i, node in enumerate(nodes):
            type_key = node.get('type_key', node.get('type', 'unknown'))
            display_type = tr_class(type_key, self.lang)
            fine = node.get('attrs', {}).get('fine_class', '')
            ocr = node.get('attrs', {}).get('Labels', 'N/A')
            coords = node.get('attrs', {})
            coord_str = f"{coords.get('xmin', 0):.0f},{coords.get('ymin', 0):.0f},{coords.get('xmax', 0):.0f},{coords.get('ymax', 0):.0f}"
            self.table.setItem(i, 0, QTableWidgetItem(node['id']))
            self.table.setItem(i, 1, QTableWidgetItem(display_type))
            self.table.setItem(i, 2, QTableWidgetItem(fine))
            self.table.setItem(i, 3, QTableWidgetItem(ocr))
            self.table.setItem(i, 4, QTableWidgetItem(coord_str))

    def run_engine(self):
        target_path = self.cropped_image_path if self.cropped_image_path else self.image_path
        self.console.append(f"[ENGINE] Starting digitization on: {os.path.basename(target_path)}")
        self._clear_boxes()
        self._clear_realtime_items()
        self._current_glow = None
        
        self.progress.show()
        self.progress.setRange(0, 0)
        
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
        self.progress.hide()
        self.console.append(f"[ENGINE ERROR] {error_msg}")
        self.status.showMessage("Digitization failed — see Neural Console for details")
        QMessageBox.critical(self, "Engine Error", f"Digitization failed:\n\n{error_msg[:500]}")

    def _draw_live_box(self, box_data):
        x1, y1, x2, y2, label = box_data
        rect = self.scene.addRect(QRectF(x1, y1, x2-x1, y2-y1), QPen(QColor(255, 0, 0), 1))
        rect.setToolTip(f"Proposal: {label}")

    def _draw_realtime_line(self, x1, y1, x2, y2, line_type):
        color_map = {
            "process": QColor(255, 0, 0),
            "signal": QColor(0, 0, 255),
            "utility": QColor(0, 200, 200),
            "software": QColor(0, 200, 0),
            "mechanical": QColor(0, 255, 255),
            "heat_trace": QColor(255, 0, 255)
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
        elif line_type == "heat_trace":
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setDashPattern([4, 2, 2, 2])
        line = self.scene.addLine(x1, y1, x2, y2, pen)
        line.setZValue(1)
        if not hasattr(self, '_realtime_items'):
            self._realtime_items = []
        self._realtime_items.append(line)

    def _draw_realtime_edge(self, src_id, tgt_id, line_type):
        src_bbox = self._realtime_nodes.get(src_id)
        tgt_bbox = self._realtime_nodes.get(tgt_id)
        if not src_bbox or not tgt_bbox:
            return
        sx1, sy1, sx2, sy2 = src_bbox
        tx1, ty1, tx2, ty2 = tgt_bbox
        smx, smy = (sx1+sx2)/2.0, (sy1+sy2)/2.0
        tmx, tmy = (tx1+tx2)/2.0, (ty1+ty2)/2.0
        color_map = {
            "process": QColor(255, 0, 0),
            "signal": QColor(0, 0, 255),
            "utility": QColor(0, 200, 200),
            "software": QColor(0, 200, 0),
            "mechanical": QColor(0, 255, 255),
            "heat_trace": QColor(255, 0, 255)
        }
        pen = QPen(color_map.get(line_type, QColor(255, 0, 0)), 3)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([8, 5])
        line = self.scene.addLine(smx, smy, tmx, tmy, pen)
        line.setZValue(2)
        if not hasattr(self, '_realtime_items'):
            self._realtime_items = []
        self._realtime_items.append(line)

    def _store_realtime_node(self, node_id, bbox):
        self._realtime_nodes[node_id] = bbox

    def _draw_ocr_bbox(self, x1, y1, x2, y2, text, conf):
        rect = self.scene.addRect(
            QRectF(x1, y1, x2-x1, y2-y1),
            QPen(QColor(0, 255, 255), 2, Qt.PenStyle.DashLine)
        )
        rect.setZValue(1.5)
        text_item = self.scene.addText(
            f"{text} ({conf:.0%})",
            QFont("Arial", 7)
        )
        text_item.setDefaultTextColor(QColor(0, 255, 255))
        text_item.setPos(x1, y1 - 18)
        text_item.setZValue(1.5)
        if not hasattr(self, '_realtime_items'):
            self._realtime_items = []
        self._realtime_items.append(rect)
        self._realtime_items.append(text_item)

    def _clear_realtime_items(self):
        if hasattr(self, '_realtime_items'):
            for item in self._realtime_items:
                if item in self.scene.items():
                    self.scene.removeItem(item)
            self._realtime_items.clear()
        if hasattr(self, '_realtime_nodes'):
            self._realtime_nodes.clear()

    def _clear_boxes(self):
        items_to_remove = []
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem):
                items_to_remove.append(item)
        for item in items_to_remove:
            self.scene.removeItem(item)

    def _on_finished(self, data):
        self.progress.hide()
        self.console.append("[SUCCESS] Digitization Complete.")
        
        try:
            with open(data["path"], "r") as f:
                result = json.load(f)
            self.latest_result = result
            self.chat_engine.index_result(result)
            nodes = result.get('nodes', [])
            edges = result.get('edges', [])
            
            self.console.append("\n[DEXPI OUTPUT] Final Industrial Schema:")
            self.console.append(json.dumps(result, indent=2))
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
                display = f"{display_type} → {fine_label} ({ocr_label})"
            else:
                display = f"{display_type} ({ocr_label}): {node['id']}"
            QTreeWidgetItem(root, [display])
            
            self.table.setItem(i, 0, QTableWidgetItem(node['id']))
            self.table.setItem(i, 1, QTableWidgetItem(display_type))
            self.table.setItem(i, 2, QTableWidgetItem(fine_label if fine_label else ''))
            self.table.setItem(i, 3, QTableWidgetItem(ocr_label))
            self.table.setItem(i, 4, QTableWidgetItem(f"{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}"))
            
            rect = self.scene.addRect(QRectF(x1, y1, x2-x1, y2-y1), 
                                       QPen(QColor(0, 255, 0), 3))
            rect.setToolTip(node['id'])
            self.node_rects[node['id']] = rect
        
        self.tree.expandAll()
        self.console.append(f"[REPORT] Finalized {len(nodes)} industrial nodes with {len(edges)} connections.")

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

    def _on_reclassify_request(self, node_id):
        if not self.latest_result:
            self.console.append("[RECLASSIFY] No results loaded yet.")
            return

        nodes = self.latest_result.get('nodes', [])
        node = next((n for n in nodes if n['id'] == node_id), None)
        if not node:
            return

        current_class = node.get('attrs', {}).get('fine_class', '') or node.get('attrs', {}).get('label', 'unknown')
        self.console.append(f"[RECLASSIFY] Opening gallery for {node_id} (current: {current_class})")

        x1 = int(node['attrs'].get('xmin', 0))
        y1 = int(node['attrs'].get('ymin', 0))
        x2 = int(node['attrs'].get('xmax', 0))
        y2 = int(node['attrs'].get('ymax', 0))

        crop = None
        target_path = self.cropped_image_path if self.cropped_image_path else getattr(self, 'image_path', None)
        if target_path:
            import cv2
            img = cv2.imread(target_path)
            if img is not None:
                crop = img[y1:y2, x1:x2].copy()

        if not hasattr(self, 'reclassify_sidebar') or self.reclassify_sidebar is None:
            self.reclassify_sidebar = ReclassifySidebar()
            self.reclassify_sidebar.class_selected.connect(
                lambda cls, parent: self._apply_reclassify(
                    self.reclassify_sidebar._current_node_id, cls, parent))
            self.reclassify_sidebar.setWindowFlags(
                Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
            self.reclassify_sidebar.setMinimumWidth(400)

        self.reclassify_sidebar.show_for_node(node_id, crop)
        self.reclassify_sidebar._current_node_id = node_id
        self.reclassify_sidebar.show()

    def _wrap_sidebar(self, widget):
        dock = QDockWidget("Reclassify", self)
        dock.setWidget(widget)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                        QDockWidget.DockWidgetFeature.DockWidgetClosable)
        return dock

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

        self.console.append(f"[RECLASSIFY] {old_class} → {new_class} ({count} symbols updated)")

    def send_chat(self):
        query = self.chat_input.text().strip()
        if not query:
            return
        if hasattr(self, '_chat_streaming') and self._chat_streaming:
            return

        self.chat_input.clear()
        self.chat_display.append(
            f"<div style='margin-bottom: 8px; padding: 6px; background: #2a2a2a; border-radius: 4px;'>"
            f"<b style='color: #4fc3f7;'>You:</b> <span style='color: #e0e0e0;'>{query}</span></div>"
        )
        self.chat_display.append(
            "<div id='ai-response' style='margin-bottom: 8px; padding: 6px; background: #1a2a1a; border-radius: 4px;'>"
            "<b style='color: #81c784;'>AI:</b> <span id='ai-text' style='color: #e0e0e0;'></span>"
            "<span id='ai-cursor' style='color: #81c784;'>▊</span></div>"
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
        self.console.append(f"[CHAT] Response complete ({len(full_response)} chars)")

    def _on_chat_error(self, error_msg):
        self._chat_streaming = False
        self.chat_input.setEnabled(True)
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"\n\n[ERROR] {error_msg}")
        self.chat_display.ensureCursorVisible()
        self.console.append(f"[CHAT ERROR] {error_msg}")

    def export_json(self):
        if not self.latest_result:
            self.console.append("[EXPORT] No digitization results to export. Run digitization first.")
            QMessageBox.warning(self, "Export", "No results to export. Run digitization first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save DEXPI JSON", self.output_dir, "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.latest_result, f, indent=2)
            self.console.append(f"[EXPORT] DEXPI JSON saved to {path}")
            self.status.showMessage(f"Exported DEXPI JSON → {os.path.basename(path)}")
        except Exception as e:
            self.console.append(f"[EXPORT ERROR] {e}")
            QMessageBox.critical(self, "Export Error", str(e))

    def export_graphml(self):
        if not self.latest_result:
            self.console.append("[EXPORT] No digitization results to export. Run digitization first.")
            QMessageBox.warning(self, "Export GraphML", "No results to export. Run digitization first.")
            return
        nodes = self.latest_result.get("nodes", [])
        edges = self.latest_result.get("edges", [])
        if not nodes:
            self.console.append("[EXPORT] No nodes in results — cannot generate GraphML.")
            QMessageBox.warning(self, "Export GraphML", "No nodes in results — cannot generate GraphML.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save GraphML", self.output_dir, "GraphML Files (*.graphml);;XML Files (*.xml);;All Files (*)"
        )
        if not path:
            return
        try:
            GraphMLFormatter.export(nodes, edges, path)
            self.console.append(f"[EXPORT] GraphML saved to {path}")
            self.status.showMessage(f"Exported GraphML → {os.path.basename(path)}")
        except Exception as e:
            self.console.append(f"[EXPORT ERROR] GraphML export failed: {e}")
            QMessageBox.critical(self, "Export Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DPIDDashboard()
    window.show()
    sys.exit(app.exec())
