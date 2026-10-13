# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``/api/events`` and ``/api/places`` (SPEC §7)."""

from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from ..db.session import session_scope
from ..domain import events
from ..domain.schemas import DuplicateIn, DuplicateOut, EventIn, EventOut

router = APIRouter(tags=["events"])


@router.get("/api/events")
def list_events(
    first: Annotated[dt.date, Query(alias="from")],
    last: Annotated[dt.date, Query(alias="to")],
) -> list[EventOut]:
    """Events overlapping ``[from, to]`` (both included), in chronological order."""
    with session_scope() as session:
        return [events.to_out(e) for e in events.events_in_range(session, first, last)]


@router.get("/api/events/{event_id}")
def get_event(event_id: int) -> EventOut:
    with session_scope() as session:
        return events.to_out(events.get_event(session, event_id))


@router.post("/api/events", status_code=status.HTTP_201_CREATED)
def create_event(body: EventIn) -> EventOut:
    with session_scope() as session:
        return events.to_out(events.create_event(session, body))


@router.put("/api/events/{event_id}")
def update_event(event_id: int, body: EventIn) -> EventOut:
    with session_scope() as session:
        return events.to_out(events.update_event(session, event_id, body))


@router.delete("/api/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int) -> Response:
    with session_scope() as session:
        events.delete_event(session, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/events/{event_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_event(event_id: int, body: DuplicateIn) -> DuplicateOut:
    with session_scope() as session:
        return DuplicateOut(ids=events.duplicate_event(session, event_id, body.dates))


@router.get("/api/places")
def list_places(q: str = "") -> list[str]:
    with session_scope() as session:
        return events.places(session, q)
