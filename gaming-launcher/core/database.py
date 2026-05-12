"""
SQLite database abstraction layer for Velox Gaming Launcher.

This module handles all database operations with the following optimizations:
- Single connection with WAL mode for better concurrent access
- Query caching to avoid redundant database hits
- Efficient indexing for common queries
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import threading


class Database:
    """Singleton database manager for Velox."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "launcher.db"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._db_path = db_path
                cls._instance._conn = None
                cls._instance._cache = {}
                cls._instance._cache_timestamps = {}
                cls._instance._cache_ttl = 5.0  # Cache TTL in seconds
            return cls._instance
    
    def _init_db(self):
        """Initialize database connection and create tables."""
        if self._initialized:
            return
        
        # Create directory if it doesn't exist
        db_dir = Path(self._db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Create connection with optimized settings
        self._conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            isolation_level=None  # Autocommit mode
        )
        
        # Enable WAL mode for better concurrent access
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-2000")  # 2MB cache
        self._conn.execute("PRAGMA temp_store=MEMORY")
        
        # Create tables
        self._create_tables()
        self._initialized = True
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self._conn.cursor()
        
        # Games table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                exe_path TEXT NOT NULL,
                cover_image_path TEXT,
                date_added TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds INTEGER,
                FOREIGN KEY (game_id) REFERENCES games(id)
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_game_id 
            ON sessions(game_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_start_time 
            ON sessions(start_time)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_game_time 
            ON sessions(game_id, start_time)
        """)
        
        self._conn.commit()
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection, initializing if necessary."""
        if not self._initialized:
            self._init_db()
        return self._conn
    
    def _invalidate_cache(self, prefix: str):
        """Invalidate cache entries matching a prefix."""
        keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._cache[key]
            del self._cache_timestamps[key]
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            age = datetime.now().timestamp() - self._cache_timestamps.get(key, 0)
            if age < self._cache_ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
        return None
    
    def _set_cached(self, key: str, value: Any):
        """Set value in cache with current timestamp."""
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.now().timestamp()
    
    # ==================== Game Operations ====================
    
    def add_game(self, name: str, exe_path: str, cover_image_path: Optional[str] = None) -> int:
        """Add a new game to the database. Returns the game ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO games (name, exe_path, cover_image_path)
            VALUES (?, ?, ?)
        """, (name, exe_path, cover_image_path))
        self.conn.commit()
        
        game_id = cursor.lastrowid
        self._invalidate_cache(f"games:{game_id}")
        self._invalidate_cache("all_games")
        return game_id
    
    def get_game(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get a single game by ID with cached total playtime."""
        cache_key = f"games:{game_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT g.id, g.name, g.exe_path, g.cover_image_path, g.date_added,
                   COALESCE(SUM(s.duration_seconds), 0) as total_playtime,
                   MAX(s.end_time) as last_played
            FROM games g
            LEFT JOIN sessions s ON g.id = s.game_id AND s.end_time IS NOT NULL
            WHERE g.id = ?
            GROUP BY g.id
        """, (game_id,))
        
        row = cursor.fetchone()
        if row:
            result = {
                'id': row[0],
                'name': row[1],
                'exe_path': row[2],
                'cover_image_path': row[3],
                'date_added': row[4],
                'total_playtime_seconds': row[5] or 0,
                'last_played': row[6]
            }
            self._set_cached(cache_key, result)
            return result
        return None
    
    def get_all_games(self) -> List[Dict[str, Any]]:
        """Get all games with their total playtime."""
        cached = self._get_cached("all_games")
        if cached:
            return cached
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT g.id, g.name, g.exe_path, g.cover_image_path, g.date_added,
                   COALESCE(SUM(s.duration_seconds), 0) as total_playtime,
                   MAX(s.end_time) as last_played
            FROM games g
            LEFT JOIN sessions s ON g.id = s.game_id AND s.end_time IS NOT NULL
            GROUP BY g.id
            ORDER BY g.name COLLATE NOCASE
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'name': row[1],
                'exe_path': row[2],
                'cover_image_path': row[3],
                'date_added': row[4],
                'total_playtime_seconds': row[5] or 0,
                'last_played': row[6]
            })
        
        self._set_cached("all_games", results)
        return results
    
    def update_game_cover(self, game_id: int, cover_path: str):
        """Update the cover image path for a game."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE games SET cover_image_path = ? WHERE id = ?
        """, (cover_path, game_id))
        self.conn.commit()
        self._invalidate_cache(f"games:{game_id}")
        self._invalidate_cache("all_games")
    
    def delete_game(self, game_id: int):
        """Delete a game and all its sessions."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE game_id = ?", (game_id,))
        cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
        self.conn.commit()
        self._invalidate_cache(f"games:{game_id}")
        self._invalidate_cache("all_games")
    
    # ==================== Session Operations ====================
    
    def start_session(self, game_id: int) -> int:
        """Start a new session for a game. Returns session ID."""
        cursor = self.conn.cursor()
        start_time = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO sessions (game_id, start_time)
            VALUES (?, ?)
        """, (game_id, start_time))
        self.conn.commit()
        
        session_id = cursor.lastrowid
        self._invalidate_cache(f"sessions:game:{game_id}")
        self._invalidate_cache("all_games")
        return session_id
    
    def end_session(self, session_id: int):
        """End a session and calculate duration."""
        cursor = self.conn.cursor()
        end_time = datetime.now().isoformat()
        
        # Get start time
        cursor.execute("SELECT start_time, game_id FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if not row:
            return
        
        start_time = row[0]
        game_id = row[1]
        
        # Calculate duration
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        duration_seconds = int((end_dt - start_dt).total_seconds())
        
        # Update session
        cursor.execute("""
            UPDATE sessions 
            SET end_time = ?, duration_seconds = ?
            WHERE id = ?
        """, (end_time, duration_seconds, session_id))
        self.conn.commit()
        
        self._invalidate_cache(f"sessions:game:{game_id}")
        self._invalidate_cache("all_games")
    
    def get_active_session(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get active (unfinished) session for a game, if any."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, game_id, start_time, end_time, duration_seconds
            FROM sessions
            WHERE game_id = ? AND end_time IS NULL
            ORDER BY start_time DESC
            LIMIT 1
        """, (game_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'game_id': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'duration_seconds': row[4]
            }
        return None
    
    def get_sessions_for_game(self, game_id: int, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get all completed sessions for a game, optionally filtered by date range."""
        cache_key = f"sessions:game:{game_id}:{start_date}:{end_date}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        cursor = self.conn.cursor()
        
        if start_date and end_date:
            cursor.execute("""
                SELECT id, game_id, start_time, end_time, duration_seconds
                FROM sessions
                WHERE game_id = ? 
                  AND end_time IS NOT NULL
                  AND DATE(start_time) >= DATE(?)
                  AND DATE(start_time) <= DATE(?)
                ORDER BY start_time DESC
            """, (game_id, start_date.isoformat(), end_date.isoformat()))
        else:
            cursor.execute("""
                SELECT id, game_id, start_time, end_time, duration_seconds
                FROM sessions
                WHERE game_id = ? AND end_time IS NOT NULL
                ORDER BY start_time DESC
            """, (game_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'game_id': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'duration_seconds': row[4]
            })
        
        self._set_cached(cache_key, results)
        return results
    
    def get_daily_playtime(self, game_id: int, days: int = 30) -> Dict[str, int]:
        """Get total playtime per day for the last N days."""
        cache_key = f"daily_playtime:{game_id}:{days}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        cursor = self.conn.cursor()
        
        # Get sessions for the date range
        end_date = datetime.now()
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        start_date = start_date - timedelta(days=days)
        
        cursor.execute("""
            SELECT DATE(start_time) as date, SUM(duration_seconds) as total
            FROM sessions
            WHERE game_id = ?
              AND end_time IS NOT NULL
              AND DATE(start_time) >= DATE(?)
              AND DATE(start_time) <= DATE(?)
            GROUP BY DATE(start_time)
            ORDER BY date
        """, (game_id, start_date.isoformat(), end_date.isoformat()))
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = row[1] or 0
        
        self._set_cached(cache_key, results)
        return results
    
    def get_calendar_data(self, game_id: int, year: int, month: int) -> Dict[int, int]:
        """Get playtime data for calendar heatmap (day of month -> seconds played)."""
        cache_key = f"calendar:{game_id}:{year}:{month}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        cursor = self.conn.cursor()
        
        from datetime import datetime
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            from datetime import timedelta
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        cursor.execute("""
            SELECT CAST(strftime('%d', start_time) AS INTEGER) as day, 
                   SUM(duration_seconds) as total
            FROM sessions
            WHERE game_id = ?
              AND end_time IS NOT NULL
              AND strftime('%Y-%m', start_time) = ?
            GROUP BY day
        """, (game_id, f"{year}-{month:02d}"))
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = row[1] or 0
        
        self._set_cached(cache_key, results)
        return results
    
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._initialized = False
