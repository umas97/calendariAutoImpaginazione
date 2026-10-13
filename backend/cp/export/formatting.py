# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dates, times and periods written in Italian (SPEC §8.2; test 13).

The names come from the tables below, never from the system locale, which may
be missing (SPEC §4, decision 12). Every dash between two values is an en dash.
"""

from __future__ import annotations

import calendar
import datetime as dt
from typing import Protocol

DAYS = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")
MONTHS = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)
MONTHS_SHORT = tuple(name[:3] for name in MONTHS)

DASH = "–"
SPACED_DASH = f" {DASH} "
ALL_DAY = "tutto il giorno"


class Timed(Protocol):
    start_date: dt.date
    end_date: dt.date | None
    all_day: bool
    start_time: str | None
    end_time: str | None


def weekday(day: dt.date) -> str:
    return DAYS[day.weekday()]


def date_column(event: Timed) -> tuple[str, str]:
    """The two lines of the date column: weekday(s), then day number(s)."""
    start, end = event.start_date, event.end_date
    if end is None or end == start:
        return weekday(start), str(start.day)
    days = f"{weekday(start)}{DASH}{weekday(end)}"
    if (start.year, start.month) == (end.year, end.month):
        return days, f"{start.day}{DASH}{end.day}"
    return days, f"{start.day} {MONTHS_SHORT[start.month - 1]}{SPACED_DASH}" + (
        f"{end.day} {MONTHS_SHORT[end.month - 1]}"
    )


def time_column(event: Timed) -> str:
    if event.all_day or event.start_time is None:
        return ALL_DAY
    if event.end_date is not None and event.end_date != event.start_date:
        start = f"{weekday(event.start_date)} {event.start_time}"
        end = weekday(event.end_date)
        if event.end_time is not None:
            end = f"{end} {event.end_time}"
        return f"{start}{SPACED_DASH}{end}"
    if event.end_time is not None:
        return f"{event.start_time}{SPACED_DASH}{event.end_time}"
    return f"ore {event.start_time}"


def _last_day(day: dt.date) -> int:
    return calendar.monthrange(day.year, day.month)[1]


def _whole_months(first: dt.date, last: dt.date) -> bool:
    return first.day == 1 and last.day == _last_day(last)


def _long(day: dt.date, *, year: bool) -> str:
    text = f"{day.day} {MONTHS[day.month - 1]}"
    return f"{text} {day.year}" if year else text


def period_label(first: dt.date, last: dt.date) -> str:
    """The period under the sheet's title: whole months by name, else full dates."""
    if _whole_months(first, last):
        a, b = MONTHS[first.month - 1], MONTHS[last.month - 1]
        if (first.year, first.month) == (last.year, last.month):
            return f"{a} {first.year}"
        if first.year == last.year:
            return f"{a}{SPACED_DASH}{b} {last.year}"
        return f"{a} {first.year}{SPACED_DASH}{b} {last.year}"
    if first == last:
        return _long(first, year=True)
    if first.year != last.year:
        return f"{_long(first, year=True)}{SPACED_DASH}{_long(last, year=True)}"
    if first.month == last.month:
        return f"{first.day}{SPACED_DASH}{_long(last, year=True)}"
    return f"{_long(first, year=False)}{SPACED_DASH}{_long(last, year=True)}"


def month_heading(year: int, month: int) -> str:
    return f"{MONTHS[month - 1]} {year}".upper()


def updated_label(day: dt.date) -> str:
    return f"aggiornato al {day:%d/%m/%Y}"


# --- the period shortcuts of the Export screen (SPEC §9.1) ---------------------


def month_span(year: int, month: int, months: int = 1) -> tuple[dt.date, dt.date]:
    """From the first day of ``year-month`` to the last day ``months`` months later."""
    first = dt.date(year, month, 1)
    index = year * 12 + month - 1 + months - 1
    end_year, end_month = divmod(index, 12)
    last = dt.date(end_year, end_month + 1, calendar.monthrange(end_year, end_month + 1)[1])
    return first, last


def pastoral_year(today: dt.date) -> tuple[dt.date, dt.date]:
    """1 September – 30 June around ``today``; in July and August, the one about to start."""
    start_year = today.year if today.month >= 7 else today.year - 1
    return dt.date(start_year, 9, 1), dt.date(start_year + 1, 6, 30)


def period_shortcuts(today: dt.date) -> dict[str, tuple[dt.date, dt.date]]:
    following = dt.date(today.year, today.month, 1) + dt.timedelta(days=31)
    return {
        "this_month": month_span(today.year, today.month),
        "next_month": month_span(following.year, following.month),
        "next_3_months": month_span(today.year, today.month, 3),
        "pastoral_year": pastoral_year(today),
    }
