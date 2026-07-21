import torch  # MUST IMPORT BEFORE PYQT6
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame,
    QScrollArea, QLineEdit, QTextEdit, QFileDialog,
    QGridLayout
)
from gui.style import GLOBAL_QSS
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPalette, QTextCursor


class ChatThread(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, chat_engine, query):
        super().__init__()
        self.chat_engine = chat_engine
        self.query = query

    def run(self):
        try:
            response = self.chat_engine.ask(self.query, stream=True)
            if response is None:
                self.error.emit("Failed to get response. Check GROQ_API_KEY.")
                return
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    self.chunk_received.emit(chunk.choices[0].delta.content)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class NavBtn(QPushButton):
    def __init__(self, icon_char, label_text, parent=None):
        self._icon_char = icon_char
        self._label_text = label_text
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self._expanded = True
        self._apply_text()
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                text-align: left;
                padding-left: 14px;
                font-size: 14px;
                font-weight: 500;
                border-radius: 12px;
                margin: 2px 8px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.10);
                color: #F8FAFC;
            }
            QPushButton:checked {
                background: rgba(59, 130, 246, 0.15);
                color: #3B82F6;
                font-weight: 600;
            }
        """)

    def set_expanded(self, expanded):
        self._expanded = expanded
        self._apply_text()

    def _apply_text(self):
        if self._expanded:
            self.setText(f"  {self._icon_char}    {self._label_text}")
            self.setToolTip("")
        else:
            self.setText(f"  {self._icon_char}")
            self.setToolTip(self._label_text)


class HomeScreen(QMainWindow):
    SIDEBAR_W_EXPANDED = 220
    SIDEBAR_W_COLLAPSED = 60
    ANIM_DURATION = 200

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DocuPID")
        self.resize(1340, 860)
        self.setMinimumSize(980, 620)
        self._sidebar_expanded = True
        self._chat_thread = None
        self._chat_streaming = False
        self._home_response_text = ""
        self._in_chat_mode = False
        self._chat_messages = []

        try:
            from core.okf_rag import OKFRAGChat
            self._rag_chat = OKFRAGChat()
        except Exception as e:
            print(f"[OKF-RAG] Init failed: {e}")
            self._rag_chat = None

        try:
            from core.knowledge_platform import KnowledgePlatform
            self._platform = KnowledgePlatform()
        except Exception as e:
            print(f"[KnowledgePlatform] Init failed: {e}")
            self._platform = None

        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor("#0F172A"))
        p.setColor(QPalette.ColorRole.WindowText, QColor("#F8FAFC"))
        p.setColor(QPalette.ColorRole.Base, QColor("#0F172A"))
        p.setColor(QPalette.ColorRole.Button, QColor("#1E293B"))
        p.setColor(QPalette.ColorRole.Highlight, QColor("#3B82F6"))
        self.setPalette(p)
        self.setStyleSheet(GLOBAL_QSS)

        central = QWidget()
        self.setCentralWidget(central)
        self._root = QHBoxLayout(central)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        self._sidebar = QFrame()
        self._sidebar.setFixedWidth(self.SIDEBAR_W_EXPANDED)
        self._sidebar.setStyleSheet("""
            QFrame {
                background: #111827;
                border-right: 1px solid #1E293B;
            }
        """)
        self._sb_layout = QVBoxLayout(self._sidebar)
        self._sb_layout.setContentsMargins(8, 16, 8, 12)
        self._sb_layout.setSpacing(2)

        self._brand_row = QHBoxLayout()
        self._brand_row.setSpacing(8)
        self._brand_icon = QLabel("DP")
        self._brand_icon.setFixedWidth(36)
        self._brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._brand_icon.setStyleSheet("""
            color: #3B82F6; font-size: 14px; font-weight: bold;
            background: #1E293B; border: 1px solid #334155; border-radius: 8px;
            padding: 4px;
        """)
        self._brand_row.addWidget(self._brand_icon)

        self._brand_text = QLabel("DocuPID")
        self._brand_text.setStyleSheet("color: #fff; font-size: 16px; font-weight: bold;")
        self._brand_row.addWidget(self._brand_text)
        self._brand_row.addStretch()
        self._sb_layout.addLayout(self._brand_row)

        self._toggle_btn = QPushButton("\u25C0")
        self._toggle_btn.setFixedSize(26, 26)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B; color: #94A3B8; border: 1px solid #334155;
                border-radius: 8px; font-size: 11px;
            }
            QPushButton:hover { background: #3B82F6; color: #fff; border-color: #3B82F6; }
        """)
        self._toggle_btn.clicked.connect(self._toggle_sidebar)
        self._brand_row.addWidget(self._toggle_btn)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: #1E293B;")
        self._sb_layout.addWidget(div)
        self._sb_layout.addSpacing(6)

        self._nav_btns = []
        self._nav_groups = []

        def add_group(name):
            lbl = QLabel(name.upper())
            lbl.setStyleSheet("color: #64748B; font-size: 10px; font-weight: bold; margin: 12px 8px 4px 12px;")
            self._sb_layout.addWidget(lbl)
            self._nav_groups.append(lbl)

        def add_btn(icon, label):
            btn = NavBtn(icon, label)
            btn.clicked.connect(lambda _, i=len(self._nav_btns): self._switch(i))
            self._sb_layout.addWidget(btn)
            self._nav_btns.append(btn)

        add_group("Dashboard")
        add_btn("⬡", "Home")

        add_group("Document Processing")
        add_btn("◎", "PID Digitization")

        add_group("AI Intelligence")
        add_btn("⬢", "OKF Dashboard")

        add_group("Administration")
        add_btn("⚙", "Engine Settings")
        add_btn("👥", "Users Management")
        add_btn("🛠", "Settings")
        add_btn("🏢", "Team")

        self._sb_layout.addStretch()

        self._team_label = QLabel("Team InsightLedger")
        self._team_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._team_label.setStyleSheet("color: #555; font-size: 10px;")
        self._sb_layout.addWidget(self._team_label)

        self._root.addWidget(self._sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("central_widget")
        self._root.addWidget(self.stack)

        self._build_pages()
        self._switch(0)
        self._load_stats()

    def _toggle_sidebar(self):
        end_w = self.SIDEBAR_W_COLLAPSED if self._sidebar_expanded else self.SIDEBAR_W_EXPANDED

        self._anim = QPropertyAnimation(self._sidebar, b"minimumWidth")
        self._anim.setDuration(self.ANIM_DURATION)
        self._anim.setStartValue(self._sidebar.width())
        self._anim.setEndValue(end_w)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim2 = QPropertyAnimation(self._sidebar, b"maximumWidth")
        self._anim2.setDuration(self.ANIM_DURATION)
        self._anim2.setStartValue(self._sidebar.width())
        self._anim2.setEndValue(end_w)
        self._anim2.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._sidebar_expanded = not self._sidebar_expanded
        expanded = self._sidebar_expanded

        self._toggle_btn.setText("\u25C0" if expanded else "\u25B6")
        self._brand_text.setVisible(expanded)
        self._team_label.setText("Team InsightLedger" if expanded else "IL")

        for lbl in self._nav_groups:
            lbl.setVisible(expanded)

        for btn in self._nav_btns:
            btn.set_expanded(expanded)

        self._anim.start()
        self._anim2.start()

    def _build_pages(self):
        self.stack.addWidget(self._home_page())
        from gui.dashboard_page import DashboardPage
        self.stack.addWidget(DashboardPage())
        from gui.okf_dashboard import OKFDashboardPage
        self.stack.addWidget(OKFDashboardPage())
        from gui.settings_page import EngineSettingsPage
        self.stack.addWidget(EngineSettingsPage())
        from gui.users_page import UsersManagementPage
        self.stack.addWidget(UsersManagementPage())
        from gui.general_settings import GeneralSettingsPage
        self.stack.addWidget(GeneralSettingsPage())
        from gui.team_screen import TeamPage
        self.stack.addWidget(TeamPage())

    def _home_page(self):
        outer = QWidget()
        outer.setObjectName("home_page")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        page.setObjectName("home_page_content")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(32, 24, 32, 32)
        page_layout.setSpacing(24)

        # Welcome Header (Top Header)
        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        welcome_lbl = QLabel("Welcome, Admin")
        welcome_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #F8FAFC;")
        sub_lbl = QLabel("Current Project: Alpha Plant Modernization")
        sub_lbl.setStyleSheet("font-size: 15px; color: #94A3B8; margin-bottom: 8px;")
        header_left.addWidget(welcome_lbl)
        header_left.addWidget(sub_lbl)
        
        header_right = QVBoxLayout()
        status_lbl = QLabel("● System Status: Online")
        status_lbl.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px;")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        sync_lbl = QLabel("Last Sync: Just now")
        sync_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        sync_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_right.addWidget(status_lbl)
        header_right.addWidget(sync_lbl)
        header_right.addStretch()

        header_layout.addLayout(header_left)
        header_layout.addStretch()
        header_layout.addLayout(header_right)
        
        page_layout.addLayout(header_layout)

        # KPI Cards Row
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)
        stats_data = [
            ("Documents Ingested", "#3B82F6", "📄", "—", "Live"),
            ("Knowledge Nodes", "#8B5CF6", "⬡", "—", "Live"),
            ("Relationships", "#10B981", "◎", "—", "Live"),
            ("Entity Types", "#F59E0B", "⊟", "—", "Live"),
            ("Total Users", "#06B6D4", "👥", "—", "Live"),
            ("RAG Chunks", "#EC4899", "✧", "—", "Live"),
        ]
        self._stat_vals = []
        for i, (label, color, icon, default_val, trend) in enumerate(stats_data):
            card = QFrame()
            card.setObjectName("card")
            card.setFixedHeight(95)
            card.setStyleSheet(f"""
                QFrame#card {{ background: #1E293B; border: 1px solid #334155; border-radius: 16px; }}
                QFrame#card:hover {{ border-color: {color}; }}
            """)
            row = QHBoxLayout(card)
            row.setContentsMargins(20, 16, 20, 16)
            row.setSpacing(16)

            icon_box = QLabel(icon)
            icon_box.setFixedSize(48, 48)
            icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_box.setStyleSheet(f"background: {color}15; color: {color}; border-radius: 12px; font-size: 22px;")
            row.addWidget(icon_box)

            info = QVBoxLayout()
            info.setSpacing(2)
            
            val_row = QHBoxLayout()
            val = QLabel(default_val)
            val.setStyleSheet("color: #F8FAFC; font-size: 24px; font-weight: 700; border: none;")
            self._stat_vals.append(val)
            val_row.addWidget(val)
            
            trend_lbl = QLabel(trend)
            trend_color = "#10B981" if "↑" in trend else "#94A3B8"
            trend_lbl.setStyleSheet(f"color: {trend_color}; font-size: 11px; font-weight: bold; border: none;")
            val_row.addStretch()
            val_row.addWidget(trend_lbl)
            
            info.addLayout(val_row)
            
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 500; border: none;")
            info.addWidget(lbl)
            
            row.addLayout(info)
            stats_grid.addWidget(card, i // 3, i % 3)
        
        page_layout.addLayout(stats_grid)

        # Main Content Split
        main_split = QHBoxLayout()
        main_split.setSpacing(24)

        # Left Column
        left_col = QVBoxLayout()
        left_col.setSpacing(24)

        # Quick Actions
        actions_card = QFrame()
        actions_card.setObjectName("card")
        act_layout = QVBoxLayout(actions_card)
        act_layout.setContentsMargins(20, 20, 20, 20)
        act_layout.setSpacing(12)
        
        act_header = QLabel("Quick Actions")
        act_header.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 600;")
        act_layout.addWidget(act_header)

        btn_grid = QGridLayout()
        btn_grid.setSpacing(12)
        
        self._upload_btn = QPushButton("⬑ Upload Document")
        self._upload_btn.setFixedHeight(44)
        self._upload_btn.setStyleSheet("QPushButton { background: #3B82F6; color: white; border-radius: 8px; font-weight: bold; } QPushButton:hover { background: #2563EB; }")
        self._upload_btn.clicked.connect(self._pick_upload_file)
        btn_grid.addWidget(self._upload_btn, 0, 0)

        self._ocr_btn = QPushButton("◎ Run OCR")
        self._ocr_btn.setFixedHeight(44)
        self._ocr_btn.setStyleSheet("QPushButton { background: #1E293B; color: white; border: 1px solid #334155; border-radius: 8px; font-weight: bold; } QPushButton:hover { background: #334155; }")
        btn_grid.addWidget(self._ocr_btn, 0, 1)

        self._kg_btn = QPushButton("⬡ Generate Knowledge Graph")
        self._kg_btn.setFixedHeight(44)
        self._kg_btn.setStyleSheet("QPushButton { background: #1E293B; color: white; border: 1px solid #334155; border-radius: 8px; font-weight: bold; } QPushButton:hover { background: #334155; }")
        btn_grid.addWidget(self._kg_btn, 1, 0)

        self._ai_btn = QPushButton("✧ Open AI Assistant")
        self._ai_btn.setFixedHeight(44)
        self._ai_btn.setStyleSheet("QPushButton { background: #1E293B; color: white; border: 1px solid #334155; border-radius: 8px; font-weight: bold; } QPushButton:hover { background: #334155; }")
        btn_grid.addWidget(self._ai_btn, 1, 1)

        act_layout.addLayout(btn_grid)
        
        self._upload_status = QLabel("")
        self._upload_status.setStyleSheet("color: #10B981; font-size: 13px; margin-top: 4px;")
        act_layout.addWidget(self._upload_status)
        
        left_col.addWidget(actions_card)

        # Recent Documents (Placeholder)
        docs_card = QFrame()
        docs_card.setObjectName("card")
        docs_layout = QVBoxLayout(docs_card)
        docs_layout.setContentsMargins(20, 20, 20, 20)
        docs_layout.setSpacing(16)
        docs_header = QLabel("Recent Documents")
        docs_header.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 600;")
        docs_layout.addWidget(docs_header)
        
        for doc, stat, prog in [("P&ID_Area_1A.pdf", "Completed", "100%"), ("Compressor_Schematic.jpg", "Processing", "65%"), ("Valve_Matrix.xlsx", "Pending", "0%")]:
            d_row = QHBoxLayout()
            d_lbl = QLabel(f"📄 {doc}")
            d_lbl.setStyleSheet("color: #E2E8F0; font-size: 13px;")
            d_stat = QLabel(stat)
            col = "#10B981" if stat == "Completed" else ("#F59E0B" if stat == "Processing" else "#64748B")
            d_stat.setStyleSheet(f"color: {col}; font-size: 11px; border: 1px solid {col}; border-radius: 4px; padding: 2px 6px;")
            d_prog = QLabel(prog)
            d_prog.setStyleSheet("color: #94A3B8; font-size: 12px;")
            d_row.addWidget(d_lbl)
            d_row.addStretch()
            d_row.addWidget(d_stat)
            d_row.addWidget(d_prog)
            docs_layout.addLayout(d_row)
            
        left_col.addWidget(docs_card)

        # Recent Activity Timeline (Placeholder)
        activity_card = QFrame()
        activity_card.setObjectName("card")
        actv_layout = QVBoxLayout(activity_card)
        actv_layout.setContentsMargins(20, 20, 20, 20)
        actv_layout.setSpacing(16)
        actv_header = QLabel("Recent Activity Timeline")
        actv_header.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 600;")
        actv_layout.addWidget(actv_header)
        
        for act in ["Uploaded document: Pump_Station_7.pdf", "OCR completed for Area 1A", "Knowledge Graph generated", "AI answered question"]:
            lbl = QLabel(f"• {act}")
            lbl.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 4px 0;")
            actv_layout.addWidget(lbl)
        
        actv_layout.addStretch()
        left_col.addWidget(activity_card, 1)

        main_split.addLayout(left_col, 1)

        # Right Column (AI Assistant)
        chat_card = QFrame()
        chat_card.setObjectName("card")
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(20, 20, 20, 20)
        chat_layout.setSpacing(16)

        chat_header = QLabel("✧  Digitwin AI Assistant")
        chat_header.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 600;")
        chat_layout.addWidget(chat_header)

        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setMinimumHeight(350)
        self._chat_display.setStyleSheet("""
            QTextEdit {
                background: #0F172A; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 12px; padding: 16px; font-size: 14px;
            }
        """)
        self._chat_display.setPlaceholderText("Ask anything about the OKF knowledge base...")
        chat_layout.addWidget(self._chat_display, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(12)

        self._home_query = QLineEdit()
        self._home_query.setPlaceholderText("Message Digitwin...")
        self._home_query.setFixedHeight(48)
        self._home_query.setStyleSheet("""
            QLineEdit {
                background: #0F172A; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 24px; padding: 0 20px; font-size: 14px;
            }
            QLineEdit:focus { border-color: #3B82F6; background: #111827; }
        """)
        self._home_query.returnPressed.connect(self._send_home_query)
        input_row.addWidget(self._home_query, 1)

        self._home_send_btn = QPushButton("↑")
        self._home_send_btn.setFixedSize(48, 48)
        self._home_send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._home_send_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6; color: #FFFFFF; border: none;
                border-radius: 24px; font-size: 20px; font-weight: bold;
            }
            QPushButton:hover { background: #2563EB; }
            QPushButton:disabled { background: #1E293B; color: #64748B; }
        """)
        self._home_send_btn.clicked.connect(self._send_home_query)
        input_row.addWidget(self._home_send_btn)

        chat_layout.addLayout(input_row)
        main_split.addWidget(chat_card, 2)

        page_layout.addLayout(main_split, 1)
        
        scroll.setWidget(page)
        outer_layout.addWidget(scroll)
        return outer

    def _pick_upload_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Documents", "",
            "All Supported (*.pdf *.xlsx *.xls *.png *.jpg *.jpeg *.bmp *.tiff *.txt *.md *.csv);;PDF (*.pdf);;Excel (*.xlsx *.xls);;Images (*.png *.jpg *.jpeg *.bmp *.tiff);;Text (*.txt *.md *.csv)"
        )
        if not files:
            return
        self._upload_btn.setEnabled(False)
        self._upload_btn.setText(f"Uploading {len(files)} file(s)...")
        self._upload_status.setText("")

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._process_uploads(files))

    def _process_uploads(self, files):
        if self._platform is None:
            self._upload_status.setStyleSheet("color: #ef4444; font-size: 12px; border: none;")
            self._upload_status.setText("Knowledge platform not available")
            self._upload_btn.setEnabled(True)
            self._upload_btn.setText("\u2B06  Upload Document")
            return

        success = 0
        failed = 0
        for f in files:
            try:
                result = self._platform.ingest_document(f)
                if result.get("status") == "error":
                    failed += 1
                else:
                    success += 1
            except Exception as e:
                print(f"[Upload] Failed: {f} — {e}")
                failed += 1

        self._upload_btn.setEnabled(True)
        self._upload_btn.setText("\u2B06  Upload Document")
        parts = []
        if success:
            parts.append(f"{success} ingested")
        if failed:
            parts.append(f"{failed} failed")
        msg = ", ".join(parts)
        color = "#10b981" if success else "#ef4444"
        self._upload_status.setStyleSheet(f"color: {color}; font-size: 12px; border: none;")
        self._upload_status.setText(msg)

    def _send_home_query(self):
        query = self._home_query.text().strip()
        if not query or self._chat_streaming:
            return

        self._home_query.clear()

        self._chat_messages = getattr(self, '_chat_messages', [])
        self._chat_messages.append(("user", query))
        self._refresh_chat()

        if self._rag_chat is None:
            self._chat_messages.append(("error", "OKF-RAG engine not available. Check GROQ_API_KEY in .env"))
            self._refresh_chat()
            return

        self._chat_streaming = True
        self._home_query.setEnabled(False)
        self._home_send_btn.setEnabled(False)
        self._home_response_text = ""

        self._chat_thread = ChatThread(self._rag_chat, query)
        self._chat_thread.chunk_received.connect(self._on_chat_chunk)
        self._chat_thread.finished.connect(self._on_chat_finished)
        self._chat_thread.error.connect(self._on_chat_error)
        self._chat_thread.start()

    def _refresh_chat(self):
        html_parts = []
        for role, text in getattr(self, '_chat_messages', []):
            if role == "user":
                html_parts.append(
                    f"<div style='margin-bottom:10px;padding:8px 12px;background:#1e293b;border-radius:8px;'>"
                    f"<b style='color:#3b82f6;'>You:</b> <span style='color:#e2e8f0;'>{text}</span></div>"
                )
            elif role == "assistant":
                html_parts.append(
                    f"<div style='margin-bottom:10px;padding:8px 12px;background:#0f172a;border-radius:8px;'>"
                    f"<b style='color:#10b981;'>OKF Assistant:</b> "
                    f"<span style='color:#e2e8f0;'>{text}</span></div>"
                )
            elif role == "streaming":
                html_parts.append(
                    f"<div style='margin-bottom:10px;padding:8px 12px;background:#0f172a;border-radius:8px;'>"
                    f"<b style='color:#10b981;'>OKF Assistant:</b> "
                    f"<span style='color:#e2e8f0;'>{text}</span>"
                    f"<span style='color:#10b981;'>|</span></div>"
                )
            elif role == "error":
                html_parts.append(
                    f"<div style='margin-bottom:10px;padding:8px 12px;background:#2d1215;border-radius:8px;'>"
                    f"<b style='color:#ef4444;'>[ERROR]</b> <span style='color:#ef4444;'>{text}</span></div>"
                )
        self._chat_display.setHtml("".join(html_parts))
        sb = self._chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_chat_chunk(self, chunk):
        self._home_response_text += chunk
        self._chat_messages = getattr(self, '_chat_messages', [])
        if self._chat_messages and self._chat_messages[-1][0] == "streaming":
            self._chat_messages[-1] = ("streaming", self._home_response_text)
        else:
            self._chat_messages.append(("streaming", self._home_response_text))
        self._refresh_chat()

    def _on_chat_finished(self):
        self._chat_streaming = False
        self._home_query.setEnabled(True)
        self._home_send_btn.setEnabled(True)
        self._home_query.setFocus()
        self._chat_messages = getattr(self, '_chat_messages', [])
        if self._chat_messages and self._chat_messages[-1][0] == "streaming":
            self._chat_messages[-1] = ("assistant", self._home_response_text)
        self._refresh_chat()

    def _on_chat_error(self, error_msg):
        self._chat_streaming = False
        self._home_query.setEnabled(True)
        self._home_send_btn.setEnabled(True)
        self._chat_messages = getattr(self, '_chat_messages', [])
        if self._chat_messages and self._chat_messages[-1][0] == "streaming":
            self._chat_messages.pop()
        self._chat_messages.append(("error", error_msg))
        self._refresh_chat()

    def _load_stats(self):
        """Load real statistics from backend KnowledgeGraph and storage."""
        import json, os
        # --- KG Stats (real) ---
        try:
            kg_path = os.path.join(os.getcwd(), "storage", "knowledge_graph.json")
            if os.path.exists(kg_path):
                with open(kg_path, "r", encoding="utf-8") as f:
                    kg_data = json.load(f)
                nodes = kg_data.get("nodes", {})
                edges = kg_data.get("edges", [])
                # Count unique source documents
                sources = set()
                type_set = set()
                for node in nodes.values():
                    type_set.add(node.get("type", ""))
                    for src in node.get("sources", []):
                        sources.add(src)
                # KPI index 0 = Documents (unique sources)
                self._stat_vals[0].setText(str(len(sources)))
                # KPI index 1 = Knowledge Nodes
                self._stat_vals[1].setText(str(len(nodes)))
                # KPI index 2 = Relationships (edges)
                self._stat_vals[2].setText(str(len(edges)))
                # KPI index 3 = Entity Types
                self._stat_vals[3].setText(str(len(type_set)))
        except Exception as e:
            print(f"[Stats] KG failed: {e}")

        # --- Platform-based stats if available ---
        if hasattr(self, '_platform') and self._platform is not None:
            try:
                kg_stats = self._platform.kg.get_stats()
                self._stat_vals[1].setText(str(kg_stats.get("total_nodes", 0)))
                self._stat_vals[2].setText(str(kg_stats.get("total_edges", 0)))
                self._stat_vals[3].setText(str(len(kg_stats.get("types", {}))))
                self._stat_vals[0].setText(str(kg_stats.get("sources", 0)))
            except Exception as e:
                print(f"[Stats] Platform KG failed: {e}")
            try:
                rag_stats = self._platform.rag.get_stats()
                # KPI index 5 = AI Queries (chunks as proxy)
                self._stat_vals[5].setText(str(rag_stats.get("total_chunks", 0)))
            except Exception as e:
                print(f"[Stats] RAG failed: {e}")

        # --- Users count ---
        try:
            users_path = os.path.join(os.getcwd(), "storage", "users.json")
            if os.path.exists(users_path):
                with open(users_path, "r", encoding="utf-8") as f:
                    users = json.load(f)
                # KPI index 4 = Users Count
                self._stat_vals[4].setText(str(len(users)))
        except Exception as e:
            print(f"[Stats] Users failed: {e}")

    def _switch(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == index)
