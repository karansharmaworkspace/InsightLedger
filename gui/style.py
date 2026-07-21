"""
InsightLedger Enterprise Design System
=================================
A single source of truth for color, spacing, radius and component QSS,
inspired by Microsoft Fabric / Azure AI Studio / Linear / Notion.

Color Palette:
- Background: #0F172A (Slate 900)
- Surface:    #111827 (Gray 900)
- Cards:      #1E293B (Slate 800)
- Border:     #334155 (Slate 700)
- Primary:    #3B82F6 (Blue 500)   / hover #2563EB
- Success:    #10B981 (Emerald 500)
- Warning:    #F59E0B (Amber 500)
- Danger:     #EF4444 (Red 500)
- Info:       #06B6D4 (Cyan 500)
- Violet:     #8B5CF6 (Violet 500)
- Text:       #F8FAFC (Slate 50)
- Text Muted: #94A3B8 (Slate 400)
- Text Faint: #64748B (Slate 500)
- Radius:     16px (cards) / 8px (controls) / 24px (pills)
"""

# ── Palette (importable so pages can build dynamic/inline styles too) ──────
BG = "#0F172A"
SURFACE = "#111827"
CARD = "#1E293B"
CARD_HOVER = "#243248"
BORDER = "#334155"
BORDER_SOFT = "#1E293B"
PRIMARY = "#3B82F6"
PRIMARY_HOVER = "#2563EB"
PRIMARY_SOFT = "rgba(59, 130, 246, 0.15)"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#EF4444"
INFO = "#06B6D4"
VIOLET = "#8B5CF6"
TEXT = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
TEXT_FAINT = "#64748B"
RADIUS_CARD = 16
RADIUS_CTRL = 8
RADIUS_PILL = 24
FONT_FAMILY = "'Segoe UI', 'Inter', -apple-system, sans-serif"

