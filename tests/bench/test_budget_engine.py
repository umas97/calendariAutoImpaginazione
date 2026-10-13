# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test 27, in process: the month query, the preview of a sheet, the export of one (SPEC §14)."""

from __future__ import annotations

import datetime as dt
import random
import statistics
import time

import pytest

from cp.db.session import session_scope
from cp.domain import events as event_ops
from cp.domain.schemas import EventIn
from cp.export.jobs import run_export
from cp.export.request import ExportRequest
from cp.export.samples import add_events, sample_events, seed_taxonomy

pytestmark = pytest.mark.bench

FIRST, LAST = dt.date(2026, 9, 1), dt.date(2027, 6, 30)


def test_month_query_with_ten_thousand_events(api, measure):
    """10 000 events over ten years (SPEC §1); the calendar asks for a six-week grid."""
    with session_scope() as session:
        groups, categories = seed_taxonomy(session)
        rng = random.Random(3)
        start = dt.date(2020, 9, 1)
        for n in range(10_000):
            day = start + dt.timedelta(days=rng.randrange(3650))
            event_ops.create_event(
                session,
                EventIn(
                    title=f"Incontro {n}",
                    start_date=day,
                    start_time="15:00",
                    end_time="16:30",
                    place="Oratorio",
                    group_ids=[rng.choice(groups)],
                    category_ids=[rng.choice(categories)],
                ),
            )
    url = "/api/events?from=2026-09-28&to=2026-11-08"
    assert api.get(url).status_code == 200  # the first, cold
    times = []
    for _ in range(20):
        started = time.perf_counter()
        response = api.get(url)
        times.append(time.perf_counter() - started)
        assert response.status_code == 200 and len(response.json()) > 50
    median_ms = statistics.median(times) * 1000
    measure("query di 6 settimane, 10 000 eventi (mediana)", median_ms, 50, "ms")


@pytest.fixture
def sheets(api, xdg_home):
    """A group with 40 events and one with 30, both on the pastoral year."""
    with session_scope() as session:
        groups, categories = seed_taxonomy(session)
        add_events(session, sample_events(40, FIRST, LAST, [groups[0]], categories, seed=40))
        add_events(session, sample_events(30, FIRST, LAST, [groups[1]], categories, seed=30))
        add_events(session, sample_events(5, FIRST, LAST, [groups[2]], categories, seed=5))
    (xdg_home / "export").mkdir()
    return groups, categories


def request(group: int, categories: list[int], **fields) -> dict:
    return {
        "period": {"from": FIRST.isoformat(), "to": LAST.isoformat()},
        "mode": "per_group",
        "formats": ["pdf"],
        "dpi": 200,
        "selections": [{"group_id": group, "category_ids": categories}],
    } | fields


def test_preview_of_a_sheet_with_forty_events(api, sheets, measure):
    groups, categories = sheets
    # The Export tab warms the engine up when it opens: a small sheet pays for it here.
    assert api.post("/api/export/preview", json=request(groups[2], categories)).status_code == 200
    started = time.perf_counter()
    response = api.post("/api/export/preview", json=request(groups[0], categories))
    elapsed = time.perf_counter() - started
    assert response.status_code == 200, response.text
    assert response.json()["sheets"][0]["event_count"] == 40
    measure("anteprima di un foglio da 40 eventi", elapsed, 1.5, "s")


def test_export_of_one_sheet_pdf_and_png(api, sheets, xdg_home, measure):
    groups, categories = sheets
    api.post("/api/export/preview", json=request(groups[2], categories))  # warm, as above
    body = request(
        groups[1], categories, formats=["pdf", "png"], output_dir=str(xdg_home / "export")
    )
    started = time.perf_counter()
    job = run_export(ExportRequest.model_validate(body))
    elapsed = time.perf_counter() - started
    assert job.status == "done" and len(job.files) == 2, job.snapshot()
    measure("export di un foglio, PDF + PNG 200 dpi", elapsed, 3, "s")
