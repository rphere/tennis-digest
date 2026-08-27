"""
Daily tennis digest bot.

1. Fetch current ATP + WTA top-N singles rankings (live, not hardcoded).
2. Fetch yesterday's finished matches.
3. Keep only matches involving a tracked (top-N) player.
4. Email an HTML digest via Gmail SMTP.

Run manually:  python main.py
Run on a schedule: see .github/workflows/daily-digest.yml (once daily,
8:30am PT, summarizing the previous day's finished matches)
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, timedelta

import config
from tennis_client import get_top_players, get_finished_events, _debug_investigate_tournament_category


def name_key(name: str) -> str:
    """Normalize a player name to "f.lastname" so rankings' full names
    ("Jannik Sinner") match fixtures' abbreviated names ("J. Sinner")."""
    parts = name.strip().split()
    if not parts:
        return ""
    first_initial = parts[0][0].lower()
    last = parts[-1].lower()
    return f"{first_initial}.{last}"


def build_tracked_name_set() -> dict[str, dict]:
    """Returns {name_key: {"label": "ATP #3", "position": 3}} for top-N in each tour."""
    tracked = {}
    for tour in config.TOURS:
        try:
            players = get_top_players(tour)
        except Exception as e:
            print(f"[warn] failed to fetch {tour} rankings: {e}")
            continue
        for p in players:
            name = p.get("name")
            pos = p.get("position") or p.get("singlesPosition")
            if name:
                tracked[name_key(name)] = {"label": f"{tour.upper()} #{pos}", "position": pos}
    return tracked


def filter_matches(events: list[dict], tracked: dict[str, dict]) -> list[dict]:
    relevant = []
    for e in events:
        p1 = (e.get("participant1") or "").strip()
        p2 = (e.get("participant2") or "").strip()
        t1 = tracked.get(name_key(p1)) if p1 else None
        t2 = tracked.get(name_key(p2)) if p2 else None
        if t1 or t2:
            relevant.append({
                "participant1": p1,
                "participant2": p2,
                "tag1": t1["label"] if t1 else None,
                "tag2": t2["label"] if t2 else None,
                "pos1": t1["position"] if t1 else None,
                "pos2": t2["position"] if t2 else None,
                "score": e.get("score", ""),
                "league": e.get("league", ""),
                "tourType": e.get("tourType", ""),
                "winner": e.get("winner"),
            })
    return relevant


def winner_loser(m: dict):
    """Returns (winner_name, winner_tag, winner_pos, loser_name, loser_tag,
    loser_pos), or None if the match's winner isn't known."""
    if m["winner"] == "p1":
        return (m["participant1"], m["tag1"], m["pos1"], m["participant2"], m["tag2"], m["pos2"])
    elif m["winner"] == "p2":
        return (m["participant2"], m["tag2"], m["pos2"], m["participant1"], m["tag1"], m["pos1"])
    return None


def find_upsets(matches: list[dict]) -> list[dict]:
    """A lower-ranked (or untracked) player beating a tracked higher-ranked
    one. Requires knowing the loser's rank; the winner may be untracked."""
    upsets = []
    for m in matches:
        wl = winner_loser(m)
        if wl is None:
            continue
        winner_name, winner_tag, winner_pos, loser_name, loser_tag, loser_pos = wl

        if loser_pos is None:
            continue  # no higher-ranked player was beaten
        if winner_pos is not None and winner_pos <= loser_pos:
            continue  # winner is equal or better ranked - not an upset

        upsets.append({
            **m,
            "winner_name": winner_name, "winner_tag": winner_tag,
            "loser_name": loser_name, "loser_tag": loser_tag, "loser_pos": loser_pos,
        })

    # Biggest upsets first: the higher-ranked (lower position number) the
    # loser, the more newsworthy.
    upsets.sort(key=lambda u: u["loser_pos"])
    return upsets


def tour_style(tour_type: str) -> dict:
    """Distinct visual accent per tour so men's/women's matches read
    differently at a glance, without touching the score formatting."""
    if tour_type == "wta":
        return {"label": "WTA", "border": "#be185d", "badge_bg": "#fce7f3", "badge_fg": "#9d174d"}
    return {"label": "ATP", "border": "#1d4ed8", "badge_bg": "#dbeafe", "badge_fg": "#1e3a8a"}


def tour_badge_html(tour_type: str) -> str:
    s = tour_style(tour_type)
    return (f'<span style="display:inline-block;padding:1px 7px;border-radius:9px;'
            f'font-family:Arial,sans-serif;font-size:10px;font-weight:700;'
            f'letter-spacing:0.5px;background:{s["badge_bg"]};color:{s["badge_fg"]};'
            f'margin-right:6px;">{s["label"]}</span>')


