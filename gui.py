import flet as ft
import threading
import time
import math
from datetime import datetime, date, timedelta
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

PRODUCTIVE = {"code", "read"}

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


def productive_pct(sessions):
    total = sum(s.get("duration", 0) for s in sessions)
    prod  = sum(s.get("duration", 0) for s in sessions if s.get("type") in PRODUCTIVE)
    return int(prod / max(total, 1) * 100), total


def ring_svg(pct, total_min, color="#4A9EE0", size=110):
    r = 42
    cx = cy = size // 2
    circ = 2 * math.pi * r
    dash = circ * pct / 100
    gap  = circ - dash
    total_str = fmt_dur(total_min)
    pct_color = "#5CB85C" if pct >= 60 else "#E0A84A" if pct >= 30 else "#E07FA0"
    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#222222" stroke-width="8"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{pct_color}" stroke-width="8"
    stroke-dasharray="{dash:.1f} {gap:.1f}"
    stroke-linecap="round"
    transform="rotate(-90 {cx} {cy})"/>
  <text x="{cx}" y="{cy - 6}" text-anchor="middle" fill="#eeeeee" font-size="13" font-weight="bold" font-family="Arial">{pct}%</text>
  <text x="{cx}" y="{cy + 10}" text-anchor="middle" fill="#888888" font-size="9" font-family="Arial">{total_str}</text>
