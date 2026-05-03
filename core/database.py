"""
SQLite abstraction layer for the Gaming Launcher.
- Single connection with WAL mode for performance
- Thread-safe via threading.Lock
- Simple dict-based query cache to avoid redundant reads on UI repaints
"""

import sqlite3
import threading
import os
import time
from typing import Optional
from datetime import datetime, timedelta
from core.models import Game, Session


# Cache TTL in seconds — cached query results expire after this duration
_CACHE_TTL = 5.0


class Database:
    """Thread-safe SQLite database manager with query caching."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Store DB next to the script/exe
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base, "launcher.db")

        self._db_path = db_path
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, any]] = {}

        # Open connection with WAL mode for concurrent read performance
        self._conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row

        self._create_tables()

    def _create_tables(self):
        """Initialize the database schema if tables don't exist."""
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    exe_path TEXT NOT NULL,
                    cover_image_path TEXT,
                    date_added TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds INTEGER,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_game_id
                    ON sessions(game_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_start_time
                    ON sessions(start_time);
            """)
            self._conn.commit()

    # ── Cache helpers ──────────────────────────────────────────────────

    def _cache_get(self, key: str):
        """Return cached value if it exists and hasn't expired."""
        if key in self._cache:
            ts, value = self._cache[key]
            if time.time() - ts < _CACHE_TTL:
                return value
            del self._cache[key]
        return None

    def _cache_set(self, key: str, value):
        """Store a value in the cache with current timestamp."""
        self._cache[key] = (time.time(), value)

    def invalidate_cache(self, prefix: str = ""):
        """Clear cache entries matching a prefix, or all if empty."""
        if not prefix:
            self._cache.clear()
        else:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]

    # ── Game CRUD ──────────────────────────────────────────────────────

    def add_game(self, name: str, exe_path: str,
                 cover_image_path: Optional[str] = None) -> int:
        """Insert a new game and return its ID."""
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO games (name, exe_path, cover_image_path) "
                "VALUES (?, ?, ?)",
                (name, exe_path, cover_image_path)
            )
            self._conn.commit()
            self.invalidate_cache("games")
            return cursor.lastrowid

    def get_all_games(self) -> list[Game]:
        """Fetch all games with computed playtime and last-played data."""
        cached = self._cache_get("games:all")
        if cached is not None:
            return cached

        with self._lock:
            rows = self._conn.execute("""
                SELECT g.*,
                       COALESCE(SUM(s.duration_seconds), 0) AS total_playtime,
                       MAX(s.end_time) AS last_played
                FROM games g
                LEFT JOIN sessions s ON s.game_id = g.id
                    AND s.end_time IS NOT NULL
                GROUP BY g.id
                ORDER BY g.name COLLATE NOCASE
            """).fetchall()

        games = []
        for r in rows:
            games.append(Game(
                id=r["id"],
                name=r["name"],
                exe_path=r["exe_path"],
                cover_image_path=r["cover_image_path"],
                date_added=r["date_added"],
                total_playtime_seconds=r["total_playtime"] or 0,
                last_played=r["last_played"]
            ))

        self._cache_set("games:all", games)
        return games

    def get_game(self, game_id: int) -> Optional[Game]:
        """Fetch a single game by ID."""
        with self._lock:
            r = self._conn.execute("""
                SELECT g.*,
                       COALESCE(SUM(s.duration_seconds), 0) AS total_playtime,
                       MAX(s.end_time) AS last_played
                FROM games g
                LEFT JOIN sessions s ON s.game_id = g.id
                    AND s.end_time IS NOT NULL
                WHERE g.id = ?
                GROUP BY g.id
            """, (game_id,)).fetchone()

        if r is None:
            return None

        return Game(
            id=r["id"],
            name=r["name"],
            exe_path=r["exe_path"],
            cover_image_path=r["cover_image_path"],
            date_added=r["date_added"],
            total_playtime_seconds=r["total_playtime"] or 0,
            last_played=r["last_played"]
        )

    def update_game(self, game_id: int, **kwargs):
        """Update game fields by keyword arguments."""
        allowed = {"name", "exe_path", "cover_image_path"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [game_id]
        with self._lock:
            self._conn.execute(
                f"UPDATE games SET {set_clause} WHERE id = ?", values
            )
            self._conn.commit()
            self.invalidate_cache()

    def delete_game(self, game_id: int):
        """Delete a game and all its sessions."""
        with self._lock:
            self._conn.execute("DELETE FROM sessions WHERE game_id = ?",
                               (game_id,))
            self._conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
            self._conn.commit()
            self.invalidate_cache()

    # ── Session CRUD ───────────────────────────────────────────────────

    def start_session(self, game_id: int) -> int:
        """Create a new session with current start_time, return session ID."""
        now = datetime.now().isoformat()
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO sessions (game_id, start_time) VALUES (?, ?)",
                (game_id, now)
            )
            self._conn.commit()
            self.invalidate_cache()
            return cursor.lastrowid

    def end_session(self, session_id: int):
        """Mark a session as ended with calculated duration."""
        now = datetime.now()
        with self._lock:
            row = self._conn.execute(
                "SELECT start_time FROM sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if row is None:
                return

            start = datetime.fromisoformat(row["start_time"])
            duration = int((now - start).total_seconds())

            self._conn.execute(
                "UPDATE sessions SET end_time = ?, duration_seconds = ? "
                "WHERE id = ?",
                (now.isoformat(), duration, session_id)
            )
            self._conn.commit()
            self.invalidate_cache()

    def get_sessions(self, game_id: int,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> list[Session]:
        """Fetch sessions for a game, optionally filtered by date range."""
        query = ("SELECT * FROM sessions WHERE game_id = ? "
                 "AND end_time IS NOT NULL")
        params: list = [game_id]

        if start_date:
            query += " AND date(start_time) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(start_time) <= date(?)"
            params.append(end_date)

        query += " ORDER BY start_time DESC"

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()

        return [
            Session(
                id=r["id"],
                game_id=r["game_id"],
                start_time=r["start_time"],
                end_time=r["end_time"],
                duration_seconds=r["duration_seconds"]
            )
            for r in rows
        ]

    def get_daily_playtime(self, game_id: int,
                           start_date: str,
                           end_date: str) -> dict[str, int]:
        """
        Return {date_string: total_seconds} for each day in the range.
        Only includes days with actual playtime.
        """
        cache_key = f"daily:{game_id}:{start_date}:{end_date}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        with self._lock:
            rows = self._conn.execute("""
                SELECT date(start_time) AS play_date,
                       SUM(duration_seconds) AS total
                FROM sessions
                WHERE game_id = ?
                  AND end_time IS NOT NULL
                  AND date(start_time) >= date(?)
                  AND date(start_time) <= date(?)
                GROUP BY play_date
            """, (game_id, start_date, end_date)).fetchall()

        result = {r["play_date"]: r["total"] for r in rows}
        self._cache_set(cache_key, result)
        return result

    def get_total_playtime(self, game_id: int) -> int:
        """Return total playtime in seconds for a game."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(duration_seconds), 0) AS total "
                "FROM sessions WHERE game_id = ? AND end_time IS NOT NULL",
                (game_id,)
            ).fetchone()
        return row["total"] if row else 0

    # ── Cleanup ────────────────────────────────────────────────────────

    def close(self):
        """Close the database connection."""
        with self._lock:
            self._conn.close()
