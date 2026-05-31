# Attendance Monitor Bot

An automated attendance monitoring tool for the LBRCE ERP portal.

It logs into the ERP, reads attendance data, generates a daily report, stores attendance history, and sends notifications through Telegram, Gmail, or WhatsApp.

## Features

- ERP login and attendance scraping
- Daily report generation in Markdown
- Attendance history tracking
- Telegram, Gmail, and WhatsApp notifications
- Local scheduler for daily checks
- GitHub Actions workflow for scheduled cloud execution

## Project Structure

- `main.py` — command-line entry point and scheduler
- `attendance_scraper.py` — ERP login and attendance extraction
- `notifier.py` — notification delivery
- `storage.py` — history and report generation
- `config.py` — environment loading and app settings
- `reports/` — generated daily reports
- `screenshots/` — debug screenshots when scraping fails
- `logs/` — runtime logs
- `attendance_history.json` — stored snapshots
- `.github/workflows/attendance-monitor.yml` — GitHub Actions workflow

## Requirements

- Python 3.12+
- Playwright
- A valid ERP username and password
- Optional notification credentials depending on the selected notifier

## Local Setup

1. Install dependencies:

   `pip install -r requirements.txt`

2. Install Playwright browser assets:

   `python -m playwright install --with-deps chromium`

3. Create or update your local `.env` file with the required values.

## Environment Variables

Required:

- `ERP_URL`
- `ERP_USERNAME`
- `ERP_PASSWORD`

Optional:

- `HEADLESS`
- `ATTENDANCE_THRESHOLD`
- `NOTIFIER_METHOD`
- `BROWSER_EXECUTABLE_PATH`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `GMAIL_TO`
- `WHATSAPP_PHONE`
- `WHATSAPP_PROFILE_DIR`

## Run Once

Run a single attendance check:

`python main.py --check-now`

## Scheduler

Run continuously and check daily at 8:00 PM local time:

`python main.py`

On Windows, you can also install a Task Scheduler job:

`python main.py --install-task`

## WhatsApp Setup

To prepare the WhatsApp Web session for automation:

`python main.py --setup-whatsapp`

## GitHub Actions

The repository includes a workflow that runs daily and can also be triggered manually.

Before using it, add these repository secrets in GitHub Actions:

- `ERP_USERNAME`
- `ERP_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Then open:

Actions -> Attendance Monitor -> Run workflow

## Output Files

Each run may update:

- `attendance_history.json`
- `reports/YYYY-MM-DD.md`
- `logs/app.log`
- `screenshots/*.png` on failures

## Notes

- Keep `.env` private and out of version control.
- If the ERP layout changes, update the selectors in `attendance_scraper.py`.
- If notification format changes are needed, update `storage.py`.
