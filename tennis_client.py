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


def get_top_players(tour: str, top_n: int = None) -> list[dict]:
    """Fetch live singles rankings for a tour and return the top N.

    Returns a list of dicts like {"name": "...", "position": 1, "id": ...}
    """
    top_n = top_n or config.TOP_N
    url = f"{config.RAPIDAPI_BASE}/tennis/v2/{tour}/ranking/singles"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Response is typically a flat list of ranking rows; be defensive about shape.
    rows = data if isinstance(data, list) else data.get("data", [])
    rows = sorted(rows, key=lambda r: r.get("position") or r.get("singlesPosition", 9999))
    return rows[:top_n]


def get_finished_events() -> list[dict]:
    """Fetch all currently-tracked live events and filter to status == Finished."""
    url = f"{config.RAPIDAPI_BASE}/tennis/v2/extend/api/events/live"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    events = data if isinstance(data, list) else data.get("data", data.get("result", []))
    return [e for e in events if str(e.get("status", "")).lower() == "finished"]
