"""
Theme and stylesheet generator for the Gaming Launcher.
Centralizes all QSS styles and makes accent color swappable at runtime.
Provides a scanline grid overlay via CSS gradient (no image file needed).
"""


def generate_stylesheet(accent: str = "#00D4FF") -> str:
    """
    Build the full application stylesheet.
    All accent-colored elements use the provided hex color.
    """

    # Derive a dimmed version of the accent for hover states
    # (simply add transparency via rgba won't work in QSS — use a darker shade)
    bg_dark = "#0D0D0D"
    bg_card = "#141420"
    bg_input = "#1A1A2E"
    border = "#222233"
    text_primary = "#E8E8F0"
    text_secondary = "#8888AA"

    return f"""
    /* ── Global ─────────────────────────────────────────── */
    QWidget {{
        background-color: {bg_dark};
        color: {text_primary};
        font-family: 'Rajdhani', 'Segoe UI', 'Arial', sans-serif;
        font-size: 14px;
    }}

    /* ── Scroll Area ────────────────────────────────────── */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: {bg_dark};
        width: 8px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {accent};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        height: 0px;
    }}

    /* ── Buttons ────────────────────────────────────────── */
    QPushButton {{
        background-color: {bg_input};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton:hover {{
        border-color: {accent};
        color: {accent};
    }}
    QPushButton:pressed {{
        background-color: {border};
    }}
    QPushButton:disabled {{
        color: #555566;
        border-color: #222222;
    }}

    /* Accent / primary button */
    QPushButton#accentBtn {{
        background-color: {accent};
        color: #0D0D0D;
        border: none;
        font-weight: 700;
    }}
    QPushButton#accentBtn:hover {{
        background-color: {accent}CC;
        color: #0D0D0D;
    }}

    /* ── Line Edits ─────────────────────────────────────── */
    QLineEdit {{
        background-color: {bg_input};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px 12px;
        color: {text_primary};
        font-size: 14px;
        selection-background-color: {accent};
    }}
    QLineEdit:focus {{
        border-color: {accent};
    }}

    /* ── Labels ─────────────────────────────────────────── */
    QLabel {{
        background: transparent;
        border: none;
    }}
    QLabel#sectionTitle {{
        font-size: 20px;
        font-weight: 700;
        color: {accent};
    }}
    QLabel#subtitle {{
        font-size: 12px;
        color: {text_secondary};
    }}

    /* ── Tab Widget ─────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {border};
        border-radius: 6px;
        background: {bg_dark};
    }}
    QTabBar::tab {{
        background: {bg_input};
        color: {text_secondary};
        padding: 10px 24px;
        border: 1px solid {border};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: {bg_dark};
        color: {accent};
        border-color: {accent};
    }}
    QTabBar::tab:hover:!selected {{
        color: {text_primary};
    }}

    /* ── Dialog / Settings ──────────────────────────────── */
    QDialog {{
        background-color: {bg_dark};
    }}
    QCheckBox {{
        color: {text_primary};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {border};
        border-radius: 4px;
        background: {bg_input};
    }}
    QCheckBox::indicator:checked {{
        background: {accent};
        border-color: {accent};
    }}

    /* ── ComboBox ────────────────────────────────────────── */
    QComboBox {{
        background-color: {bg_input};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 12px;
        color: {text_primary};
    }}
    QComboBox:hover {{
        border-color: {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {bg_input};
        color: {text_primary};
        border: 1px solid {border};
        selection-background-color: {accent};
        selection-color: #0D0D0D;
    }}

    /* ── ToolTip ─────────────────────────────────────────── */
    QToolTip {{
        background-color: {bg_input};
        color: {text_primary};
        border: 1px solid {accent};
        padding: 4px 8px;
        border-radius: 4px;
    }}

    /* ── Title Bar ───────────────────────────────────────── */
    QWidget#titleBar {{
        background-color: #0A0A14;
        border-bottom: 1px solid {border};
    }}
    QPushButton#titleBtn {{
        background: transparent;
        border: none;
        border-radius: 4px;
        padding: 6px;
        min-width: 36px;
        max-width: 36px;
        min-height: 28px;
        max-height: 28px;
    }}
    QPushButton#titleBtn:hover {{
        background-color: #222233;
    }}
    QPushButton#closeBtn {{
        background: transparent;
        border: none;
        border-radius: 4px;
        padding: 6px;
        min-width: 36px;
        max-width: 36px;
        min-height: 28px;
        max-height: 28px;
    }}
    QPushButton#closeBtn:hover {{
        background-color: #CC3333;
    }}

    /* ── Game Card ───────────────────────────────────────── */
    QFrame#gameCard {{
        background-color: {bg_card};
        border: 1px solid {border};
        border-radius: 10px;
    }}
    QFrame#gameCard:hover {{
        border-color: {accent};
    }}
    """


# ── Scanline overlay stylesheet for the central widget ──────────────

def scanline_overlay_style() -> str:
    """
    Returns a stylesheet fragment that applies a subtle CSS grid pattern
    over the main background. Lightweight — no image file needed.
    """
    return """
    QWidget#centralBg {
        background-color: #0D0D0D;
        /* Grid pattern via repeating linear gradients in QSS is limited,
           so we use a semi-transparent pattern rendered by a custom paint. */
    }
    """
