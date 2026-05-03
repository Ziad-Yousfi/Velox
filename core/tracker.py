"""
Process tracking engine for the Gaming Launcher.
- Launches game executables via subprocess
- Polls process status every 5 seconds using a QTimer (no dedicated thread needed)
- Records sessions in SQLite when a game exits
- Minimal CPU usage: timer only ticks while at least one game is being tracked
"""

import os
import subprocess
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.database import Database
from core.models import Game


class GameTracker(QObject):
    """
    Lightweight game process tracker.
    Uses QTimer (5s interval) on the main event loop — no extra threads.
    Timer auto-stops when nothing is being tracked.
    """

    # Signals emitted for UI updates
    session_started = pyqtSignal(int, int)      # game_id, session_id
    session_ended = pyqtSignal(int, int, int)    # game_id, session_id, duration_seconds

    def __init__(self, database: Database, parent=None):
        super().__init__(parent)
        self._db = database

        # Active tracking map: game_id → tracking info dict
        self._active: dict[int, dict] = {}

        # Polling timer — 5 second interval, only runs when needed
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self._poll_processes)

    # ── Public API ─────────────────────────────────────────────────────

    def launch_game(self, game: Game) -> bool:
        """
        Launch a game's executable and start tracking its session.
        Returns True if launched successfully, False otherwise.
        """
        if game.id in self._active:
            return False  # Already tracking this game

        # Verify the executable exists
        if not os.path.isfile(game.exe_path):
            return False

        try:
            # Launch the game process in its own directory
            working_dir = os.path.dirname(game.exe_path)
            import sys
            if sys.platform == "win32":
                # Windows: detach from launcher's console
                process = subprocess.Popen(
                    [game.exe_path],
                    cwd=working_dir if working_dir else None,
                    creationflags=subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            elif sys.platform == "darwin":
                # macOS: use 'open' command for .app bundles
                if game.exe_path.endswith(".app"):
                    process = subprocess.Popen(
                        ["open", "-a", game.exe_path],
                        cwd=working_dir if working_dir else None,
                    )
                else:
                    process = subprocess.Popen(
                        [game.exe_path],
                        cwd=working_dir if working_dir else None,
                        start_new_session=True,
                    )
            else:
                # Linux / other: start in new session to detach
                process = subprocess.Popen(
                    [game.exe_path],
                    cwd=working_dir if working_dir else None,
                    start_new_session=True,
                )
        except (OSError, PermissionError, FileNotFoundError) as e:
            print(f"[Tracker] Failed to launch {game.exe_path}: {e}")
            return False

        # Record session start in database
        session_id = self._db.start_session(game.id)

        self._active[game.id] = {
            "process": process,
            "pid": process.pid,
            "session_id": session_id,
            "start_time": datetime.now(),
            "game_name": game.name,
        }

        # Start polling if not already active
        if not self._timer.isActive():
            self._timer.start()

        self.session_started.emit(game.id, session_id)
        print(f"[Tracker] Started tracking '{game.name}' (PID {process.pid})")
        return True

    def stop_tracking(self, game_id: int):
        """Manually stop tracking a game (e.g. user clicks Stop button)."""
        if game_id not in self._active:
            return

        info = self._active[game_id]
        self._finalize_session(game_id, info)

        # Try to terminate the process gracefully
        try:
            info["process"].terminate()
        except OSError:
            pass

    def is_tracking(self, game_id: int) -> bool:
        """Check if a game is currently being tracked."""
        return game_id in self._active

    def has_active_sessions(self) -> bool:
        """Check if any games are currently being tracked."""
        return len(self._active) > 0

    def get_active_game_ids(self) -> list[int]:
        """Return list of game IDs currently being tracked."""
        return list(self._active.keys())

    def stop_all(self):
        """End all active tracking sessions (called on app exit)."""
        for game_id in list(self._active.keys()):
            info = self._active[game_id]
            self._finalize_session(game_id, info)
        self._active.clear()
        self._timer.stop()

    # ── Internal polling ───────────────────────────────────────────────

    def _poll_processes(self):
        """
        Called every 5 seconds by QTimer.
        Check each tracked process — if it has exited, finalize its session.
        """
        finished = []

        for game_id, info in self._active.items():
            process = info["process"]
            retcode = process.poll()

            if retcode is not None:
                # Process has exited
                finished.append(game_id)

        # Finalize all finished sessions
        for game_id in finished:
            info = self._active.pop(game_id)
            self._finalize_session(game_id, info)

        # Stop timer if nothing left to track (saves CPU)
        if not self._active:
            self._timer.stop()
            print("[Tracker] All processes exited — polling stopped.")

    def _finalize_session(self, game_id: int, info: dict):
        """Calculate duration, update DB, emit signal."""
        start = info["start_time"]
        duration = int((datetime.now() - start).total_seconds())

        # Ensure at least 1 second of playtime is recorded
        duration = max(duration, 1)

        self._db.end_session(info["session_id"])
        self.session_ended.emit(game_id, info["session_id"], duration)

        print(
            f"[Tracker] Session ended for '{info['game_name']}' "
            f"— {duration}s played"
        )
