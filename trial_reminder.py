"""
One-off reminders that the api-tennis.com free trial is ending soon.

Trial started 2026-08-27; api-tennis.com trials run 14 days, so it ends
2026-09-10. Sends a heads-up email on Sep 1, Sep 5, and the end date
itself (Sep 10) via the same Gmail SMTP config main.py uses.

Run manually:  python trial_reminder.py
Run on a schedule: see .github/workflows/trial-reminder.yml
"""

import smtplib
from email.mime.text import MIMEText
from datetime import date, timedelta

import config

TRIAL_START = date(2026, 8, 27)
TRIAL_LENGTH_DAYS = 14
TRIAL_END = TRIAL_START + timedelta(days=TRIAL_LENGTH_DAYS)


def send_reminder():
    days_left = (TRIAL_END - date.today()).days
    end_label = TRIAL_END.strftime("%B %d, %Y")

    if days_left > 0:
        body = (
            f"Your api-tennis.com free trial ends on {end_label} "
            f"({days_left} day{'s' if days_left != 1 else ''} from now). "
            "Subscribe at https://api-tennis.com/ to keep the tennis digest "
            "running - once the trial ends, the daily digest will stop "
            "receiving match data."
        )
    else:
        body = (
            f"Your api-tennis.com free trial ended on {end_label}. "
            "The tennis digest bot will stop working until you subscribe "
            "to a paid plan at https://api-tennis.com/."
        )

    msg = MIMEText(body)
    msg["Subject"] = "Reminder: api-tennis.com trial ending soon"
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.RECIPIENT_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_ADDRESS, config.RECIPIENT_EMAIL, msg.as_string())

    print(f"Trial reminder sent. Days left: {days_left}")


if __name__ == "__main__":
    missing = [k for k in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "RECIPIENT_EMAIL")
               if not getattr(config, k)]
    if missing:
        raise SystemExit(f"Missing required config/secrets: {', '.join(missing)}")
    send_reminder()
