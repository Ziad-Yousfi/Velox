"""
Process tracking engine for Velox Gaming Launcher.

This module handles lightweight process monitoring with the following optimizations:
- Polling every 5 seconds (not every frame) to minimize CPU usage
- Background thread that never blocks the UI
- System tray support for tracking when launcher is minimized/closed
- Memory footprint under 15 MB when running in tray mode
"""

import subprocess
import sys
import time
import threading
from typing import Optional, Callable, Dict
from datetime import datetime
import os


class ProcessTracker:
    """
    Lightweight process tracker that monitors game processes.
    
    Uses polling every 5 seconds instead of continuous monitoring
    to minimize CPU and memory usage.
    """
    
    def __init__(self):
        self._processes: Dict[int, dict] = {}  # pid -> {game_id, session_id, start_time}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._poll_interval = 5.0  # seconds between polls
        self._on_session_end_callbacks: list[Callable] = []
        
        # Track processes we've spawned
        self._spawned_pids: Dict[int, int] = {}  # pid -> game_id
        self._process_objects: Dict[int, subprocess.Popen] = {}  # pid -> Popen object
    
    def add_session_end_callback(self, callback: Callable[[int, int], None]):
        """Add a callback to be called when a session ends."""
        self._on_session_end_callbacks.append(callback)
    
    @staticmethod
    def _is_win32_process_running(pid: int) -> bool:
        """Check if a Windows process is running without spawning a console window."""
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            SYNCHRONIZE = 0x00100000
            WAIT_TIMEOUT = 0x102
            ERROR_ACCESS_DENIED = 5

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
            if not handle:
                # If access is denied, the process exists and is running
                return kernel32.GetLastError() == ERROR_ACCESS_DENIED

            try:
                wait_result = kernel32.WaitForSingleObject(handle, 0)
                return wait_result == WAIT_TIMEOUT
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            # Fallback to tasklist with CREATE_NO_WINDOW so no console window flashes
            try:
                creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=creationflags
                )
                return str(pid) in result.stdout
            except Exception:
                return False

    @staticmethod
    def _find_pids_by_exe(exe_path: str) -> list[int]:
        """Find all running PIDs matching the executable name."""
        try:
            import ctypes
            from ctypes import wintypes

            exe_name = os.path.basename(exe_path).lower()
            pids = []

            TH32CS_SNAPPROCESS = 0x00000002
            class PROCESSENTRY32W(ctypes.Structure):
                _fields_ = [
                    ('dwSize', wintypes.DWORD),
                    ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long),
                    ('dwFlags', wintypes.DWORD),
                    ('szExeFile', ctypes.c_wchar * 260)
                ]

            kernel32 = ctypes.windll.kernel32
            snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if snap == -1 or not snap:
                return pids

            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)

            try:
                if kernel32.Process32FirstW(snap, ctypes.byref(entry)):
                    while True:
                        if entry.szExeFile.lower() == exe_name:
                            pids.append(entry.th32ProcessID)
                        if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                            break
            finally:
                kernel32.CloseHandle(snap)

            return pids
        except Exception:
            return []

    @staticmethod
    def _find_child_pids(parent_pid: int) -> list[int]:
        """Find active child PIDs of a given parent PID."""
        try:
            import ctypes
            from ctypes import wintypes

            TH32CS_SNAPPROCESS = 0x00000002
            class PROCESSENTRY32W(ctypes.Structure):
                _fields_ = [
                    ('dwSize', wintypes.DWORD),
                    ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long),
                    ('dwFlags', wintypes.DWORD),
                    ('szExeFile', ctypes.c_wchar * 260)
                ]

            kernel32 = ctypes.windll.kernel32
            snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if snap == -1 or not snap:
                return []

            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            children = []

            try:
                if kernel32.Process32FirstW(snap, ctypes.byref(entry)):
                    while True:
                        if entry.th32ParentProcessID == parent_pid:
                            children.append(entry.th32ProcessID)
                        if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                            break
            finally:
                kernel32.CloseHandle(snap)

            return children
        except Exception:
            return []

    def _launch_win32_elevated(self, exe_path: str, exe_dir: str, game_id: int, verb: str = "runas") -> Optional[int]:
        """Launch an executable or shortcut via ShellExecuteExW with UAC elevation support."""
        try:
            import ctypes
            from ctypes import wintypes

            SEE_MASK_NOCLOSEPROCESS = 0x00000040
            SW_SHOWNORMAL = 1

            class SHELLEXECUTEINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('fMask', wintypes.ULONG),
                    ('hwnd', wintypes.HWND),
                    ('lpVerb', wintypes.LPCWSTR),
                    ('lpFile', wintypes.LPCWSTR),
                    ('lpParameters', wintypes.LPCWSTR),
                    ('lpDirectory', wintypes.LPCWSTR),
                    ('nShow', ctypes.c_int),
                    ('hInstApp', wintypes.HINSTANCE),
                    ('lpIDList', wintypes.LPVOID),
                    ('lpClass', wintypes.LPCWSTR),
                    ('hkeyClass', wintypes.HKEY),
                    ('dwHotKey', wintypes.DWORD),
                    ('hIconOrMonitor', wintypes.HANDLE),
                    ('hProcess', wintypes.HANDLE)
                ]

            existing_pids = set(self._find_pids_by_exe(exe_path))

            sei = SHELLEXECUTEINFO()
            sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
            sei.fMask = SEE_MASK_NOCLOSEPROCESS
            sei.lpVerb = verb
            sei.lpFile = exe_path
            sei.lpDirectory = exe_dir or None
            sei.nShow = SW_SHOWNORMAL

            res = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
            if not res:
                err = ctypes.windll.kernel32.GetLastError()
                print(f"ShellExecuteEx failed with error code: {err}")
                return None

            pid = None
            if sei.hProcess:
                pid = ctypes.windll.kernel32.GetProcessId(sei.hProcess)

            if not pid:
                # Wait briefly for process to register if handle was cross-integrity
                for _ in range(25):
                    time.sleep(0.1)
                    current_pids = set(self._find_pids_by_exe(exe_path))
                    new_pids = current_pids - existing_pids
                    if new_pids:
                        pid = next(iter(new_pids))
                        break
                    elif current_pids:
                        pid = next(iter(current_pids))
                        break

            if pid:
                self._spawned_pids[pid] = game_id
                return pid

            return None
        except Exception as e:
            print(f"Error in _launch_win32_elevated: {e}")
            return None

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is still running."""
        # 1. If we hold the Popen object, checking poll() is instantaneous and requires no subprocess
        proc = self._process_objects.get(pid)
        if proc is not None:
            if proc.poll() is not None:
                self._process_objects.pop(pid, None)
                return False
            return True

        # 2. Otherwise check OS-level process existence
        try:
            if sys.platform == 'win32':
                return self._is_win32_process_running(pid)
            else:
                # Unix-like: use kill -0
                os.kill(pid, 0)
                return True
        except (OSError, ProcessLookupError):
            return False
    
    def _tracking_loop(self):
        """Main tracking loop that runs in background thread."""
        while self._running:
            pids_to_check = list(self._spawned_pids.keys())
            
            for pid in pids_to_check:
                if not self._is_process_running(pid):
                    # Check if process launched child processes (e.g. game launcher wrapper)
                    child_pids = self._find_child_pids(pid) if sys.platform == 'win32' else []
                    active_child = None
                    for c_pid in child_pids:
                        if self._is_process_running(c_pid):
                            active_child = c_pid
                            break

                    if active_child:
                        # Continue tracking the child game process instead of ending session
                        game_id = self._spawned_pids.pop(pid)
                        self._process_objects.pop(pid, None)
                        self._spawned_pids[active_child] = game_id
                        continue

                    # Process has ended
                    self._process_objects.pop(pid, None)
                    game_id = self._spawned_pids.pop(pid, None)
                    if game_id:
                        # Notify callbacks
                        for callback in self._on_session_end_callbacks:
                            try:
                                callback(game_id, pid)
                            except Exception as e:
                                print(f"Error in session end callback: {e}")
            
            # Sleep for poll interval
            time.sleep(self._poll_interval)
    
    def start_tracking(self):
        """Start the background tracking thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
    
    def stop_tracking(self):
        """Stop the background tracking thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
    
    def launch_and_track(self, exe_path: str, game_id: int) -> Optional[int]:
        """
        Launch a game executable and start tracking it.
        
        Returns the PID of the launched process, or None if launch failed.
        """
        try:
            exe_path = exe_path.strip('\"\'')
            exe_path = os.path.abspath(exe_path)
            if not os.path.exists(exe_path):
                print(f"Executable not found: {exe_path}")
                return None

            exe_dir = os.path.dirname(exe_path)
            is_shortcut = exe_path.lower().endswith('.lnk')
            
            # Launch the process detached from parent
            if sys.platform == 'win32':
                if not is_shortcut:
                    try:
                        # Use CREATE_NEW_PROCESS_GROUP without DETACHED_PROCESS to preserve proper GUI & stdio
                        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
                        process = subprocess.Popen(
                            [exe_path],
                            cwd=exe_dir,
                            creationflags=creationflags
                        )
                        pid = process.pid
                        self._spawned_pids[pid] = game_id
                        self._process_objects[pid] = process
                        return pid
                    except OSError as e:
                        # WinError 740: ERROR_ELEVATION_REQUIRED or PermissionError (access denied)
                        if getattr(e, 'winerror', None) == 740 or e.errno == 13:
                            print(f"Elevation required for {exe_path}, requesting via UAC ShellExecute...")
                            return self._launch_win32_elevated(exe_path, exe_dir, game_id, verb="runas")
                        raise
                else:
                    return self._launch_win32_elevated(exe_path, exe_dir, game_id, verb="open")
            else:
                # Unix-like: use preexec_fn to detach
                process = subprocess.Popen(
                    [exe_path],
                    cwd=exe_dir,
                    preexec_fn=os.setsid
                )
                pid = process.pid
                self._spawned_pids[pid] = game_id
                self._process_objects[pid] = process
                return pid
            
        except Exception as e:
            print(f"Failed to launch {exe_path}: {e}")
            return None
    
    def get_tracked_games(self) -> Dict[int, int]:
        """Get a copy of currently tracked games (pid -> game_id)."""
        return dict(self._spawned_pids)
    
    def is_tracking_game(self, game_id: int) -> bool:
        """Check if a specific game is currently being tracked."""
        return game_id in self._spawned_pids.values()


# Singleton instance for global access
_tracker_instance: Optional[ProcessTracker] = None


def get_tracker() -> ProcessTracker:
    """Get the global ProcessTracker singleton."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ProcessTracker()
    return _tracker_instance


