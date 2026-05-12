"""
Data models for the Velox Gaming Launcher.

These dataclasses represent the core entities in our application:
- Game: Represents a game/application added by the user
- Session: Represents a play session with start/end times and duration
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Game:
    """Represents a game or application tracked by the launcher."""
    id: Optional[int] = None
    name: str = ""
    exe_path: str = ""
    cover_image_path: Optional[str] = None
    date_added: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Computed fields (not stored in DB directly)
    total_playtime_seconds: int = 0
    last_played: Optional[str] = None
    
    @property
    def total_playtime_formatted(self) -> str:
        """Format total playtime as human-readable string (e.g., '47h 23m')."""
        hours = self.total_playtime_seconds // 3600
        minutes = (self.total_playtime_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    @property
    def last_played_formatted(self) -> str:
        """Format last played date as human-readable string."""
        if not self.last_played:
            return "Never"
        try:
            dt = datetime.fromisoformat(self.last_played)
            return dt.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            return self.last_played


@dataclass
class Session:
    """Represents a single play session for a game."""
    id: Optional[int] = None
    game_id: int = 0
    start_time: str = ""
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None
    
    @property
    def duration_formatted(self) -> str:
        """Format session duration as human-readable string."""
        if self.duration_seconds is None:
            return "In progress"
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    @property
    def start_time_formatted(self) -> str:
        """Format start time as human-readable string."""
        try:
            dt = datetime.fromisoformat(self.start_time)
            return dt.strftime("%I:%M %p")
        except (ValueError, TypeError):
            return self.start_time
    
    @property
    def end_time_formatted(self) -> str:
        """Format end time as human-readable string."""
        if not self.end_time:
            return "Now"
        try:
            dt = datetime.fromisoformat(self.end_time)
            return dt.strftime("%I:%M %p")
        except (ValueError, TypeError):
            return self.end_time
