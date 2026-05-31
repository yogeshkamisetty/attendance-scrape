from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from attendance_scraper import AttendanceSnapshot
from config import HISTORY_PATH, REPORTS_DIR, now_local


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_daily_snapshot(snapshot: AttendanceSnapshot) -> list[dict[str, Any]]:
    history = load_history()
    record = snapshot.to_dict()
    history = [entry for entry in history if entry.get("date") != snapshot.date]
    history.append(record)
    history.sort(key=lambda entry: entry.get("date", ""))
    HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return history


def previous_record(history: list[dict[str, Any]], current_date: str) -> dict[str, Any] | None:
    earlier = [entry for entry in history if entry.get("date", "") < current_date]
    if not earlier:
        return None
    return sorted(earlier, key=lambda entry: entry.get("date", ""))[-1]


def compare_with_previous(
    current: AttendanceSnapshot, previous: dict[str, Any] | None
) -> dict[str, Any]:
    if not previous:
        return {"overall_delta": None, "subject_deltas": {}}

    previous_overall = float(previous.get("overall_percentage", 0))
    current_subjects = {subject.subject: subject for subject in current.subjects}
    previous_subjects = {
        item.get("subject"): float(item.get("percentage", 0))
        for item in previous.get("subjects", [])
    }
    subject_deltas = {}
    for subject, current_data in current_subjects.items():
        if subject in previous_subjects:
            subject_deltas[subject] = round(current_data.percentage - previous_subjects[subject], 2)

    return {
        "overall_delta": round(current.overall_percentage - previous_overall, 2),
        "subject_deltas": subject_deltas,
    }


def generate_markdown_report(
    snapshot: AttendanceSnapshot, comparison: dict[str, Any], threshold: float
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    warnings = []
    if snapshot.shortage_subjects:
        warnings.append(
            f"Subjects below {threshold:g}%: " + ", ".join(snapshot.shortage_subjects)
        )

    overall_delta = comparison.get("overall_delta")
    if overall_delta is not None:
        if overall_delta < 0:
            warnings.append(f"Attendance dropped by {abs(overall_delta):.2f}%")
        elif overall_delta > 0:
            warnings.append(f"Attendance increased by {overall_delta:.2f}%")

    lines = [
        f"Date: {snapshot.date}",
        "",
        f"Overall Attendance: {snapshot.overall_percentage:.2f}%",
        "",
        f"Total Classes Conducted: {snapshot.total_classes_conducted}",
        f"Classes Attended: {snapshot.classes_attended}",
        "",
        "Subject-wise:",
    ]
    for subject in snapshot.subjects:
        lines.append(
            f"- {subject.subject}: {subject.percentage:.1f}% "
            f"({subject.classes_present}/{subject.classes_held})"
        )

    lines.extend(["", "Warnings:"])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- No warnings")

    lines.extend(["", f"Generated At: {now_local():%Y-%m-%d %H:%M:%S IST}"])
    path = REPORTS_DIR / f"{snapshot.date}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def generate_telegram_report(
    snapshot: AttendanceSnapshot, comparison: dict[str, Any], threshold: float
) -> str:
    theory, labs = _split_subject_groups(snapshot)
    generated_at = now_local().strftime("%I:%M %p - %b %d, %Y")

    lines = [
        "<b>📊 Attendance Bot</b>",
        "<b>Attendance Report</b>",
        escape(now_local().strftime("%B %d, %Y")),
        "",
        f"<b>Overall:</b> <code>{snapshot.overall_percentage:.2f}%</code>",
        f"<b>Conducted:</b> <code>{snapshot.total_classes_conducted}</code>",
        f"<b>Attended:</b> <code>{snapshot.classes_attended}</code>",
        "",
    ]

    if theory:
        lines.extend(["<b>THEORY</b>", *_format_subject_lines(theory), ""])
    if labs:
        lines.extend(["<b>LABS &amp; OTHERS</b>", *_format_subject_lines(labs), ""])

    if snapshot.shortage_subjects:
        shortage = ", ".join(
            f"{subject.subject} ({subject.percentage:.1f}%)"
            for subject in snapshot.subjects
            if subject.subject in snapshot.shortage_subjects
        )
        lines.append(f"⚠️ <b>Below {threshold:g}%:</b> {escape(shortage)}")

    overall_delta = comparison.get("overall_delta")
    if overall_delta is not None:
        if overall_delta < 0:
            lines.append(f"🔻 <b>Attendance dropped:</b> {abs(overall_delta):.2f}%")
        elif overall_delta > 0:
            lines.append(f"✅ <b>Attendance increased:</b> {overall_delta:.2f}%")

    lines.extend(["", f"<i>Generated at {escape(generated_at)} IST</i>"])
    return "\n".join(lines)


def generate_telegram_alert(snapshot: AttendanceSnapshot, threshold: float) -> str:
    lines = [
        "🚨 <b>Attendance alert</b>",
        "",
        f"<b>Date:</b> {escape(now_local().strftime('%B %d, %Y'))}",
        f"<b>Overall:</b> <code>{snapshot.overall_percentage:.2f}%</code>",
    ]
    if snapshot.shortage_subjects:
        lines.append("")
        for subject in snapshot.subjects:
            if subject.subject in snapshot.shortage_subjects:
                lines.append(
                    f"⚠️ {escape(subject.subject)} is below {threshold:g}% "
                    f"(<code>{subject.percentage:.1f}%</code>)"
                )
    return "\n".join(lines)


def _split_subject_groups(
    snapshot: AttendanceSnapshot,
) -> tuple[list[Any], list[Any]]:
    lab_keywords = ("lab", "association", "self learning", "tutorial")
    theory = []
    labs = []
    for subject in snapshot.subjects:
        target = labs if any(word in subject.subject.lower() for word in lab_keywords) else theory
        target.append(subject)
    return theory, labs


def _format_subject_lines(subjects: list[Any]) -> list[str]:
    return [
        (
            f"{_status_icon(subject.percentage)} "
            f"{escape(_shorten(subject.subject, 26))}\n"
            f"<code>{_bar(subject.percentage)}</code> "
            f"<b>{subject.percentage:.1f}%</b> "
            f"<code>{subject.classes_present}/{subject.classes_held}</code>"
        )
        for subject in subjects
    ]


def _status_icon(percentage: float) -> str:
    if percentage < 75:
        return "🔴"
    if percentage >= 90:
        return "🟢"
    return "🔵"


def _bar(percentage: float, width: int = 12) -> str:
    filled = round(width * max(0, min(percentage, 100)) / 100)
    return "█" * filled + "░" * (width - filled)


def _shorten(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"
