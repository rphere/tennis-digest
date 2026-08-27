"""
Configuration for the tennis digest bot.
Edit TOP_N to change how many ranked players (per tour) you track.
"""

import os

# How many top-ranked players per tour to track (rankings are fetched live each run)
TOP_N = 50

# Tours to cover
TOURS = ["atp", "wta"]

# Pulled from environment / GitHub Actions secrets.
# NOTE: the secret is still named RAPIDAPI_KEY in GitHub (left as-is to avoid
# an extra manual step), but it now holds an api-tennis.com APIkey, not a
# RapidAPI key — see tennis_client.py.
API_TENNIS_KEY = os.environ.get("RAPIDAPI_KEY", "")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "")

# If no tracked-player matches finished today, still send a short "nothing today" email
# rather than staying silent (set False to skip sending on empty days)
SEND_ON_EMPTY_DAY = True
