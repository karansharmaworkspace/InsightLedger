from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QComboBox, QCheckBox, QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt
import json
import os


class GeneralSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = os.path.join(os.getcwd(), "storage", "settings.json")
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        self.config = self._load_config()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # --- Appearance ---
        appearance_card = self._card("Appearance")
        app_layout = QGridLayout()
        app_layout.setSpacing(10)

        app_layout.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        self.theme_combo.setCurrentText(self.config.get("theme", "Dark"))
        self.theme_combo.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px;")
        app_layout.addWidget(self.theme_combo, 0, 1)

        app_layout.addWidget(QLabel("Language:"), 1, 0)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Hindi", "German", "Japanese", "Chinese"])
        self.lang_combo.setCurrentText(self.config.get("language", "English"))
        self.lang_combo.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px;")
        app_layout.addWidget(self.lang_combo, 1, 1)

        card_layout = appearance_card.findChild(QVBoxLayout)
        if card_layout:
            card_layout.addLayout(app_layout)
        layout.addWidget(appearance_card)

        # --- Processing ---
        processing_card = self._card("Processing Defaults")
        proc_layout = QGridLayout()
        proc_layout.setSpacing(10)

        proc_layout.addWidget(QLabel("Default tile size:"), 0, 0)
        self.tile_spin = QSpinBox()
        self.tile_spin.setRange(320, 1920)
        self.tile_spin.setSingleStep(64)
        self.tile_spin.setValue(self.config.get("tile_size", 640))
        self.tile_spin.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px;")
        proc_layout.addWidget(self.tile_spin, 0, 1)

        self.auto_crop = QCheckBox("Enable auto-crop detection")
        self.auto_crop.setChecked(self.config.get("auto_crop", False))
        self.auto_crop.setStyleSheet("color: #ccc;")
        proc_layout.addWidget(self.auto_crop, 1, 0, 1, 2)

        self.gpu_accel = QCheckBox("GPU acceleration (CUDA)")
        self.gpu_accel.setChecked(self.config.get("gpu_accel", False))
        self.gpu_accel.setStyleSheet("color: #ccc;")
        proc_layout.addWidget(self.gpu_accel, 2, 0, 1, 2)

        card_layout = processing_card.findChild(QVBoxLayout)
        if card_layout:
            card_layout.addLayout(proc_layout)
        layout.addWidget(processing_card)

        # --- Output ---
        output_card = self._card("Output")
        out_layout = QGridLayout()
        out_layout.setSpacing(10)

        out_layout.addWidget(QLabel("Default output dir:"), 0, 0)
        self.output_dir = QLineEdit(self.config.get("output_dir", "output"))
        self.output_dir.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px;")
        out_layout.addWidget(self.output_dir, 0, 1)

        self.auto_export = QCheckBox("Auto-export DEXPI JSON after digitization")
        self.auto_export.setChecked(self.config.get("auto_export", False))
        self.auto_export.setStyleSheet("color: #ccc;")
        out_layout.addWidget(self.auto_export, 1, 0, 1, 2)

        card_layout = output_card.findChild(QVBoxLayout)
        if card_layout:
            card_layout.addLayout(out_layout)
        layout.addWidget(output_card)

        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.setFixedWidth(150)
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _card(self, title_text):
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: #16213e; border: 1px solid #1a1a3e; border-radius: 8px; padding: 15px; }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        title = QLabel(title_text)
        title.setStyleSheet("color: #e94560; font-size: 15px; font-weight: bold; border: none;")
        layout.addWidget(title)
        return card

    def _load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                return json.load(f)
        return {}

    def _save_config(self):
        self.config = {
            "theme": self.theme_combo.currentText(),
            "language": self.lang_combo.currentText(),
            "tile_size": self.tile_spin.value(),
            "auto_crop": self.auto_crop.isChecked(),
            "gpu_accel": self.gpu_accel.isChecked(),
            "output_dir": self.output_dir.text().strip(),
            "auto_export": self.auto_export.isChecked(),
        }
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)
        self.status_label.setText("Settings saved.")
        self.status_label.setStyleSheet("color: #0f0; font-size: 11px;")
