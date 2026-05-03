"""
Global Stats Window for the Gaming Launcher.
Aggregates playtime data across ALL games in the library.
Features:
  Tab 1 — Bar Chart: combined daily playtime (last 30 days) for all games
  Tab 2 — Calendar Heatmap: combined monthly view
  Tab 3 — Per-game breakdown table (sorted by total playtime)

Reuses BarChartWidget and CalendarHeatmapWidget from stats_window.py.
"""

import calendar
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QWidget, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QGridLayout
)
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QLinearGradient, QPen
from PyQt6.QtCore import Qt, QRectF

from core.database import Database
from core.models import Game, format_playtime
from ui.stats_window import (
    BarChartWidget, CalendarHeatmapWidget, SessionListWidget
)


# ═══════════════════════════════════════════════════════════════════════
#  PER-GAME BREAKDOWN WIDGET — Shows each game's playtime in a styled table
# ═══════════════════════════════════════════════════════════════════════

class GameBreakdownWidget(QWidget):
    """Custom-painted horizontal bar breakdown of each game's playtime."""

    def __init__(self, accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._games: list[tuple[str, int]] = []  # [(name, total_seconds), ...]
        self._max_seconds: int = 1
        self.setMinimumSize(600, 200)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def set_data(self, games: list[Game]):
        """Set game data — sorted by playtime descending."""
        self._games = [
            (g.name, g.total_playtime_seconds) for g in games
        ]
        self._games.sort(key=lambda x: x[1], reverse=True)
        self._max_seconds = max(
            (s for _, s in self._games), default=1
        ) or 1
        # Adjust widget minimum height based on game count
        row_height = 40
        header = 30
        self.setMinimumHeight(header + len(self._games) * row_height + 20)
        self.update()

    def paintEvent(self, event):
        if not self._games:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        left_margin = 200   # Space for game names
        right_margin = 100  # Space for time labels
        bar_area_w = w - left_margin - right_margin
        row_height = 40
        top = 10

        accent = QColor(self._accent)

        # Define a palette for different games (cycled)
        palette = [
            accent,
            QColor("#FF0080"),
            QColor("#00FF88"),
            QColor("#AA00FF"),
            QColor("#FF8800"),
            QColor("#00AAFF"),
            QColor("#FF4444"),
            QColor("#44FF44"),
        ]

        font_name = painter.font()
        font_name.setPixelSize(13)
        font_name.setBold(True)

        font_time = painter.font()
        font_time.setPixelSize(12)

        for i, (name, seconds) in enumerate(self._games):
            y = top + i * row_height
            bar_color = palette[i % len(palette)]

            # Game name (left side)
            painter.setFont(font_name)
            painter.setPen(QColor("#E8E8F0"))
            name_rect = QRectF(10, y + 4, left_margin - 20, row_height - 8)
            # Truncate name if too long
            metrics = painter.fontMetrics()
            elided = metrics.elidedText(
                name, Qt.TextElideMode.ElideRight, int(left_margin - 20)
            )
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignVCenter, elided)

            # Bar
            bar_w = (seconds / self._max_seconds) * bar_area_w if self._max_seconds > 0 else 0
            bar_w = max(bar_w, 4)  # Minimum visible bar
            bar_rect = QRectF(left_margin, y + 8, bar_w, row_height - 16)

            grad = QLinearGradient(bar_rect.left(), 0, bar_rect.right(), 0)
            grad.setColorAt(0, bar_color)
            grad.setColorAt(1, bar_color.darker(180))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_rect, 4, 4)

            # Playtime label (right of bar)
            painter.setFont(font_time)
            painter.setPen(QColor("#CCCCDD"))
            time_text = format_playtime(seconds)
            time_rect = QRectF(
                left_margin + bar_area_w + 10, y + 4,
                right_margin - 20, row_height - 8
            )
            painter.drawText(
                time_rect, Qt.AlignmentFlag.AlignVCenter, time_text
            )

        painter.end()


# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL STATS WINDOW — Aggregated stats for all games
# ═══════════════════════════════════════════════════════════════════════

