import torch
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt


class TeamPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #1e1e1e;")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Team InsightLedger")
        title.setStyleSheet("color: #fff; font-size: 22px; font-weight: 700; border: none;")
        layout.addWidget(title)

        sub = QLabel("The people behind DPID AI")
        sub.setStyleSheet("color: #64748b; font-size: 13px; border: none; margin-bottom: 8px;")
        layout.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid = QHBoxLayout(container)
        grid.setSpacing(16)

        members = [
            ("Tapesh Kumar", "Team Leader", "Architecture, Pipeline, Coordination"),
            ("Karan Sharma", "Developer", "Detection, Topology, GUI"),
            ("Harshit Goyal", "Developer", "Classification, DINOv2, RAG"),
            ("Divya Swami", "Developer", "API, Backend, Deployment"),
        ]

        for name, role, focus in members:
            card = QFrame()
            card.setFixedWidth(240)
            card.setStyleSheet("""
                QFrame {
                    background: #111827;
                    border: 1px solid #1e293b;
                    border-radius: 12px;
                    padding: 20px;
                }
                QFrame:hover {
                    border-color: #3b82f6;
                }
            """)
            v = QVBoxLayout(card)
            v.setContentsMargins(20, 20, 20, 20)
            v.setSpacing(8)

            avatar = QLabel(name[0])
            avatar.setFixedSize(48, 48)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet("""
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                color: #fff;
                border-radius: 24px;
                font-size: 20px;
                font-weight: 700;
                border: none;
            """)
            v.addWidget(avatar)

            n = QLabel(name)
            n.setStyleSheet("color: #fff; font-size: 15px; font-weight: 600; border: none;")
            v.addWidget(n)

            r = QLabel(role)
            r.setStyleSheet("color: #3b82f6; font-size: 12px; border: none;")
            v.addWidget(r)

            f = QLabel(focus)
            f.setStyleSheet("color: #64748b; font-size: 11px; border: none;")
            f.setWordWrap(True)
            v.addWidget(f)

            v.addStretch()
            grid.addWidget(card)

        grid.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
