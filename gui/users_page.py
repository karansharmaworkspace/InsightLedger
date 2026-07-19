from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QComboBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt
import json
import os


class UsersManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.users_file = os.path.join(os.getcwd(), "storage", "users.json")
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        self._setup_ui()
        self._load_users()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Users Management")
        title.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Manage shared user access and local server configuration")
        subtitle.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(subtitle)

        # --- Add User ---
        add_card = self._card("Add User")
        add_layout = QGridLayout()
        add_layout.setSpacing(10)

        add_layout.addWidget(QLabel("Username:"), 0, 0)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px;")
        add_layout.addWidget(self.username_input, 0, 1)

        add_layout.addWidget(QLabel("Role:"), 0, 2)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Viewer", "Editor", "Admin"])
        self.role_combo.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px;")
        add_layout.addWidget(self.role_combo, 0, 3)

        self.add_user_btn = QPushButton("Add User")
        self.add_user_btn.clicked.connect(self._add_user)
        add_layout.addWidget(self.add_user_btn, 0, 4)

        card_layout = add_card.findChild(QVBoxLayout)
        if card_layout:
            card_layout.addLayout(add_layout)
        layout.addWidget(add_card)

        # --- User Table ---
        table_card = self._card("Registered Users")
        table_layout = QVBoxLayout()

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(4)
        self.user_table.setHorizontalHeaderLabels(["Username", "Role", "Status", "Actions"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.user_table.setStyleSheet("background: #1e1e1e; color: #bbb; gridline-color: #333; font-size: 12px;")
        table_layout.addWidget(self.user_table)

        card_layout = table_card.findChild(QVBoxLayout)
        if card_layout:
            card_layout.addLayout(table_layout)
        layout.addWidget(table_card, 1)

        # --- Local Server ---
        server_card = self._card("Local Server")
        server_layout = QGridLayout()
        server_layout.setSpacing(10)

        self.server_enabled = QCheckBox("Enable local sharing server")
        self.server_enabled.setStyleSheet("color: #ccc;")
        server_layout.addWidget(self.server_enabled, 0, 0, 1, 2)

        server_layout.addWidget(QLabel("Port:"), 1, 0)
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(8080)
        self.port_input.setStyleSheet("background: #2d2d2d; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px;")
        server_layout.addWidget(self.port_input, 1, 1)

        self.start_server_btn = QPushButton("Start Server")
        self.start_server_btn.clicked.connect(self._toggle_server)
        server_layout.addWidget(self.start_server_btn, 1, 2)

        self.server_status = QLabel("Server stopped")
        self.server_status.setStyleSheet("color: #888; font-size: 11px;")
        server_layout.addWidget(self.server_status, 2, 0, 1, 3)

        card_layout = server_card.findChild(QVBoxLayout)
        if card_layout:
            card_layout.addLayout(server_layout)
        layout.addWidget(server_card)

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

    def _load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, "r") as f:
                self.users = json.load(f)
        else:
            self.users = [{"username": "admin", "role": "Admin", "status": "Active"}]
            self._save_users()
        self._refresh_table()

    def _save_users(self):
        with open(self.users_file, "w") as f:
            json.dump(self.users, f, indent=2)

    def _refresh_table(self):
        self.user_table.setRowCount(len(self.users))
        for i, user in enumerate(self.users):
            self.user_table.setItem(i, 0, QTableWidgetItem(user["username"]))
            self.user_table.setItem(i, 1, QTableWidgetItem(user["role"]))
            self.user_table.setItem(i, 2, QTableWidgetItem(user.get("status", "Active")))

            del_btn = QPushButton("Remove")
            del_btn.setStyleSheet("background: #c62828; color: #fff; border: none; padding: 4px 10px; border-radius: 3px; font-size: 11px;")
            del_btn.clicked.connect(lambda _, idx=i: self._remove_user(idx))
            self.user_table.setCellWidget(i, 3, del_btn)

    def _add_user(self):
        username = self.username_input.text().strip()
        role = self.role_combo.currentText()
        if not username:
            QMessageBox.warning(self, "Add User", "Enter a username.")
            return
        if any(u["username"] == username for u in self.users):
            QMessageBox.warning(self, "Add User", "User already exists.")
            return
        self.users.append({"username": username, "role": role, "status": "Active"})
        self._save_users()
        self._refresh_table()
        self.username_input.clear()

    def _remove_user(self, idx):
        if self.users[idx]["username"] == "admin":
            QMessageBox.warning(self, "Remove", "Cannot remove admin user.")
            return
        self.users.pop(idx)
        self._save_users()
        self._refresh_table()

    def _toggle_server(self):
        if self.start_server_btn.text() == "Start Server":
            self.start_server_btn.setText("Stop Server")
            self.server_status.setText(f"Running on port {self.port_input.value()}")
            self.server_status.setStyleSheet("color: #0f0; font-size: 11px;")
        else:
            self.start_server_btn.setText("Start Server")
            self.server_status.setText("Server stopped")
            self.server_status.setStyleSheet("color: #888; font-size: 11px;")
