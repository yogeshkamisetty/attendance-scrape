from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from config import SCREENSHOTS_DIR, Settings, now_local


LOGGER = logging.getLogger(__name__)


@dataclass
class SubjectAttendance:
    subject: str
    classes_held: int
    classes_present: int
    percentage: float


@dataclass
class AttendanceSnapshot:
    date: str
    overall_percentage: float
    total_classes_conducted: int
    classes_attended: int
    shortage_subjects: list[str]
    subjects: list[SubjectAttendance]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["subjects"] = [asdict(subject) for subject in self.subjects]
        return payload


class AttendanceScraper:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self) -> AttendanceSnapshot:
        with sync_playwright() as playwright:
            launch_args: dict[str, Any] = {"headless": self.settings.headless}
            if self.settings.browser_executable_path:
                launch_args["executable_path"] = self.settings.browser_executable_path

            browser = playwright.chromium.launch(**launch_args)
            page = browser.new_page(viewport={"width": 1440, "height": 1600})
            try:
                self._load_with_retry(page, self.settings.erp_url)
                self._login_with_retry(page)
                self._open_attendance_page(page)
                return self._extract_attendance(page)
            finally:
                browser.close()

    def _load_with_retry(self, page: Page, url: str) -> None:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                LOGGER.info("Loading ERP page, attempt %s", attempt)
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                return
            except Exception as exc:
                last_error = exc
                LOGGER.warning("ERP page load attempt %s failed: %s", attempt, exc)
        self._screenshot(page, "page-load-failed")
        raise RuntimeError("ERP page failed to load after 3 attempts") from last_error

    def _login_with_retry(self, page: Page) -> None:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                LOGGER.info("Logging into ERP, attempt %s", attempt)
                self._fill_login_form(page)
                self._click_login(page)
                page.wait_for_timeout(2_500)
                if self._is_logged_in(page):
                    LOGGER.info("ERP login succeeded")
                    return
                raise RuntimeError("Login did not reach an authenticated page")
            except Exception as exc:
                last_error = exc
                LOGGER.warning("ERP login attempt %s failed: %s", attempt, exc)
                self._load_with_retry(page, self.settings.erp_url)

        self._screenshot(page, "login-failed")
        raise RuntimeError("ERP login failed after 3 attempts") from last_error

    def _fill_login_form(self, page: Page) -> None:
        username = page.locator("#txtusername, input[name='txtusername']").first
        password = page.locator("#txtpassword, input[name='txtpassword']").first
        username.wait_for(state="visible", timeout=10_000)
        password.wait_for(state="visible", timeout=10_000)
        username.fill(self.settings.username)
        password.fill(self.settings.password)

    def _click_login(self, page: Page) -> None:
        candidates = [
            page.get_by_role("button", name=re.compile(r"login", re.I)),
            page.locator("button:has-text('Login')"),
            page.locator("input[type='submit'][value*='Login' i]"),
        ]
        for candidate in candidates:
            if candidate.count() > 0:
                candidate.first.click()
                return
        raise RuntimeError("Login button was not found")

    def _is_logged_in(self, page: Page) -> bool:
        text = self._body_text(page).lower()
        return "log out" in text or "student progress" in text or "pay fee" in text

    def _open_attendance_page(self, page: Page) -> None:
        history_url = self.settings.erp_url.rstrip("/") + "/Discipline/StudentHistory.aspx"
        self._load_with_retry(page, history_url)
        page.wait_for_timeout(1_500)
        self._select_latest_term_if_needed(page)

        attendance_button = page.locator(
            "#ContentPlaceHolder1_btnAtt, input[type='submit'][value*='Attendance' i]"
        ).first
        try:
            attendance_button.wait_for(state="visible", timeout=10_000)
            attendance_button.click()
            page.wait_for_timeout(2_500)
        except Exception as exc:
            self._screenshot(page, "attendance-button-not-found")
            raise RuntimeError("Attendance page/control could not be found") from exc

        try:
            page.locator("#ContentPlaceHolder1_gvStdHistory").wait_for(
                state="visible", timeout=15_000
            )
        except PlaywrightTimeoutError as exc:
            self._screenshot(page, "attendance-layout-changed")
            raise RuntimeError("Attendance table was not found; ERP layout may have changed") from exc

    def _select_latest_term_if_needed(self, page: Page) -> None:
        # The ERP currently defaults to the latest available year/semester.
        for selector in ("#ContentPlaceHolder1_ddlYear", "#ContentPlaceHolder1_ddlsem"):
            control = page.locator(selector)
            if control.count() == 0:
                continue
            current = control.input_value()
            if current and current != "0":
                continue
            options = control.locator("option").evaluate_all(
                "els => els.map(o => o.value).filter(v => v && v !== '0')"
            )
            if options:
                control.select_option(options[-1])
                page.wait_for_timeout(1_000)

    def _extract_attendance(self, page: Page) -> AttendanceSnapshot:
        body_text = self._body_text(page)
        overall_match = re.search(r"Overall\(%\)\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%", body_text)
        if not overall_match:
            self._screenshot(page, "overall-attendance-missing")
            raise RuntimeError("Overall attendance percentage was not found")

        rows = page.locator("#ContentPlaceHolder1_gvStdHistory tr").evaluate_all(
            """
            rows => rows.map(row =>
                Array.from(row.cells).map(cell => cell.innerText.trim())
            )
            """
        )
        subjects = self._parse_subject_rows(rows)
        shortage_subjects = [
            subject.subject
            for subject in subjects
            if subject.percentage < self.settings.attendance_threshold
        ]

        return AttendanceSnapshot(
            date=now_local().date().isoformat(),
            overall_percentage=float(overall_match.group(1)),
            total_classes_conducted=sum(subject.classes_held for subject in subjects),
            classes_attended=sum(subject.classes_present for subject in subjects),
            shortage_subjects=shortage_subjects,
            subjects=subjects,
        )

    def _parse_subject_rows(self, rows: list[list[str]]) -> list[SubjectAttendance]:
        if not rows:
            raise RuntimeError("Attendance table is empty")

        header = [cell.strip().lower() for cell in rows[0]]
        try:
            subject_idx = self._header_index(header, "subject")
            held_idx = self._header_index(header, "classes held")
            present_idx = self._header_index(header, "classes present")
            percent_idx = self._header_index(header, "attendance percentage")
        except ValueError as exc:
            raise RuntimeError("Attendance table columns changed") from exc

        subjects: list[SubjectAttendance] = []
        for row in rows[1:]:
            if len(row) <= max(subject_idx, held_idx, present_idx, percent_idx):
                continue
            subject = row[subject_idx].strip()
            if not subject:
                continue
            subjects.append(
                SubjectAttendance(
                    subject=subject,
                    classes_held=int(float(row[held_idx])),
                    classes_present=int(float(row[present_idx])),
                    percentage=self._parse_percentage(row[percent_idx]),
                )
            )
        return subjects

    @staticmethod
    def _header_index(header: list[str], expected: str) -> int:
        for index, value in enumerate(header):
            if expected in value:
                return index
        raise ValueError(expected)

    @staticmethod
    def _parse_percentage(value: str) -> float:
        match = re.search(r"[0-9]+(?:\.[0-9]+)?", value)
        if not match:
            return 0.0
        return float(match.group(0))

    @staticmethod
    def _body_text(page: Page) -> str:
        try:
            return page.locator("body").inner_text(timeout=10_000)
        except Exception:
            return ""

    def _screenshot(self, page: Page, reason: str) -> Path:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOTS_DIR / f"{now_local():%Y%m%d-%H%M%S}-{reason}.png"
        try:
            page.screenshot(path=str(path), full_page=True)
            LOGGER.info("Saved screenshot: %s", path)
        except Exception as exc:
            LOGGER.warning("Failed to save screenshot for %s: %s", reason, exc)
        return path
