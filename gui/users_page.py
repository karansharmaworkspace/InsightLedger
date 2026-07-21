from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QComboBox, QSpinBox, QCheckBox, QScrollArea
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
        header = QLabel("User Management")
        header.setStyleSheet("color: #F8FAFC; font-size: 28px; font-weight: bold;")
        layout.addWidget(header)

        subtitle = QLabel("Enterprise administration and local server access control")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 15px; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # Top Statistics Cards (dynamic, updated after load)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        def make_stat_card(title, attr_name, color, icon):
            card = QFrame()
            card.setObjectName("card")
            card.setFixedHeight(100)
            card.setStyleSheet(
                f"QFrame#card {{ background: #1E293B; border: 1px solid #334155; border-radius: 16px; }}"
            )
            r = QHBoxLayout(card)
            r.setContentsMargins(20, 20, 20, 20)

            icn = QLabel(icon)
            icn.setFixedSize(50, 50)
            icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icn.setStyleSheet(
                f"background: {color}15; color: {color}; border-radius: 12px; font-size: 24px;"
            )
            r.addWidget(icn)

            info = QVBoxLayout()
            info.setSpacing(4)
            v = QLabel("—")
            v.setStyleSheet("color: #F8FAFC; font-size: 28px; font-weight: bold; border: none;")
            setattr(self, attr_name, v)
            info.addWidget(v)
            t = QLabel(title)
            t.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 500; border: none;")
            info.addWidget(t)

            r.addLayout(info)
            r.addStretch()
            return card

        stats_layout.addWidget(make_stat_card("Total Users", "_stat_total", "#3B82F6", "👥"))
        stats_layout.addWidget(make_stat_card("Active Users", "_stat_active", "#10B981", "✓"))
        stats_layout.addWidget(make_stat_card("Admins", "_stat_admins", "#F59E0B", "🛡"))
        stats_layout.addWidget(make_stat_card("Viewers", "_stat_viewers", "#06B6D4", "👤"))
        layout.addLayout(stats_layout)

        # Add User Row
        add_card = QFrame()
        add_card.setObjectName("card")
        add_card.setStyleSheet("QFrame#card { background: #1E293B; border: 1px solid #334155; border-radius: 16px; }")
        add_layout_outer = QVBoxLayout(add_card)
        add_layout_outer.setContentsMargins(20, 20, 20, 20)
        add_layout_outer.setSpacing(12)

        add_title = QLabel("Add New User")
        add_title.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 600; border: none;")
        add_layout_outer.addWidget(add_title)

        add_row = QHBoxLayout()
        add_row.setSpacing(12)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedHeight(40)
        self.username_input.setStyleSheet(
            "QLineEdit { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 8px; padding: 0 12px; }"
            "QLineEdit:focus { border-color: #3B82F6; }"
        )
        add_row.addWidget(self.username_input, 2)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Viewer", "Editor", "Admin"])
        self.role_combo.setFixedHeight(40)
        self.role_combo.setStyleSheet(
            "QComboBox { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 8px; padding: 0 12px; }"
        )
        add_row.addWidget(self.role_combo, 1)

        self.add_user_btn = QPushButton("+ Add User")
        self.add_user_btn.setFixedHeight(40)
        self.add_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_user_btn.setStyleSheet(
            "QPushButton { background: #3B82F6; color: white; border-radius: 8px; font-weight: bold; border: none; padding: 0 20px; }"
            "QPushButton:hover { background: #2563EB; }"
        )
        self.add_user_btn.clicked.connect(self._add_user)
        add_row.addWidget(self.add_user_btn)

        add_layout_outer.addLayout(add_row)
        layout.addWidget(add_card)

        # User Table Card
        table_card = QFrame()
        table_card.setObjectName("card")
        table_card.setStyleSheet("QFrame#card { background: #1E293B; border: 1px solid #334155; border-radius: 16px; }")
        t_layout = QVBoxLayout(table_card)
        t_layout.setContentsMargins(20, 20, 20, 20)
        t_layout.setSpacing(16)

        t_header = QHBoxLayout()
        t_title = QLabel("Registered Users")
        t_title.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: 600; border: none;")
        t_header.addWidget(t_title)
        t_header.addStretch()
        t_layout.addLayout(t_header)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(["", "Username", "Role", "Status", "Actions"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.user_table.setStyleSheet("""
            QTableWidget { background: transparent; border: none; color: #E2E8F0; gridline-color: #334155; font-size: 13px; }
            QHeaderView::section { background: #0F172A; color: #94A3B8; font-weight: bold; border: none; border-bottom: 1px solid #334155; padding: 10px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #1E293B; }
            QTableWidget::item:selected { background: #334155; }
        """)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.setShowGrid(False)
        self.user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t_layout.addWidget(self.user_table)

        layout.addWidget(table_card, 2)

        # Local Server Card
        server_card = QFrame()
        server_card.setObjectName("card")
        server_card.setStyleSheet("QFrame#card { background: #1E293B; border: 1px solid #334155; border-radius: 16px; }")
        sv_layout = QVBoxLayout(server_card)
        sv_layout.setContentsMargins(20, 20, 20, 20)
        sv_layout.setSpacing(16)

        sv_title = QLabel("Local Sharing Server")
        sv_title.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 600; border: none;")
        sv_layout.addWidget(sv_title)

        sv_row = QHBoxLayout()
        sv_row.setSpacing(16)

        self.server_enabled = QCheckBox("Enable local sharing server")
        self.server_enabled.setStyleSheet(
            "QCheckBox { color: #94A3B8; font-size: 13px; }"
            "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #475569; }"
            "QCheckBox::indicator:checked { background: #3B82F6; border: none; }"
        )
        sv_row.addWidget(self.server_enabled)

        port_lbl = QLabel("Port:")
        port_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        sv_row.addWidget(port_lbl)

        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(8080)
        self.port_input.setFixedHeight(36)
        self.port_input.setStyleSheet(
            "QSpinBox { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; }"
        )
        sv_row.addWidget(self.port_input)

        self.start_server_btn = QPushButton("Start Server")
        self.start_server_btn.setFixedHeight(36)
        self.start_server_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_server_btn.setStyleSheet(
            "QPushButton { background: #10B981; color: white; border-radius: 8px; font-weight: bold; border: none; padding: 0 20px; }"
            "QPushButton:hover { background: #059669; }"
        )
        self.start_server_btn.clicked.connect(self._toggle_server)
        sv_row.addWidget(self.start_server_btn)
        sv_row.addStretch()

        self.server_status = QLabel("Server stopped")
        self.server_status.setStyleSheet("color: #64748B; font-size: 12px; border: none;")
        sv_row.addWidget(self.server_status)

        sv_layout.addLayout(sv_row)
        layout.addWidget(server_card)

        layout.addStretch()
        scroll.setWidget(page)
        main_layout.addWidget(scroll)

    def _load_users(self):
        """Load real users from users.json backend file."""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
            except Exception:
                self.users = []
        else:
            self.users = []

        # Seed admin if empty
        if not self.users:
            self.users = [{"username": "admin", "role": "Admin", "status": "Active"}]
            self._save_users()

        self._refresh_table()
        self._update_stats()

    def _update_stats(self):
        """Update the statistics cards with real user counts."""
        total = len(self.users)
        active = sum(1 for u in self.users if u.get("status", "Active") == "Active")
        admins = sum(1 for u in self.users if u.get("role") == "Admin")
        viewers = sum(1 for u in self.users if u.get("role") == "Viewer")

        self._stat_total.setText(str(total))
        self._stat_active.setText(str(active))
        self._stat_admins.setText(str(admins))
        self._stat_viewers.setText(str(viewers))

    def _save_users(self):
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(self.users, f, indent=2)

    def _refresh_table(self):
        self.user_table.setRowCount(len(self.users))
        for i, user in enumerate(self.users):
            # Avatar
            avatar = QLabel("👤")
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet("background: #334155; border-radius: 12px; margin: 6px;")
            self.user_table.setCellWidget(i, 0, avatar)

            # Username
            usr_item = QTableWidgetItem(user.get("username", ""))
            usr_item.setForeground(Qt.GlobalColor.white)
            self.user_table.setItem(i, 1, usr_item)

            # Role Badge
            role = user.get("role", "Viewer")
            role_lbl = QLabel(role)
            role_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            role_color = "#F59E0B" if role == "Admin" else ("#3B82F6" if role == "Editor" else "#94A3B8")
            role_lbl.setStyleSheet(
                f"background: {role_color}22; color: {role_color}; border: 1px solid {role_color}; "
                f"border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold; margin: 8px;"
            )
            self.user_table.setCellWidget(i, 2, role_lbl)

            # Status
            status = user.get("status", "Active")
            stat_lbl = QLabel(f"● {status}")
            stat_col = "#10B981" if status == "Active" else "#64748B"
            stat_lbl.setStyleSheet(f"color: {stat_col}; font-size: 12px; margin: 8px; border: none;")
            self.user_table.setCellWidget(i, 3, stat_lbl)

            # Actions
            action_w = QWidget()
            al = QHBoxLayout(action_w)
            al.setContentsMargins(4, 4, 4, 4)
            al.setSpacing(8)

            def _btn(text, col, idx=i):
                b = QPushButton(text)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {col}; border: 1px solid {col}; "
                    f"border-radius: 4px; padding: 4px 10px; font-size: 11px; }}"
                    f"QPushButton:hover {{ background: {col}; color: #FFFFFF; }}"
                )
                return b

            del_btn = _btn("Delete", "#EF4444")
            del_btn.clicked.connect(lambda _, idx=i: self._remove_user(idx))
            al.addWidget(_btn("Edit", "#3B82F6"))
            al.addWidget(del_btn)
            al.addStretch()
            self.user_table.setCellWidget(i, 4, action_w)
            self.user_table.setRowHeight(i, 52)

    def _add_user(self):
        username = self.username_input.text().strip()
        role = self.role_combo.currentText()
        if not username:
            QMessageBox.warning(self, "Add User", "Please enter a username.")
            return
        if any(u["username"] == username for u in self.users):
            QMessageBox.warning(self, "Add User", f"User '{username}' already exists.")
            return
        self.users.append({"username": username, "role": role, "status": "Active"})
        self._save_users()
        self._refresh_table()
        self._update_stats()
        self.username_input.clear()

    def _remove_user(self, idx):
        if self.users[idx]["username"] == "admin":
            QMessageBox.warning(self, "Remove", "Cannot remove the admin user.")
            return
        self.users.pop(idx)
        self._save_users()
        self._refresh_table()
        self._update_stats()

    def _toggle_server(self):
        if self.start_server_btn.text() == "Start Server":
            self.start_server_btn.setText("Stop Server")
            self.start_server_btn.setStyleSheet(
                "QPushButton { background: #EF4444; color: white; border-radius: 8px; font-weight: bold; border: none; padding: 0 20px; }"
                "QPushButton:hover { background: #DC2626; }"
            )
            self.server_status.setText(f"● Running on port {self.port_input.value()}")
            self.server_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold; border: none;")
        else:
            self.start_server_btn.setText("Start Server")
            self.start_server_btn.setStyleSheet(
                "QPushButton { background: #10B981; color: white; border-radius: 8px; font-weight: bold; border: none; padding: 0 20px; }"
                "QPushButton:hover { background: #059669; }"
            )
            self.server_status.setText("Server stopped")
            self.server_status.setStyleSheet("color: #64748B; font-size: 12px; border: none;")
