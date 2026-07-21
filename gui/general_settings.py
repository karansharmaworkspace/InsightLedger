from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QComboBox, QCheckBox, QLineEdit, QSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt
import json
import os

from gui.style import TEXT, TEXT_MUTED, SUCCESS, DANGER, PRIMARY


class GeneralSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = os.path.join(os.getcwd(), "storage", "settings.json")
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        self.config = self._load_config()
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # Header
        title = QLabel("Settings")
        title.setObjectName("page_title")
        layout.addWidget(title)

        subtitle = QLabel("General application preferences, processing defaults, and export behavior")
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)

        # --- Appearance ---
        appearance_card, app_body = self._card("\U0001F3A8", "Appearance", "Theme and language preferences")
        app_layout = QGridLayout()
        app_layout.setSpacing(14)
        app_layout.setColumnStretch(1, 1)

        app_layout.addWidget(self._field_label("Theme"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        self.theme_combo.setCurrentText(self.config.get("theme", "Dark"))
        app_layout.addWidget(self.theme_combo, 0, 1)

        app_layout.addWidget(self._field_label("Language"), 1, 0)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Hindi", "German", "Japanese", "Chinese"])
        self.lang_combo.setCurrentText(self.config.get("language", "English"))
        app_layout.addWidget(self.lang_combo, 1, 1)

        app_body.addLayout(app_layout)
        layout.addWidget(appearance_card)

        # --- Processing ---
        processing_card, proc_body = self._card("\u2699", "Processing Defaults", "Defaults applied to new digitization jobs")
        proc_layout = QGridLayout()
        proc_layout.setSpacing(14)
        proc_layout.setColumnStretch(1, 1)

        proc_layout.addWidget(self._field_label("Default tile size"), 0, 0)
        self.tile_spin = QSpinBox()
        self.tile_spin.setRange(320, 1920)
        self.tile_spin.setSingleStep(64)
        self.tile_spin.setSuffix(" px")
        self.tile_spin.setValue(self.config.get("tile_size", 640))
        proc_layout.addWidget(self.tile_spin, 0, 1)

        self.auto_crop = QCheckBox("Enable auto-crop detection")
        self.auto_crop.setChecked(self.config.get("auto_crop", False))
        proc_layout.addWidget(self.auto_crop, 1, 0, 1, 2)

        self.gpu_accel = QCheckBox("GPU acceleration (CUDA)")
        self.gpu_accel.setChecked(self.config.get("gpu_accel", False))
        proc_layout.addWidget(self.gpu_accel, 2, 0, 1, 2)

        proc_body.addLayout(proc_layout)
        layout.addWidget(processing_card)

        # --- Output ---
        output_card, out_body = self._card("\U0001F4E4", "Output & Export", "Where results are written and how exports behave")
        out_layout = QGridLayout()
        out_layout.setSpacing(14)
        out_layout.setColumnStretch(1, 1)

        out_layout.addWidget(self._field_label("Default output directory"), 0, 0)
        self.output_dir = QLineEdit(self.config.get("output_dir", "output"))
        out_layout.addWidget(self.output_dir, 0, 1)

        self.auto_export = QCheckBox("Auto-export DEXPI JSON after digitization")
        self.auto_export.setChecked(self.config.get("auto_export", False))
        out_layout.addWidget(self.auto_export, 1, 0, 1, 2)

        out_body.addLayout(out_layout)
        layout.addWidget(output_card)

        # Save row
        save_row = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primary_btn")
        save_btn.setFixedHeight(40)
        save_btn.setFixedWidth(160)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_config)
        save_row.addWidget(save_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED};")
        save_row.addWidget(self.status_label)
        save_row.addStretch()
        layout.addLayout(save_row)

        layout.addStretch()

        scroll.setWidget(page)
        outer.addWidget(scroll)

    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        return lbl

    def _card(self, icon, title_text, description):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(38, 38)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"background: {PRIMARY}22; color: {PRIMARY}; border-radius: 10px; font-size: 16px;"
        )
        header.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title = QLabel(title_text)
        title.setObjectName("section_title")
        desc = QLabel(description)
        desc.setObjectName("muted")
        title_col.addWidget(title)
        title_col.addWidget(desc)
        header.addLayout(title_col)
        header.addStretch()

        layout.addLayout(header)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #334155;")
        layout.addWidget(div)

        return card, layout

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
        self.status_label.setText("\u2713 Settings saved")
        self.status_label.setStyleSheet(f"color: {SUCCESS}; font-size: 12px; font-weight: 600;")
