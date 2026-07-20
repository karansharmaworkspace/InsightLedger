import torch  # MUST IMPORT BEFORE PYQT6
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame,
    QScrollArea, QLineEdit, QTextEdit, QFileDialog
)
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
                color: #888;
                border: none;
                text-align: left;
                padding-left: 14px;
                font-size: 13px;
                border-radius: 6px;
                margin: 1px 8px;
            }
            QPushButton:hover {
                background: rgba(0,120,212,0.10);
                color: #d4d4d4;
            }
            QPushButton:checked {
                background: rgba(0,120,212,0.18);
                color: #0078d4;
                font-weight: bold;
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
        p.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        p.setColor(QPalette.ColorRole.WindowText, QColor("#d4d4d4"))
        p.setColor(QPalette.ColorRole.Base, QColor("#252526"))
        p.setColor(QPalette.ColorRole.Button, QColor("#333"))
        p.setColor(QPalette.ColorRole.Highlight, QColor("#0078d4"))
        self.setPalette(p)

        central = QWidget()
        self.setCentralWidget(central)
        self._root = QHBoxLayout(central)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        self._sidebar = QFrame()
        self._sidebar.setFixedWidth(self.SIDEBAR_W_EXPANDED)
        self._sidebar.setStyleSheet("""
            QFrame {
                background: #252526;
                border-right: 1px solid #333;
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
            color: #0078d4; font-size: 13px; font-weight: bold;
            background: #1e1e1e; border: 1px solid #333; border-radius: 6px;
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
                background: #333; color: #888; border: 1px solid #444;
                border-radius: 5px; font-size: 11px;
            }
            QPushButton:hover { background: #0078d4; color: #fff; border-color: #0078d4; }
        """)
        self._toggle_btn.clicked.connect(self._toggle_sidebar)
        self._brand_row.addWidget(self._toggle_btn)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background: #333;")
        self._sb_layout.addWidget(div)
        self._sb_layout.addSpacing(6)

        self._nav_btns = []
        nav_items = [
            ("\u2B21", "Home"),
            ("\u25CE", "PID Digitization"),
            ("\u229E", "OKF Dashboard"),
            ("\u2699", "Engine Settings"),
            ("\u2295", "Users Management"),
            ("\u2692", "Settings"),
            ("\u263A", "Team"),
        ]
        for icon, label in nav_items:
            btn = NavBtn(icon, label)
            btn.clicked.connect(lambda _, i=len(self._nav_btns): self._switch(i))
            self._sb_layout.addWidget(btn)
            self._nav_btns.append(btn)

        self._sb_layout.addStretch()

        self._team_label = QLabel("Team InsightLedger")
        self._team_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._team_label.setStyleSheet("color: #555; font-size: 10px;")
        self._sb_layout.addWidget(self._team_label)

        self._root.addWidget(self._sidebar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: #1e1e1e;")
        self._root.addWidget(self.stack)

        self._build_pages()
        self._switch(0)

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
        outer.setStyleSheet("background: #1e1e1e;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        page = QWidget()
        page.setStyleSheet("background: transparent;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(24, 20, 24, 20)
        page_layout.setSpacing(16)

        stats_grid = QHBoxLayout()
        stats_grid.setSpacing(12)
        stats_data = [
            ("Knowledge Nodes", "#3b82f6", "\u2B21"),
            ("Relationships", "#8b5cf6", "\u25CE"),
            ("Entity Types", "#10b981", "\u229E"),
            ("Documents", "#f59e0b", "\u2295"),
        ]
        self._stat_vals = []
        for label, color, icon in stats_data:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: #111827;
                    border: 1px solid #1e293b;
                    border-radius: 12px;
                    padding: 16px;
                }}
                QFrame:hover {{ border-color: {color}; }}
            """)
            card.setFixedHeight(80)
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 12, 16, 12)
            row.setSpacing(12)

            icon_box = QLabel(icon)
            icon_box.setFixedSize(44, 44)
            icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_box.setStyleSheet(f"""
                background: {color}22; color: {color};
                border-radius: 10px; font-size: 18px;
            """)
            row.addWidget(icon_box)

            info = QVBoxLayout()
            info.setSpacing(2)
            val = QLabel("—")
            val.setStyleSheet("color: #fff; font-size: 22px; font-weight: 700; border: none;")
            self._stat_vals.append(val)
            info.addWidget(val)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #64748b; font-size: 11px; border: none;")
            info.addWidget(lbl)
            row.addLayout(info)
            row.addStretch()

            stats_grid.addWidget(card)
        page_layout.addLayout(stats_grid)

        upload_row = QHBoxLayout()
        upload_row.setSpacing(12)

        self._upload_btn = QPushButton("\u2B06  Upload Document")
        self._upload_btn.setFixedHeight(44)
        self._upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upload_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3b82f6, stop:1 #8b5cf6);
                color: #fff;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 24px;
            }
            QPushButton:hover { opacity: 0.9; }
            QPushButton:disabled { background: #334155; color: #64748b; }
        """)
        self._upload_btn.clicked.connect(self._pick_upload_file)
        upload_row.addWidget(self._upload_btn)

        self._upload_status = QLabel("")
        self._upload_status.setStyleSheet("color: #10b981; font-size: 12px; border: none;")
        upload_row.addWidget(self._upload_status)
        upload_row.addStretch()
        page_layout.addLayout(upload_row)

        chat_card = QFrame()
        chat_card.setStyleSheet("""
            QFrame {
                background: #111827;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
        """)
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(16, 16, 16, 16)
        chat_layout.setSpacing(12)

        chat_header = QLabel("\u25CE  OKF Knowledge Assistant")
        chat_header.setStyleSheet("color: #fff; font-size: 15px; font-weight: 600; border: none;")
        chat_layout.addWidget(chat_header)

        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setMinimumHeight(200)
        self._chat_display.setStyleSheet("""
            QTextEdit {
                background: #0f172a;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }
        """)
        self._chat_display.setPlaceholderText("Ask anything about the OKF knowledge base...")
        chat_layout.addWidget(self._chat_display, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self._home_query = QLineEdit()
        self._home_query.setPlaceholderText("Ask the OKF knowledge base...")
        self._home_query.setFixedHeight(40)
        self._home_query.setStyleSheet("""
            QLineEdit {
                background: #0f172a;
                color: #fff;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)
        self._home_query.returnPressed.connect(self._send_home_query)
        input_row.addWidget(self._home_query, 1)

        self._home_send_btn = QPushButton("\u2191")
        self._home_send_btn.setFixedSize(40, 40)
        self._home_send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._home_send_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2563eb; }
            QPushButton:disabled { background: #334155; color: #64748b; }
        """)
        self._home_send_btn.clicked.connect(self._send_home_query)
        input_row.addWidget(self._home_send_btn)

        chat_layout.addLayout(input_row)
        page_layout.addWidget(chat_card, 1)

        page_layout.addStretch()

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

        self._chat_display.append(
            f"<div style='margin-bottom:12px; padding:8px 12px; background:#1e293b; border-radius:8px;'>"
            f"<b style='color:#3b82f6;'>You:</b> <span style='color:#e2e8f0;'>{query}</span></div>"
        )

        if self._rag_chat is None:
            self._chat_display.append(
                "<div style='color:#ef4444;'>[ERROR] OKF-RAG engine not available. Check GROQ_API_KEY in .env</div>"
            )
            return

        self._ai_label = QLabel()
        self._ai_label.setStyleSheet("color: #e2e8f0; font-size: 13px; padding: 8px 12px; background: #0f172a; border-radius: 8px; margin-bottom: 12px;")
        self._ai_label.setWordWrap(True)
        self._chat_display.append("")
        self._chat_display.setHtml(self._chat_display.toHtml() + "<div id='ai'></div>")

        self._chat_streaming = True
        self._home_query.setEnabled(False)
        self._home_send_btn.setEnabled(False)
        self._home_response_text = ""

        self._chat_thread = ChatThread(self._rag_chat, query)
        self._chat_thread.chunk_received.connect(self._on_chat_chunk)
        self._chat_thread.finished.connect(self._on_chat_finished)
        self._chat_thread.error.connect(self._on_chat_error)
        self._chat_thread.start()

    def _on_chat_chunk(self, chunk):
        self._home_response_text += chunk
        html = self._chat_display.toHtml()
        marker = "<div id='ai'></div>"
        if marker in html:
            new_html = html.replace(marker,
                f"<div style='margin-bottom:12px; padding:8px 12px; background:#0f172a; border-radius:8px;'>"
                f"<b style='color:#10b981;'>OKF Assistant:</b> "
                f"<span style='color:#e2e8f0;'>{self._home_response_text}</span>"
                f"<span style='color:#10b981;'>|</span></div>"
            )
            self._chat_display.setHtml(new_html)

    def _on_chat_finished(self):
        self._chat_streaming = False
        self._home_query.setEnabled(True)
        self._home_send_btn.setEnabled(True)
        self._home_query.setFocus()
        html = self._chat_display.toHtml()
        marker = "<div id='ai'></div>"
        if marker in html:
            new_html = html.replace(marker,
                f"<div style='margin-bottom:12px; padding:8px 12px; background:#0f172a; border-radius:8px;'>"
                f"<b style='color:#10b981;'>OKF Assistant:</b> "
                f"<span style='color:#e2e8f0;'>{self._home_response_text}</span></div>"
            )
            self._chat_display.setHtml(new_html)
        sb = self._chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_chat_error(self, error_msg):
        self._chat_streaming = False
        self._home_query.setEnabled(True)
        self._home_send_btn.setEnabled(True)
        html = self._chat_display.toHtml()
        marker = "<div id='ai'></div>"
        if marker in html:
            new_html = html.replace(marker,
                f"<div style='margin-bottom:12px; padding:8px 12px; background:#2d1215; border-radius:8px;'>"
                f"<b style='color:#ef4444;'>[ERROR]</b> <span style='color:#ef4444;'>{error_msg}</span></div>"
            )
            self._chat_display.setHtml(new_html)

    def _switch(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == index)
