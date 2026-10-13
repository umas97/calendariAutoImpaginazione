# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Italian dates, times and periods: test 13 of SPEC §15 (tables of §8.2)."""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest

from cp.export import formatting as fmt

D = dt.date


def ev(start, end=None, all_day=False, start_time=None, end_time=None):
    return SimpleNamespace(
        start_date=start,
        end_date=end,
        all_day=all_day,
        start_time=start_time,
        end_time=end_time,
    )


@pytest.mark.parametrize(
    ("event", "date", "time"),
    [
        (ev(D(2026, 10, 17), start_time="15:00", end_time="16:30"), ("sab", "17"), "15:00 – 16:30"),
        (ev(D(2026, 10, 17), start_time="15:00"), ("sab", "17"), "ore 15:00"),
        (ev(D(2026, 10, 25), all_day=True), ("dom", "25"), "tutto il giorno"),
        (
            ev(D(2026, 8, 14), D(2026, 8, 16), all_day=True),
            ("ven–dom", "14–16"),
            "tutto il giorno",
        ),
        (
            ev(D(2026, 8, 14), D(2026, 8, 16), start_time="18:00", end_time="16:00"),
            ("ven–dom", "14–16"),
            "ven 18:00 – dom 16:00",
        ),
        (
            ev(D(2026, 4, 30), D(2026, 5, 2), start_time="18:00", end_time="16:00"),
            ("gio–sab", "30 apr – 2 mag"),
            "gio 18:00 – sab 16:00",
        ),
        (
            ev(D(2026, 12, 31), D(2027, 1, 2), all_day=True),
            ("gio–sab", "31 dic – 2 gen"),
            "tutto il giorno",
        ),
    ],
)
def test_columns(event, date, time):
    assert fmt.date_column(event) == date
    assert fmt.time_column(event) == time


def test_several_days_without_end_time():
    event = ev(D(2026, 8, 14), D(2026, 8, 16), start_time="18:00")
    assert fmt.time_column(event) == "ven 18:00 – dom"


def test_week_starts_on_monday_with_italian_names():
    monday = D(2026, 10, 12)
    names = [fmt.weekday(monday + dt.timedelta(days=i)) for i in range(7)]
    assert names == ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
    assert fmt.MONTHS_SHORT == (
        "gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"
    )  # fmt: skip


@pytest.mark.parametrize(
    ("first", "last", "label"),
    [
        (D(2026, 10, 1), D(2027, 6, 30), "ottobre 2026 – giugno 2027"),
        (D(2026, 10, 1), D(2026, 12, 31), "ottobre – dicembre 2026"),
        (D(2026, 10, 1), D(2026, 10, 31), "ottobre 2026"),
        (D(2027, 2, 1), D(2027, 2, 28), "febbraio 2027"),
        (D(2026, 10, 13), D(2026, 12, 20), "13 ottobre – 20 dicembre 2026"),
        (D(2026, 10, 13), D(2027, 1, 6), "13 ottobre 2026 – 6 gennaio 2027"),
        (D(2026, 10, 13), D(2026, 10, 20), "13 – 20 ottobre 2026"),
        (D(2026, 10, 13), D(2026, 10, 13), "13 ottobre 2026"),
        # Ends on a month's last day but does not start on a first: full dates.
        (D(2026, 10, 2), D(2026, 10, 31), "2 – 31 ottobre 2026"),
    ],
)
def test_period_label(first, last, label):
    assert fmt.period_label(first, last) == label


def test_month_heading_and_updated():
    assert fmt.month_heading(2026, 10) == "OTTOBRE 2026"
    assert fmt.updated_label(D(2026, 10, 3)) == "aggiornato al 03/10/2026"


@pytest.mark.parametrize("month", range(1, 13))
def test_pastoral_year_in_every_month(month):
    today = D(2026, month, 15)
    first, last = fmt.pastoral_year(today)
    if month >= 7:  # July and August: the one about to start; from September, the current one
        assert (first, last) == (D(2026, 9, 1), D(2027, 6, 30))
    else:
        assert (first, last) == (D(2025, 9, 1), D(2026, 6, 30))


def test_period_shortcuts():
    shortcuts = fmt.period_shortcuts(D(2026, 12, 13))
    assert shortcuts["this_month"] == (D(2026, 12, 1), D(2026, 12, 31))
    assert shortcuts["next_month"] == (D(2027, 1, 1), D(2027, 1, 31))
    assert shortcuts["next_3_months"] == (D(2026, 12, 1), D(2027, 2, 28))
    assert shortcuts["pastoral_year"] == (D(2026, 9, 1), D(2027, 6, 30))
