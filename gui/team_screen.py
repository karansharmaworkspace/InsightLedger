import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout, QProgressBar
)
from PyQt6.QtCore import Qt


class TeamPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _create_card(self):
        card = QFrame()
        card.setStyleSheet("QFrame { background: #1E293B; border: 1px solid #334155; border-radius: 12px; }")
        return card

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar { width: 8px; background: #0F172A; } QScrollBar::handle { background: #334155; border-radius: 4px; }")

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # Top: Project Overview
        header_card = self._create_card()
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(24, 20, 24, 20)
        
        p_name = QVBoxLayout()
        title = QLabel("InsightLedger Enterprise Edition")
        title.setStyleSheet("color: #F8FAFC; font-size: 24px; font-weight: bold; border: none;")
        p_name.addWidget(title)
        sprint = QLabel("Sprint 4: Knowledge Graph Expansion")
        sprint.setStyleSheet("color: #3B82F6; font-size: 14px; font-weight: bold; border: none;")
        p_name.addWidget(sprint)
        h_layout.addLayout(p_name)
        h_layout.addStretch()

        deadlines = QHBoxLayout()
        deadlines.setSpacing(20)
        
        def stat_box(title, val, val_col):
            v = QVBoxLayout()
            v.setSpacing(4)
            lbl = QLabel(title)
            lbl.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
            v.addWidget(lbl)
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(f"color: {val_col}; font-size: 18px; font-weight: bold; border: none;")
            v.addWidget(val_lbl)
            return v
            
        deadlines.addLayout(stat_box("Deadline", "Oct 24", "#EF4444"))
        deadlines.addLayout(stat_box("Progress", "78%", "#10B981"))
        h_layout.addLayout(deadlines)
        layout.addWidget(header_card)

        # Team Member Cards
        members_lbl = QLabel("Team InsightLedger")
        members_lbl.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(members_lbl)

        team_grid = QGridLayout()
        team_grid.setSpacing(16)
        
        members = [
            ("Tapesh Kumar", "Team Leader", "Architecture, Pipeline", "System Design", "42", "High", "Just now", "#3B82F6"),
            ("Karan Sharma", "Developer", "Detection, Topology", "UI Polishing", "38", "High", "10m ago", "#8B5CF6"),
            ("Harshit Goyal", "Developer", "Classification, RAG", "RAG Pipeline", "35", "High", "2m ago", "#10B981"),
            ("Divya Swami", "Developer", "API, Backend", "Server Setup", "40", "High", "Just now", "#F59E0B"),
        ]
        
        for i, (name, role, resp, task, done, perf, last_act, color) in enumerate(members):
            mc = self._create_card()
            ml = QVBoxLayout(mc)
            ml.setContentsMargins(16, 16, 16, 16)
            
            top_row = QHBoxLayout()
            av = QLabel(name[0])
            av.setFixedSize(40, 40)
            av.setAlignment(Qt.AlignmentFlag.AlignCenter)
            av.setStyleSheet(f"background: {color}; color: white; border-radius: 20px; font-size: 18px; font-weight: bold; border: none;")
            top_row.addWidget(av)
            
            nr = QVBoxLayout()
            n = QLabel(name)
            n.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 14px; border: none;")
            nr.addWidget(n)
            rl = QLabel(role)
            rl.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
            nr.addWidget(rl)
            top_row.addLayout(nr)
            top_row.addStretch()
            

            ml.addLayout(top_row)
            
            ml.addSpacing(8)
            
            def info_row(k, v):
                r = QHBoxLayout()
                kl = QLabel(k)
                kl.setStyleSheet("color: #64748B; font-size: 12px; border: none;")
                vl = QLabel(v)
                vl.setStyleSheet("color: #E2E8F0; font-size: 12px; border: none;")
                vl.setAlignment(Qt.AlignmentFlag.AlignRight)
                r.addWidget(kl)
                r.addWidget(vl)
                return r
                
            ml.addLayout(info_row("Focus:", resp))
            ml.addLayout(info_row("Current:", task))
            ml.addLayout(info_row("Completed:", done))
            ml.addLayout(info_row("Activity:", last_act))
            
            team_grid.addWidget(mc, i // 2, i % 2)
            
        layout.addLayout(team_grid)

        # Sprint Progress
        sprint_lbl = QLabel("Sprint Progress & Milestones")
        sprint_lbl.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(sprint_lbl)
        
        sp_card = self._create_card()
        spl = QVBoxLayout(sp_card)
        spl.setContentsMargins(20, 20, 20, 20)
        spl.setSpacing(16)
        
        for kpi, prog, col in [("OCR & Text Extraction", 100, "#10B981"), ("Symbol Detection", 85, "#3B82F6"), ("Knowledge Graph Generation", 60, "#F59E0B"), ("RAG Search", 40, "#8B5CF6"), ("Compliance Engine", 10, "#EF4444")]:
            pr_row = QHBoxLayout()
            lbl = QLabel(kpi)
            lbl.setFixedWidth(180)
            lbl.setStyleSheet("color: #E2E8F0; font-size: 13px; border: none;")
            bar = QProgressBar()
            bar.setValue(prog)
            bar.setFixedHeight(8)
            bar.setTextVisible(False)
            bar.setStyleSheet(f"QProgressBar {{ background: #0F172A; border-radius: 4px; border: none; }} QProgressBar::chunk {{ background: {col}; border-radius: 4px; }}")
            pct = QLabel(f"{prog}%")
            pct.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
            pr_row.addWidget(lbl)
            pr_row.addWidget(bar)
            pr_row.addWidget(pct)
            spl.addLayout(pr_row)
            
        layout.addWidget(sp_card)

        # Kanban Board
        kb_lbl = QLabel("Kanban Board")
        kb_lbl.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(kb_lbl)
        
        kb_layout = QHBoxLayout()
        kb_layout.setSpacing(16)
        
        def kanban_col(title, tasks):
            c = QVBoxLayout()
            h = QLabel(title)
            h.setStyleSheet("color: #94A3B8; font-size: 14px; font-weight: bold;")
            c.addWidget(h)
            for t in tasks:
                tc = QFrame()
                tc.setStyleSheet("QFrame { background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 12px; }")
                tcl = QVBoxLayout(tc)
                tl = QLabel(t)
                tl.setStyleSheet("color: #E2E8F0; font-size: 13px; border: none;")
                tl.setWordWrap(True)
                tcl.addWidget(tl)
                c.addWidget(tc)
            c.addStretch()
            return c
            
        kb_layout.addLayout(kanban_col("To Do", ["Write tests for Graph", "Deploy container to AKS", "Setup logging"]))
        kb_layout.addLayout(kanban_col("In Progress", ["Refine UI styles", "Optimize embedding search"]))
        kb_layout.addLayout(kanban_col("Done", ["Setup PySide6 shell", "Integrate Groq API", "Parse PID PDFs"]))
        layout.addLayout(kb_layout)

        # Grid for Activity, Docs, Repo
        bot_grid = QGridLayout()
        bot_grid.setSpacing(16)
        
        # Activity
        act_card = self._create_card()
        actl = QVBoxLayout(act_card)
        actl.addWidget(QLabel("Recent Activity").setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: bold; border: none;") or QLabel("Recent Activity", styleSheet="color: #F8FAFC; font-size: 16px; font-weight: bold; border: none;"))
        for a in ["Commit: Fix dark mode", "PR merged: RAG update", "Karan moved task to In Progress"]:
            actl.addWidget(QLabel(f"• {a}", styleSheet="color: #94A3B8; font-size: 13px; border: none;"))
        actl.addStretch()
        bot_grid.addWidget(act_card, 0, 0)
        
        # Docs
        doc_card = self._create_card()
        docl = QVBoxLayout(doc_card)
        docl.addWidget(QLabel("Shared Documents", styleSheet="color: #F8FAFC; font-size: 16px; font-weight: bold; border: none;"))
        for d in ["System_Architecture.pdf", "API_Specs.docx", "UI_Mockups.fig"]:
            docl.addWidget(QLabel(f"📄 {d}", styleSheet="color: #3B82F6; font-size: 13px; border: none;"))
        docl.addStretch()
        bot_grid.addWidget(doc_card, 0, 1)

        # Repo
        rep_card = self._create_card()
        repl = QVBoxLayout(rep_card)
        repl.addWidget(QLabel("Repository Overview", styleSheet="color: #F8FAFC; font-size: 16px; font-weight: bold; border: none;"))
        repl.addWidget(QLabel("Branch: main", styleSheet="color: #E2E8F0; font-size: 13px; border: none;"))
        repl.addWidget(QLabel("Commits: 142", styleSheet="color: #94A3B8; font-size: 13px; border: none;"))
        repl.addWidget(QLabel("Contributors: 4", styleSheet="color: #94A3B8; font-size: 13px; border: none;"))
        repl.addStretch()
        bot_grid.addWidget(rep_card, 0, 2)
        
        layout.addLayout(bot_grid)

        # Architecture Preview
        arch_lbl = QLabel("System Architecture Pipeline")
        arch_lbl.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(arch_lbl)
        
        arch_card = self._create_card()
        archl = QHBoxLayout(arch_card)
        archl.setContentsMargins(24, 24, 24, 24)
        
        steps = ["Upload", "OCR", "Detection", "Knowledge Graph", "RAG", "AI Assistant"]
        for i, s in enumerate(steps):
            sl = QLabel(s)
            sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sl.setStyleSheet("background: #0F172A; color: #3B82F6; border: 1px solid #334155; border-radius: 8px; padding: 12px; font-weight: bold;")
            archl.addWidget(sl)
            if i < len(steps) - 1:
                arr = QLabel("→")
                arr.setStyleSheet("color: #64748B; font-size: 20px; font-weight: bold; border: none;")
                archl.addWidget(arr)
                
        layout.addWidget(arch_card)

        layout.addStretch()
        scroll.setWidget(page)
        main_layout.addWidget(scroll)
