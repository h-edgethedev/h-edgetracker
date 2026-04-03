import os
import json
import urllib.request
import urllib.error
import storage


API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        cfg_path = storage.DATA_DIR / "config.json"
        if cfg_path.exists():
            with open(cfg_path) as f:
                key = json.load(f).get("api_key", "")
    return key


def _call_claude(prompt: str, system: str = "") -> str:
    api_key = _get_api_key()
    if not api_key:
        return (
            "No API key found. Set ANTHROPIC_API_KEY environment variable "
            "or run: python cli.py set-key YOUR_KEY"
        )

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 1000,
        "system": system or "You are a personal productivity coach. Be concise, warm, and direct. No markdown bullets — write in flowing paragraphs.",
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"API error {e.code}: {body}"
    except Exception as e:
        return f"Error: {e}"


def _format_sessions(sessions: list) -> str:
    if not sessions:
        return "No sessions recorded."
    lines = []
    for s in sessions:
        lines.append(f"- {s['type'].upper()}: \"{s['name']}\" for {s['duration']} min")
    total = sum(s.get("duration", 0) for s in sessions)
    lines.append(f"\nTotal: {total} minutes")
    return "\n".join(lines)


def daily_summary(date_str: str = None) -> str:
    sessions = storage.load_today() if not date_str else storage.load_date(date_str)
    if not sessions:
        return "No activity recorded for this day yet."
    formatted = _format_sessions(sessions)
    prompt = f"Here are my laptop activities for today:\n{formatted}\n\nGive me a warm, honest daily summary of what I accomplished. Keep it under 120 words."
    return _call_claude(prompt)


def productivity_tips(date_str: str = None) -> str:
    sessions = storage.load_today() if not date_str else storage.load_date(date_str)
    if not sessions:
        return "No activity recorded yet — start tracking to get personalized tips."
    formatted = _format_sessions(sessions)
    prompt = f"Here are my laptop activities today:\n{formatted}\n\nGive me 3 specific, actionable tips to help me use my time better tomorrow. Be direct and practical, no generic advice."
    return _call_claude(prompt)


def time_balance(date_str: str = None) -> str:
    sessions = storage.load_today() if not date_str else storage.load_date(date_str)
    if not sessions:
        return "No activity recorded yet."
    formatted = _format_sessions(sessions)
    prompt = f"Here are my laptop activities today:\n{formatted}\n\nAnalyze my time balance — am I spending too much time on entertainment vs productive work? Give a short honest assessment and one concrete recommendation."
    return _call_claude(prompt)


def set_api_key(key: str):
    storage.ensure_dir()
    cfg_path = storage.DATA_DIR / "config.json"
    cfg = {}
    if cfg_path.exists():
        with open(cfg_path) as f:
            cfg = json.load(f)
    cfg["api_key"] = key
    with open(cfg_path, "w") as f:
        json.dump(cfg, f)
    print(f"API key saved to {cfg_path}")
