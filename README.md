# Attendance Monitor Bot

An automated attendance monitoring tool for the LBRCE ERP portal.

It logs into the ERP, reads attendance data, generates a daily report, stores attendance history, and sends notifications through Telegram, Gmail, or WhatsApp.

## Overview

This project is designed to:

- check attendance automatically
- store daily snapshots and history
- generate a markdown report for every run
- notify via Telegram, Gmail, or WhatsApp
- run locally on Windows or in GitHub Actions

## Features

- ERP login and attendance scraping
- Daily report generation in Markdown
- Attendance history tracking
- Telegram, Gmail, and WhatsApp notifications
- Local scheduler for daily checks
- GitHub Actions workflow for scheduled cloud execution
- Debug screenshots and logs on failures
- Report comparison against the previous run

## How It Works

1. Load credentials and settings from `.env`
2. Open the ERP portal in Playwright
3. Log in and navigate to the attendance page
4. Extract overall and subject-wise attendance data
5. Save the snapshot to `attendance_history.json`
6. Generate a report in `reports/YYYY-MM-DD.md`
7. Send the report through the selected notifier
8. If attendance is below threshold, send an alert as well

## Project Structure

- `main.py` — command-line entry point and scheduler
- `attendance_scraper.py` — ERP login and attendance extraction
- `notifier.py` — notification delivery
- `storage.py` — history and report generation
- `config.py` — environment loading and app settings
- `CONTEXT.md` — project notes, fixes, and reference information
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

4. Verify the bot locally:

   `python main.py --check-now`

## Example `.env`

```dotenv
ERP_URL='https://erp.lbrce.ac.in/'
ERP_USERNAME='your_username'
ERP_PASSWORD='your_password'
HEADLESS='true'
ATTENDANCE_THRESHOLD='75'
NOTIFIER_METHOD='telegram'
TELEGRAM_BOT_TOKEN='your_bot_token'
TELEGRAM_CHAT_ID='your_chat_id'
```

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

## GitHub Actions Workflow

The repository includes `.github/workflows/attendance-monitor.yml`.

It:

- runs on a schedule at 6:00 PM IST
- supports manual runs with `workflow_dispatch`
- installs Python and Playwright Chromium
- runs the attendance check
- uploads logs and screenshots
- commits updated reports and attendance history back to the repository

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

## Notifications

### Telegram

Set:

- `NOTIFIER_METHOD='telegram'`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### Gmail

Set:

- `NOTIFIER_METHOD='gmail'`
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `GMAIL_TO`

### WhatsApp

Set:

- `NOTIFIER_METHOD='whatsapp'`
- `WHATSAPP_PHONE`
- `WHATSAPP_PROFILE_DIR` if you want a custom profile folder

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

## Troubleshooting

- If login fails, confirm `ERP_USERNAME` and `ERP_PASSWORD`.
- If Telegram messages do not arrive, confirm `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
- If Playwright fails to launch Chrome, set `BROWSER_EXECUTABLE_PATH` or install Chromium via Playwright.
- If the ERP page layout changes, update selectors in `attendance_scraper.py`.
- If a failure occurs, check the latest file in `screenshots/` and the log in `logs/app.log`.
