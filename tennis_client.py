"""
Thin client around the api-tennis.com REST API (docs: https://api-tennis.com/documentation).

Two calls matter for this bot:
  1. Rankings          -> method=get_standings, event_type=ATP|WTA
  2. Finished matches   -> method=get_fixtures, date_start=<day>, date_stop=<day>

Unlike the previous RapidAPI "Tennis API - ATP WTA ITF" provider, get_fixtures
returns completed matches (event_status == "Finished") with score/winner
inline for a given date, so there's no need to poll a "live events" feed and
hope to catch a fleeting Finished status before it disappears.
"""

import requests
import config

API_TENNIS_BASE = "https://api.api-tennis.com/tennis/"

# api-tennis.com identifies each tour by a numeric event_type_key rather than
# a string like "atp"/"wta". These came from get_events in the provider docs;
# the debug dump below prints the raw keys/status values seen on each run so
# a wrong id (or a provider renumbering) is easy to spot from Action logs.
TOUR_EVENT_TYPE_KEYS = {"atp": 265, "wta": 266}


def _debug_dump(label: str, resp: requests.Response):
    """Print enough of the raw response to diagnose shape/auth problems from
    Action logs, without dumping something enormous."""
    print(f"[debug] {label}: HTTP {resp.status_code}")
    snippet = resp.text[:500].replace("\n", " ")
    print(f"[debug] {label} body (first 500 chars): {snippet}")


def _get(method: str, **params) -> dict:
    params = {"method": method, "APIkey": config.API_TENNIS_KEY, **params}
    resp = requests.get(API_TENNIS_BASE, params=params, timeout=30)
    _debug_dump(method, resp)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        print(f"[warn] {method} returned success={data.get('success')}: {str(data)[:300]}")
    return data


def get_top_players(tour: str, top_n: int = None) -> list[dict]:
    """Fetch live singles rankings for a tour and return the top N.

    Returns a list of dicts like {"name": "...", "position": 1, ...}
    """
    top_n = top_n or config.TOP_N
    data = _get("get_standings", event_type=tour.upper())
    rows = data.get("result") or []

    print(f"[debug] {tour} rankings: parsed {len(rows)} row(s)")
    if rows:
        print(f"[debug] {tour} rankings: first row keys = {list(rows[0].keys())}")

    for r in rows:
        r["name"] = r.get("player")
        try:
            r["position"] = int(r.get("place"))
        except (TypeError, ValueError):
            r["position"] = None

    rows = sorted(rows, key=lambda r: r.get("position") or 9999)
    return rows[:top_n]


def _format_set(s: dict) -> str:
    """Turn one set's score_first/score_second into "6-3", or "6-7(6)" for a
    tiebreak set. api-tennis.com encodes the tiebreak point count as a
    decimal suffix on the game count, e.g. score_first="6.6",
    score_second="7.8" for a 6-7 set decided 6-8 in the breaker."""
    first = str(s.get("score_first", ""))
    second = str(s.get("score_second", ""))
    main1, _, tiebreak1 = first.partition(".")
    main2, _, tiebreak2 = second.partition(".")
    if tiebreak1 and tiebreak2:
        try:
            # Convention is to show the *loser's* tiebreak point count.
            loser_tiebreak = tiebreak1 if int(main1) < int(main2) else tiebreak2
            return f"{main1}-{main2}({loser_tiebreak})"
        except ValueError:
            pass
    return f"{main1}-{main2}"


def _format_scoreline(scores: list[dict], winner: str) -> str:
    """Turn api-tennis.com's per-set scores array into "6-3, 6-7(6), 6-3" text,
    always showing the winner's game count first per set (standard tennis
    reporting convention), regardless of event_first_player/event_second_player
    order. `winner` is "p1" (score_first is the winner) or "p2"; any other
    value leaves the original score_first/score_second order untouched."""
    def _set_num(s):
        try:
            return int(s.get("score_set"))
        except (TypeError, ValueError):
            return 0

    ordered = sorted(scores or [], key=_set_num)
    if winner == "p2":
        ordered = [{"score_first": s.get("score_second"), "score_second": s.get("score_first"),
                    "score_set": s.get("score_set")} for s in ordered]
    return ", ".join(_format_set(s) for s in ordered)


def _debug_investigate_tournament_category():
    """One-off: check whether get_tournaments exposes a tier field (250/500/
    1000/Grand Slam) that get_fixtures doesn't."""
    data = _get("get_tournaments")
    rows = data.get("result") or []
    print(f"[debug] get_tournaments: parsed {len(rows)} row(s)")
    if rows:
        print(f"[debug] get_tournaments: first row keys = {list(rows[0].keys())}")
    for r in rows:
        name = str(r.get("tournament_name", ""))
        if "Monterrey" in name or "Winston" in name:
            print(f"[debug] get_tournaments match: {r}")


def get_finished_events(day: str) -> list[dict]:
    """Fetch fixtures across tracked tours for `day` (YYYY-MM-DD) and filter
    to matches with event_status == "Finished"."""
    events = []
    for tour, event_type_key in TOUR_EVENT_TYPE_KEYS.items():
        data = _get("get_fixtures", date_start=day, date_stop=day, event_type_key=event_type_key)
        rows = data.get("result") or []

        print(f"[debug] {tour} fixtures: parsed {len(rows)} row(s)")
        if rows:
            print(f"[debug] {tour} fixtures: first row keys = {list(rows[0].keys())}")
            statuses = sorted(set(str(r.get("event_status")) for r in rows))
            print(f"[debug] {tour} fixtures: distinct status values seen = {statuses}")
            finished_sample = next((r for r in rows if r.get("event_status") == "Finished"), None)
            if finished_sample:
                print(f"[debug] {tour} fixtures: sample scores field = {finished_sample.get('scores')}")
            tournaments = sorted(set(str(r.get("tournament_name")) for r in rows))
            print(f"[debug] {tour} fixtures: distinct tournaments seen = {tournaments}")

        for r in rows:
            winner_raw = r.get("event_winner")
            winner = {"First Player": "p1", "Second Player": "p2"}.get(winner_raw)
            events.append({
                "participant1": r.get("event_first_player", ""),
                "participant2": r.get("event_second_player", ""),
                "score": _format_scoreline(r.get("scores"), winner) or r.get("event_final_result", ""),
                "league": r.get("tournament_name", ""),
                "tourType": tour,
                "status": r.get("event_status", ""),
                "winner": winner,
            })

    return [e for e in events if e["status"] == "Finished"]
