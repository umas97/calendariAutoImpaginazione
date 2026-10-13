# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Events: create, change, delete, duplicate, query by range (SPEC §7).

:func:`chronological_key` is *the* order of events, here and in the export
(SPEC §5.1): nothing else sorts events.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Iterable
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import Event, EventCategory, EventGroup, now
from .errors import Invalid, NotFound
from .schemas import EventIn, EventOut
from .validation import MAX_DAYS, CleanEvent, check_references, clean_event

MAX_DUPLICATES = 100
PLACES_LIMIT = 10


class Sortable(Protocol):
    id: int
    title: str
    start_date: dt.date
    all_day: bool
    start_time: str | None
    end_time: str | None


def chronological_key(event: Sortable, clip_from: dt.date | None = None) -> tuple:
    """The sort key of an event (SPEC §7.3; test 7).

    ``clip_from`` is the first day of an export period: an event that began
    earlier sorts as if it began that day, under the period's first month.
    """
    start = event.start_date
    if clip_from is not None and start < clip_from:
        start = clip_from
    return (
        start,
        not event.all_day,
        event.start_time or "",
        event.end_time is None,
        event.end_time or "",
        event.title.casefold(),
        event.id,
    )


def to_out(event: Event) -> EventOut:
    return EventOut(
        id=event.id,
        title=event.title,
        start_date=event.start_date,
        end_date=event.end_date,
        all_day=event.all_day,
        start_time=event.start_time,
        end_time=event.end_time,
        place=event.place,
        notes=event.notes,
        group_ids=event.group_ids,
        category_ids=event.category_ids,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def events_in_range(session: Session, first: dt.date, last: dt.date) -> list[Event]:
    """Events overlapping ``[first, last]``, both ends included, in chronological order.

    An event is in if it starts by ``last`` and ends on or after ``first``. No
    event lasts more than ``MAX_DAYS``, so the start is also bounded from below,
    which keeps the query on the ``start_date`` index.
    """
    if last < first:
        raise Invalid("La fine dell'intervallo è prima dell'inizio.", field="to")
    query = select(Event).where(
        Event.start_date <= last,
        Event.start_date >= first - dt.timedelta(days=MAX_DAYS),
        func.coalesce(Event.end_date, Event.start_date) >= first,
    )
    return sorted(session.scalars(query), key=chronological_key)


def get_event(session: Session, event_id: int) -> Event:
    event = session.get(Event, event_id)
    if event is None:
        raise NotFound(f"Evento inesistente: {event_id}.")
    return event


def _apply(event: Event, clean: CleanEvent) -> None:
    event.title = clean.title
    event.start_date = clean.start_date
    event.end_date = clean.end_date
    event.all_day = clean.all_day
    event.start_time = clean.start_time
    event.end_time = clean.end_time
    event.place = clean.place
    event.notes = clean.notes
    _set_links(event, clean.group_ids, clean.category_ids)


def _set_links(event: Event, group_ids: Iterable[int], category_ids: Iterable[int]) -> None:
    """Replace the event's links, keeping the rows that do not change."""
    wanted_groups = list(group_ids)
    existing = {link.group_id: link for link in event.group_links}
    event.group_links = [existing.get(gid) or EventGroup(group_id=gid) for gid in wanted_groups]
    existing_c = {link.category_id: link for link in event.category_links}
    links = []
    for position, cid in enumerate(category_ids):
        link = existing_c.get(cid) or EventCategory(category_id=cid)
        link.position = position
        links.append(link)
    event.category_links = links


def create_event(session: Session, data: EventIn) -> Event:
    clean = clean_event(data)
    check_references(session, clean)
    event = Event()
    _apply(event, clean)
    session.add(event)
    session.flush()
    return event


def update_event(session: Session, event_id: int, data: EventIn) -> Event:
    event = get_event(session, event_id)
    clean = clean_event(data)
    check_references(session, clean, had_groups=event.group_ids, had_categories=event.category_ids)
    _apply(event, clean)
    # The links alone do not dirty the row; the timestamp must move anyway.
    event.updated_at = now()
    session.flush()
    return event


def delete_event(session: Session, event_id: int) -> None:
    session.delete(get_event(session, event_id))
    session.flush()


def duplicate_event(session: Session, event_id: int, dates: Iterable[dt.date]) -> list[int]:
    """Copy an event onto each date, keeping times, length, place, notes and links (test 8)."""
    source = get_event(session, event_id)
    unique = sorted(set(dates))
    if not unique:
        raise Invalid("Scegli almeno una data.", field="dates")
    if len(unique) > MAX_DUPLICATES:
        raise Invalid(f"Puoi duplicare su al massimo {MAX_DUPLICATES} date.", field="dates")
    length = (source.end_date - source.start_date) if source.end_date else None
    copies = []
    for day in unique:
        copy = Event(
            title=source.title,
            start_date=day,
            end_date=day + length if length is not None else None,
            all_day=source.all_day,
            start_time=source.start_time,
            end_time=source.end_time,
            place=source.place,
            notes=source.notes,
        )
        _set_links(copy, source.group_ids, source.category_ids)
        copies.append(copy)
    session.add_all(copies)
    session.flush()
    return [copy.id for copy in copies]


def places(session: Session, q: str = "", limit: int = PLACES_LIMIT) -> list[str]:
    """Places already used, most frequent first, for the dialog's autocompletion (§7.5).

    Spellings that differ only in case count as one place, shown in their most
    frequent spelling. ``q`` matches as a prefix first, then anywhere.
    """
    rows = session.execute(
        select(Event.place, func.count()).where(Event.place != "").group_by(Event.place)
    )
    totals: Counter[str] = Counter()
    spellings: dict[str, Counter[str]] = {}
    for place, count in rows:
        key = place.casefold()
        totals[key] += count
        spellings.setdefault(key, Counter())[place] += count
    needle = q.strip().casefold()
    matches = [key for key in totals if needle in key]
    matches.sort(key=lambda key: (not key.startswith(needle), -totals[key], key))
    return [spellings[key].most_common(1)[0][0] for key in matches[:limit]]
