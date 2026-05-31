from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime, time as day_time, timedelta
from pathlib import Path

from attendance_scraper import AttendanceScraper
from config import ensure_directories, load_settings, require_credentials, write_initial_env
from notifier import Notifier
from storage import (
    compare_with_previous,
    generate_markdown_report,
    generate_telegram_alert,
    generate_telegram_report,
    previous_record,
    save_daily_snapshot,
)


def setup_logging() -> None:
    log_path = Path(__file__).resolve().parent / "logs" / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def run_check() -> None:
    settings = load_settings()
    require_credentials(settings)

    scraper = AttendanceScraper(settings)
    snapshot = scraper.run()
    history = save_daily_snapshot(snapshot)
    comparison = compare_with_previous(snapshot, previous_record(history, snapshot.date))
    report_path = generate_markdown_report(snapshot, comparison)
    report_text = report_path.read_text(encoding="utf-8")

    notifier = Notifier(settings)
    notification_text = (
        generate_telegram_report(snapshot, comparison)
        if settings.notifier_method == "telegram"
        else report_text
    )
    notifier.send_report(f"Attendance Report - {snapshot.date}", notification_text)

    if snapshot.overall_percentage < settings.attendance_threshold or snapshot.shortage_subjects:
        alert_lines = [
            "Attendance Alert",
            f"Date: {snapshot.date}",
            f"Overall Attendance: {snapshot.overall_percentage:.2f}%",
        ]
        if snapshot.shortage_subjects:
            alert_lines.append("Below 75%: " + ", ".join(snapshot.shortage_subjects))
        alert_text = (
            generate_telegram_alert(snapshot)
            if settings.notifier_method == "telegram"
            else "\n".join(alert_lines)
        )
        notifier.send_report("Attendance Alert", alert_text)

    logging.getLogger(__name__).info("Attendance check completed. Report: %s", report_path)


def seconds_until_8_pm() -> float:
    now = datetime.now()
    target = datetime.combine(now.date(), day_time(hour=20, minute=0))
    if now >= target:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def run_scheduler() -> None:
    logger = logging.getLogger(__name__)
    logger.info("Scheduler started. Attendance check runs daily at 8:00 PM.")
    while True:
        sleep_for = seconds_until_8_pm()
        logger.info("Next attendance check in %.0f seconds", sleep_for)
        time.sleep(sleep_for)
        try:
            run_check()
        except Exception:
            logger.exception("Scheduled attendance check failed")


def install_windows_task() -> None:
    script_path = Path(__file__).resolve()
    command = f'"{sys.executable}" "{script_path}" --check-now'
    task_name = "LBRCE Attendance Monitor"
    subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN",
            task_name,
            "/TR",
            command,
            "/SC",
            "DAILY",
            "/ST",
            "20:00",
            "/F",
        ],
        check=True,
    )
    print(f"Installed Windows Task Scheduler job: {task_name}")


def setup_whatsapp() -> None:
    settings = load_settings()
    Notifier(settings).setup_whatsapp_session()
    print("WhatsApp Web setup completed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LBRCE ERP attendance monitoring bot")
    parser.add_argument("--check-now", action="store_true", help="Run the attendance check now")
    parser.add_argument(
        "--install-task",
        action="store_true",
        help="Install a Windows Task Scheduler job for daily 8:00 PM checks",
    )
    parser.add_argument(
        "--setup-whatsapp",
        action="store_true",
        help="Open WhatsApp Web for one-time QR login using the automation profile",
    )
    parser.add_argument("--init-env", action="store_true", help="Write credentials to .env")
    parser.add_argument("--username", help="ERP username for --init-env")
    parser.add_argument("--password", help="ERP password for --init-env")
    return parser.parse_args()


def main() -> None:
    ensure_directories()
    setup_logging()
    args = parse_args()

    if args.init_env:
        if not args.username or not args.password:
            raise SystemExit("--init-env requires --username and --password")
        write_initial_env(args.username, args.password)
        print("Local .env configured.")
        return

    if args.setup_whatsapp:
        setup_whatsapp()
    elif args.install_task:
        install_windows_task()
    elif args.check_now:
        run_check()
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
