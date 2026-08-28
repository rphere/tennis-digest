# Tennis Digest Bot

Sends you a daily email, at 8:30am PT, summarizing the **previous day's**
finished ATP/WTA matches involving whoever is currently ranked in the
**top `TOP_N`** (see `config.py`) on either tour (rankings are fetched live
each run, not hardcoded — so the tracked list updates itself as rankings
move). Also flags **upsets** (a lower-ranked or untracked player beating a
tracked higher-ranked one) in their own section at the top of the email.

## How it works

- `tennis_client.py` — talks to the [api-tennis.com](https://api-tennis.com/documentation) API
- `main.py` — fetches rankings, fetches yesterday's finished matches, filters, builds and sends the email
- `trial_reminder.py` — sends a heads-up email before the api-tennis.com trial ends (see below)
- `config.py` — tunables (top-N cutoff, tours) and where secrets are read from
- `.github/workflows/daily-digest.yml` — runs `main.py` once a day for free via GitHub Actions
- `.github/workflows/trial-reminder.yml` — runs `trial_reminder.py` on three fixed dates

**Data source:** `get_fixtures(date_start, date_stop)` on api-tennis.com
returns completed matches for a given date with score/winner inline
(`event_status == "Finished"`) — a real by-date results endpoint. Because
of this, one run per day is enough; there's no need to poll multiple times
to catch a match's fleeting "Finished" status the way an earlier version
of this bot (built on a different provider) had to. There's no dedup
tracking between runs, since the schedule only fires once a day — if you
add `workflow_dispatch` re-runs on top of the daily schedule for the same
day, you'll get a duplicate email with the same matches.

**Trial reminders:** api-tennis.com has no permanent free tier — plans
start with a 14-day trial, then from $40/month. See their [pricing
page](https://api-tennis.com/) for current rates. `trial_reminder.py`
emails `RECIPIENT_EMAIL` a heads-up on three fixed calendar dates (edit
`TRIAL_START` in that file and the `cron` lines in
`.github/workflows/trial-reminder.yml` if you start a new trial later).

## One-time setup

### 1. Get an api-tennis.com API key
1. Register for a free trial at [api-tennis.com](https://api-tennis.com/).
2. Find your `APIkey` in the account dashboard.

### 2. Get a Gmail app password
1. Turn on 2-Step Verification on the Google account you want to send from: https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords and create an app password (choose "Mail" as the app).
3. Copy the 16-character password — you'll paste it as a secret, not your normal Gmail password.

### 3. Create the GitHub repo
1. Create a new repo (public or private — all four secrets below live in GitHub's encrypted secret store regardless of repo visibility, never in code) and push these files to it.
2. In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
   - `RAPIDAPI_KEY` — your api-tennis.com `APIkey` from step 1 (secret name kept as-is from an earlier provider)
   - `GMAIL_ADDRESS` — the Gmail address you're sending from
   - `GMAIL_APP_PASSWORD` — the app password from step 2
   - `RECIPIENT_EMAIL` — where the digest should be sent (can be the same address)

### 4. Test it
Go to the **Actions** tab → **Daily Tennis Digest** → **Run workflow** to trigger it manually and confirm you get an email. Once that works, it'll run automatically every day at 8:30am PT (edit the `cron` line in `.github/workflows/daily-digest.yml` to change it).

## Running locally (optional, for testing)

```bash
pip install -r requirements.txt
export RAPIDAPI_KEY=xxx
export GMAIL_ADDRESS=you@gmail.com
export GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
export RECIPIENT_EMAIL=you@gmail.com
python main.py
```

## Tuning

- Change `TOP_N` in `config.py` to track more/fewer players per tour.
- Change `SEND_ON_EMPTY_DAY` to `False` if you'd rather get no email on days with zero matches involving tracked players, instead of a "nothing today" email.
