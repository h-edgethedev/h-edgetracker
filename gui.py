import flet as ft
import threading
import time
from datetime import datetime
import storage
import ai
from tracker import ActivityTracker

TYPE_COLORS = {
    "code":   "#4A9EE0",
    "video":  "#E0A84A",
    "read":   "#5CB85C",
    "browse": "#9B7FE0",
    "social": "#E07FA0",
    "game":   "#4AE0C0",
    "other":  "#888888",
}

EMOJI = {
    "code": "💻", "video": "🎬", "read": "📖",
    "browse": "🌐", "social": "💬", "game": "🎮", "other": "📝",
}


def fmt_dur(minutes):
    if minutes < 60:
        return f"{minutes}m"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m"


def fmt_elapsed(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def main(page: ft.Page):
    page.title = "H~EDGE Tracker"
    page.window_width = 940
    page.window_height = 700
    page.window_min_width = 700
    page.window_min_height = 500
    page.bgcolor = "#111111"
    page.padding = 0

    tracker = ActivityTracker(poll_interval=5)

    ai_text       = ft.Ref[ft.Text]()
    live_label    = ft.Ref[ft.Text]()
    total_text    = ft.Ref[ft.Text]()
    sessions_text = ft.Ref[ft.Text]()
    breakdown_col = ft.Ref[ft.Column]()
    sessions_col  = ft.Ref[ft.Column]()
    status_dot    = ft.Ref[ft.Container]()

    def type_chip(t):
        color = TYPE_COLORS.get(t, "#888888")
        return ft.Container(
            content=ft.Text(
                f"{EMOJI.get(t, '📝')} {t}",
                size=11,
                color=color,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor="#1e1e1e",
            border_radius=4,
            border=ft.border.all(0.5, color),
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
        )

    def session_row(s):
        t = datetime.fromisoformat(s["time"]).strftime("%H:%M")
        name = s["name"][:50] + ("…" if len(s["name"]) > 50 else "")
        return ft.Container(
            content=ft.Row([
                type_chip(s["type"]),
                ft.Text(name, size=12, color="#cccccc", expand=True),
                ft.Text(fmt_dur(s["duration"]), size=12, color="#aaaaaa", weight=ft.FontWeight.W_500),
                ft.Text(t, size=11, color="#666666"),
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            border=ft.border.only(bottom=ft.BorderSide(0.5, "#222222")),
        )

    def breakdown_row(t, mins, total):
        pct = int(mins / max(total, 1) * 100)
        color = TYPE_COLORS.get(t, "#888888")
        bar_width = max(4, int(pct * 1.8))
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"{EMOJI.get(t, '📝')} {t}", size=13, color="#dddddd"),
                    ft.Row([
                        ft.Text(fmt_dur(mins), size=12, color="#aaaaaa", weight=ft.FontWeight.W_500),
                        ft.Text(f"  {pct}%", size=11, color="#666666"),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    content=ft.Container(width=bar_width, height=4, bgcolor=color, border_radius=2),
                    bgcolor="#222222",
                    border_radius=2,
                    width=180,
                    height=4,
                ),
            ], spacing=5),
            padding=ft.padding.only(bottom=12),
        )

    def refresh_ui():
        sessions = storage.load_today()
        total    = storage.total_minutes_today()
        by_type  = storage.sessions_by_type(sessions)

        if total_text.current:
            total_text.current.value = fmt_dur(total)
        if sessions_text.current:
            sessions_text.current.value = f"{len(sessions)} sessions"

        if breakdown_col.current:
            breakdown_col.current.controls = (
                [breakdown_row(t, m, total) for t, m in sorted(by_type.items(), key=lambda x: -x[1])]
                if by_type else [ft.Text("No data yet", size=12, color="#555555")]
            )

        if sessions_col.current:
            recent = sessions[-20:][::-1]
            sessions_col.current.controls = (
                [session_row(s) for s in recent]
                if recent else [ft.Container(
                    content=ft.Text("Tracking will appear here automatically...", size=12, color="#555555"),
                    padding=20,
                )]
            )
        page.update()

    def on_new_session(_session):
        refresh_ui()

    def live_updater():
        while True:
            cur = tracker.get_current()
            if live_label.current:
                if cur:
                    icon    = EMOJI.get(cur["type"], "📝")
                    elapsed = fmt_elapsed(cur["elapsed_sec"])
                    name    = cur["name"][:38]
                    live_label.current.value = f"{icon}  {name}  ·  {elapsed}"
                    live_label.current.color = TYPE_COLORS.get(cur["type"], "#aaaaaa")
                    if status_dot.current:
                        status_dot.current.bgcolor = "#1D9E75"
                else:
                    live_label.current.value = "Waiting for activity..."
                    live_label.current.color  = "#555555"
                    if status_dot.current:
                        status_dot.current.bgcolor = "#333333"
            try:
                page.update()
            except Exception:
                break
            time.sleep(1)

    def ask_ai(mode):
        if ai_text.current:
            ai_text.current.value = "Thinking..."
            ai_text.current.color = "#888888"
        page.update()

        def fetch():
            if mode == "summary":
                result = ai.daily_summary()
            elif mode == "tips":
                result = ai.productivity_tips()
            else:
                result = ai.time_balance()
            if ai_text.current:
                ai_text.current.value = result
                ai_text.current.color = "#cccccc"
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    def ai_btn(label, mode):
        return ft.ElevatedButton(
            label,
            on_click=lambda _: ask_ai(mode),
            bgcolor="#1e1e1e",
            color="#aaaaaa",
            elevation=0,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                side=ft.BorderSide(0.5, "#333333"),
            ),
        )

    top_bar = ft.Container(
        content=ft.Row([
            ft.Text("H~EDGE", size=15, weight=ft.FontWeight.W_500, color="#eeeeee"),
            ft.Text("Tracker", size=15, color="#555555"),
            ft.Container(expand=True),
            ft.Container(ref=status_dot, width=8, height=8, border_radius=4, bgcolor="#333333"),
            ft.Text(ref=live_label, value="Starting...", size=12, color="#555555"),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        border=ft.border.only(bottom=ft.BorderSide(0.5, "#222222")),
    )

    stats_card = ft.Container(
        content=ft.Column([
            ft.Text("TOTAL TODAY", size=10, color="#555555", weight=ft.FontWeight.W_500),
            ft.Text(ref=total_text, value="0m", size=28, weight=ft.FontWeight.W_500, color="#eeeeee"),
            ft.Text(ref=sessions_text, value="0 sessions", size=12, color="#666666"),
        ], spacing=3),
        bgcolor="#181818",
        border_radius=8,
        padding=ft.padding.all(16),
    )

    left_panel = ft.Container(
        content=ft.Column([
            stats_card,
            ft.Container(height=24),
            ft.Text("BREAKDOWN", size=10, color="#555555", weight=ft.FontWeight.W_500),
            ft.Container(height=10),
            ft.Column(ref=breakdown_col, controls=[], spacing=0),
            ft.Container(height=24),
            ft.Text("AI INSIGHTS", size=10, color="#555555", weight=ft.FontWeight.W_500),
            ft.Container(height=10),
            ft.Row([ai_btn("Summary", "summary"), ai_btn("Tips", "tips"), ai_btn("Balance", "balance")], spacing=6, wrap=True),
            ft.Container(height=12),
            ft.Text(
                ref=ai_text,
                value="Track some activity, then hit a button above for AI insights.",
                size=12, color="#666666",
            ),
        ], spacing=0, scroll=ft.ScrollMode.AUTO),
        width=290,
        padding=ft.padding.all(20),
        border=ft.border.only(right=ft.BorderSide(0.5, "#222222")),
    )

    right_panel = ft.Container(
        content=ft.Column([
            ft.Text("ACTIVITY LOG", size=10, color="#555555", weight=ft.FontWeight.W_500),
            ft.Container(height=10),
            ft.Column(ref=sessions_col, controls=[], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
        ], spacing=0, expand=True),
        padding=ft.padding.all(20),
        expand=True,
    )

    body = ft.Row([left_panel, right_panel], spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
    page.add(ft.Column([top_bar, body], spacing=0, expand=True))

    tracker.on_update = on_new_session
    tracker.start()
    refresh_ui()
    threading.Thread(target=live_updater, daemon=True).start()


if __name__ == "__main__":
    ft.app(target=main)