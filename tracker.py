import time
import threading
from datetime import datetime
from typing import Callable, Optional
import storage

try:
    import win32gui
    import win32process
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


CATEGORY_RULES = {
    "code": [
        "visual studio code", "vs code", "vscode", "pycharm", "intellij",
        "sublime text", "atom", "vim", "neovim", "emacs", "notepad++",
        "android studio", "eclipse", "code", "terminal", "cmd", "powershell",
        "git bash", "windows powershell", "jupyter", "spyder", "idle",
        "github", "stackoverflow", "leetcode", "replit", "codepen", "figma",
    ],
    "video": [
        "youtube", "netflix", "vlc", "mpv", "windows media player", "movies & tv",
        "prime video", "disney+", "hulu", "twitch", "vimeo", "dailymotion",
        "media player", "video player", "mx player",
    ],
    "read": [
        "pdf", "adobe acrobat", "foxit", "sumatra", "okular", "evince",
        "kindle", "epub", "ebook", "notion", "obsidian", "onenote",
        "google docs", "word", "pages", "reader",
    ],
    "browse": [
        "chrome", "firefox", "edge", "opera", "brave", "safari",
        "internet explorer", "vivaldi", "arc",
    ],
    "social": [
        "twitter", "x.com", "instagram", "facebook", "whatsapp", "telegram",
        "discord", "slack", "linkedin", "reddit", "tiktok",
    ],
    "game": [
        "steam", "epic games", "origin", "battle.net", "minecraft",
        "game", "gaming",
    ],
}

IDLE_THRESHOLD = 300  # seconds — if same window for > this with no change, mark as idle


def classify_window(title: str, process_name: str = "") -> str:
    title_lower = title.lower()
    proc_lower = process_name.lower()
    combined = f"{title_lower} {proc_lower}"

    for category, keywords in CATEGORY_RULES.items():
        if any(kw in combined for kw in keywords):
            return category
    return "other"


def get_active_window_info() -> tuple[str, str]:
    """Returns (window_title, process_name)"""
    if not WIN32_AVAILABLE:
        return ("Simulation Mode - VS Code", "code.exe")
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            process_name = proc.name()
        except Exception:
            process_name = ""
        return (title, process_name)
    except Exception:
        return ("", "")


class ActivityTracker:
    def __init__(self, poll_interval: int = 5, on_update: Optional[Callable] = None):
        self.poll_interval = poll_interval
        self.on_update = on_update
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._current_title = ""
        self._current_type = "other"
        self._session_start: Optional[datetime] = None
        self._current_name = ""

        self.live_sessions: list = []
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._flush_current()

    def _loop(self):
        while self._running:
            try:
                title, process = get_active_window_info()
                if title and title != self._current_title:
                    self._flush_current()
                    self._current_title = title
                    self._current_type = classify_window(title, process)
                    self._current_name = title[:80]
                    self._session_start = datetime.now()
            except Exception:
                pass
            time.sleep(self.poll_interval)

    def _flush_current(self):
        if not self._session_start or not self._current_title:
            return
        duration_sec = (datetime.now() - self._session_start).total_seconds()
        duration_min = round(duration_sec / 60, 1)

        if duration_min < 0.3:
            return

        session = {
            "type": self._current_type,
            "name": self._current_name,
            "duration": round(duration_min),
            "duration_sec": round(duration_sec),
            "time": self._session_start.isoformat(),
            "end": datetime.now().isoformat(),
        }

        storage.save_session(session)

        with self._lock:
            self.live_sessions.append(session)

        if self.on_update:
            try:
                self.on_update(session)
            except Exception:
                pass

        self._session_start = None
        self._current_title = ""

    def get_current(self) -> dict:
        if not self._session_start:
            return {}
        elapsed = round((datetime.now() - self._session_start).total_seconds())
        return {
            "type": self._current_type,
            "name": self._current_name,
            "elapsed_sec": elapsed,
        }

    def get_live_sessions(self) -> list:
        with self._lock:
            return list(self.live_sessions)
