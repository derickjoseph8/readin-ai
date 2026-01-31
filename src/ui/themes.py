"""Theme definitions and management for ReadIn AI UI."""

from typing import Dict, Any


# Theme color definitions
THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "name": "Dark",
        "background": "#1e1e2e",
        "surface": "#313244",
        "surface_alt": "#45475a",
        "border": "#45475a",
        "text_primary": "#cdd6f4",
        "text_secondary": "#a6adc8",
        "text_muted": "#6c7086",
        "accent": "#89b4fa",
        "accent_hover": "#74a8f7",
        "success": "#a6e3a1",
        "warning": "#f9e2af",
        "error": "#f38ba8",
        "header_bg": "#11111b",
        "scrollbar_bg": "#1e1e2e",
        "scrollbar_thumb": "#45475a",
    },
    "light": {
        "name": "Light",
        "background": "#ffffff",
        "surface": "#f1f5f9",
        "surface_alt": "#e2e8f0",
        "border": "#cbd5e1",
        "text_primary": "#1e293b",
        "text_secondary": "#475569",
        "text_muted": "#94a3b8",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "success": "#22c55e",
        "warning": "#eab308",
        "error": "#ef4444",
        "header_bg": "#f8fafc",
        "scrollbar_bg": "#f1f5f9",
        "scrollbar_thumb": "#cbd5e1",
    },
    "dark_gold": {
        "name": "Dark Gold (Premium)",
        "background": "#0f0f0f",
        "surface": "#1a1a1a",
        "surface_alt": "#262626",
        "border": "#333333",
        "text_primary": "#ffffff",
        "text_secondary": "#a3a3a3",
        "text_muted": "#737373",
        "accent": "#d4af37",
        "accent_hover": "#c9a227",
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "header_bg": "#0a0a0a",
        "scrollbar_bg": "#0f0f0f",
        "scrollbar_thumb": "#333333",
    },
    "dark_emerald": {
        "name": "Dark Emerald",
        "background": "#0f1412",
        "surface": "#1a2420",
        "surface_alt": "#243830",
        "border": "#2d4a3e",
        "text_primary": "#ffffff",
        "text_secondary": "#a7c4b5",
        "text_muted": "#6b8f7d",
        "accent": "#10b981",
        "accent_hover": "#059669",
        "success": "#34d399",
        "warning": "#fbbf24",
        "error": "#f87171",
        "header_bg": "#0a0f0d",
        "scrollbar_bg": "#0f1412",
        "scrollbar_thumb": "#2d4a3e",
    },
    "midnight": {
        "name": "Midnight Blue",
        "background": "#0f172a",
        "surface": "#1e293b",
        "surface_alt": "#334155",
        "border": "#475569",
        "text_primary": "#f8fafc",
        "text_secondary": "#cbd5e1",
        "text_muted": "#94a3b8",
        "accent": "#60a5fa",
        "accent_hover": "#3b82f6",
        "success": "#4ade80",
        "warning": "#fcd34d",
        "error": "#f87171",
        "header_bg": "#020617",
        "scrollbar_bg": "#0f172a",
        "scrollbar_thumb": "#475569",
    },
}


def get_theme(theme_name: str) -> Dict[str, str]:
    """Get a theme by name, falling back to dark_gold if not found."""
    return THEMES.get(theme_name, THEMES["dark_gold"])


def get_theme_names() -> list:
    """Get list of available theme names with display names."""
    return [(key, theme["name"]) for key, theme in THEMES.items()]


