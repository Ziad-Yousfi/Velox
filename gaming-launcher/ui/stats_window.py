"""
Stats Window for Velox Gaming Launcher.

Displays detailed playtime statistics with:
- Tab 1: Bar chart showing playtime per day (last 30 days)
- Tab 2: Calendar heatmap with color-coded intensity
- Session list for selected days
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QScrollArea, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QRect
from datetime import datetime, timedelta
import calendar


class StatsWindow(QDialog):
    """Statistics window showing playtime data for a game."""
    
    ACCENT_COLOR = "#00D4FF"
    BG_COLOR = "#1A1A1A"
    
    def __init__(self, game_data: dict, db, parent=None):
        super().__init__(parent)
        self.game_data = game_data
        self.db = db
        self.game_id = game_data['id']
        self.game_name = game_data['name']
        
        self.setWindowTitle(f"Stats - {self.game_name}")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        # Remove window frame for custom look
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Set up the stats window UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel(f"📊 {self.game_name} - STATISTICS")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.close)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("statsTabs")
        
        # Tab 1: Bar Chart
        self.chart_tab = QWidget()
        self._setup_chart_tab()
        self.tabs.addTab(self.chart_tab, "📈 Daily Playtime")
        
        # Tab 2: Calendar Heatmap
        self.calendar_tab = QWidget()
        self._setup_calendar_tab()
        self.tabs.addTab(self.calendar_tab, "📅 Calendar")
        
        layout.addWidget(self.tabs)
    
    def _setup_chart_tab(self):
        """Set up the bar chart tab."""
        layout = QVBoxLayout(self.chart_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Total playtime summary
        total_seconds = self.game_data.get('total_playtime_seconds', 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        summary_label = QLabel(f"Total Playtime: {hours}h {minutes}m")
        summary_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        summary_label.setStyleSheet(f"color: {self.ACCENT_COLOR};")
        layout.addWidget(summary_label)
        
        # Date range label
        self.date_range_label = QLabel("Last 30 Days")
        self.date_range_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.date_range_label)
        
        # Custom bar chart widget
        self.bar_chart = BarChartWidget(self.game_id, self.db)
        self.bar_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.bar_chart)
    
    def _setup_calendar_tab(self):
        """Set up the calendar heatmap tab."""
        layout = QVBoxLayout(self.calendar_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Navigation
        nav_layout = QHBoxLayout()
        
        self.prev_month_btn = QPushButton("◀ Prev")
        self.prev_month_btn.clicked.connect(self._prev_month)
        
        self.month_label = QLabel("")
        self.month_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_month_btn = QPushButton("Next ▶")
        self.next_month_btn.clicked.connect(self._next_month)
        
        nav_layout.addWidget(self.prev_month_btn)
        nav_layout.addWidget(self.month_label)
        nav_layout.addWidget(self.next_month_btn)
        layout.addLayout(nav_layout)
        
        # Current month and year
        self.current_date = datetime.now()
        self._update_month_label()
        
        # Calendar heatmap widget
        self.calendar_heatmap = CalendarHeatmapWidget(
            self.game_id, self.db, 
            self.current_date.year, 
            self.current_date.month
        )
        self.calendar_heatmap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.calendar_heatmap)
        
        # Selected day sessions
        self.sessions_label = QLabel("Click on a day to view sessions")
        self.sessions_label.setFont(QFont("Segoe UI", 10))
        self.sessions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sessions_label)
        
        # Sessions scroll area
        self.sessions_scroll = QScrollArea()
        self.sessions_scroll.setWidgetResizable(True)
        self.sessions_scroll.setMaximumHeight(150)
        self.sessions_scroll.hide()  # Hidden until a day is clicked
        
        self.sessions_container = QWidget()
        self.sessions_layout = QVBoxLayout(self.sessions_container)
        self.sessions_layout.setSpacing(5)
        
        self.sessions_scroll.setWidget(self.sessions_container)
        layout.addWidget(self.sessions_scroll)
    
    def _update_month_label(self):
        """Update the month/year label."""
        self.month_label.setText(
            self.current_date.strftime("%B %Y")
        )
    
    def _prev_month(self):
        """Navigate to previous month."""
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
            self.current_date.year, 
            self.current_date.month
        )
    
    def _next_month(self):
        """Navigate to next month."""
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
            self.current_date.year, 
            self.current_date.month
        )
    
    def show_sessions_for_day(self, day: int, playtime_seconds: int):
        """Show sessions for a specific day."""
        # Clear existing sessions
        while self.sessions_layout.count():
            item = self.sessions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if playtime_seconds == 0:
            label = QLabel(f"No playtime on {day}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sessions_layout.addWidget(label)
        else:
            # Get sessions for this day
            from datetime import datetime
            date_str = f"{self.current_date.year}-{self.current_date.month:02d}-{day:02d}"
            
            # Query sessions
            sessions = self.db.get_sessions_for_game(self.game_id)
            day_sessions = [
                s for s in sessions 
                if s['start_time'].startswith(date_str)
            ]
            
            if not day_sessions:
                label = QLabel(f"No sessions recorded")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.sessions_layout.addWidget(label)
            else:
                hours = playtime_seconds // 3600
                minutes = (playtime_seconds % 3600) // 60
                header = QLabel(f"📅 {date_str} - {hours}h {minutes}m total")
                header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                header.setStyleSheet(f"color: {self.ACCENT_COLOR};")
                self.sessions_layout.addWidget(header)
                
                for session in day_sessions:
                    start = session['start_time'][11:16]  # HH:MM
                    duration = session['duration_seconds'] or 0
                    h = duration // 3600
                    m = (duration % 3600) // 60
                    session_label = QLabel(f"  • {start} - {h}h {m}m")
                    session_label.setFont(QFont("Segoe UI", 9))
                    self.sessions_layout.addWidget(session_label)
                
                self.sessions_layout.addStretch()
        
        self.sessions_scroll.show()
    
    def _apply_styles(self):
        """Apply gaming-themed styles."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.BG_COLOR};
                border: 2px solid {self.ACCENT_COLOR};
                border-radius: 10px;
            }}
            
            QLabel {{
                color: #FFFFFF;
            }}
            
            QPushButton {{
                background-color: transparent;
                border: 2px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                color: {self.ACCENT_COLOR};
                font-weight: bold;
                padding: 5px 15px;
            }}
            
            QPushButton:hover {{
                background-color: {self.ACCENT_COLOR};
                color: #000000;
            }}
            
            QTabWidget::pane {{
                border: 1px solid #333333;
                border-radius: 5px;
                background-color: #0D0D0D;
            }}
            
            QTabBar::tab {{
                background-color: #1A1A1A;
                color: #888888;
                padding: 10px 20px;
                border: 1px solid #333333;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {self.ACCENT_COLOR};
                color: #000000;
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: #252525;
            }}
            
            QScrollArea {{
                border: 1px solid #333333;
                border-radius: 5px;
                background-color: #0D0D0D;
            }}
        """)


class BarChartWidget(QWidget):
    """Custom bar chart widget for displaying daily playtime."""
    
    def __init__(self, game_id: int, db, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.db = db
        self.setMinimumHeight(250)
        self._data = []
        self._load_data()
    
    def _load_data(self):
        """Load playtime data for last 30 days."""
        self._data = self.db.get_daily_playtime(self.game_id, days=30)
        self.update()
    
    def paintEvent(self, event):
        """Paint the bar chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Margins
        left_margin = 50
        right_margin = 10
        top_margin = 10
        bottom_margin = 30
        
        chart_width = width - left_margin - right_margin
        chart_height = height - top_margin - bottom_margin
        
        if not self._data:
            painter.drawText(
                width // 2, height // 2,
                Qt.AlignmentFlag.AlignCenter,
                "No playtime data"
            )
            return
        
        # Find max value for scaling
        values = list(self._data.values())
        max_value = max(values) if values else 1
        
        # Draw bars
        num_days = len(self._data)
        if num_days == 0:
            return
        
        bar_width = (chart_width / num_days) * 0.7
        gap = (chart_width / num_days) * 0.3
        
        accent_color = QColor("#00D4FF")
        
        for i, (date_str, seconds) in enumerate(self._data.items()):
            x = left_margin + i * (bar_width + gap) + gap / 2
            
            # Calculate bar height
            bar_height = (seconds / max_value) * chart_height if max_value > 0 else 0
            
            # Draw bar with gradient effect
            y = top_margin + chart_height - bar_height
            
            # Bar fill
            painter.fillRect(int(x), int(y), int(bar_width), int(bar_height), accent_color)
            
            # Bar glow effect
            glow_color = QColor(0, 212, 255, 50)
            painter.fillRect(int(x - 2), int(y), int(bar_width + 4), int(bar_height), glow_color)
        
        # Draw axis lines
        painter.setPen(QColor("#444444"))
        painter.drawLine(left_margin, top_margin + chart_height, 
                        width - right_margin, top_margin + chart_height)
        painter.drawLine(left_margin, top_margin, left_margin, top_margin + chart_height)
        
        # Draw Y-axis labels
        painter.setPen(QColor("#888888"))
        painter.setFont(QFont("Segoe UI", 8))
        
        # Max value label
        max_hours = max_value / 3600
        if max_hours >= 1:
            painter.drawText(5, top_margin + 15, f"{max_hours:.1f}h")
        else:
            max_mins = max_value / 60
            painter.drawText(5, top_margin + 15, f"{max_mins:.0f}m")
        
        # Zero label
        painter.drawText(5, top_margin + chart_height + 5, "0")