GLOBAL_QSS = f"""
/* ============================= Global ============================= */
QMainWindow, QWidget#central_widget, QStackedWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: {FONT_FAMILY};
}}
QWidget {{
    font-family: {FONT_FAMILY};
    selection-background-color: {PRIMARY};
    selection-color: #FFFFFF;
}}
QToolTip {{
    background-color: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ============================= Scroll Areas ======================== */
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ============================= Scrollbars ========================== */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{ background: #475569; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{ background: #475569; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ============================= Cards ================================ */
QFrame#card {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#card_flat {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS_CARD}px;
}}

/* ============================= Labels =============================== */
QLabel {{ color: {TEXT}; background: transparent; }}
QLabel#page_title {{ color: {TEXT}; font-size: 26px; font-weight: 700; }}
QLabel#page_subtitle {{ color: {TEXT_MUTED}; font-size: 14px; }}
QLabel#section_title {{ color: {TEXT}; font-size: 15px; font-weight: 600; }}
QLabel#muted {{ color: {TEXT_MUTED}; font-size: 12px; }}

/* ============================= Line / Text Edits ==================== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CTRL}px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {PRIMARY};
    background-color: {SURFACE};
}}
QLineEdit:disabled, QTextEdit:disabled {{
    color: {TEXT_FAINT};
    background-color: {SURFACE};
}}
QLineEdit#search_field {{
    border-radius: {RADIUS_PILL}px;
    padding: 8px 16px;
    background-color: {CARD};
}}

/* ============================= ComboBox ============================= */
QComboBox {{
    background-color: {BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CTRL}px;
    padding: 7px 12px;
    font-size: 13px;
    min-height: 20px;
}}
QComboBox:hover {{ border-color: #475569; }}
QComboBox:focus {{ border-color: {PRIMARY}; }}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_MUTED};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    selection-background-color: {PRIMARY_SOFT};
    selection-color: {PRIMARY};
    outline: none;
    padding: 4px;
}}

/* ============================= SpinBox =============================== */
QSpinBox, QDoubleSpinBox {{
    background-color: {BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CTRL}px;
    padding: 6px 10px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {PRIMARY}; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {CARD};
    width: 16px;
    border-left: 1px solid {BORDER};
}}

/* ============================= CheckBox / Radio ====================== */
QCheckBox {{ color: {TEXT}; font-size: 13px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border-radius: 5px;
    border: 1.5px solid {BORDER};
    background: {BG};
}}
QCheckBox::indicator:hover {{ border-color: {PRIMARY}; }}
QCheckBox::indicator:checked {{
    background: {PRIMARY};
    border-color: {PRIMARY};
}}
QRadioButton {{ color: {TEXT}; font-size: 13px; spacing: 8px; }}
QRadioButton::indicator {{
    width: 18px; height: 18px;
    border-radius: 9px;
    border: 1.5px solid {BORDER};
    background: {BG};
}}
QRadioButton::indicator:checked {{
    background: {PRIMARY};
    border-color: {PRIMARY};
}}

/* ============================= Buttons =============================== */
QPushButton {{
    background-color: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CTRL}px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #253449; border-color: #475569; }}
QPushButton:pressed {{ background-color: #1a2637; }}
QPushButton:disabled {{ color: {TEXT_FAINT}; background-color: {SURFACE}; border-color: {BORDER_SOFT}; }}

QPushButton#primary_btn {{
    background-color: {PRIMARY};
    color: #FFFFFF;
    border: none;
    border-radius: {RADIUS_CTRL}px;
    padding: 9px 18px;
    font-weight: 600;
}}
QPushButton#primary_btn:hover {{ background-color: {PRIMARY_HOVER}; }}
QPushButton#primary_btn:pressed {{ background-color: #1D4ED8; }}
QPushButton#primary_btn:disabled {{ background-color: {CARD}; color: {TEXT_FAINT}; }}

QPushButton#secondary_btn {{
    background-color: transparent;
    color: {PRIMARY};
    border: 1px solid {PRIMARY};
    border-radius: {RADIUS_CTRL}px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton#secondary_btn:hover {{ background-color: {PRIMARY_SOFT}; }}

QPushButton#danger_btn {{
    background-color: {DANGER};
    color: #FFFFFF;
    border: none;
    border-radius: {RADIUS_CTRL}px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton#danger_btn:hover {{ background-color: #DC2626; }}

QPushButton#ghost_btn {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border: none;
    padding: 6px 10px;
}}
QPushButton#ghost_btn:hover {{ color: {TEXT}; background-color: rgba(255,255,255,0.06); border-radius: 6px; }}

/* ============================= Tables ================================= */
QTableWidget, QTableView {{
    background-color: {CARD};
    alternate-background-color: #202f47;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 12px;
    gridline-color: {BORDER};
    selection-background-color: {PRIMARY_SOFT};
    selection-color: {TEXT};
    outline: none;
}}
QTableWidget::item, QTableView::item {{
    padding: 8px;
    border-bottom: 1px solid {BORDER_SOFT};
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {PRIMARY_SOFT};
    color: {TEXT};
}}
QHeaderView::section {{
    background-color: {SURFACE};
    color: {TEXT_MUTED};
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}}
QHeaderView::section:first {{ border-top-left-radius: 12px; }}
QHeaderView::section:last {{ border-top-right-radius: 12px; }}
QTableCornerButton::section {{ background-color: {SURFACE}; border: none; }}

/* ============================= Tree Widget ============================ */
QTreeWidget {{
    background-color: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 12px;
    outline: none;
    padding: 4px;
}}
QTreeWidget::item {{ padding: 6px 4px; border-radius: 6px; }}
QTreeWidget::item:hover {{ background-color: rgba(255,255,255,0.05); }}
QTreeWidget::item:selected {{ background-color: {PRIMARY_SOFT}; color: {PRIMARY}; }}

/* ============================= Tabs ==================================== */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    background: {CARD};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 9px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 13px;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{
    color: {PRIMARY};
    background: {CARD};
    border-bottom: 2px solid {PRIMARY};
}}

/* ============================= Progress Bar ============================ */
QProgressBar {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    text-align: center;
    color: {TEXT};
    font-size: 11px;
    font-weight: 600;
    min-height: 14px;
}}
QProgressBar::chunk {{
    background-color: {PRIMARY};
    border-radius: 7px;
}}

/* ============================= Splitter ================================ */
QSplitter::handle {{
    background-color: {BORDER_SOFT};
}}
QSplitter::handle:hover {{ background-color: {PRIMARY}; }}

/* ============================= ToolBar / StatusBar ====================== */
QToolBar {{
    background-color: {SURFACE};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px;
    spacing: 6px;
}}
QStatusBar {{
    background-color: {SURFACE};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
}}

/* ============================= Menus ==================================== */
QMenu {{
    background-color: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{ padding: 8px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background-color: {PRIMARY_SOFT}; color: {PRIMARY}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 6px 4px; }}
"""

# ── Reusable inline style snippets for pages that build widgets dynamically ──
def kpi_card_qss(accent: str) -> str:
    """Return QSS for a KPI/stat card that highlights with `accent` on hover."""
    return f"""
        QFrame#card {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: {RADIUS_CARD}px;
        }}
        QFrame#card:hover {{
            border-color: {accent};
        }}
    """


def badge_qss(color: str) -> str:
    """Small pill-style status badge."""
    return (
        f"color: {color}; background: {color}22; border: 1px solid {color}55;"
        f"border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
    )
