"""
Global Statistics Window for Velox Gaming Launcher.

Features:
1. Orthogonal 2-axis chart (X = Games, Y = Hours) comparing playtime across all games.
2. Combined statistics view: aggregated KPIs, 30-day activity chart, and playtime breakdown.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QFrame, QScrollArea, QSizePolicy, QGridLayout,
    QProgressBar
)
from PyQt6.QtCore import Qt, QPoint, QRectF, QPointF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QBrush, QPen,
    QPainterPath, QPolygonF
)

from core.database import Database


# ── Design tokens ──────────────────────────────────────────────────────────────
BG_DARK   = "#080B14"
BG_SURF   = "#0F1623"
BG_RAISED = "#161E2E"
ACCENT    = "#00C8FF"
ACCENT2   = "#7B2FFF"
TEXT      = "#E8F0FE"
TEXT_DIM  = "#6B7FA3"
BORDER    = "#1E2A42"
SUCCESS   = "#00FF88"
# ───────────────────────────────────────────────────────────────────────────────


class OrthogonalChartWidget(QWidget):
    """
    Repère orthogonal à 2 axes:
    - Axe des abscisses (X) : Les Jeux
    - Axe des ordonnées (Y) : Le temps en Heures
    """

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setMinimumHeight(380)
        self.setMouseTracking(True)
        self._hovered_idx = -1
        self._games_data: List[Dict[str, Any]] = []
        self.refresh_data()

    def refresh_data(self):
        all_games = self.db.get_all_games()
        # Sort by playtime descending, or keep all games
        self._games_data = sorted(all_games, key=lambda g: g.get("total_playtime_seconds", 0), reverse=True)
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        W = self.width()
        H = self.height()
        ML, MR, MT, MB = 75, 45, 45, 65
        cw = W - ML - MR

        n = len(self._games_data)
        if n == 0:
            return

        slot_w = cw / n
        if ML <= pos.x() <= W - MR and MT <= pos.y() <= H - MB:
            idx = int((pos.x() - ML) / slot_w)
            if 0 <= idx < n and idx != self._hovered_idx:
                self._hovered_idx = idx
                self.update()
                return

        if self._hovered_idx != -1:
            self._hovered_idx = -1
            self.update()

    def leaveEvent(self, event):
        if self._hovered_idx != -1:
            self._hovered_idx = -1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        W = self.width()
        H = self.height()

        # Margins: Left (for hours scale), Right, Top, Bottom (for game titles)
        ML, MR, MT, MB = 75, 45, 45, 65
        cw = W - ML - MR
        ch = H - MT - MB

        # Background
        painter.fillRect(0, 0, W, H, QColor(BG_DARK))

        if not self._games_data:
            painter.setPen(QColor(TEXT_DIM))
            painter.setFont(QFont("Rajdhani", 12))
            painter.drawText(QRectF(0, 0, W, H), Qt.AlignmentFlag.AlignCenter, "Aucun jeu dans la bibliothèque")
            return

        # Playtimes in hours
        playtimes_h = [g.get("total_playtime_seconds", 0) / 3600.0 for g in self._games_data]
        max_h = max(playtimes_h) if playtimes_h else 0

        # Scale ceiling for Y axis
        if max_h <= 1.0:
            scale_max = 1.0
            step = 0.25
        elif max_h <= 5.0:
            scale_max = 5.0
            step = 1.0
        elif max_h <= 10.0:
            scale_max = 10.0
            step = 2.0
        elif max_h <= 25.0:
            scale_max = 25.0
            step = 5.0
        elif max_h <= 50.0:
            scale_max = 50.0
            step = 10.0
        else:
            scale_max = (int(max_h // 20) + 1) * 20.0
            step = scale_max / 5.0

        num_ticks = int(scale_max / step)

        # ── 1. Grille horizontale & Graduations Axe Y (Heures) ─────────────────
        painter.setFont(QFont("Segoe UI", 8))
        grid_pen = QPen(QColor(BORDER))
        grid_pen.setStyle(Qt.PenStyle.DashLine)

        for i in range(num_ticks + 1):
            val_h = i * step
            y = MT + ch - (val_h / scale_max) * ch

            # Gridline
            painter.setPen(grid_pen)
            painter.drawLine(int(ML), int(y), int(W - MR), int(y))

            # Y tick label
            painter.setPen(QColor(TEXT_DIM))
            if step < 1.0:
                lbl = f"{val_h:.2f} h"
            elif step % 1 == 0:
                lbl = f"{int(val_h)} h"
            else:
                lbl = f"{val_h:.1f} h"

            painter.drawText(
                QRectF(0, y - 9, ML - 10, 18),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                lbl,
            )

        # ── 2. Tracé des deux axes orthogonaux ────────────────────────────────
        axis_pen = QPen(QColor(ACCENT), 2)
        painter.setPen(axis_pen)

        # Axe Y (Heures)
        painter.drawLine(int(ML), int(MT - 15), int(ML), int(MT + ch))
        # Flèche Axe Y
        arrow_y = QPolygonF([
            QPointF(ML, MT - 24),
            QPointF(ML - 5, MT - 14),
            QPointF(ML + 5, MT - 14),
        ])
        painter.setBrush(QBrush(QColor(ACCENT)))
        painter.drawPolygon(arrow_y)

        # Titre Axe Y
        painter.setFont(QFont("Rajdhani", 9, QFont.Weight.Bold))
        painter.setPen(QColor(ACCENT))
        painter.drawText(QRectF(ML + 10, MT - 30, 120, 20), Qt.AlignmentFlag.AlignLeft, "▲ HEURES (h)")

        # Axe X (Jeux)
        painter.setPen(axis_pen)
        painter.drawLine(int(ML), int(MT + ch), int(W - MR + 20), int(MT + ch))
        # Flèche Axe X
        arrow_x = QPolygonF([
            QPointF(W - MR + 28, MT + ch),
            QPointF(W - MR + 18, MT + ch - 5),
            QPointF(W - MR + 18, MT + ch + 5),
        ])
        painter.setBrush(QBrush(QColor(ACCENT)))
        painter.drawPolygon(arrow_x)

        # Titre Axe X
        painter.drawText(QRectF(W - MR - 40, MT + ch + 35, 70, 20), Qt.AlignmentFlag.AlignRight, "JEUX ▶")

        # ── 3. Barres de données par Jeu ──────────────────────────────────────
        n = len(self._games_data)
        slot_w = cw / n
        bar_w = min(max(slot_w * 0.55, 24), 70)

        for i, game in enumerate(self._games_data):
            tot_sec = game.get("total_playtime_seconds", 0)
            hrs = tot_sec / 3600.0
            bar_h = (hrs / scale_max) * ch if scale_max > 0 else 0

            cx = ML + i * slot_w + slot_w / 2
            bx = cx - bar_w / 2
            by = MT + ch - bar_h

            is_hovered = (i == self._hovered_idx)

            # Bar gradient
            grad = QLinearGradient(bx, by, bx, MT + ch)
            if is_hovered:
                grad.setColorAt(0.0, QColor("#FFFFFF"))
                grad.setColorAt(0.2, QColor(ACCENT))
                grad.setColorAt(1.0, QColor(ACCENT2))
            else:
                grad.setColorAt(0.0, QColor(ACCENT))
                grad.setColorAt(1.0, QColor(ACCENT2))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)

            if bar_h > 3:
                bar_path = QPainterPath()
                bar_path.addRoundedRect(QRectF(bx, by, bar_w, bar_h), 5, 5)
                painter.drawPath(bar_path)
            else:
                # Minimum tick for games with 0 or low playtime
                painter.setBrush(QColor(BORDER))
                painter.drawRoundedRect(QRectF(bx, MT + ch - 3, bar_w, 3), 1, 1)

            # Exact playtime label above the bar
            painter.setFont(QFont("Rajdhani", 9, QFont.Weight.Bold))
            painter.setPen(QColor(ACCENT if not is_hovered else "#FFFFFF"))

            h_int = tot_sec // 3600
            m_int = (tot_sec % 3600) // 60
            if tot_sec == 0:
                time_str = "0h"
            elif h_int > 0:
                time_str = f"{h_int}h {m_int}m" if m_int > 0 else f"{h_int}h"
            else:
                time_str = f"{m_int}m"

            painter.drawText(
                QRectF(cx - 40, by - 22, 80, 18),
                Qt.AlignmentFlag.AlignCenter,
                time_str,
            )

            # Game name on X axis (below)
            painter.setFont(QFont("Rajdhani", 9, QFont.Weight.Bold if is_hovered else QFont.Weight.Medium))
            painter.setPen(QColor(TEXT if is_hovered else TEXT_DIM))

            name = game.get("name", "")
            # Shorten if needed
            if len(name) > 14:
                name_disp = name[:12] + "…"
            else:
                name_disp = name

            painter.drawText(
                QRectF(cx - (slot_w / 2), MT + ch + 8, slot_w, 24),
                Qt.AlignmentFlag.AlignCenter,
                name_disp,
            )


class CombinedDailyChart(QWidget):
    """30-day aggregate activity chart across all games."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setMinimumHeight(200)
        self._data: Dict[str, int] = {}
        self.refresh_data()

    def refresh_data(self):
        self._data = self.db.get_combined_daily_playtime(days=30)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()
        ML, MR, MT, MB = 50, 20, 20, 30
        cw = W - ML - MR
        ch = H - MT - MB

        painter.fillRect(0, 0, W, H, QColor(BG_DARK))

        if not self._data:
            painter.setPen(QColor(TEXT_DIM))
            painter.drawText(QRectF(0, 0, W, H), Qt.AlignmentFlag.AlignCenter, "Aucune session enregistrée récemment")
            return

        values = list(self._data.values())
        max_sec = max(values) if values else 1
        max_h = max_sec / 3600.0
        ceil_h = max(1.0, float(int(max_h) + 1))

        # Y scale
        painter.setFont(QFont("Segoe UI", 7))
        painter.setPen(QColor(TEXT_DIM))
        painter.drawText(QRectF(0, MT - 6, ML - 8, 14), Qt.AlignmentFlag.AlignRight, f"{ceil_h:.0f}h")
        painter.drawText(QRectF(0, MT + ch - 8, ML - 8, 14), Qt.AlignmentFlag.AlignRight, "0h")

        # Bars
        n = len(self._data)
        bar_w = max(2, (cw / n) - 3)

        for i, (dt, sec) in enumerate(self._data.items()):
            h_ratio = sec / (ceil_h * 3600)
            bh = h_ratio * ch
            bx = ML + i * (cw / n) + 1
            by = MT + ch - bh

            grad = QLinearGradient(bx, by, bx, MT + ch)
            grad.setColorAt(0.0, QColor(ACCENT))
            grad.setColorAt(1.0, QColor(ACCENT2))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(bx, by, bar_w, max(2, bh)), 2, 2)

            # Date every 5 days
            if i % 5 == 0:
                painter.setPen(QColor(TEXT_DIM))
                day_str = dt[8:10] + "/" + dt[5:7]
                painter.drawText(QRectF(bx - 12, MT + ch + 6, 30, 16), Qt.AlignmentFlag.AlignCenter, day_str)


