from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QScrollArea, QSpinBox
)
from PyQt6.QtCore import Qt
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


class EngineSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # Header
        header = QLabel("Settings")
        header.setStyleSheet("color: #F8FAFC; font-size: 28px; font-weight: bold;")
        layout.addWidget(header)
        
        subtitle = QLabel("System preferences, AI configurations, and processing parameters")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 15px; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # Grid for Cards
        grid = QGridLayout()
        grid.setSpacing(24)

        # --- General Card ---
        general_card = self._create_card("General")
        g_layout = QVBoxLayout()
        g_layout.setSpacing(16)
        
        g_layout.addWidget(self._create_field("Appearance", "combo", ["Dark", "Light", "System Auto"]))
        g_layout.addWidget(self._create_field("Language", "combo", ["English", "German", "Spanish", "Japanese"]))
        g_layout.addWidget(self._create_field("Notifications", "check", "Enable system notifications", checked=True))
        
        general_card.layout().addLayout(g_layout)
        grid.addWidget(general_card, 0, 0)

        # --- AI Models Card ---
        ai_card = self._create_card("AI Models")
        ai_layout = QVBoxLayout()
        ai_layout.setSpacing(16)
        
        ai_layout.addWidget(self._create_field("Vision Model", "text", os.getenv("VISION_MODEL", "llama-3.2-11b-vision-preview")))
        ai_layout.addWidget(self._create_field("Chat Model", "text", os.getenv("CHAT_MODEL", "mixtral-8x7b-32768")))
        ai_layout.addWidget(self._create_field("Embedding Model", "text", "nomic-embed-text-v1_5"))
        ai_layout.addWidget(self._create_field("Groq API Key", "password", os.getenv("GROQ_API_KEY", "")))
        
        ai_card.layout().addLayout(ai_layout)
        grid.addWidget(ai_card, 0, 1)

        # --- Processing Card ---
        proc_card = self._create_card("Processing")
        p_layout = QVBoxLayout()
        p_layout.setSpacing(16)
        
        p_layout.addWidget(self._create_field("GPU Acceleration (CUDA)", "check", "Enable hardware acceleration", checked=True))
        p_layout.addWidget(self._create_field("Max Threads", "spin", value=8, vrange=(1, 32)))
        p_layout.addWidget(self._create_field("OCR Engine", "combo", ["Tesseract", "EasyOCR", "PaddleOCR"]))
        p_layout.addWidget(self._create_field("Batch Size", "spin", value=16, vrange=(1, 128)))
        
        proc_card.layout().addLayout(p_layout)
        grid.addWidget(proc_card, 1, 0)

        # --- Export Card ---
        exp_card = self._create_card("Export")
        e_layout = QVBoxLayout()
        e_layout.setSpacing(16)
        
        e_layout.addWidget(self._create_field("Auto-Export DEXPI", "check", "Export DEXPI JSON automatically", checked=True))
        e_layout.addWidget(self._create_field("Auto-Export GraphML", "check", "Export Knowledge Graph to GraphML", checked=False))
        e_layout.addWidget(self._create_field("Auto-Export JSON", "check", "Export raw JSON data", checked=True))
        e_layout.addWidget(self._create_field("Auto-Export CSV", "check", "Export tabular data to CSV", checked=False))
        
        exp_card.layout().addLayout(e_layout)
        grid.addWidget(exp_card, 1, 1)

        layout.addLayout(grid)

        # --- Logs & Maintenance ---
        logs_card = self._create_card("System Maintenance")
        l_layout = QHBoxLayout()
        l_layout.setSpacing(16)
        
        def make_btn(text, style_color):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(44)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {style_color}22; color: {style_color}; border: 1px solid {style_color}; border-radius: 8px; font-weight: bold; padding: 0 20px; }}
                QPushButton:hover {{ background: {style_color}; color: #FFFFFF; }}
            """)
            return btn
            
        l_layout.addWidget(make_btn("Open Logs", "#3B82F6"))
        l_layout.addWidget(make_btn("Clear Cache", "#F59E0B"))
        l_layout.addStretch()
        l_layout.addWidget(make_btn("Reset Settings", "#EF4444"))
        
        logs_card.layout().addLayout(l_layout)
        layout.addWidget(logs_card)
        
        layout.addStretch()
        scroll.setWidget(page)
        main_layout.addWidget(scroll)

    def _create_card(self, title_text):
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("QFrame#card { background: #1E293B; border: 1px solid #334155; border-radius: 16px; }")
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        title = QLabel(title_text)
        title.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: bold; border: none;")
        layout.addWidget(title)
        
        return card

    def _create_field(self, label_text, ftype, val=None, checked=False, vrange=None, value=None):
        w = QWidget()
        w.setStyleSheet("border: none; background: transparent;")
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #E2E8F0; font-size: 14px; font-weight: 500;")
        lbl.setMinimumWidth(150)
        
        if ftype == "check":
            l.addWidget(lbl)
            cb = QCheckBox(val) # val acts as label
            cb.setChecked(checked)
            cb.setStyleSheet("QCheckBox { color: #94A3B8; font-size: 13px; } QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #475569; } QCheckBox::indicator:checked { background: #3B82F6; border: none; }")
            l.addWidget(cb)
            l.addStretch()
            return w
            
        l.addWidget(lbl)
        
        if ftype == "combo":
            cb = QComboBox()
            cb.addItems(val)
            cb.setFixedHeight(36)
            cb.setStyleSheet("QComboBox { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 4px 12px; } QComboBox::drop-down { border: none; }")
            l.addWidget(cb, 1)
        elif ftype == "text":
            le = QLineEdit(val)
            le.setFixedHeight(36)
            le.setStyleSheet("QLineEdit { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 4px 12px; } QLineEdit:focus { border-color: #3B82F6; }")
            l.addWidget(le, 1)
        elif ftype == "password":
            le = QLineEdit(val)
            le.setEchoMode(QLineEdit.EchoMode.Password)
            le.setFixedHeight(36)
            le.setStyleSheet("QLineEdit { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 4px 12px; } QLineEdit:focus { border-color: #3B82F6; }")
            l.addWidget(le, 1)
        elif ftype == "spin":
            sb = QSpinBox()
            if vrange:
                sb.setRange(vrange[0], vrange[1])
            if value:
                sb.setValue(value)
            sb.setFixedHeight(36)
            sb.setStyleSheet("QSpinBox { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 4px 12px; }")
            l.addWidget(sb, 1)
            
        return w
