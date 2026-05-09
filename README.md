# 🎮 Velox Gaming Launcher

A lightweight, RAM-efficient gaming launcher for Windows with automatic playtime tracking and detailed statistics.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-6.7-green?logo=qt)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey?logo=sqlite)

## Features

- **Game Management** — Add any .exe with custom name and cover image
- **Automatic Time Tracking** — Launches games and records play sessions
- **Stats Dashboard** — Bar chart (30 days) + calendar heatmap (monthly)
- **Gaming Aesthetic** — Dark theme, neon accents, frameless window, scanline overlay
- **System Tray** — Minimizes to tray, continues tracking in background
- **RAM Efficient** — ~40-50 MB idle, no Electron/Chromium

## Tech Stack

| Component     | Technology              | Why                                      |
|---------------|-------------------------|------------------------------------------|
| UI Framework  | PyQt6 (native Qt)       | Native rendering, ~40 MB RAM             |
| Database      | SQLite (WAL mode)       | Zero config, single-file, fast reads     |
| Charts        | Custom QPainter         | No matplotlib = saves ~100 MB RAM        |
| Process Track | subprocess + QTimer     | 5s poll interval, zero CPU when idle     |
| Icons         | Inline SVG strings      | No file I/O, crisp at any resolution     |

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup

```bash
# Clone or download the project
cd gaming-launcher

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Optional: Custom Font

Download [Rajdhani](https://fonts.google.com/specimen/Rajdhani) from Google Fonts and place the `.ttf` files in:

```
gaming-launcher/assets/fonts/
```

The app falls back to Segoe UI if no custom font is found.

## Running

```bash
python main.py
```

## Building Standalone .exe

```bash
# Install PyInstaller (included in requirements.txt)
pyinstaller --onefile --windowed --name "VeloxLauncher" ^
  --add-data "assets;assets" ^
  --icon assets/icons/app.ico ^
  main.py
```

The compiled `.exe` will be in the `dist/` folder.

## Usage

1. **Add a game**: Click the `+ ADD GAME` button, select a `.exe` file, set a name
2. **Launch**: Click `PLAY` on a game card — the launcher tracks playtime automatically
3. **Stop**: Click `STOP` to manually end tracking, or wait for the game to exit
4. **View stats**: Click `INFO` to see bar chart and calendar heatmap
5. **Settings**: Click the gear icon to change accent color or tray behavior
6. **Right-click** a game card to delete it

## RAM Optimization Decisions

| Decision                          | Impact                                  |
|-----------------------------------|------------------------------------------|
| QPainter charts vs matplotlib     | Saves ~100 MB RAM                        |
| Inline SVG vs PNG icons           | Saves ~5-10 MB, no file I/O             |
| QTimer polling vs dedicated thread| No thread overhead, auto-stops when idle |
| Lazy cover loading                | Only loads images visible in viewport    |
| SQLite query cache (5s TTL)       | Prevents redundant DB reads on repaint   |
| Single WAL-mode connection        | Fast concurrent reads, minimal overhead  |
| Suspend UI when minimized to tray | Near-zero CPU/GPU usage in background    |

## Project Structure

```
gaming-launcher/
├── main.py                  # Entry point
├── core/
│   ├── __init__.py
│   ├── models.py            # Game, Session dataclasses
│   ├── database.py          # SQLite abstraction (WAL, cache)
│   └── tracker.py           # Process tracking engine
├── ui/
│   ├── __init__.py
│   ├── main_window.py       # Main window + tray + settings
│   ├── game_card.py         # Game card widget
│   ├── stats_window.py      # Stats popup (chart + calendar)
│   ├── add_game_dialog.py   # Add game dialog
│   ├── icons.py             # Inline SVG icon strings
│   └── theme.py             # QSS stylesheet generator
├── assets/
│   └── fonts/               # Optional custom TTF fonts
├── settings.json            # Auto-created user settings
├── launcher.db              # Auto-created SQLite database
├── requirements.txt
└── README.md
```

## License

MIT — free for personal and commercial use.