class GlobalStatsWindow(QDialog):
    """
    Stats popup aggregating ALL games. Contains:
      Tab 1 — Bar chart (combined last 30 days)
      Tab 2 — Calendar heatmap (combined monthly)
      Tab 3 — Per-game breakdown
    """

    def __init__(self, database: Database,
                 accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._db = database
        self._accent = accent
        self._games: list[Game] = []

        self.setWindowTitle("Library Stats — All Games")
        self.setMinimumSize(800, 580)
        self.resize(840, 620)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header with aggregated total
        header_layout = QHBoxLayout()
        title = QLabel("📊  LIBRARY OVERVIEW")
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {self._accent};"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._total_label = QLabel("Total: ...")
        self._total_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #E8E8F0;"
        )
        header_layout.addWidget(self._total_label)

        self._games_count_label = QLabel("")
        self._games_count_label.setStyleSheet(
            "font-size: 13px; color: #8888AA; margin-left: 12px;"
        )
        header_layout.addWidget(self._games_count_label)

        layout.addLayout(header_layout)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ── Tab 1: Combined Bar Chart ─────────────────────────────────
        chart_page = QWidget()
        chart_layout = QVBoxLayout(chart_page)
        chart_layout.setContentsMargins(8, 8, 8, 8)

        self._chart_range_label = QLabel("Last 30 days — all games combined")
        self._chart_range_label.setStyleSheet(
            "font-size: 13px; color: #8888AA;"
        )
        chart_layout.addWidget(self._chart_range_label)

        self._bar_chart = BarChartWidget(self._accent)
        chart_layout.addWidget(self._bar_chart)

        tabs.addTab(chart_page, "📊 Daily Playtime")

        # ── Tab 2: Combined Calendar Heatmap ──────────────────────────
        cal_page = QWidget()
        cal_layout = QVBoxLayout(cal_page)
        cal_layout.setContentsMargins(8, 8, 8, 8)

        # Month navigation
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("◀")
        prev_btn.setFixedSize(36, 36)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.clicked.connect(self._prev_month)
        nav_layout.addWidget(prev_btn)

        self._month_label = QLabel()
        self._month_label.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {self._accent};"
        )
        self._month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self._month_label, stretch=1)

        next_btn = QPushButton("▶")
        next_btn.setFixedSize(36, 36)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.clicked.connect(self._next_month)
        nav_layout.addWidget(next_btn)
        cal_layout.addLayout(nav_layout)

        # Calendar + session info
        cal_body = QHBoxLayout()

        self._heatmap = CalendarHeatmapWidget(self._accent)
        self._heatmap.day_clicked.connect(self._on_day_clicked)
        cal_body.addWidget(self._heatmap, stretch=3)

        # Day detail panel (shows per-game breakdown for clicked day)
        self._day_detail = QLabel("Click a day to see details")
        self._day_detail.setStyleSheet(
            "color: #666677; font-size: 13px; padding: 8px;"
        )
        self._day_detail.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._day_detail.setWordWrap(True)
        self._day_detail.setMinimumWidth(200)
        cal_body.addWidget(self._day_detail, stretch=2)

        cal_layout.addLayout(cal_body)
        tabs.addTab(cal_page, "📅 Calendar")

        # ── Tab 3: Per-game breakdown ─────────────────────────────────
        breakdown_page = QWidget()
        breakdown_layout = QVBoxLayout(breakdown_page)
        breakdown_layout.setContentsMargins(8, 8, 8, 8)

        breakdown_header = QLabel("Playtime by Game")
        breakdown_header.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {self._accent};"
        )
        breakdown_layout.addWidget(breakdown_header)

        # Scrollable breakdown
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._breakdown = GameBreakdownWidget(self._accent)
        scroll.setWidget(self._breakdown)
        breakdown_layout.addWidget(scroll)

        tabs.addTab(breakdown_page, "🎮 Per Game")

    # ── Data Loading ───────────────────────────────────────────────────

    def _load_data(self):
        """Load all games and compute aggregated stats."""
        self._games = self._db.get_all_games()

        # Total playtime across all games
        total_seconds = sum(g.total_playtime_seconds for g in self._games)
        self._total_label.setText(f"Total: {format_playtime(total_seconds)}")
        self._games_count_label.setText(f"{len(self._games)} games")

        # Load bar chart (combined)
        self._load_chart_data()
        # Load calendar (combined)
        self._load_calendar_data()
        # Load breakdown
        self._breakdown.set_data(self._games)

    def _get_combined_daily_playtime(
            self, start_date: str, end_date: str) -> dict[str, int]:
        """Merge daily playtime from all games into a single dict."""
        combined: dict[str, int] = {}
        for game in self._games:
            game_data = self._db.get_daily_playtime(
                game.id, start_date, end_date
            )
            for day, seconds in game_data.items():
                combined[day] = combined.get(day, 0) + seconds
        return combined

    def _load_chart_data(self):
        """Load combined last 30 days for the bar chart."""
        today = datetime.now().date()
        start = today - timedelta(days=29)
        data = self._get_combined_daily_playtime(
            start.isoformat(), today.isoformat()
        )
        self._bar_chart.set_data(data, days=30)

        total_secs = sum(data.values())
        self._chart_range_label.setText(
            f"Last 30 days — {format_playtime(total_secs)} played (all games)"
        )

    def _load_calendar_data(self):
        """Load combined playtime for the current calendar month."""
        y, m = self._heatmap.get_month()
        days_in_month = calendar.monthrange(y, m)[1]
        start = f"{y}-{m:02d}-01"
        end = f"{y}-{m:02d}-{days_in_month:02d}"

        data = self._get_combined_daily_playtime(start, end)
        self._heatmap.set_data(data)

        month_name = calendar.month_name[m]
        self._month_label.setText(f"{month_name} {y}")

    def _prev_month(self):
        y, m = self._heatmap.get_month()
        if m == 1:
            y -= 1
            m = 12
        else:
            m -= 1
        self._heatmap.set_month(y, m)
        self._load_calendar_data()

    def _next_month(self):
        y, m = self._heatmap.get_month()
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
        self._heatmap.set_month(y, m)
        self._load_calendar_data()

    def _on_day_clicked(self, date_str: str):
        """Show per-game breakdown for a clicked day."""
        lines = [f"<b style='color:{self._accent};'>{date_str}</b><br><br>"]
        has_data = False

        for game in self._games:
            data = self._db.get_daily_playtime(
                game.id, date_str, date_str
            )
            seconds = data.get(date_str, 0)
            if seconds > 0:
                has_data = True
                lines.append(
                    f"<span style='color:#E8E8F0;'>{game.name}</span>: "
                    f"<span style='color:{self._accent};'>"
                    f"{format_playtime(seconds)}</span><br>"
                )

        if not has_data:
            lines.append(
                "<span style='color:#666677;'>No playtime recorded</span>"
            )

        self._day_detail.setText("".join(lines))
