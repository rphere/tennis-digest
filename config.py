"""
Configuration for the tennis digest bot.
Edit TOP_N to change how many ranked players (per tour) you track.
"""

import os

# How many top-ranked players per tour to track (rankings are fetched live each run)
TOP_N = 15

# Tours to cover
TOURS = ["atp", "wta"]

# RapidAPI "Tennis API - ATP WTA ITF" by matchstat
RAPIDAPI_HOST = "tennis-api-atp-wta-itf.p.rapidapi.com"
RAPIDAPI_BASE = f"https://{RAPIDAPI_HOST}"

# Pulled from environment / GitHub Actions secrets
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "")

# If no tracked-player matches finished today, still send a short "nothing today" email
# rather than staying silent (set False to skip sending on empty days)
SEND_ON_EMPTY_DAY = True