def build_upsets_html(upsets: list[dict]) -> str:
    if not upsets:
        return ""

    rows = []
    for u in upsets:
        s = tour_style(u.get("tourType"))
        winner_label = f"{u['winner_name']} ({u['winner_tag']})" if u["winner_tag"] else u["winner_name"]
        loser_label = f"{u['loser_name']} ({u['loser_tag']})" if u["loser_tag"] else u["loser_name"]
        rows.append(f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;border-left:3px solid {s['border']};">{tour_badge_html(u.get('tourType'))}{u['league']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{winner_label} def. {loser_label}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;"><b>{u['score']}</b></td>
        </tr>
        """)

    return f"""
    <h2>Upsets</h2>
    <table style="border-collapse:collapse;width:100%;font-family:sans-serif;font-size:14px;margin-bottom:24px;">
      <tr style="text-align:left;background:#fff5f5;">
        <th style="padding:8px;">Tournament</th>
        <th style="padding:8px;">Result</th>
        <th style="padding:8px;">Score</th>
      </tr>
      {''.join(rows)}
    </table>
    """


def build_email_html(matches: list[dict], upsets: list[dict], target_date: date) -> str:
    day_label = target_date.strftime("%A, %B %d, %Y")
    upsets_html = build_upsets_html(upsets)

    if not matches:
        return f"""
        <h2>Tennis Digest — {day_label}</h2>
        {upsets_html}
        <p>No finished matches on {day_label} involving your tracked top-{config.TOP_N} ATP/WTA players.</p>
        """

    rows = []
    for m in matches:
        s = tour_style(m.get("tourType"))
        wl = winner_loser(m)
        if wl:
            winner_name, winner_tag, _, loser_name, loser_tag, _ = wl
            winner_label = f"{winner_name} ({winner_tag})" if winner_tag else winner_name
            loser_label = f"{loser_name} ({loser_tag})" if loser_tag else loser_name
            matchup = f"{winner_label} def. {loser_label}"
        else:
            # Winner unknown (shouldn't normally happen) - fall back to
            # participant order, matching the score's participant1-first
            # fallback order in tennis_client._format_scoreline.
            p1_label = f"{m['participant1']} ({m['tag1']})" if m["tag1"] else m["participant1"]
            p2_label = f"{m['participant2']} ({m['tag2']})" if m["tag2"] else m["participant2"]
            matchup = f"{p1_label} vs {p2_label}"
        rows.append(f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;border-left:3px solid {s['border']};">{tour_badge_html(m.get('tourType'))}{m['league']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{matchup}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;"><b>{m['score']}</b></td>
        </tr>
        """)

    return f"""
    <h2>Tennis Digest — {day_label}</h2>
    {upsets_html}
    <p>{len(matches)} match(es) involving current top-{config.TOP_N} ATP/WTA players finished:</p>
    <table style="border-collapse:collapse;width:100%;font-family:sans-serif;font-size:14px;">
      <tr style="text-align:left;background:#f5f5f5;">
        <th style="padding:8px;">Tournament</th>
        <th style="padding:8px;">Match</th>
        <th style="padding:8px;">Score</th>
      </tr>
      {''.join(rows)}
    </table>
    """


def send_email(html_body: str, target_date: date):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Tennis Digest — {target_date.strftime('%b %d, %Y')}"
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_ADDRESS, config.RECIPIENT_EMAIL, msg.as_string())


def main():
    missing = [k for k in ("API_TENNIS_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "RECIPIENT_EMAIL")
               if not getattr(config, k)]
    if missing:
        raise SystemExit(f"Missing required config/secrets: {', '.join(missing)}")

    try:
        _debug_investigate_tournament_category()
    except Exception as e:
        print(f"[debug] tournament category investigation failed: {e}")

    target_date = date.today() - timedelta(days=1)
    day = target_date.isoformat()
    print(f"Summarizing matches from {day}")

    tracked = build_tracked_name_set()
    print(f"Tracking {len(tracked)} players across {config.TOURS}")

    events = get_finished_events(day)
    print(f"Fetched {len(events)} finished events")

    matches = filter_matches(events, tracked)
    print(f"{len(matches)} match(es) involve tracked players")

    if not matches and not config.SEND_ON_EMPTY_DAY:
        print("No matches and SEND_ON_EMPTY_DAY is False — skipping email.")
        return

    upsets = find_upsets(matches)
    print(f"{len(upsets)} of those are upsets")

    upset_signatures = {(u["participant1"], u["participant2"], u["league"], u["score"]) for u in upsets}
    other_matches = [m for m in matches
                      if (m["participant1"], m["participant2"], m["league"], m["score"]) not in upset_signatures]

    html = build_email_html(other_matches, upsets, target_date)
    send_email(html, target_date)
    print("Digest email sent.")


if __name__ == "__main__":
    main()