def reset_tracker():
    """Reset the tracker singleton (useful for testing)."""
    global _tracker_instance
    if _tracker_instance:
        _tracker_instance.stop_tracking()
    _tracker_instance = None


class TrayTracker:
    """
    Minimal system tray application for tracking games when launcher is closed.
    
    This runs as a separate minimal process with ~5-15 MB RAM footprint.
    """
    
    def __init__(self, db_path: str = "launcher.db"):
        self.db_path = db_path
        self.tracker = ProcessTracker()
        self.running = False
        
    def run(self):
        """Run the tray tracker."""
        from core.database import Database
        
        db = Database(self.db_path)
        
        # Check for any active sessions that need to be continued
        # (This would happen if launcher crashed while game was running)
        
        # Set up session end callback
        def on_session_end(game_id: int, pid: int):
            # End the session in database
            active_session = db.get_active_session(game_id)
            if active_session:
                db.end_session(active_session['id'])
            print(f"Session ended for game {game_id}")
        
        self.tracker.add_session_end_callback(on_session_end)
        
        # Start tracking
        self.tracker.start_tracking()
        self.running = True
        
        # Keep running until signaled to stop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.tracker.stop_tracking()
            db.close()
    
    def stop(self):
        """Stop the tray tracker."""
        self.running = False


if __name__ == "__main__":
    # Run as standalone tray tracker
    import argparse
    
    parser = argparse.ArgumentParser(description='Velox Tray Tracker')
    parser.add_argument('--db', default='launcher.db', help='Path to database file')
    args = parser.parse_args()
    
    tray = TrayTracker(args.db)
    tray.run()
