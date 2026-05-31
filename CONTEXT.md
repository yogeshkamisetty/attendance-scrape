# Project Context

## Purpose
This project is an attendance monitoring automation for the LBRCE ERP portal. It logs in, reads attendance data, saves a daily snapshot, generates a markdown report, and sends notifications through Telegram, Gmail, or WhatsApp depending on configuration.

## Current State
The project is set up as a Git repository and pushed to GitHub at:
https://github.com/yogeshkamisetty/attendance-scrape.git

A GitHub Actions workflow has been added at:
.github/workflows/attendance-monitor.yml

## What Has Been Done
- Initialized the repository and pushed the code to GitHub.
- Added repository secrets guidance for:
  - ERP_USERNAME
  - ERP_PASSWORD
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_CHAT_ID
- Added the GitHub Actions workflow for scheduled and manual runs.
- Verified the bot runs locally with `python main.py --check-now`.
- Confirmed Telegram notifications are working.
- Generated a daily report in reports/.

## Issues Found and Resolved
### 1. Hardcoded attendance threshold text
The report and alert text previously said "75%" even though the threshold comes from `ATTENDANCE_THRESHOLD`.

Fixed by updating:
- `storage.py` report generation
- `storage.py` Telegram report formatting
- `storage.py` Telegram alert formatting
- `main.py` alert text

Now the displayed threshold always matches the configured value.

### 2. Scheduler time calculation used local naive time
The scheduler previously used `datetime.now()` without the app timezone.

Fixed by changing `seconds_until_8_pm()` in `main.py` to use `now_local()` from `config.py`, which follows `Asia/Kolkata`.

### 3. Missing workflow file in GitHub Actions
GitHub Actions initially showed the default onboarding screen because the repository had no workflow file.

Fixed by creating `.github/workflows/attendance-monitor.yml` with:
- `workflow_dispatch`
- daily schedule
- Python setup
- Playwright installation
- attendance run
- artifact upload
- commit/push of generated report files

## Important Files
- `main.py` — entry point, CLI, scheduler, one-time checks
- `attendance_scraper.py` — ERP login and attendance extraction
- `notifier.py` — Telegram, Gmail, WhatsApp delivery
- `storage.py` — history, comparison, report generation
- `config.py` — settings, paths, timezone, `.env` handling
- `requirements.txt` — Python dependencies
- `.github/workflows/attendance-monitor.yml` — GitHub Actions automation
- `.env` — local secrets and runtime settings; keep private
- `reports/` — generated markdown reports by date
- `screenshots/` — debug screenshots when scraping fails
- `logs/` — runtime logs
- `attendance_history.json` — saved daily snapshots

## Folder Structure Reference
- `attendance_bot/`
  - `main.py`
  - `attendance_scraper.py`
  - `notifier.py`
  - `storage.py`
  - `config.py`
  - `requirements.txt`
  - `.env`
  - `.github/workflows/attendance-monitor.yml`
  - `reports/`
  - `screenshots/`
  - `logs/`
  - `attendance_history.json`

## Operational Notes
- Keep `.env` out of Git.
- Add GitHub repository secrets instead of storing credentials in the workflow.
- Manual workflow runs are available under GitHub Actions once the workflow is present.
- The workflow is scheduled for 6:00 PM IST, which is 12:30 PM UTC.
- Local checks can be run with:
  - `python main.py --check-now`

## Future Reference
If the ERP layout changes, likely update points are:
- selectors in `attendance_scraper.py`
- notification formatting in `storage.py`
- workflow steps in `.github/workflows/attendance-monitor.yml`

