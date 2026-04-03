import json
import os
from datetime import datetime, date
from pathlib import Path

DATA_DIR = Path.home() / ".hedgetracker"
DATA_FILE = DATA_DIR / "activities.json"


def ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def load_all() -> dict:
    ensure_dir()
    if not DATA_FILE.exists():
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_all(data: dict):
    ensure_dir()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def today_key() -> str:
    return date.today().isoformat()


def load_today() -> list:
    return load_all().get(today_key(), [])


def save_session(session: dict):
    data = load_all()
    key = today_key()
    if key not in data:
        data[key] = []
    data[key].append(session)
    save_all(data)


def load_date(date_str: str) -> list:
    return load_all().get(date_str, [])


def all_dates() -> list:
    return sorted(load_all().keys(), reverse=True)


def total_minutes_today() -> int:
    return sum(s.get("duration", 0) for s in load_today())


def sessions_by_type(sessions: list) -> dict:
    result = {}
    for s in sessions:
        t = s.get("type", "other")
        result[t] = result.get(t, 0) + s.get("duration", 0)
    return result
