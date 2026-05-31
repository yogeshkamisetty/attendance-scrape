from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
import requests

from config import Settings


LOGGER = logging.getLogger(__name__)


class Notifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_report(self, subject: str, message: str) -> None:
        method = self.settings.notifier_method
        if method == "telegram":
            self._send_telegram(message)
        elif method == "gmail":
            self._send_gmail(subject, message)
        elif method == "whatsapp":
            self._send_whatsapp(message)
        else:
            LOGGER.info(
                "Notifier is disabled. Set NOTIFIER_METHOD=telegram, gmail, or whatsapp."
            )

    def _send_telegram(self, message: str) -> None:
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            LOGGER.warning("Telegram notifier is selected but token/chat id are missing")
            return

        url = (
            "https://api.telegram.org/bot"
            f"{self.settings.telegram_bot_token}/sendMessage"
        )
        response = requests.post(
            url,
            json={
                "chat_id": self.settings.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=30,
        )
        response.raise_for_status()
        LOGGER.info("Telegram report sent")

    def _send_gmail(self, subject: str, message: str) -> None:
        if (
            not self.settings.gmail_user
            or not self.settings.gmail_app_password
            or not self.settings.gmail_to
        ):
            LOGGER.warning("Gmail notifier is selected but email settings are missing")
            return

        email = EmailMessage()
        email["From"] = self.settings.gmail_user
        email["To"] = self.settings.gmail_to
        email["Subject"] = subject
        email.set_content(message)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(self.settings.gmail_user, self.settings.gmail_app_password)
            smtp.send_message(email)
        LOGGER.info("Gmail report sent")

    def setup_whatsapp_session(self) -> None:
        """Open WhatsApp Web visibly so the QR code can be scanned once."""
        with sync_playwright() as playwright:
            launch_args = self._whatsapp_launch_args(headless=False)
            context = playwright.chromium.launch_persistent_context(
                str(self.settings.whatsapp_profile_dir),
                **launch_args,
            )
            page = context.new_page()
            page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=60_000)
            LOGGER.info("Scan the WhatsApp QR code if prompted.")
            try:
                page.get_by_role("textbox").first.wait_for(timeout=180_000)
                LOGGER.info("WhatsApp Web session is ready")
            finally:
                context.close()

    def _send_whatsapp(self, message: str) -> None:
        if not self.settings.whatsapp_phone:
            LOGGER.warning("WhatsApp notifier is selected but WHATSAPP_PHONE is missing")
            return

        phone = "".join(ch for ch in self.settings.whatsapp_phone if ch.isdigit())
        if not phone:
            LOGGER.warning("WHATSAPP_PHONE does not contain a valid phone number")
            return

        url = f"https://web.whatsapp.com/send?phone={phone}&text={quote(message)}"
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                str(self.settings.whatsapp_profile_dir),
                **self._whatsapp_launch_args(headless=self.settings.headless),
            )
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                self._click_whatsapp_send(page)
                LOGGER.info("WhatsApp report sent")
            finally:
                context.close()

    def _click_whatsapp_send(self, page) -> None:
        selectors = [
            "button[aria-label='Send']",
            "span[data-icon='send']",
            "[data-testid='send']",
        ]
        last_error: Exception | None = None
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=45_000)
                locator.click()
                page.wait_for_timeout(2_000)
                return
            except Exception as exc:
                last_error = exc

        try:
            page.keyboard.press("Enter")
            page.wait_for_timeout(2_000)
            return
        except PlaywrightTimeoutError as exc:
            last_error = exc

        raise RuntimeError(
            "WhatsApp send button was not found. Run `python main.py --setup-whatsapp`."
        ) from last_error

    def _whatsapp_launch_args(self, headless: bool) -> dict:
        args = {
            "headless": headless,
            "viewport": {"width": 1280, "height": 900},
        }
        if self.settings.browser_executable_path:
            args["executable_path"] = self.settings.browser_executable_path
        return args
