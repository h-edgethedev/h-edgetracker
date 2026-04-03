"""
H~EDGE Tracker CLI
Usage:
  python cli.py start          Start tracking in background
  python cli.py status         Show current session + today's stats
  python cli.py summary        AI daily summary
  python cli.py tips           AI productivity tips
  python cli.py balance        AI time balance analysis
  python cli.py history        Show past days
  python cli.py set-key KEY    Save Anthropic API key
  python cli.py stop           Stop tracker (if running as process)
"""

import sys
import time
import os
import storage
import ai
from tracker import ActivityTracker, get_active_window_info, classify_window
from datetime import datetime

COLORS = {
    "code":   "\033[94m",  # blue
    "video":  "\033[93m",  # yellow
    "read":   "\033[92m",  # green
    "browse": "\033[95m",  # magenta
    "social": "\033[91m",  # red
    "game":   "\033[96m",  # cyan
    "other":  "\033[90m",  # gray
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
}

ICONS = {
    "code": "💻", "video": "🎬", "read": "📖",
    "browse": "🌐", "social": "💬", "game": "🎮", "other": "📝",
}


def color(text, *keys):
    prefix = "".join(COLORS.get(k, "") for k in keys)
    return f"{prefix}{text}{COLORS['reset']}"


def fmt_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}m"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m"


def print_header():
    print(color("\n  H~EDGE Tracker", "bold"))
    print(color("  ─────────────────────────────", "dim"))


def cmd_status():
    print_header()
    sessions = storage.load_today()
    total = storage.total_minutes_today()
    by_type = storage.sessions_by_type(sessions)

    print(f"\n  {color('Today — ' + datetime.now().strftime('%A, %d %B'), 'bold')}")
    print(f"  Total tracked: {color(fmt_duration(total), 'bold')}")
    print(f"  Sessions: {len(sessions)}\n")

    if by_type:
        print(color("  Breakdown:", "bold"))
        for t, mins in sorted(by_type.items(), key=lambda x: -x[1]):
            icon = ICONS.get(t, "📝")
            bar_len = min(20, int(mins / max(total, 1) * 20))
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"  {icon} {t:<8} {color(bar, t)} {fmt_duration(mins)}")

    print()
    if sessions:
        print(color("  Recent sessions:", "bold"))
        for s in sessions[-5:][::-1]:
            icon = ICONS.get(s["type"], "📝")
            t = datetime.fromisoformat(s["time"]).strftime("%H:%M")
            print(f"  {icon} {color(s['name'][:45], 'dim')} — {fmt_duration(s['duration'])} @ {t}")
    print()


def cmd_history():
    print_header()
    dates = storage.all_dates()
    if not dates:
        print("\n  No history yet.\n")
        return
    print(f"\n  {color('Activity history', 'bold')}\n")
    for d in dates[:7]:
        sessions = storage.load_date(d)
        total = sum(s.get("duration", 0) for s in sessions)
        by_type = storage.sessions_by_type(sessions)
        top = max(by_type, key=by_type.get) if by_type else "—"
        icon = ICONS.get(top, "📝")
        print(f"  {d}  {icon} {fmt_duration(total)}  ({len(sessions)} sessions)")
    print()


def cmd_summary():
    print_header()
    print(f"\n  {color('Fetching AI summary...', 'dim')}\n")
    result = ai.daily_summary()
    print(f"  {result}\n")


def cmd_tips():
    print_header()
    print(f"\n  {color('Generating productivity tips...', 'dim')}\n")
    result = ai.productivity_tips()
    print(f"  {result}\n")


def cmd_balance():
    print_header()
    print(f"\n  {color('Analyzing time balance...', 'dim')}\n")
    result = ai.time_balance()
    print(f"  {result}\n")


def cmd_start():
    print_header()
    print(f"\n  {color('Tracker started. Monitoring active windows...', 'bold')}")
    print(f"  {color('Press Ctrl+C to stop.', 'dim')}\n")

    def on_update(session):
        icon = ICONS.get(session["type"], "📝")
        name = session["name"][:50]
        dur = fmt_duration(session["duration"])
        t = datetime.fromisoformat(session["time"]).strftime("%H:%M")
        print(f"  {icon} {color(name, 'dim')} — {dur} @ {t}")

    tracker = ActivityTracker(poll_interval=5, on_update=on_update)
    tracker.start()

    try:
        while True:
            cur = tracker.get_current()
            if cur:
                elapsed = cur["elapsed_sec"]
                icon = ICONS.get(cur["type"], "📝")
                m, s = divmod(elapsed, 60)
                print(f"\r  {color('NOW:', 'bold')} {icon} {cur['name'][:40]} ({m}m {s}s)    ", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        tracker.stop()
        print(f"\n\n  {color('Tracker stopped. Run `python cli.py status` to see your stats.', 'dim')}\n")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0].lower()
    if cmd == "start":
        cmd_start()
    elif cmd == "status":
        cmd_status()
    elif cmd == "summary":
        cmd_summary()
    elif cmd == "tips":
        cmd_tips()
    elif cmd == "balance":
        cmd_balance()
    elif cmd == "history":
        cmd_history()
    elif cmd == "set-key" and len(args) > 1:
        ai.set_api_key(args[1])
    elif cmd == "set-key":
        print("  Usage: python cli.py set-key YOUR_ANTHROPIC_API_KEY")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
