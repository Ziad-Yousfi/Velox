"""
Data models for the Gaming Launcher.
Simple dataclasses representing database entities — no heavy ORM needed.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Game:
    """Represents a game/application in the launcher."""
    id: int = 0
    name: str = ""
    exe_path: str = ""
    cover_image_path: Optional[str] = None
    date_added: str = field(default_factory=lambda: datetime.now().isoformat())
    # Computed fields (populated by DB queries, not stored directly)
    total_playtime_seconds: int = 0
    last_played: Optional[str] = None


@dataclass
class Session:
    """Represents a single play session for a game."""
    id: int = 0
    game_id: int = 0
    start_time: str = ""
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None

    @property
    def duration_formatted(self) -> str:
        """Return human-readable duration string like '2h 15m'."""
        if self.duration_seconds is None or self.duration_seconds <= 0:
            return "0m"
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


def format_playtime(seconds: int) -> str:
    """Format total seconds into a readable playtime string."""
    if seconds <= 0:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_last_played(iso_string: Optional[str]) -> str:
    """Format an ISO datetime string into a readable 'last played' label."""
    if not iso_string:
        return "Never"
    try:
        dt = datetime.fromisoformat(iso_string)
        now = datetime.now()
        delta = now - dt
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        else:
            return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return "Unknown"
