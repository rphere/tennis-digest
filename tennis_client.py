"""
Thin client around the RapidAPI "Tennis API - ATP WTA ITF" endpoints
(docs: https://tennisapidoc.matchstat.com/).

Two calls matter for this bot:
  1. Rankings  -> GET /tennis/v2/{tour}/ranking/singles
  2. Live/finished events -> GET /tennis/v2/extend/api/events/live

NOTE ON DATA MODEL:
This API's "Fixtures" endpoints (Today table) only return matches that have
NOT been played yet — the provider strips any row with a non-empty result.
Completed results instead show up through the "live events" feed with
status "Finished" for matches that wrapped up recently. This script relies
on that feed. If you subscribe and find finished matches drop off that feed
too quickly (e.g. they disappear after a few hours), the more robust fix is
to poll multiple times a day rather than once, or switch to a provider with
an explicit "results by date" endpoint. See README for notes.
"""

import requests
import config


def _headers():
    return {
        "X-RapidAPI-Key": config.RAPIDAPI_KEY,
        "X-RapidAPI-Host": config.RAPIDAPI_HOST,
    }


def _debug_dump(label: str, resp: requests.Response):
    """Print enough of the raw response to diagnose shape/auth problems from
    Action logs, without dumping something enormous."""
    print(f"[debug] {label}: HTTP {resp.status_code}")
    snippet = resp.text[:500].replace("\n", " ")
    print(f"[debug] {label} body (first 500 chars): {snippet}")


def get_top_players(tour: str, top_n: int = None) -> list[dict]:
    """Fetch live singles rankings for a tour and return the top N.

    Returns a list of dicts like {"name": "...", "position": 1, "id": ...}
    """
    top_n = top_n or config.TOP_N
    url = f"{config.RAPIDAPI_BASE}/tennis/v2/{tour}/ranking/singles"
    resp = requests.get(url, headers=_headers(), timeout=30)
    _debug_dump(f"{tour} rankings", resp)
    resp.raise_for_status()
    data = resp.json()

    # Response shape varies by provider version — try the common envelopes.
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("data") or data.get("result") or data.get("results") or []
        if isinstance(rows, dict):
            # some endpoints nest again, e.g. {"data": {"rankings": [...]}}
            rows = rows.get("rankings") or rows.get("data") or []
    else:
        rows = []

    print(f"[debug] {tour} rankings: parsed {len(rows)} row(s)")
    if rows:
        print(f"[debug] {tour} rankings: first row keys = {list(rows[0].keys())}")

    # Some provider versions nest the player's name under a "player" object
    # instead of putting it at the top level of the ranking row.
    for r in rows:
        if not r.get("name") and isinstance(r.get("player"), dict):
            r["name"] = r["player"].get("name")

    rows = sorted(rows, key=lambda r: r.get("position") or r.get("singlesPosition") or 9999)
    return rows[:top_n]


def get_finished_events() -> list[dict]:
    """Fetch all currently-tracked live events and filter to status == Finished."""
    url = f"{config.RAPIDAPI_BASE}/tennis/v2/extend/api/events/live"
    resp = requests.get(url, headers=_headers(), timeout=30)
    _debug_dump("live events", resp)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        events = data.get("data") or data.get("result") or data.get("results") or []
        if isinstance(events, dict):
            events = events.get("events") or events.get("data") or []
    else:
        events = []

    print(f"[debug] live events: parsed {len(events)} row(s)")
    if events:
        print(f"[debug] live events: first row keys = {list(events[0].keys())}")
        statuses = sorted(set(str(e.get("status")) for e in events))
        print(f"[debug] live events: distinct status values seen = {statuses}")

    return [e for e in events if str(e.get("status", "")).lower() == "finished"]
