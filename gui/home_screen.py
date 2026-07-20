import torch  # MUST IMPORT BEFORE PYQT6
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame,
    QLineEdit, QTextEdit, QScrollArea
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
            from core.okf_rag import OntologyRAGChat
            self._rag_chat = OntologyRAGChat()
        except Exception as e:
            print(f"[OntologyRAG] Init failed: {e}")
            self._rag_chat = None

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

    def _home_page(self):
        page = QWidget()
        page.setStyleSheet("background: #1e1e1e;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(container)
        cl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        cl.setContentsMargins(80, 40, 80, 20)
        cl.setSpacing(0)

        self._chat_area_widget = QWidget()
        self._chat_area_widget.setStyleSheet("background: transparent;")
        self._chat_area_layout = QVBoxLayout(self._chat_area_widget)
        self._chat_area_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._chat_area_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_area_layout.setSpacing(0)

        cl.addWidget(self._chat_area_widget)

        self._welcome_widget = QWidget()
        self._welcome_widget.setStyleSheet("background: transparent;")
        welcome_layout = QVBoxLayout(self._welcome_widget)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        welcome_layout.setContentsMargins(0, 60, 0, 0)
        welcome_layout.setSpacing(12)

        title = QLabel("DocuPID")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #fff; font-size: 32px; font-weight: 600; border: none;")
        welcome_layout.addWidget(title)

        sub = QLabel("What can I help you with?")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #999; font-size: 16px; border: none;")
        welcome_layout.addWidget(sub)

        welcome_layout.addSpacing(40)

        suggestions = [
            ("Symbols", "What P&ID symbols exist?"),
            ("Valves", "Tell me about valve types"),
            ("Pumps", "List all pump subclasses"),
            ("Instruments", "What instrument classes are there?"),
        ]

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for label, query in suggestions:
            card = QPushButton(label)
            card.setFixedSize(160, 56)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet("""
                QPushButton {
                    background: #252526;
                    color: #bbb;
                    border: 1px solid #333;
                    border-radius: 12px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #2d2d2d;
                    color: #fff;
                    border-color: #555;
                }
            """)
            card.clicked.connect(lambda _, q=query: self._quick_query(q))
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        welcome_layout.addLayout(cards_layout)
        welcome_layout.addStretch()

        cl.addWidget(self._welcome_widget)

        scroll.setWidget(container)
        page_layout.addWidget(scroll, 1)

        input_bar = QWidget()
        input_bar.setFixedHeight(80)
        input_bar.setStyleSheet("background: #1e1e1e; border-top: 1px solid #333;")
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(100, 12, 100, 16)

        self._home_query = QLineEdit()
        self._home_query.setPlaceholderText("Ask the OKF knowledge base...")
        self._home_query.setFixedHeight(48)
        self._home_query.setStyleSheet("""
            QLineEdit {
                background: #2d2d2d;
                color: #fff;
                border: 1px solid #444;
                border-radius: 24px;
                padding: 0 52px 0 18px;
                font-size: 14px;
                selection-background-color: #0078d4;
            }
            QLineEdit:focus {
                border-color: #666;
            }
        """)
        self._home_query.returnPressed.connect(self._send_home_query)
        input_layout.addWidget(self._home_query)

        self._home_send_btn = QPushButton("\u2191")
        self._home_send_btn.setFixedSize(36, 36)
        self._home_send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._home_send_btn.setStyleSheet("""
            QPushButton {
                background: #555;
                color: #999;
                border: none;
                border-radius: 18px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover { background: #0078d4; color: #fff; }
            QPushButton:pressed { background: #005a9e; }
            QPushButton:disabled { background: #333; color: #555; }
        """)
        self._home_send_btn.clicked.connect(self._send_home_query)

        send_container = QWidget()
        send_container.setFixedSize(36, 36)
        send_container.setStyleSheet("background: transparent;")
        send_container_layout = QVBoxLayout(send_container)
        send_container_layout.setContentsMargins(0, 0, 0, 0)
        send_container_layout.addWidget(self._home_send_btn)
        input_layout.addWidget(send_container, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        page_layout.addWidget(input_bar)
        return page

    def _quick_query(self, text):
        self._home_query.setText(text)
        self._send_home_query()

    def _ensure_chat_mode(self):
        if not self._in_chat_mode:
            self._in_chat_mode = True
            self._welcome_widget.hide()
            self._chat_display = QTextEdit()
            self._chat_display.setReadOnly(True)
            self._chat_display.setStyleSheet("""
                QTextEdit {
                    background: transparent;
                    color: #d4d4d4;
                    border: none;
                    font-size: 14px;
                    line-height: 1.6;
                    selection-background-color: #0078d4;
                }
            """)
            self._chat_area_layout.addWidget(self._chat_display)

    def _send_home_query(self):
        query = self._home_query.text().strip()
        if not query or self._chat_streaming:
            return

        self._ensure_chat_mode()
        self._home_query.clear()

        if self._rag_chat is None:
            self._chat_display.append(
                f"<div style='margin-bottom:16px;'><b style='color:#0078d4;'>You:</b> {query}</div>"
            )
            self._chat_display.append(
                "<div style='color:#e94560;'>[ERROR] OKF-RAG engine not available. Check GROQ_API_KEY in .env</div>"
            )
            return

        self._chat_display.append(
            f"<div style='margin-bottom:16px; padding:8px 12px; background:#252526; border-radius:8px;'>"
            f"<b style='color:#0078d4;'>You:</b> <span style='color:#d4d4d4;'>{query}</span></div>"
        )

        self._ai_label = QLabel("<b style='color:#81c784;'>OKF Assistant:</b> ")
        self._ai_label.setStyleSheet("color: #d4d4d4; font-size: 14px; padding: 8px 12px; background: #1a2a1a; border-radius: 8px; margin-bottom: 16px;")
        self._ai_label.setWordWrap(True)
        self._chat_area_layout.addWidget(self._ai_label)

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
        self._ai_label.setText(
            f"<b style='color:#81c784;'>OKF Assistant:</b> "
            f"<span style='color:#d4d4d4;'>{self._home_response_text}</span>"
            f"<span style='color:#81c784;'>|</span>"
        )

    def _on_chat_finished(self):
        self._chat_streaming = False
        self._home_query.setEnabled(True)
        self._home_send_btn.setEnabled(True)
        self._home_query.setFocus()
        self._ai_label.setText(
            f"<b style='color:#81c784;'>OKF Assistant:</b> "
            f"<span style='color:#d4d4d4;'>{self._home_response_text}</span>"
        )

    def _on_chat_error(self, error_msg):
        self._chat_streaming = False
        self._home_query.setEnabled(True)
        self._home_send_btn.setEnabled(True)
        self._ai_label.setText(
            f"<b style='color:#e94560;'>[ERROR]</b> <span style='color:#e94560;'>{error_msg}</span>"
        )

    def _switch(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == index)
