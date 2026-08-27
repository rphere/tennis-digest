"""
Daily tennis digest bot.

1. Fetch current ATP + WTA top-N singles rankings (live, not hardcoded).
2. Fetch recently finished matches.
3. Keep only matches involving a tracked (top-N) player.
4. Email an HTML digest via Gmail SMTP.

Run manually:  python main.py
Run on a schedule: see .github/workflows/daily-digest.yml
"""

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

import config
from tennis_client import get_top_players, get_finished_events

SENT_LOG_PATH = "sent_log.json"


def match_key(m: dict) -> str:
    """Stable-ish identifier for a match so repeat runs don't re-email it."""
    names = sorted([m["participant1"], m["participant2"]])
    return f"{date.today().isoformat()}|{m['league']}|{names[0]}|{names[1]}|{m['score']}"


def load_sent_log() -> set:
    if not os.path.exists(SENT_LOG_PATH):
        return set()
    try:
        with open(SENT_LOG_PATH) as f:
            data = json.load(f)
        # only keep today's entries so the file doesn't grow forever
        return set(k for k in data.get(date.today().isoformat(), []))
    except Exception:
        return set()


def save_sent_log(keys: set):
    with open(SENT_LOG_PATH, "w") as f:
        json.dump({date.today().isoformat(): sorted(keys)}, f)


def build_tracked_name_set() -> dict[str, str]:
    """Returns {lowercased player name: 'ATP #3' style label} for top-N in each tour."""
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
                tracked[name.lower()] = f"{tour.upper()} #{pos}"
    return tracked


def filter_matches(events: list[dict], tracked: dict[str, str]) -> list[dict]:
    relevant = []
    for e in events:
        p1 = (e.get("participant1") or "").strip()
        p2 = (e.get("participant2") or "").strip()
        tag1 = tracked.get(p1.lower())
        tag2 = tracked.get(p2.lower())
        if tag1 or tag2:
            relevant.append({
                "participant1": p1,
                "participant2": p2,
                "tag1": tag1,
                "tag2": tag2,
                "score": e.get("score", ""),
                "league": e.get("league", ""),
                "tourType": e.get("tourType", ""),
            })
    return relevant


def build_email_html(matches: list[dict]) -> str:
    today = date.today().strftime("%A, %B %d, %Y")
    if not matches:
        return f"""
        <h2>Tennis Digest — {today}</h2>
        <p>No finished matches today involving your tracked top-15 ATP/WTA players.</p>
        """

    rows = []
    for m in matches:
        p1_label = f"{m['participant1']} ({m['tag1']})" if m["tag1"] else m["participant1"]
        p2_label = f"{m['participant2']} ({m['tag2']})" if m["tag2"] else m["participant2"]
        rows.append(f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;">{m['league']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{p1_label} vs {p2_label}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;"><b>{m['score']}</b></td>
        </tr>
        """)

    return f"""
    <h2>Tennis Digest — {today}</h2>
    <p>{len(matches)} match(es) involving current top-15 ATP/WTA players finished:</p>
    <table style="border-collapse:collapse;width:100%;font-family:sans-serif;font-size:14px;">
      <tr style="text-align:left;background:#f5f5f5;">
        <th style="padding:8px;">Tournament</th>
        <th style="padding:8px;">Match</th>
        <th style="padding:8px;">Score</th>
      </tr>
      {''.join(rows)}
    </table>
    """


def send_email(html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Tennis Digest — {date.today().strftime('%b %d, %Y')}"
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_ADDRESS, config.RECIPIENT_EMAIL, msg.as_string())


def main():
    missing = [k for k in ("RAPIDAPI_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "RECIPIENT_EMAIL")
               if not getattr(config, k)]
    if missing:
        raise SystemExit(f"Missing required config/secrets: {', '.join(missing)}")

    tracked = build_tracked_name_set()
    print(f"Tracking {len(tracked)} players across {config.TOURS}")

    events = get_finished_events()
    print(f"Fetched {len(events)} finished events")

    matches = filter_matches(events, tracked)
    print(f"{len(matches)} match(es) involve tracked players")

    already_sent = load_sent_log()
    new_matches = [m for m in matches if match_key(m) not in already_sent]
    print(f"{len(new_matches)} of those haven't been emailed yet today")

    if not new_matches and not config.SEND_ON_EMPTY_DAY:
        print("Nothing new and SEND_ON_EMPTY_DAY is False — skipping email.")
        return

    html = build_email_html(new_matches)
    send_email(html)
    print("Digest email sent.")

    already_sent.update(match_key(m) for m in new_matches)
    save_sent_log(already_sent)


if __name__ == "__main__":
    main()
