# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``/api/export``: counts, preview, export jobs (SPEC §8.7, §9.1).

Counts, preview and files all come from ``export/selection.py::build_sheets``
(SPEC §5.1).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, Response, status

from .. import folders
from ..export import formatting, render
from ..export.jobs import runner
from ..export.preview import store
from ..export.request import ExportRequest, check_request
from ..export.selection import event_counts

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/options")
def options() -> dict[str, Any]:
    """The period shortcuts for today, the home and the default folder; readies the PDF engine."""
    render.warm_up()
    shortcuts = formatting.period_shortcuts(dt.date.today())
    return {
        "shortcuts": {
            key: {"from": first.isoformat(), "to": last.isoformat()}
            for key, (first, last) in shortcuts.items()
        },
        "default_dir": str(folders.default_export_dir()),
        "home": str(folders.home()),
        "busy": runner.busy(),
    }


class CountsRequest(ExportRequest):
    #: The ticked groups: the complete calendar counts only these (default: all).
    included: list[int] | None = None


@router.post("/counts")
def counts(body: CountsRequest) -> dict[str, Any]:
    """Events per group, ticked or not, and in the complete calendar, for the period."""
    return event_counts(check_request(body, needs_output=False), body.included)


@router.post("/preview")
def preview(body: ExportRequest) -> dict[str, Any]:
    return store.preview(body)


@router.get("/preview/{generation}/{index}.png")
def preview_image(generation: int, index: int) -> Response:
    return Response(
        store.image(generation, index),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def start_export(body: ExportRequest) -> dict[str, Any]:
    return runner.start(body).snapshot()


@router.get("/jobs/{job_id}")
def job(job_id: str) -> dict[str, Any]:
    return runner.get(job_id).snapshot()
