"""
Static lookup of each tournament's ATP/WTA tier (Grand Slam / Masters 1000 /
500 / 250 / Finals). api-tennis.com's get_fixtures and get_tournaments
endpoints expose no tier field at all (verified directly against the live
API's full get_tournaments response - 10,222 rows, only tournament_key,
tournament_name, event_type_key, event_type_type, tournament_sourface), so
this has to be maintained by hand.

Sourced from the official 2026 ATP and WTA tour calendar PDFs
(atptour.com, wtatennis.com). Keyed by the short tournament name the way
api-tennis.com's tournament_name field returns it (e.g. "Winston-Salem",
not "Winston-Salem Open presented by Truist").

NEEDS YEARLY UPKEEP: tournament categories and host cities can change
between seasons (e.g. Antwerp -> Brussels for 2026's ATP 250, the WTA
Finals' host city). A tournament not listed here just gets no tier label
rather than an error.
"""

ATP_TIERS = {
    "Brisbane": "ATP 250",
    "Hong Kong": "ATP 250",
    "Adelaide": "ATP 250",
    "Auckland": "ATP 250",
    "Australian Open": "Grand Slam",
    "Montpellier": "ATP 250",
    "Dallas": "ATP 500",
    "Rotterdam": "ATP 500",
    "Buenos Aires": "ATP 250",
    "Doha": "ATP 500",
    "Rio de Janeiro": "ATP 500",
    "Delray Beach": "ATP 250",
    "Acapulco": "ATP 500",
    "Dubai": "ATP 500",
    "Santiago": "ATP 250",
    "Indian Wells": "ATP Masters 1000",
    "Miami Open": "ATP Masters 1000",
    "Bucharest": "ATP 250",
    "Houston": "ATP 250",
    "Marrakech": "ATP 250",
    "Monte-Carlo": "ATP Masters 1000",
    "Barcelona": "ATP 500",
    "Munich": "ATP 500",
    "Madrid": "ATP Masters 1000",
    "Rome": "ATP Masters 1000",
    "Hamburg": "ATP 500",
    "Geneva": "ATP 250",
    "Roland Garros": "Grand Slam",
    "'s-Hertogenbosch": "ATP 250",
    "Stuttgart": "ATP 250",
    "Halle": "ATP 500",
    "Queen's Club": "ATP 500",
    "Mallorca": "ATP 250",
    "Eastbourne": "ATP 250",
    "Wimbledon": "Grand Slam",
    "Bastad": "ATP 250",
    "Gstaad": "ATP 250",
    "Umag": "ATP 250",
    "Kitzbuhel": "ATP 250",
    "Estoril": "ATP 250",
    "Washington": "ATP 500",
    "Los Cabos": "ATP 250",
    "Montreal": "ATP Masters 1000",
    "Cincinnati": "ATP Masters 1000",
    "Winston-Salem": "ATP 250",
    "US Open": "Grand Slam",
    "Chengdu": "ATP 250",
    "Hangzhou": "ATP 250",
    "Tokyo": "ATP 500",
    "Beijing": "ATP 500",
    "Shanghai": "ATP Masters 1000",
    "Almaty": "ATP 250",
    "Brussels": "ATP 250",
    "Lyon": "ATP 250",
    "Basel": "ATP 500",
    "Vienna": "ATP 500",
    "Paris": "ATP Masters 1000",
    "Stockholm": "ATP 250",
    "ATP Finals": "ATP Finals",
    "Next Gen Finals": "Next Gen Finals",
}

WTA_TIERS = {
    "Brisbane": "WTA 500",
    "Auckland": "WTA 250",
    "Adelaide": "WTA 500",
    "Hobart": "WTA 250",
    "Australian Open": "Grand Slam",
    "Abu Dhabi": "WTA 500",
    "Transylvania Open": "WTA 250",
    "Ostrava": "WTA 250",
    "Doha": "WTA 1000",
    "Dubai": "WTA 1000",
    "Merida": "WTA 500",
    "Austin": "WTA 250",
    "Indian Wells": "WTA 1000",
    "Miami Open": "WTA 1000",
    "Charleston": "WTA 500",
    "Bogota": "WTA 250",
    "Linz": "WTA 500",
    "Stuttgart": "WTA 500",
    "Rouen": "WTA 250",
    "Madrid": "WTA 1000",
    "Rome": "WTA 1000",
    "Strasbourg": "WTA 500",
    "Rabat": "WTA 250",
    "Roland Garros": "Grand Slam",
    "Queen's Club": "WTA 500",
    "'s-Hertogenbosch": "WTA 250",
    "Berlin": "WTA 500",
    "Nottingham": "WTA 250",
    "Bad Homburg": "WTA 500",
    "Eastbourne": "WTA 250",
    "Wimbledon": "Grand Slam",
    "Iasi": "WTA 250",
    "Athens": "WTA 250",
    "Hamburg": "WTA 500",
    "Prague": "WTA 250",
    "Washington": "WTA 500",
    "Memphis": "WTA 250",
    "Toronto": "WTA 1000",
    "Cincinnati": "WTA 1000",
    "Monterrey": "WTA 500",
    "US Open": "Grand Slam",
    "Guadalajara": "WTA 500",
    "Sao Paulo": "WTA 250",
    "Singapore": "WTA 500",
    "Seoul": "WTA 250",
    "Beijing": "WTA 1000",
    "Wuhan": "WTA 1000",
    "Ningbo": "WTA 500",
    "Osaka": "WTA 250",
    "Tokyo": "WTA 500",
    "Guangzhou": "WTA 250",
    "Chennai": "WTA 250",
    "Hong Kong": "WTA 250",
    "WTA Finals": "WTA Finals",
}


def get_tier(tour_type: str, tournament_name: str) -> str | None:
    """Returns a short tier label ("250", "Masters 1000", "Grand Slam", ...)
    with the redundant ATP/WTA prefix stripped - the digest already shows
    a colored ATP/WTA badge next to the tournament name. None if unknown."""
    table = WTA_TIERS if tour_type == "wta" else ATP_TIERS
    full = table.get((tournament_name or "").strip())
    if not full:
        return None
    for prefix in ("ATP ", "WTA "):
        if full.startswith(prefix):
            return full[len(prefix):]
    return full
