"""
Stats Window for Velox Gaming Launcher.

Displays detailed playtime statistics with:
- Tab 1: Bar chart showing playtime per day (last 30 days) — gradient fills
- Tab 2: Calendar heatmap with rounded cells and 5 intensity levels
- Session list for selected days
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QScrollArea, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QRectF, QPointF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QBrush, QPen,
    QRadialGradient
)
from datetime import datetime, timedelta
import calendar


# ── Design tokens ──────────────────────────────────────────────────────────────
BG_DARK   = "#080B14"
BG_SURF   = "#0F1623"
BG_RAISED = "#161E2E"
ACCENT    = "#00C8FF"
ACCENT2   = "#7B2FFF"
TEXT      = "#E8F0FE"
TEXT_DIM  = "#6B7FA3"
BORDER    = "#1E2A42"
# ───────────────────────────────────────────────────────────────────────────────


class StatsWindow(QDialog):
    """Statistics window showing playtime data for a game."""

    ACCENT_COLOR = ACCENT
    BG_COLOR     = BG_SURF

    def __init__(self, game_data: dict, db, parent=None):
        super().__init__(parent)
        self.game_data = game_data
        self.db        = db
        self.game_id   = game_data["id"]
        self.game_name = game_data["name"]

        self.setWindowTitle(f"Stats — {self.game_name}")
        self.setMinimumSize(880, 660)
        self.setModal(True)

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint
        )

        # Drag support
        self._drag_pos = None

        self._setup_ui()
        self._apply_styles()

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Title bar ─────────────────────────────────────────────────────────
        title_bar = QFrame()
        title_bar.setObjectName("statsTitleBar")
        title_bar.setFixedHeight(46)
        tb_l = QHBoxLayout(title_bar)
        tb_l.setContentsMargins(18, 0, 12, 0)

        icon_lbl = QLabel("📊")
        icon_lbl.setFont(QFont("Segoe UI", 14))

        name_lbl = QLabel(f"{self.game_name}")
        name_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {TEXT};")

        # Playtime summary badge
        total_s = self.game_data.get("total_playtime_seconds", 0)
        h = total_s // 3600
        m = (total_s % 3600) // 60
        time_lbl = QLabel(f"  ⏱ {h}h {m}m total  ")
        time_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        time_lbl.setObjectName("timeBadge")

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("statsCloseBtn")
        close_btn.clicked.connect(self.close)

        tb_l.addWidget(icon_lbl)
        tb_l.addWidget(name_lbl)
        tb_l.addSpacing(12)
        tb_l.addWidget(time_lbl)
        tb_l.addStretch()
        tb_l.addWidget(close_btn)

        title_bar.mousePressEvent = self._on_title_press
        title_bar.mouseMoveEvent  = self._on_title_move

        root.addWidget(title_bar)

        # ── Content ───────────────────────────────────────────────────────────
        content = QWidget()
        content.setObjectName("statsContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(12)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("statsTabs")

        self.chart_tab = QWidget()
        self._setup_chart_tab()
        self.tabs.addTab(self.chart_tab, "📈  Playtime quotidien")

        self.calendar_tab = QWidget()
        self._setup_calendar_tab()
        self.tabs.addTab(self.calendar_tab, "📅  Calendrier")

        cl.addWidget(self.tabs)
        root.addWidget(content)

    def _setup_chart_tab(self):
        layout = QVBoxLayout(self.chart_tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl = QLabel("30 derniers jours")
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet(f"color: {TEXT_DIM};")
        layout.addWidget(lbl)

        self.bar_chart = BarChartWidget(self.game_id, self.db)
        self.bar_chart.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.bar_chart)

    def _setup_calendar_tab(self):
        layout = QVBoxLayout(self.calendar_tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Month navigation
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setObjectName("navBtn")
        self.prev_btn.setFixedSize(34, 34)
        self.prev_btn.clicked.connect(self._prev_month)

        self.month_lbl = QLabel("")
        self.month_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.next_btn = QPushButton("▶")
        self.next_btn.setObjectName("navBtn")
        self.next_btn.setFixedSize(34, 34)
        self.next_btn.clicked.connect(self._next_month)

        nav.addWidget(self.prev_btn)
        nav.addWidget(self.month_lbl)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

        self.current_date = datetime.now()
        self._update_month_label()

        self.calendar_heatmap = CalendarHeatmapWidget(
            self.game_id, self.db,
            self.current_date.year,
            self.current_date.month,
        )
        self.calendar_heatmap.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.calendar_heatmap)

        self.sessions_lbl = QLabel("Cliquez sur un jour pour voir les sessions")
        self.sessions_lbl.setFont(QFont("Segoe UI", 9))
        self.sessions_lbl.setStyleSheet(f"color: {TEXT_DIM};")
        self.sessions_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sessions_lbl)

        self.sessions_scroll = QScrollArea()
        self.sessions_scroll.setWidgetResizable(True)
        self.sessions_scroll.setMaximumHeight(130)
        self.sessions_scroll.setObjectName("sessionsScroll")
        self.sessions_scroll.hide()

        self.sessions_container = QWidget()
        self.sessions_layout = QVBoxLayout(self.sessions_container)
        self.sessions_layout.setSpacing(4)
        self.sessions_scroll.setWidget(self.sessions_container)
        layout.addWidget(self.sessions_scroll)

    # ── Month navigation ───────────────────────────────────────────────────────
    def _update_month_label(self):
        months_fr = [
            "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]
        self.month_lbl.setText(
            f"{months_fr[self.current_date.month]} {self.current_date.year}"
        )

    def _prev_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(
                year=self.current_date.year - 1, month=12
            )
        else:
            self.current_date = self.current_date.replace(
                month=self.current_date.month - 1
            )
        self._update_month_label()
        self.calendar_heatmap.update_month(
            self.current_date.year, self.current_date.month
        )

    def _next_month(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(
                year=self.current_date.year + 1, month=1
            )
        else:
            self.current_date = self.current_date.replace(
                month=self.current_date.month + 1
            )
        self._update_month_label()
        self.calendar_heatmap.update_month(
            self.current_date.year, self.current_date.month
        )

    def show_sessions_for_day(self, day: int, playtime_seconds: int):
        """Show session list for a clicked calendar day."""
        while self.sessions_layout.count():
            item = self.sessions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if playtime_seconds == 0:
            lbl = QLabel(f"Aucune session le {day}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {TEXT_DIM};")
            self.sessions_layout.addWidget(lbl)
        else:
            date_str = (
                f"{self.current_date.year}-"
                f"{self.current_date.month:02d}-"
                f"{day:02d}"
            )
            sessions = self.db.get_sessions_for_game(self.game_id)
            day_sessions = [
                s for s in sessions if s["start_time"].startswith(date_str)
            ]

            h_total = playtime_seconds // 3600
            m_total = (playtime_seconds % 3600) // 60
            header = QLabel(f"📅  {date_str}  —  {h_total}h {m_total}m au total")
            header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            header.setStyleSheet(f"color: {ACCENT};")
            self.sessions_layout.addWidget(header)

            for s in day_sessions:
                start = s["start_time"][11:16]
                dur = s.get("duration_seconds") or 0
                sh = dur // 3600
                sm = (dur % 3600) // 60
                row = QLabel(f"   ▸  {start}  —  {sh}h {sm}m")
                row.setFont(QFont("Segoe UI", 9))
                row.setStyleSheet(f"color: {TEXT_DIM};")
                self.sessions_layout.addWidget(row)

            self.sessions_layout.addStretch()

        self.sessions_scroll.show()

    # ── Drag ──────────────────────────────────────────────────────────────────
    def _on_title_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def _on_title_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ── Styles ─────────────────────────────────────────────────────────────────
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_SURF};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}

            #statsTitleBar {{
                background-color: {BG_DARK};
                border-bottom: 1px solid {BORDER};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}

            #timeBadge {{
                background-color: {BORDER};
                color: {ACCENT};
                border-radius: 10px;
                padding: 2px 8px;
            }}

            #statsCloseBtn {{
                background-color: transparent;
                border: none;
                color: {TEXT_DIM};
                font-size: 13px;
                border-radius: 5px;
            }}
            #statsCloseBtn:hover {{
                background-color: #CC2222;
                color: #FFFFFF;
            }}

            #statsContent {{
                background-color: {BG_SURF};
            }}

            QLabel {{
                color: {TEXT};
            }}

            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 8px;
                background-color: {BG_DARK};
            }}

            QTabBar::tab {{
                background-color: transparent;
                color: {TEXT_DIM};
                padding: 9px 20px;
                font-size: 10px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {ACCENT};
                color: #000000;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {BORDER};
                color: {TEXT};
            }}

            #navBtn {{
                background-color: transparent;
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {TEXT_DIM};
                font-size: 11px;
            }}
            #navBtn:hover {{
                border-color: {ACCENT};
                color: {ACCENT};
            }}

            #sessionsScroll {{
                border: 1px solid {BORDER};
                border-radius: 6px;
                background-color: {BG_DARK};
            }}
            #sessionsScroll QScrollBar:vertical {{
                background: transparent;
                width: 5px;
            }}
            #sessionsScroll QScrollBar::handle:vertical {{
                background: {BORDER};
                border-radius: 3px;
            }}
            #sessionsScroll QScrollBar::handle:vertical:hover {{
                background: {ACCENT};
            }}
            #sessionsScroll QScrollBar::add-line:vertical,
            #sessionsScroll QScrollBar::sub-line:vertical {{
                height: 0;
            }}

            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)


# ── Bar Chart ──────────────────────────────────────────────────────────────────
class BarChartWidget(QWidget):
    """Custom bar chart — gradient-filled bars, grid lines, labels."""

    def __init__(self, game_id: int, db, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.db      = db
        self.setMinimumHeight(260)
        self._data: dict = {}
        self._load_data()

    def _load_data(self):
        self._data = self.db.get_daily_playtime(self.game_id, days=30)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()

        ML, MR, MT, MB = 54, 14, 16, 38

        cw = W - ML - MR   # chart width
        ch = H - MT - MB   # chart height

        # ── Background ────────────────────────────────────────────────────────
        painter.fillRect(0, 0, W, H, QColor(BG_DARK))

        if not self._data:
            painter.setPen(QColor(TEXT_DIM))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(
                QRectF(0, 0, W, H),
                Qt.AlignmentFlag.AlignCenter,
                "Aucune donnée de jeu",
            )
            return

        values     = list(self._data.values())
        max_value  = max(values) if values else 1
        num_days   = len(self._data)

        # ── Grid lines ────────────────────────────────────────────────────────
        grid_pen = QPen(QColor(BORDER))
        grid_pen.setWidthF(0.6)
        painter.setPen(grid_pen)

        for i in range(1, 5):
            gy = int(MT + ch * (1 - i / 4))
            painter.drawLine(ML, gy, ML + cw, gy)

            secs  = max_value * i / 4
            label = f"{secs/3600:.1f}h" if secs >= 3600 else f"{int(secs/60)}m"
            painter.setPen(QColor(TEXT_DIM))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(QRectF(2, gy - 8, ML - 4, 16),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             label)
            painter.setPen(grid_pen)

        # ── Axes ──────────────────────────────────────────────────────────────
        axis_pen = QPen(QColor(BORDER))
        axis_pen.setWidthF(1.2)
        painter.setPen(axis_pen)
        painter.drawLine(ML, MT, ML, MT + ch)
        painter.drawLine(ML, MT + ch, ML + cw, MT + ch)

        # ── Bars ──────────────────────────────────────────────────────────────
        bar_total_w = cw / num_days
        bar_w       = max(bar_total_w * 0.55, 4.0)
        gap         = bar_total_w - bar_w

        for i, (date_str, seconds) in enumerate(self._data.items()):
            bh = (seconds / max_value) * ch if max_value > 0 else 0
            bh = max(bh, 2.0)
            bx = ML + i * bar_total_w + gap / 2
            by = MT + ch - bh

            # Gradient fill: bottom cyan → top violet
            grad = QLinearGradient(bx, by + bh, bx, by)
            grad.setColorAt(0.0, QColor(ACCENT))
            grad.setColorAt(1.0, QColor(ACCENT2))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)

            radius = min(3.0, bar_w / 2)
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), radius, radius)

            # Glow overlay
            glow = QColor(0, 200, 255, 25)
            painter.setBrush(glow)
            painter.drawRoundedRect(
                QRectF(bx - 2, by, bar_w + 4, bh), radius, radius
            )

            # X-axis date label (every ~5 bars to avoid overlap)
            if num_days <= 15 or i % max(1, num_days // 8) == 0:
                painter.setPen(QColor(TEXT_DIM))
                painter.setFont(QFont("Segoe UI", 6))
                label = date_str[5:]  # MM-DD
                painter.drawText(
                    QRectF(bx - 4, MT + ch + 5, bar_w + 8, 14),
                    Qt.AlignmentFlag.AlignCenter,
                    label,
                )


# ── Calendar Heatmap ───────────────────────────────────────────────────────────
class CalendarHeatmapWidget(QWidget):
    """Calendar heatmap — rounded cells, 5 intensity levels."""

    # 5 levels: no play → very light → light → medium → bright
    LEVELS = [
        QColor("#0D1320"),   # 0: no play (dark bg)
        QColor("#003040"),   # 1: < 15 min
        QColor("#005570"),   # 2: 15min – 1h
        QColor("#0088AA"),   # 3: 1h – 3h
        QColor(ACCENT),      # 4: 3h+
    ]

    def __init__(self, game_id: int, db, year: int, month: int, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.db      = db
        self.year    = year
        self.month   = month
        self._data: dict = {}
        self._load_data()
        self.setMinimumHeight(340)
        self._clicked_day: int | None = None

    def _load_data(self):
        self._data = self.db.get_calendar_data(self.game_id, self.year, self.month)
        self.update()

    def update_month(self, year: int, month: int):
        self.year  = year
        self.month = month
        self._clicked_day = None
        self._load_data()

    def _intensity(self, seconds: int) -> int:
        if seconds == 0:
            return 0
        if seconds < 900:       # < 15 min
            return 1
        if seconds < 3600:      # < 1h
            return 2
        if seconds < 10800:     # < 3h
            return 3
        return 4

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()

        painter.fillRect(0, 0, W, H, QColor(BG_DARK))

        cal       = calendar.Calendar(firstweekday=6)
        raw_days  = list(cal.itermonthdays(self.year, self.month))
        # Include leading/trailing zeros for proper week alignment
        # But we only paint actual month days; zeros = empty

        COLS, ROWS = 7, 6
        HDR_H      = 28
        PAD        = 10

        cell_w = (W - PAD * 2) / COLS
        cell_h = (H - PAD - HDR_H) / ROWS
        radius = 6.0

        # Day headers
        day_names_fr = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))

        for i, name in enumerate(day_names_fr):
            cx = PAD + i * cell_w + cell_w / 2
            cy = PAD + HDR_H / 2
            if name in ("Sam", "Dim"):
                painter.setPen(QColor(ACCENT2))
            else:
                painter.setPen(QColor(TEXT_DIM))
            painter.drawText(
                QRectF(PAD + i * cell_w, PAD, cell_w, HDR_H),
                Qt.AlignmentFlag.AlignCenter,
                name,
            )

        # Cells
        today = None
        from datetime import date as ddate
        try:
            today = ddate.today()
        except Exception:
            pass

        for idx, day_num in enumerate(raw_days):
            col = idx % 7
            row = idx // 7

            if row >= ROWS:
                break

            rx = PAD + col * cell_w + 2
            ry = PAD + HDR_H + row * cell_h + 2
            rw = cell_w - 4
            rh = cell_h - 4

            if day_num == 0:
                # Empty (prev/next month)
                c = QColor(BG_DARK)
                c.setAlphaF(0.3)
                painter.setBrush(c)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(rx, ry, rw, rh), radius, radius)
                continue

            playtime = self._data.get(day_num, 0)
            level    = self._intensity(playtime)
            color    = self.LEVELS[level]

            # Highlight today
            is_today = (
                today is not None
                and today.year  == self.year
                and today.month == self.month
                and today.day   == day_num
            )

            if self._clicked_day == day_num:
                painter.setBrush(QColor(ACCENT))
            else:
                painter.setBrush(color)

            if is_today:
                pen = QPen(QColor(ACCENT))
                pen.setWidthF(1.8)
                painter.setPen(pen)
            else:
                painter.setPen(Qt.PenStyle.NoPen)

            painter.drawRoundedRect(QRectF(rx, ry, rw, rh), radius, radius)

            # Day number (top area of cell)
            if self._clicked_day == day_num:
                painter.setPen(QColor("#000000"))
            elif level >= 3:
                painter.setPen(QColor("#FFFFFF"))
            elif level >= 1:
                painter.setPen(QColor(ACCENT))
            else:
                painter.setPen(QColor(TEXT_DIM))

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(
                QRectF(rx + 5, ry + 3, rw - 10, 14),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(day_num),
            )

            # Hours and minutes displayed clearly in the cell
            if playtime > 0:
                ph = playtime // 3600
                pm = (playtime % 3600) // 60
                if ph > 0 and pm > 0:
                    time_txt = f"{ph}h{pm:02d}"
                elif ph > 0:
                    time_txt = f"{ph}h"
                else:
                    time_txt = f"{pm}m"

                if self._clicked_day == day_num:
                    painter.setPen(QColor("#000000"))
                elif level >= 2:
                    painter.setPen(QColor("#FFFFFF"))
                else:
                    painter.setPen(QColor("#00E5FF"))

                painter.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
                painter.drawText(
                    QRectF(rx + 2, ry + 16, rw - 4, rh - 18),
                    Qt.AlignmentFlag.AlignCenter,
                    time_txt,
                )

        # Legend
        legend_y = H - 14
        legend_labels = ["0", "<15m", "<1h", "<3h", "3h+"]
        box_w, box_h = 14, 10
        lx = PAD
        painter.setFont(QFont("Segoe UI", 7))
        for i, (lvl_color, lbl) in enumerate(zip(self.LEVELS, legend_labels)):
            painter.setBrush(lvl_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(lx, legend_y, box_w, box_h), 2, 2)
            painter.setPen(QColor(TEXT_DIM))
            painter.drawText(
                QRectF(lx + box_w + 2, legend_y - 1, 32, 12),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                lbl,
            )
            lx += box_w + 36

    def mousePressEvent(self, event):
        W = self.width()
        H = self.height()
        COLS, ROWS = 7, 6
        HDR_H = 28
        PAD   = 10

        cell_w = (W - PAD * 2) / COLS
        cell_h = (H - PAD - HDR_H) / ROWS

        x = event.position().x()
        y = event.position().y()

        if y < PAD + HDR_H:
            return

        col = int((x - PAD) / cell_w)
        row = int((y - PAD - HDR_H) / cell_h)

        if col < 0 or col >= 7 or row < 0 or row >= ROWS:
            return

        cal       = calendar.Calendar(firstweekday=6)
        raw_days  = list(cal.itermonthdays(self.year, self.month))
        idx       = row * 7 + col

        if idx >= len(raw_days) or raw_days[idx] == 0:
            return

        actual_day = raw_days[idx]
        self._clicked_day = actual_day
        self.update()

        playtime = self._data.get(actual_day, 0)
        if hasattr(self.parent(), "show_sessions_for_day"):
            self.parent().show_sessions_for_day(actual_day, playtime)
