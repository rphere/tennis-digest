# Tennis Digest Bot

Sends you a daily email of finished ATP/WTA matches involving whoever is
currently ranked in the **top 15** on either tour (rankings are fetched
live each run, not hardcoded — so the tracked list updates itself as
rankings move).

## How it works

- `tennis_client.py` — talks to the [api-tennis.com](https://api-tennis.com/documentation) API
- `main.py` — fetches rankings, fetches finished matches, filters, builds and sends the email
- `config.py` — tunables (top-N cutoff, tours) and where secrets are read from
- `.github/workflows/daily-digest.yml` — runs `main.py` once a day for free via GitHub Actions

**Data source:** unlike the RapidAPI provider this bot used previously,
`get_fixtures(date_start, date_stop)` on api-tennis.com returns completed
matches for a given date with score/winner inline (`event_status ==
"Finished"`) — a real by-date results endpoint, not a "live" feed you have
to catch mid-transition. The workflow still runs **four times a day**
(roughly 11pm/5am/11am/4pm PT — edit the `cron` lines in
`.github/workflows/daily-digest.yml` to change this) since matches finish
throughout the day and you likely want same-day emails, not one big
end-of-day digest — but reliability no longer depends on run timing the way
it did with the old provider.

So you don't get the same match emailed to you multiple times as the day's
runs repeat, `main.py` keeps a small `sent_log.json` file of what's already
been reported today, and the workflow commits that file back to the repo
after each run so the next run can read it. If a run finds nothing new
since the last one, it sends no email at all (this overrides
`SEND_ON_EMPTY_DAY` — that setting only controls the "zero matches ever
today" case, not "zero *new* matches this run"). The log resets
automatically each day since it's keyed by date.

If you'd rather have exactly one email per day instead, delete three of
the four `cron` lines in the workflow file and keep just one.

**Note:** api-tennis.com has no permanent free tier — plans start with a
14-day trial, then from $40/month. See their [pricing page](https://api-tennis.com/) for current rates.

## One-time setup

### 1. Get an api-tennis.com API key
1. Register for a free trial at [api-tennis.com](https://api-tennis.com/).
2. Find your `APIkey` in the account dashboard.

### 2. Get a Gmail app password
1. Turn on 2-Step Verification on the Google account you want to send from: https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords and create an app password (choose "Mail" as the app).
3. Copy the 16-character password — you'll paste it as a secret, not your normal Gmail password.

### 3. Create the GitHub repo
1. Create a new **private** repo and push these files to it.
2. In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
   - `RAPIDAPI_KEY` — your api-tennis.com `APIkey` from step 1 (secret name kept as-is from an earlier provider)
   - `GMAIL_ADDRESS` — the Gmail address you're sending from
   - `GMAIL_APP_PASSWORD` — the app password from step 2
   - `RECIPIENT_EMAIL` — where the digest should be sent (can be the same address)

### 4. Test it
Go to the **Actions** tab → **Daily Tennis Digest** → **Run workflow** to trigger it manually and confirm you get an email. Once that works, it'll run automatically every day at the scheduled time (12:00 UTC by default — edit the `cron` line in `.github/workflows/daily-digest.yml` to change it).

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
