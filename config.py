from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv, set_key


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
REPORTS_DIR = BASE_DIR / "reports"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
LOGS_DIR = BASE_DIR / "logs"
HISTORY_PATH = BASE_DIR / "attendance_history.json"
WHATSAPP_PROFILE_DIR = BASE_DIR / "whatsapp_profile"


@dataclass(frozen=True)
class Settings:
    erp_url: str
    username: str
    password: str
    headless: bool
    browser_executable_path: str | None
    attendance_threshold: float
    notifier_method: str
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    gmail_user: str | None
    gmail_app_password: str | None
    gmail_to: str | None
    whatsapp_phone: str | None
    whatsapp_profile_dir: Path


def ensure_directories() -> None:
    for path in (REPORTS_DIR, SCREENSHOTS_DIR, LOGS_DIR, WHATSAPP_PROFILE_DIR):
        path.mkdir(parents=True, exist_ok=True)
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text("[]\n", encoding="utf-8")


def write_initial_env(username: str, password: str) -> None:
    """Create or update the local .env with ERP credentials."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_PATH.exists():
        ENV_PATH.write_text("", encoding="utf-8")
    set_key(ENV_PATH, "ERP_URL", "https://erp.lbrce.ac.in/")
    set_key(ENV_PATH, "ERP_USERNAME", username)
    set_key(ENV_PATH, "ERP_PASSWORD", password)
    set_key(ENV_PATH, "HEADLESS", os.getenv("HEADLESS", "true"))
    set_key(ENV_PATH, "ATTENDANCE_THRESHOLD", os.getenv("ATTENDANCE_THRESHOLD", "75"))
    set_key(ENV_PATH, "NOTIFIER_METHOD", os.getenv("NOTIFIER_METHOD", "none"))


def load_settings() -> Settings:
    load_dotenv(ENV_PATH)
    default_chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    browser_path = os.getenv("BROWSER_EXECUTABLE_PATH")
    if not browser_path and Path(default_chrome).exists():
        browser_path = default_chrome

    return Settings(
        erp_url=os.getenv("ERP_URL", "https://erp.lbrce.ac.in/"),
        username=os.getenv("ERP_USERNAME", ""),
        password=os.getenv("ERP_PASSWORD", ""),
        headless=os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"},
        browser_executable_path=browser_path,
        attendance_threshold=float(os.getenv("ATTENDANCE_THRESHOLD", "75")),
        notifier_method=os.getenv("NOTIFIER_METHOD", "none").lower(),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        gmail_user=os.getenv("GMAIL_USER"),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD"),
        gmail_to=os.getenv("GMAIL_TO"),
        whatsapp_phone=os.getenv("WHATSAPP_PHONE"),
        whatsapp_profile_dir=Path(os.getenv("WHATSAPP_PROFILE_DIR", str(WHATSAPP_PROFILE_DIR))),
    )


def require_credentials(settings: Settings) -> None:
    if not settings.username or not settings.password:
        raise RuntimeError(
            f"ERP credentials are missing. Add ERP_USERNAME and ERP_PASSWORD to {ENV_PATH}."
        )