class GlobalStatsWindow(QDialog):
    """Window showing comparative orthogonal chart & combined library statistics."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Statistiques Globales — Velox")
        self.setMinimumSize(920, 640)
        self.setModal(True)

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._drag_pos: Optional[QPoint] = None

        self._setup_ui()
        self._apply_styles()

    # ── Drag Support ──────────────────────────────────────────────────────────
    def _on_title_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _on_title_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ── UI Setup ──────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Title Bar ─────────────────────────────────────────────────────────
        title_bar = QFrame()
        title_bar.setObjectName("globalStatsTitleBar")
        title_bar.setFixedHeight(48)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(20, 0, 14, 0)

        icon_lbl = QLabel("📊")
        icon_lbl.setFont(QFont("Segoe UI", 14))

        title_lbl = QLabel("STATISTIQUES GLOBALES DE LA BIBLIOTHÈQUE")
        title_lbl.setFont(QFont("Rajdhani", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {ACCENT};")

        close_btn = QPushButton("✕")
        close_btn.setObjectName("globalStatsCloseBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.close)

        tb_layout.addWidget(icon_lbl)
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        tb_layout.addWidget(close_btn)

        title_bar.mousePressEvent = self._on_title_press
        title_bar.mouseMoveEvent  = self._on_title_move
        root.addWidget(title_bar)

        # ── Content ───────────────────────────────────────────────────────────
        content = QWidget()
        content.setObjectName("statsContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(22, 16, 22, 18)
        cl.setSpacing(14)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("globalStatsTabs")

        # ── Tab 1 : Repère Orthogonal (Jeux vs Heures) ────────────────────────
        self.tab_orthogonal = QWidget()
        to_layout = QVBoxLayout(self.tab_orthogonal)
        to_layout.setContentsMargins(16, 14, 16, 14)
        to_layout.setSpacing(10)

        desc_1 = QLabel("Repère orthogonal : Comparatif du temps de jeu (Heures) par jeu")
        desc_1.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
        desc_1.setStyleSheet(f"color: {TEXT_DIM};")
        to_layout.addWidget(desc_1)

        self.orthogonal_chart = OrthogonalChartWidget(self.db)
        to_layout.addWidget(self.orthogonal_chart)

        self.tabs.addTab(self.tab_orthogonal, "📊  Comparatif par jeu (Axes X / Y)")

        # ── Tab 2 : Statistiques Combinées ────────────────────────────────────
        self.tab_combined = QWidget()
        tc_layout = QVBoxLayout(self.tab_combined)
        tc_layout.setContentsMargins(16, 14, 16, 14)
        tc_layout.setSpacing(14)

        # Scrollable area for combined stats
        comb_scroll = QScrollArea()
        comb_scroll.setWidgetResizable(True)
        comb_scroll.setObjectName("combScroll")

        scroll_widget = QWidget()
        sw_layout = QVBoxLayout(scroll_widget)
        sw_layout.setContentsMargins(0, 0, 8, 0)
        sw_layout.setSpacing(16)

        stats = self.db.get_combined_stats()
        all_games = self.db.get_all_games()

        # KPI Cards Grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)

        # Card 1: Total Playtime
        tot_s = stats["total_playtime_seconds"]
        tot_h = tot_s // 3600
        tot_m = (tot_s % 3600) // 60
        time_display = f"{tot_h}h {tot_m}m"

        kpi_grid.addWidget(self._make_kpi_card("⏱ TEMPS CUMULÉ", time_display, f"{tot_s:,} secondes au total"), 0, 0)
        kpi_grid.addWidget(self._make_kpi_card("🎮 BIBLIOTHÈQUE", f"{stats['total_games']} jeux", "enregistrés dans Velox"), 0, 1)
        kpi_grid.addWidget(self._make_kpi_card("🎯 SESSIONS JOUÉES", f"{stats['total_sessions']} sessions", "parties enregistrées"), 0, 2)

        avg_s = stats["avg_session_seconds"]
        avg_h = avg_s // 3600
        avg_m = (avg_s % 3600) // 60
        avg_disp = f"{avg_h}h {avg_m}m" if avg_h > 0 else f"{avg_m}m"
        kpi_grid.addWidget(self._make_kpi_card("⏳ MOYENNE / SESSION", avg_disp, "durée moyenne par partie"), 1, 0)

        top = stats["top_game"]
        top_name = top["name"] if top else "Aucun"
        top_pct = f"{top['percentage']}% du temps total" if top else "-"
        kpi_grid.addWidget(self._make_kpi_card("🏆 JEU FAVORI", top_name, top_pct), 1, 1, 1, 2)

        sw_layout.addLayout(kpi_grid)

        # Daily combined activity chart
        act_lbl = QLabel("📈 Activité combinée quotidienne (30 derniers jours)")
        act_lbl.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
        act_lbl.setStyleSheet(f"color: {TEXT_DIM};")
        sw_layout.addWidget(act_lbl)

        self.daily_chart = CombinedDailyChart(self.db)
        sw_layout.addWidget(self.daily_chart)

        # Breakdown per game table
        breakdown_lbl = QLabel("📊 Répartition du temps de jeu total")
        breakdown_lbl.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
        breakdown_lbl.setStyleSheet(f"color: {TEXT_DIM};")
        sw_layout.addWidget(breakdown_lbl)

        breakdown_frame = QFrame()
        breakdown_frame.setObjectName("breakdownBox")
        bf_layout = QVBoxLayout(breakdown_frame)
        bf_layout.setSpacing(10)
        bf_layout.setContentsMargins(14, 12, 14, 12)

        sorted_games = sorted(all_games, key=lambda g: g.get("total_playtime_seconds", 0), reverse=True)
        for g in sorted_games:
            g_sec = g.get("total_playtime_seconds", 0)
            g_pct = int((g_sec / tot_s * 100)) if tot_s > 0 else 0
            gh = g_sec // 3600
            gm = (g_sec % 3600) // 60
            time_txt = f"{gh}h {gm}m" if gh > 0 else f"{gm}m"

            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(12)

            name_l = QLabel(g["name"])
            name_l.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
            name_l.setFixedWidth(160)
            name_l.setStyleSheet(f"color: {TEXT};")

            pbar = QProgressBar()
            pbar.setValue(g_pct)
            pbar.setTextVisible(False)
            pbar.setFixedHeight(8)
            pbar.setObjectName("gameProgress")

            time_lbl = QLabel(f"{time_txt}  ({g_pct}%)")
            time_lbl.setFont(QFont("Segoe UI", 9))
            time_lbl.setFixedWidth(100)
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            time_lbl.setStyleSheet(f"color: {ACCENT};")

            row_l.addWidget(name_l)
            row_l.addWidget(pbar)
            row_l.addWidget(time_lbl)
            bf_layout.addWidget(row_w)

        sw_layout.addWidget(breakdown_frame)

        comb_scroll.setWidget(scroll_widget)
        tc_layout.addWidget(comb_scroll)

        self.tabs.addTab(self.tab_combined, "🌐  Statistiques combinées")

        cl.addWidget(self.tabs)
        root.addWidget(content)

    def _make_kpi_card(self, title: str, value: str, subtext: str) -> QFrame:
        card = QFrame()
        card.setObjectName("kpiCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Rajdhani", 8, QFont.Weight.Bold))
        t_lbl.setStyleSheet(f"color: {TEXT_DIM}; letter-spacing: 1px;")

        v_lbl = QLabel(value)
        v_lbl.setFont(QFont("Rajdhani", 16, QFont.Weight.Bold))
        v_lbl.setStyleSheet(f"color: {TEXT};")

        s_lbl = QLabel(subtext)
        s_lbl.setFont(QFont("Segoe UI", 8))
        s_lbl.setStyleSheet(f"color: {ACCENT};")

        cl.addWidget(t_lbl)
        cl.addWidget(v_lbl)
        cl.addWidget(s_lbl)
        return card

    # ── Styles ────────────────────────────────────────────────────────────────
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_SURF};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}

            #globalStatsTitleBar {{
                background-color: {BG_DARK};
                border-bottom: 1px solid {BORDER};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}

            #globalStatsCloseBtn {{
                background: transparent;
                border: none;
                color: {TEXT_DIM};
                font-size: 13px;
                border-radius: 5px;
            }}
            #globalStatsCloseBtn:hover {{
                background-color: #CC2222;
                color: #FFFFFF;
            }}

            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 8px;
                background-color: {BG_DARK};
            }}

            QTabBar::tab {{
                background-color: transparent;
                color: {TEXT_DIM};
                padding: 9px 22px;
                font-size: 10px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                margin-right: 6px;
            }}
            QTabBar::tab:selected {{
                background-color: {ACCENT};
                color: #000000;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {BORDER};
                color: {TEXT};
            }}

            #kpiCard {{
                background-color: {BG_RAISED};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}

            #breakdownBox {{
                background-color: {BG_RAISED};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}

            #gameProgress {{
                background-color: {BG_DARK};
                border: none;
                border-radius: 4px;
            }}
            #gameProgress::chunk {{
                background-color: {ACCENT};
                border-radius: 4px;
            }}

            #combScroll {{
                border: none;
                background: transparent;
            }}
            #combScroll QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            #combScroll QScrollBar::handle:vertical {{
                background: {BORDER};
                border-radius: 3px;
            }}
        """)
