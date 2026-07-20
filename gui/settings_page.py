from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QProgressBar, QTextEdit, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


class EngineSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Engine Settings")
        title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Manage API keys, model configuration, and engine health")
        subtitle.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(subtitle)

        # --- API Key Section ---
        api_card = self._card("Groq API Key")
        api_layout = QVBoxLayout()

        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_input.setText(os.getenv("GROQ_API_KEY", ""))
        self.api_input.setPlaceholderText("gsk_...")
        self.api_input.setStyleSheet("""
            QLineEdit { background: #2d2d2d; color: #fff; border: 1px solid #444;
                        border-radius: 6px; padding: 12px; font-size: 13px; min-height: 20px; }
        """)
        api_layout.addWidget(self.api_input)

        api_btn_row = QHBoxLayout()
        self.toggle_vis_btn = QPushButton("Show")
        self.toggle_vis_btn.setFixedWidth(80)
        self.toggle_vis_btn.clicked.connect(self._toggle_api_visibility)
        self.save_api_btn = QPushButton("Save")
        self.save_api_btn.setFixedWidth(80)
        self.save_api_btn.clicked.connect(self._save_api_key)
        api_btn_row.addWidget(self.toggle_vis_btn)
        api_btn_row.addWidget(self.save_api_btn)
        api_btn_row.addStretch()
        api_layout.addLayout(api_btn_row)

        self.api_status = QLabel("")
        self.api_status.setStyleSheet("font-size: 11px;")
        api_layout.addWidget(self.api_status)

        api_card_layout = api_card.findChild(QVBoxLayout)
        if api_card_layout:
            api_card_layout.addLayout(api_layout)
        layout.addWidget(api_card)

        # --- Model Config ---
        model_card = self._card("Model Configuration")
        model_layout = QVBoxLayout()

        row = QGridLayout()
        row.setSpacing(10)

        row.addWidget(QLabel("Vision Model:"), 0, 0)
        self.vision_model = QLineEdit(os.getenv("VISION_MODEL", ""))
        self.vision_model.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 12px; min-height: 20px;")
        row.addWidget(self.vision_model, 0, 1)

        row.addWidget(QLabel("Chat Model:"), 1, 0)
        self.chat_model = QLineEdit(os.getenv("CHAT_MODEL", ""))
        self.chat_model.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 12px; min-height: 20px;")
        row.addWidget(self.chat_model, 1, 1)

        row.addWidget(QLabel("Model Path:"), 2, 0)
        self.model_path = QLineEdit(os.getenv("PT_MODEL_PATH", "models/32class.pt"))
        self.model_path.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 12px; min-height: 20px;")
        row.addWidget(self.model_path, 2, 1)

        model_layout.addLayout(row)

        self.save_model_btn = QPushButton("Save Configuration")
        self.save_model_btn.clicked.connect(self._save_model_config)
        model_layout.addWidget(self.save_model_btn)

        model_card_layout = model_card.findChild(QVBoxLayout)
        if model_card_layout:
            model_card_layout.addLayout(model_layout)
        layout.addWidget(model_card)

        # --- Engine Health ---
        health_card = self._card("Engine Health")
        health_layout = QVBoxLayout()

        self.health_log = QTextEdit()
        self.health_log.setReadOnly(True)
        self.health_log.setMaximumHeight(150)
        self.health_log.setStyleSheet("background: #000; color: #0f0; border: none; font-family: Consolas; font-size: 11px;")
        health_layout.addWidget(self.health_log)

        self.check_health_btn = QPushButton("Run Health Check")
        self.check_health_btn.clicked.connect(self._run_health_check)
        health_layout.addWidget(self.check_health_btn)

        health_card_layout = health_card.findChild(QVBoxLayout)
        if health_card_layout:
            health_card_layout.addLayout(health_layout)
        layout.addWidget(health_card)

        layout.addStretch()

    def _card(self, title_text):
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: #16213e; border: 1px solid #1a1a3e; border-radius: 8px; }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        title = QLabel(title_text)
        title.setStyleSheet("color: #e94560; font-size: 15px; font-weight: bold; border: none;")
        layout.addWidget(title)
        return card

    def _toggle_api_visibility(self):
        if self.api_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_vis_btn.setText("Hide")
        else:
            self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_vis_btn.setText("Show")

    def _save_api_key(self):
        key = self.api_input.text().strip()
        env_path = os.path.join(os.getcwd(), ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        found = False
        for i, line in enumerate(lines):
            if line.startswith("GROQ_API_KEY="):
                lines[i] = f"GROQ_API_KEY={key}\n"
                found = True
                break
        if not found:
            lines.append(f"GROQ_API_KEY={key}\n")
        with open(env_path, "w") as f:
            f.writelines(lines)
        os.environ["GROQ_API_KEY"] = key
        self.api_status.setText("API key saved.")
        self.api_status.setStyleSheet("color: #0f0; font-size: 11px;")

    def _save_model_config(self):
        env_path = os.path.join(os.getcwd(), ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()

        updates = {
            "VISION_MODEL=": self.vision_model.text().strip(),
            "CHAT_MODEL=": self.chat_model.text().strip(),
            "PT_MODEL_PATH=": self.model_path.text().strip(),
        }
        for prefix, value in updates.items():
            found = False
            for i, line in enumerate(lines):
                if line.startswith(prefix):
                    lines[i] = f"{prefix}{value}\n"
                    found = True
                    break
            if not found:
                lines.append(f"{prefix}{value}\n")

        with open(env_path, "w") as f:
            f.writelines(lines)
        self.api_status.setText("Configuration saved. Restart to apply.")
        self.api_status.setStyleSheet("color: #ff0; font-size: 11px;")

    def _run_health_check(self):
        self.health_log.clear()
        self.health_log.append("[HEALTH] Running checks...")

        # Check .env
        key = os.getenv("GROQ_API_KEY", "")
        if key:
            self.health_log.append(f"[OK] GROQ_API_KEY set ({key[:8]}...)")
        else:
            self.health_log.append("[FAIL] GROQ_API_KEY not set")

        # Check model file
        model = os.getenv("PT_MODEL_PATH", "models/32class.pt")
        if os.path.exists(model):
            size_mb = os.path.getsize(model) / (1024 * 1024)
            self.health_log.append(f"[OK] Model file exists ({size_mb:.1f} MB)")
        else:
            self.health_log.append(f"[FAIL] Model not found: {model}")

        # Check Groq connection
        try:
            from groq import Groq
            client = Groq(api_key=key)
            self.health_log.append("[OK] Groq client initialized")
        except Exception as e:
            self.health_log.append(f"[FAIL] Groq init error: {e}")

        # Check PyTorch
        try:
            import torch
            self.health_log.append(f"[OK] PyTorch {torch.__version__}")
        except ImportError:
            self.health_log.append("[FAIL] PyTorch not installed")

        # Check OpenCV
        try:
            import cv2
            self.health_log.append(f"[OK] OpenCV {cv2.__version__}")
        except ImportError:
            self.health_log.append("[FAIL] OpenCV not installed")

        self.health_log.append("[HEALTH] Check complete.")
