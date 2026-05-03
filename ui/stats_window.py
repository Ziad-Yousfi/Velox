"""
Stats Window for the Gaming Launcher.
Two-tab popup showing detailed playtime analytics for a single game:
  Tab 1 — Bar Chart: daily playtime for the last 30 days
  Tab 2 — Calendar Heatmap: monthly view with color-coded cells

All charts are painted with QPainter (no matplotlib) to keep RAM minimal.
"""

import calendar
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QWidget, QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, QLinearGradient
)
from PyQt6.QtCore import Qt, QRect, QRectF, pyqtSignal

from core.database import Database
from core.models import Game, Session, format_playtime


# ═══════════════════════════════════════════════════════════════════════
#  BAR CHART WIDGET — Daily playtime for a date range
# ═══════════════════════════════════════════════════════════════════════

class BarChartWidget(QWidget):
    """Custom-painted bar chart showing daily play hours."""

    def __init__(self, accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._data: dict[str, int] = {}   # {date_str: seconds}
        self._labels: list[str] = []
        self._values: list[float] = []    # hours
        self._max_value: float = 1.0
        self.setMinimumSize(600, 300)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def set_data(self, daily_playtime: dict[str, int], days: int = 30):
        """
        Set chart data from {date_string: total_seconds} dict.
        Fills in zeros for days with no playtime.
        """
        self._labels.clear()
        self._values.clear()
        today = datetime.now().date()

        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.isoformat()
            seconds = daily_playtime.get(day_str, 0)
            hours = seconds / 3600.0
            self._labels.append(day.strftime("%d"))
            self._values.append(hours)

        self._max_value = max(self._values) if self._values else 1.0
        if self._max_value < 0.5:
            self._max_value = 1.0
        self._data = daily_playtime
        self.update()

    def paintEvent(self, event):
        if not self._values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Chart margins
        left_margin = 50
        right_margin = 15
        top_margin = 20
        bottom_margin = 40
        chart_w = w - left_margin - right_margin
        chart_h = h - top_margin - bottom_margin

        n = len(self._values)
        if n == 0 or chart_w <= 0 or chart_h <= 0:
            painter.end()
            return

        bar_w = max(chart_w / n - 2, 3)
        spacing = chart_w / n

        accent_color = QColor(self._accent)

        # Draw Y-axis labels and grid lines
        painter.setPen(QPen(QColor("#333344"), 1))
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)

        num_grid = 5
        for i in range(num_grid + 1):
            y_val = self._max_value * i / num_grid
            y_pos = top_margin + chart_h - (chart_h * i / num_grid)
            # Grid line
            painter.setPen(QPen(QColor("#222233"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(
                int(left_margin), int(y_pos),
                int(w - right_margin), int(y_pos)
            )
            # Label
            painter.setPen(QColor("#8888AA"))
            label = f"{y_val:.1f}h"
            painter.drawText(
                QRect(0, int(y_pos) - 8, left_margin - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label
            )

        # Draw bars
        for i, (label, value) in enumerate(
                zip(self._labels, self._values)):
            x = left_margin + i * spacing + (spacing - bar_w) / 2
            bar_h = (value / self._max_value) * chart_h if self._max_value > 0 else 0
            y = top_margin + chart_h - bar_h

            if value > 0:
                # Gradient fill for the bar
                grad = QLinearGradient(x, y, x, top_margin + chart_h)
                grad.setColorAt(0, accent_color)
                grad.setColorAt(1, accent_color.darker(250))
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(
                    QRectF(x, y, bar_w, bar_h), 3, 3
                )

            # X-axis label (show every few labels to avoid overlap)
            if n <= 15 or i % (n // 10 + 1) == 0:
                painter.setPen(QColor("#8888AA"))
                painter.drawText(
                    QRect(int(x - spacing / 2), int(top_margin + chart_h + 4),
                          int(spacing), 20),
                    Qt.AlignmentFlag.AlignCenter, label
                )

        painter.end()


# ═══════════════════════════════════════════════════════════════════════
#  CALENDAR HEATMAP WIDGET — Monthly view with color intensity
# ═══════════════════════════════════════════════════════════════════════

class CalendarHeatmapWidget(QWidget):
    """
    Monthly calendar with cells colored by playtime intensity.
    Clicking a day emits day_clicked with the date string.
    """

    day_clicked = pyqtSignal(str)  # "YYYY-MM-DD"

    def __init__(self, accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._year = datetime.now().year
        self._month = datetime.now().month
        self._data: dict[str, int] = {}
        self._selected_day: str = ""
        self.setMinimumSize(500, 350)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def set_data(self, daily_playtime: dict[str, int]):
        """Set the playtime data dict {date_string: total_seconds}."""
        self._data = daily_playtime
        self.update()

    def set_month(self, year: int, month: int):
        self._year = year
        self._month = month
        self.update()

    def get_month(self) -> tuple[int, int]:
        return self._year, self._month

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        margin = 10
        header_h = 30
        day_names_h = 25
        grid_top = margin + header_h + day_names_h
        grid_w = w - 2 * margin
        grid_h = h - grid_top - margin

        cell_w = grid_w / 7
        cal = calendar.Calendar(firstweekday=0)  # Monday first
        month_days = cal.monthdayscalendar(self._year, self._month)
        num_rows = len(month_days)
        cell_h = grid_h / num_rows if num_rows > 0 else grid_h / 5

        accent = QColor(self._accent)

        # Day name headers
        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#8888AA"))
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, name in enumerate(day_names):
            x = margin + i * cell_w
            painter.drawText(
                QRectF(x, margin + header_h, cell_w, day_names_h),
                Qt.AlignmentFlag.AlignCenter, name
            )

        # Draw cells
        font.setPixelSize(13)
        font.setBold(False)
        painter.setFont(font)

        for row_idx, week in enumerate(month_days):
            for col_idx, day in enumerate(week):
                if day == 0:
                    continue

                x = margin + col_idx * cell_w + 2
                y = grid_top + row_idx * cell_h + 2
                cw = cell_w - 4
                ch = cell_h - 4

                date_str = f"{self._year}-{self._month:02d}-{day:02d}"
                seconds = self._data.get(date_str, 0)
                hours = seconds / 3600.0

                # Color based on intensity
                if hours <= 0:
                    bg = QColor("#1A1A2E")
                elif hours < 1:
                    bg = QColor(accent)
                    bg.setAlpha(60)
                elif hours < 3:
                    bg = QColor(accent)
                    bg.setAlpha(130)
                else:
                    bg = QColor(accent)
                    bg.setAlpha(220)

                # Highlight selected day
                if date_str == self._selected_day:
                    painter.setPen(QPen(accent, 2))
                else:
                    painter.setPen(QPen(QColor("#333344"), 1))

                painter.setBrush(QBrush(bg))
                painter.drawRoundedRect(QRectF(x, y, cw, ch), 6, 6)

                # Day number
                painter.setPen(QColor("#E8E8F0") if hours > 0
                               else QColor("#666677"))
                painter.drawText(
                    QRectF(x, y + 2, cw, ch * 0.5),
                    Qt.AlignmentFlag.AlignCenter, str(day)
                )

                # Playtime label (if any)
                if hours > 0:
                    font_small = painter.font()
                    font_small.setPixelSize(9)
                    painter.setFont(font_small)
                    painter.setPen(QColor("#CCCCDD"))
                    time_str = (f"{hours:.1f}h" if hours >= 1
                                else f"{int(seconds / 60)}m")
                    painter.drawText(
                        QRectF(x, y + ch * 0.45, cw, ch * 0.45),
                        Qt.AlignmentFlag.AlignCenter, time_str
                    )
                    font.setPixelSize(13)
                    painter.setFont(font)

        painter.end()

    def mousePressEvent(self, event):
        """Detect which day cell was clicked."""
        pos = event.position()
        w = self.width()
        h = self.height()
        margin = 10
        header_h = 30
        day_names_h = 25
        grid_top = margin + header_h + day_names_h
        grid_w = w - 2 * margin
        grid_h = h - grid_top - margin
        cell_w = grid_w / 7

        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(self._year, self._month)
        num_rows = len(month_days)
        cell_h = grid_h / num_rows if num_rows > 0 else grid_h / 5

        col = int((pos.x() - margin) / cell_w)
        row = int((pos.y() - grid_top) / cell_h)

        if 0 <= row < num_rows and 0 <= col < 7:
            day = month_days[row][col]
            if day > 0:
                date_str = f"{self._year}-{self._month:02d}-{day:02d}"
                self._selected_day = date_str
                self.update()
                self.day_clicked.emit(date_str)

        super().mousePressEvent(event)


# ═══════════════════════════════════════════════════════════════════════
#  SESSION LIST WIDGET — Shows individual sessions for a selected day
# ═══════════════════════════════════════════════════════════════════════

class SessionListWidget(QWidget):
    """Displays session details for a single day."""

    def __init__(self, accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self._placeholder = QLabel("Click a day to see sessions")
        self._placeholder.setStyleSheet("color: #666677; font-size: 13px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)

    def show_sessions(self, date_str: str, sessions: list[Session]):
        """Replace content with session entries for the given date."""
        # Clear existing items
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not sessions:
            lbl = QLabel(f"No sessions on {date_str}")
            lbl.setStyleSheet("color: #666677; font-size: 13px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(lbl)
            return

        header = QLabel(f"Sessions on {date_str}")
        header.setStyleSheet(
            f"color: {self._accent}; font-size: 14px; font-weight: 700;"
        )
        self._layout.addWidget(header)

        for s in sessions:
            try:
                start = datetime.fromisoformat(s.start_time)
                end = datetime.fromisoformat(s.end_time) if s.end_time else None
            except (ValueError, TypeError):
                start = None
                end = None

            start_str = start.strftime("%H:%M") if start else "?"
            end_str = end.strftime("%H:%M") if end else "?"
            dur_str = s.duration_formatted

            row = QLabel(f"  {start_str} → {end_str}  ({dur_str})")
            row.setStyleSheet("color: #CCCCDD; font-size: 13px;")
            self._layout.addWidget(row)

        self._layout.addStretch()


# ═══════════════════════════════════════════════════════════════════════
#  STATS WINDOW — Main dialog combining chart + calendar
# ═══════════════════════════════════════════════════════════════════════

class StatsWindow(QDialog):
    """
    Stats popup for a single game. Contains:
      Tab 1 — Bar chart (last 30 days)
      Tab 2 — Calendar heatmap (monthly)
    """

    def __init__(self, game: Game, database: Database,
                 accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._game = game
        self._db = database
        self._accent = accent

        self.setWindowTitle(f"Stats — {game.name}")
        self.setMinimumSize(720, 520)
        self.resize(760, 560)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )

        self._build_ui()
        self._load_chart_data()
        self._load_calendar_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header with total playtime
        header_layout = QHBoxLayout()
        title = QLabel(self._game.name)
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {self._accent};"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        total = format_playtime(self._game.total_playtime_seconds)
        self._total_label = QLabel(f"Total: {total}")
        self._total_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #E8E8F0;"
        )
        header_layout.addWidget(self._total_label)
        layout.addLayout(header_layout)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ── Tab 1: Bar Chart ───────────────────────────────────────────
        chart_page = QWidget()
        chart_layout = QVBoxLayout(chart_page)
        chart_layout.setContentsMargins(8, 8, 8, 8)

        self._chart_range_label = QLabel("Last 30 days")
        self._chart_range_label.setStyleSheet(
            "font-size: 13px; color: #8888AA;"
        )
        chart_layout.addWidget(self._chart_range_label)

        self._bar_chart = BarChartWidget(self._accent)
        chart_layout.addWidget(self._bar_chart)

        tabs.addTab(chart_page, "📊 Bar Chart")

        # ── Tab 2: Calendar Heatmap ────────────────────────────────────
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

        # Calendar + session list (side by side)
        cal_body = QHBoxLayout()

        self._heatmap = CalendarHeatmapWidget(self._accent)
        self._heatmap.day_clicked.connect(self._on_day_clicked)
        cal_body.addWidget(self._heatmap, stretch=3)

        self._session_list = SessionListWidget(self._accent)
        self._session_list.setMinimumWidth(200)
        cal_body.addWidget(self._session_list, stretch=2)

        cal_layout.addLayout(cal_body)
        tabs.addTab(cal_page, "📅 Calendar")

    # ── Data Loading ───────────────────────────────────────────────────

    def _load_chart_data(self):
        """Load last 30 days of playtime data for the bar chart."""
        today = datetime.now().date()
        start = today - timedelta(days=29)
        data = self._db.get_daily_playtime(
            self._game.id, start.isoformat(), today.isoformat()
        )
        self._bar_chart.set_data(data, days=30)

        # Show range total
        total_secs = sum(data.values())
        self._chart_range_label.setText(
            f"Last 30 days — {format_playtime(total_secs)} played"
        )

    def _load_calendar_data(self):
        """Load playtime data for the current calendar month."""
        y, m = self._heatmap.get_month()
        cal_obj = calendar.Calendar()
        days_in_month = calendar.monthrange(y, m)[1]
        start = f"{y}-{m:02d}-01"
        end = f"{y}-{m:02d}-{days_in_month:02d}"

        data = self._db.get_daily_playtime(self._game.id, start, end)
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
        """When a calendar day is clicked, show its sessions."""
        sessions = self._db.get_sessions(
            self._game.id, start_date=date_str, end_date=date_str
        )
        self._session_list.show_sessions(date_str, sessions)
