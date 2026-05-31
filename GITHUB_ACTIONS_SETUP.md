# GitHub Actions Setup

This workflow runs the attendance bot every day at 6:00 PM IST and sends the report through Telegram.

## 1. Push This Project To GitHub

Use the `attendance_bot` folder as the repository root. Your GitHub repo should show `main.py`, `requirements.txt`, and `.github/workflows/attendance-monitor.yml` directly in the top level.

Keep `.env` private. It is already ignored by `.gitignore`.

## 2. Add Repository Secrets

In GitHub:

`Repository -> Settings -> Secrets and variables -> Actions -> New repository secret`

Add these secrets:

- `ERP_USERNAME`
- `ERP_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 3. Enable Actions

Go to:

`Repository -> Actions`

Enable workflows if GitHub asks.

## 4. Test Manually

Open:

`Actions -> Attendance Monitor -> Run workflow`

The workflow should:

- install Python dependencies
- install Playwright Chromium
- log into ERP
- generate `attendance_history.json`
- generate `reports/YYYY-MM-DD.md`
- send Telegram report
- commit updated report/history back to the repo

## Notes

- GitHub schedules use UTC. The workflow uses `30 12 * * *`, which is 6:00 PM IST.
- GitHub scheduled workflows can start a few minutes late.
- If the college ERP blocks GitHub runner IP addresses, the local Windows Task Scheduler setup will be more reliable.