</svg>"""


def main(page: ft.Page):
    page.title = "H~EDGE Tracker"
    page.window_width = 940
    page.window_height = 700
    page.window_min_width = 700
    page.window_min_height = 500
    page.bgcolor = "#111111"
    page.padding = 0

    tracker = ActivityTracker(poll_interval=5)

    ai_text         = ft.Ref[ft.Text]()
    live_label      = ft.Ref[ft.Text]()
    total_text      = ft.Ref[ft.Text]()
    sessions_text   = ft.Ref[ft.Text]()
    breakdown_col   = ft.Ref[ft.Column]()
    sessions_col    = ft.Ref[ft.Column]()
    status_dot      = ft.Ref[ft.Container]()
    history_col     = ft.Ref[ft.Column]()
    history_detail  = ft.Ref[ft.Column]()
    hist_ai_text    = ft.Ref[ft.Text]()

    # ── Helpers ────────────────────────────────────────────────────────────

    def type_chip(t):
        color = TYPE_COLORS.get(t, "#888888")
        return ft.Container(
            content=ft.Text(f"{EMOJI.get(t, '📝')} {t}", size=11, color=color, weight=ft.FontWeight.W_500),
            bgcolor="#1e1e1e", border_radius=4,
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
                    bgcolor="#222222", border_radius=2, width=180, height=4,
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

    def show_day_detail(date_str, sessions):
        if not history_detail.current:
            return
        pct, total = productive_pct(sessions)
        by_type = storage.sessions_by_type(sessions)
        rows = [
            ft.Text(f"Details — {date_str}", size=13, color="#eeeeee", weight=ft.FontWeight.W_500),
            ft.Container(height=8),
        ]
        for t, m in sorted(by_type.items(), key=lambda x: -x[1]):
            rows.append(breakdown_row(t, m, total))
        rows.append(ft.Container(height=12))
        rows.append(ft.Text("AI SUMMARY", size=10, color="#555555", weight=ft.FontWeight.W_500))
        rows.append(ft.Container(height=8))
        rows.append(ft.ElevatedButton(
            "Get AI Summary",
            on_click=lambda _, d=date_str: ask_hist_ai(d),
            bgcolor="#1e1e1e", color="#aaaaaa", elevation=0,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6), side=ft.BorderSide(0.5, "#333333")),
        ))
        rows.append(ft.Container(height=8))
        rows.append(ft.Text(ref=hist_ai_text, value="", size=12, color="#aaaaaa"))
        history_detail.current.controls = rows
        page.update()

    def build_history_rings():
        if not history_col.current:
            return
        dates = storage.all_dates()
        if not dates:
            history_col.current.controls = [
                ft.Container(
                    content=ft.Text("No history yet. Start tracking to see your past days here.", size=13, color="#555555"),
                    padding=40,
                )
            ]
            page.update()
            return

        rings = []
        for d in dates[:14]:
            sessions = storage.load_date(d)
            pct, total = productive_pct(sessions)
            by_type = storage.sessions_by_type(sessions)
            top = max(by_type, key=by_type.get) if by_type else "other"

            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
                today = date.today()
                delta = (today - dt.date()).days
                if delta == 0:
                    label = "Today"
                elif delta == 1:
                    label = "Yesterday"
                else:
                    label = dt.strftime("%a %d %b")
            except Exception:
                label = d

            svg = ring_svg(pct, total)
            ring_card = ft.Container(
                content=ft.Column([
                    ft.Image(src_base64=None, src=f"data:image/svg+xml,{svg.strip()}", width=110, height=110),
                    ft.Text(label, size=12, color="#cccccc", text_align=ft.TextAlign.CENTER),
                    ft.Text(f"{EMOJI.get(top, '📝')} {top}", size=11, color="#666666", text_align=ft.TextAlign.CENTER),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#181818",
                border_radius=10,
                padding=ft.padding.all(12),
                width=130,
                on_click=lambda _, d=d, s=sessions: show_day_detail(d, s),
                ink=True,
            )
            rings.append(ring_card)

        history_col.current.controls = [
            ft.Text("PAST DAYS", size=10, color="#555555", weight=ft.FontWeight.W_500),
            ft.Container(height=12),
            ft.Row(rings, wrap=True, spacing=10, run_spacing=10),
        ]
        page.update()

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

    def ask_hist_ai(date_str):
        if hist_ai_text.current:
            hist_ai_text.current.value = "Thinking..."
        page.update()

        def fetch():
            result = ai.daily_summary(date_str)
            if hist_ai_text.current:
                hist_ai_text.current.value = result
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

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

    # ── UI ─────────────────────────────────────────────────────────────────

    def ai_btn(label, mode):
        return ft.ElevatedButton(
            label,
            on_click=lambda _: ask_ai(mode),
            bgcolor="#1e1e1e", color="#aaaaaa", elevation=0,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6), side=ft.BorderSide(0.5, "#333333")),
        )

    def tab_btn(label, idx, ref_tabs, ref_indicator):
        def on_click(_):
            for i, tab in enumerate(ref_tabs):
                tab.visible = (i == idx)
            page.update()
        return ft.TextButton(
            label,
            on_click=on_click,
            style=ft.ButtonStyle(color="#aaaaaa", padding=ft.padding.symmetric(horizontal=16, vertical=8)),
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

    # ── Today tab ──────────────────────────────────────────────────────────
    stats_card = ft.Container(
        content=ft.Column([
            ft.Text("TOTAL TODAY", size=10, color="#555555", weight=ft.FontWeight.W_500),
            ft.Text(ref=total_text, value="0m", size=28, weight=ft.FontWeight.W_500, color="#eeeeee"),
            ft.Text(ref=sessions_text, value="0 sessions", size=12, color="#666666"),
        ], spacing=3),
        bgcolor="#181818", border_radius=8, padding=ft.padding.all(16),
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
            ft.Text(ref=ai_text, value="Track some activity, then hit a button above for AI insights.", size=12, color="#666666"),
        ], spacing=0, scroll=ft.ScrollMode.AUTO),
        width=290, padding=ft.padding.all(20),
        border=ft.border.only(right=ft.BorderSide(0.5, "#222222")),
    )

    right_panel = ft.Container(
        content=ft.Column([
            ft.Text("ACTIVITY LOG", size=10, color="#555555", weight=ft.FontWeight.W_500),
            ft.Container(height=10),
            ft.Column(ref=sessions_col, controls=[], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
        ], spacing=0, expand=True),
        padding=ft.padding.all(20), expand=True,
    )

    today_tab = ft.Row([left_panel, right_panel], spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)

    # ── History tab ────────────────────────────────────────────────────────
    history_left = ft.Container(
        content=ft.Column([
            ft.Column(ref=history_col, controls=[], spacing=0, scroll=ft.ScrollMode.AUTO),
        ], spacing=0, scroll=ft.ScrollMode.AUTO),
        expand=True, padding=ft.padding.all(20),
        border=ft.border.only(right=ft.BorderSide(0.5, "#222222")),
    )

    history_right = ft.Container(
        content=ft.Column(ref=history_detail, controls=[
            ft.Text("Click a day to see details", size=13, color="#555555"),
        ], spacing=0, scroll=ft.ScrollMode.AUTO),
        width=290, padding=ft.padding.all(20),
    )

    history_tab = ft.Row(
        [history_left, history_right],
        spacing=0, expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
        visible=False,
    )

    # ── Tab bar ────────────────────────────────────────────────────────────
    tabs = [today_tab, history_tab]

    def switch_tab(idx):
        for i, t in enumerate(tabs):
            t.visible = (i == idx)
        if idx == 1:
            build_history_rings()
        page.update()

    tab_bar = ft.Container(
        content=ft.Row([
            ft.TextButton("Today", on_click=lambda _: switch_tab(0),
                style=ft.ButtonStyle(color="#eeeeee", padding=ft.padding.symmetric(horizontal=16, vertical=6))),
            ft.TextButton("History", on_click=lambda _: switch_tab(1),
                style=ft.ButtonStyle(color="#aaaaaa", padding=ft.padding.symmetric(horizontal=16, vertical=6))),
        ], spacing=0),
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
        border=ft.border.only(bottom=ft.BorderSide(0.5, "#222222")),
    )

    page.add(ft.Column([top_bar, tab_bar, today_tab, history_tab], spacing=0, expand=True))

    tracker.on_update = on_new_session
    tracker.start()
    refresh_ui()
    threading.Thread(target=live_updater, daemon=True).start()


if __name__ == "__main__":
    ft.app(target=main)