def generate_stylesheet(theme_name: str) -> str:
    """Generate a complete QSS stylesheet for the given theme."""
    theme = get_theme(theme_name)

    return f"""
/* Main Window */
QMainWindow, QDialog, QWidget {{
    background-color: {theme["background"]};
    color: {theme["text_primary"]};
    font-family: 'Segoe UI', 'SF Pro Display', system-ui, sans-serif;
}}

/* Labels */
QLabel {{
    color: {theme["text_primary"]};
    background: transparent;
}}

QLabel[class="secondary"] {{
    color: {theme["text_secondary"]};
}}

QLabel[class="muted"] {{
    color: {theme["text_muted"]};
}}

QLabel[class="accent"] {{
    color: {theme["accent"]};
}}

QLabel[class="success"] {{
    color: {theme["success"]};
}}

QLabel[class="header"] {{
    color: {theme["text_secondary"]};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

/* Buttons */
QPushButton {{
    background-color: {theme["surface"]};
    color: {theme["text_primary"]};
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {theme["surface_alt"]};
    border-color: {theme["accent"]};
}}

QPushButton:pressed {{
    background-color: {theme["background"]};
}}

QPushButton:disabled {{
    background-color: {theme["surface"]};
    color: {theme["text_muted"]};
    border-color: {theme["border"]};
}}

QPushButton[class="primary"] {{
    background-color: {theme["accent"]};
    color: {theme["background"]};
    border: none;
}}

QPushButton[class="primary"]:hover {{
    background-color: {theme["accent_hover"]};
}}

QPushButton[class="icon"] {{
    background-color: {theme["surface"]};
    border: none;
    border-radius: 4px;
    padding: 4px;
    min-width: 24px;
    min-height: 24px;
}}

QPushButton[class="icon"]:hover {{
    background-color: {theme["surface_alt"]};
}}

/* Text inputs */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {theme["surface"]};
    color: {theme["text_primary"]};
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {theme["accent"]};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {theme["accent"]};
}}

QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {theme["background"]};
    color: {theme["text_muted"]};
}}

/* Combo boxes */
QComboBox {{
    background-color: {theme["surface"]};
    color: {theme["text_primary"]};
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {theme["accent"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {theme["text_secondary"]};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {theme["surface"]};
    color: {theme["text_primary"]};
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    selection-background-color: {theme["accent"]};
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {theme["surface_alt"]};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background-color: {theme["accent"]};
    border: none;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {theme["accent_hover"]};
}}

QSlider::sub-page:horizontal {{
    background-color: {theme["accent"]};
    border-radius: 2px;
}}

/* Checkboxes */
QCheckBox {{
    color: {theme["text_primary"]};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {theme["border"]};
    border-radius: 4px;
    background-color: {theme["surface"]};
}}

QCheckBox::indicator:hover {{
    border-color: {theme["accent"]};
}}

QCheckBox::indicator:checked {{
    background-color: {theme["accent"]};
    border-color: {theme["accent"]};
}}

/* Tab widget */
QTabWidget::pane {{
    background-color: {theme["background"]};
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {theme["surface"]};
    color: {theme["text_secondary"]};
    border: 1px solid {theme["border"]};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {theme["background"]};
    color: {theme["text_primary"]};
    border-bottom: 2px solid {theme["accent"]};
}}

QTabBar::tab:hover:!selected {{
    background-color: {theme["surface_alt"]};
}}

/* Scroll bars */
QScrollBar:vertical {{
    background-color: {theme["scrollbar_bg"]};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {theme["scrollbar_thumb"]};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {theme["text_muted"]};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    height: 0;
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {theme["scrollbar_bg"]};
    height: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {theme["scrollbar_thumb"]};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {theme["text_muted"]};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    width: 0;
    background: none;
}}

/* Group boxes */
QGroupBox {{
    color: {theme["text_primary"]};
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
}}

QGroupBox::title {{
    color: {theme["text_secondary"]};
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}

/* Spin boxes */
QSpinBox, QDoubleSpinBox {{
    background-color: {theme["surface"]};
    color: {theme["text_primary"]};
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    padding: 6px 8px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {theme["accent"]};
}}

/* Tool tips */
QToolTip {{
    background-color: {theme["surface"]};
    color: {theme["text_primary"]};
    border: 1px solid {theme["border"]};
    border-radius: 4px;
    padding: 6px 10px;
}}

/* Frame */
QFrame[class="card"] {{
    background-color: {theme["surface"]};
    border: 1px solid {theme["border"]};
    border-radius: 8px;
}}

/* Separator */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    background-color: {theme["border"]};
}}

/* List widget */
QListWidget {{
    background-color: {theme["surface"]};
    color: {theme["text_primary"]};
    border: 1px solid {theme["border"]};
    border-radius: 6px;
    padding: 4px;
}}

QListWidget::item {{
    padding: 8px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {theme["accent"]};
    color: {theme["background"]};
}}

QListWidget::item:hover:!selected {{
    background-color: {theme["surface_alt"]};
}}
"""


def get_overlay_stylesheet(theme_name: str, opacity: float = 0.92) -> str:
    """Generate overlay-specific stylesheet with custom styling."""
    theme = get_theme(theme_name)

    return f"""
/* Overlay Window */
QWidget#overlay {{
    background-color: rgba({_hex_to_rgb(theme["background"])}, {opacity});
    border: 1px solid {theme["border"]};
    border-radius: 12px;
}}

/* Header */
QWidget#header {{
    background-color: {theme["header_bg"]};
    border-bottom: 1px solid {theme["border"]};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}}

/* Question section */
QWidget#question_section {{
    background-color: {theme["surface"]};
    border-radius: 8px;
    padding: 12px;
}}

/* Answer section */
QWidget#answer_section {{
    background-color: {theme["surface"]};
    border-radius: 8px;
    border-left: 3px solid {theme["success"]};
    padding: 12px;
}}

/* Section labels */
QLabel#section_label {{
    color: {theme["text_muted"]};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

QLabel#answer_label {{
    color: {theme["success"]};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

/* Content labels */
QLabel#question_text {{
    color: {theme["text_secondary"]};
    font-size: 14px;
    line-height: 1.5;
}}

QLabel#answer_text {{
    color: {theme["success"]};
    font-size: 14px;
    line-height: 1.6;
}}

/* Status text */
QLabel#status {{
    color: {theme["text_muted"]};
    font-size: 11px;
    font-style: italic;
}}

/* Header buttons */
QPushButton#header_btn {{
    background-color: {theme["surface"]};
    color: {theme["text_secondary"]};
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    min-width: 24px;
}}

QPushButton#header_btn:hover {{
    background-color: {theme["surface_alt"]};
    color: {theme["text_primary"]};
}}

QPushButton#close_btn {{
    background-color: rgba(239, 68, 68, 0.8);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

QPushButton#close_btn:hover {{
    background-color: rgba(239, 68, 68, 1.0);
}}

/* Usage warning */
QLabel#usage_warning {{
    color: {theme["warning"]};
    font-size: 11px;
}}
"""


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to RGB values for rgba()."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"
