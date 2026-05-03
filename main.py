"""
Vaultex Gaming Launcher — Entry Point
A lightweight, RAM-efficient gaming launcher for Windows with:
  - Manual game/app management
  - Automatic playtime tracking
  - Stats dashboard (bar chart + calendar heatmap)
  - Gaming aesthetic (dark theme, neon accents, frameless window)

Usage:
    python main.py          # Run in development
    pyinstaller main.spec   # Build standalone .exe
"""

import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtCore import Qt


def get_base_dir() -> str:
    """Resolve base directory — works for both dev and frozen (PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_custom_fonts():
    """
    Load custom TTF/OTF fonts from assets/fonts/.
    Falls back to Segoe UI if no custom fonts are found.
    Returns the preferred font family name.
    """
    fonts_dir = os.path.join(get_base_dir(), "assets", "fonts")
    loaded_families = []

    if os.path.exists(fonts_dir):
        for font_file in os.listdir(fonts_dir):
            if font_file.lower().endswith(('.ttf', '.otf')):
                font_path = os.path.join(fonts_dir, font_file)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id >= 0:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    loaded_families.extend(families)
                    print(f"[Font] Loaded: {families}")

    # Preferred font priority: Rajdhani → Orbitron → Exo 2 → loaded → Segoe UI
    preferred = ["Rajdhani", "Orbitron", "Exo 2"]
    for name in preferred:
        if name in loaded_families:
            return name

    if loaded_families:
        return loaded_families[0]

    return "Segoe UI"


def main():
    # ── High DPI support ───────────────────────────────────────────────
    # Qt6 handles high DPI by default, but ensure it's enabled
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    # ── Create application ─────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("Vaultex Launcher")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")  # Consistent cross-platform look

    # ── Load fonts ─────────────────────────────────────────────────────
    font_family = load_custom_fonts()
    app_font = QFont(font_family, 11)
    app.setFont(app_font)
    print(f"[App] Using font: {font_family}")

    # ── Create and show main window ────────────────────────────────────
    # Import here to avoid circular imports and reduce startup overhead
    from ui.main_window import MainWindow, load_settings

    settings = load_settings()
    window = MainWindow(settings)
    window.show()

    print("[App] Vaultex Launcher started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