class CalendarHeatmapWidget(QWidget):
    """Calendar heatmap widget showing playtime intensity."""
    
    # Color levels based on playtime
    COLORS = {
        0: QColor("#1A1A1A"),      # No playtime
        1: QColor("#004455"),      # < 1 hour (dim)
        2: QColor("#0088AA"),      # 1-3 hours (medium)
        3: QColor("#00D4FF"),      # 3+ hours (bright)
    }
    
    def __init__(self, game_id: int, db, year: int, month: int, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.db = db
        self.year = year
        self.month = month
        self._data = {}
        self._load_data()
        self.setMinimumHeight(300)
    
    def _load_data(self):
        """Load calendar data for current month."""
        self._data = self.db.get_calendar_data(self.game_id, self.year, self.month)
        self.update()
    
    def update_month(self, year: int, month: int):
        """Update to a different month."""
        self.year = year
        self.month = month
        self._load_data()
    
    def paintEvent(self, event):
        """Paint the calendar heatmap."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Get calendar info
        cal = calendar.Calendar(firstweekday=6)  # Start with Sunday
        month_days = list(cal.itermonthdays(self.year, self.month))
        
        # Filter out zero days from previous/next months
        month_days = [d for d in month_days if d != 0]
        
        # Grid dimensions
        cols = 7  # Days of week
        rows = 6  # Max weeks in a month
        
        cell_width = (width - 20) // cols
        cell_height = (height - 40) // rows
        
        # Draw day headers
        day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        painter.setPen(QColor("#888888"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        
        for i, name in enumerate(day_names):
            x = i * cell_width + 10
            y = 15
            painter.drawText(int(x), int(y), name)
        
        # Draw calendar cells
        start_y = 35
        
        for week in range(rows):
            for day in range(cols):
                day_num = week * cols + day + 1
                
                if day_num > len(month_days):
                    continue
                
                actual_day = month_days[day_num - 1]
                
                x = day * cell_width + 10
                y = start_y + week * cell_height
                
                # Get playtime for this day
                playtime = self._data.get(actual_day, 0)
                
                # Determine color based on playtime intensity
                if playtime == 0:
                    color = self.COLORS[0]
                elif playtime < 3600:  # < 1 hour
                    color = self.COLORS[1]
                elif playtime < 10800:  # < 3 hours
                    color = self.COLORS[2]
                else:
                    color = self.COLORS[3]
                
                # Draw cell
                cell_rect = QRect(int(x), int(y), cell_width - 5, cell_height - 5)
                painter.fillRect(cell_rect, color)
                
                # Draw day number
                if color != self.COLORS[0]:
                    painter.setPen(QColor("#FFFFFF"))
                else:
                    painter.setPen(QColor("#666666"))
                
                painter.setFont(QFont("Segoe UI", 10))
                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, str(actual_day))
    
    def mousePressEvent(self, event):
        """Handle click on calendar day."""
        width = self.width()
        height = self.height()
        
        cell_width = (width - 20) // 7
        cell_height = (height - 40) // 6
        start_y = 35
        
        # Find which cell was clicked
        x = event.position().x()
        y = event.position().y()
        
        if y < 35:
            return  # Clicked on headers
        
        col = int((x - 10) / cell_width)
        row = int((y - start_y) / cell_height)
        
        if col < 0 or col > 6 or row < 0 or row > 5:
            return
        
        day_num = row * 7 + col + 1
        
        # Get actual day from calendar
        cal = calendar.Calendar(firstweekday=6)
        month_days = list(cal.itermonthdays(self.year, self.month))
        month_days = [d for d in month_days if d != 0]
        
        if day_num <= len(month_days):
            actual_day = month_days[day_num - 1]
            playtime = self._data.get(actual_day, 0)
            
            # Notify parent window
            if hasattr(self.parent(), 'show_sessions_for_day'):
                self.parent().show_sessions_for_day(actual_day, playtime)
