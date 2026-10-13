# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The rules an event must satisfy (SPEC §7.2; tests 4-5).

Two steps. :func:`clean_event` checks the form on its own and normalizes it
(stripped text, no end date equal to the start, no times on an all-day event,
no repeated ids). :func:`check_references` then checks the group and category
ids against the database. Both collect every problem before raising, so the
dialog can mark all the wrong fields at once.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Category, Group
from .errors import FieldError, InvalidFields
from .schemas import EventIn

TITLE_MAX = 120
PLACE_MAX = 120
NOTES_MAX = 2000
#: Counted inclusively: from the 1st to the 31st of a month is allowed.
MAX_DAYS = 31

_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

MSG_TITLE = "Il titolo è obbligatorio (massimo 120 caratteri)."
MSG_START_TIME = "Indica l'ora di inizio, oppure scegli “Tutto il giorno”."
MSG_TIME_FORMAT = "Ora non valida: usa il formato HH:MM."
MSG_END_BEFORE_START_TIME = "L'ora di fine deve essere dopo l'inizio."
MSG_END_BEFORE_START_DATE = "La data di fine è prima della data di inizio."
MSG_TOO_LONG = "Un evento può durare al massimo 31 giorni."
MSG_PLACE = "Il luogo può avere al massimo 120 caratteri."
MSG_NOTES = "Le note possono avere al massimo 2000 caratteri."
MSG_NO_GROUP = "Scegli almeno un gruppo."
MSG_NO_CATEGORY = "Scegli almeno una categoria."


@dataclass
class CleanEvent:
    title: str
    start_date: dt.date
    end_date: dt.date | None
    all_day: bool
    start_time: str | None
    end_time: str | None
    place: str
    notes: str
    group_ids: list[int]
    category_ids: list[int]

    @property
    def last_date(self) -> dt.date:
        return self.end_date or self.start_date


def _unique(ids: Iterable[int]) -> list[int]:
    return list(dict.fromkeys(ids))


def clean_event(data: EventIn) -> CleanEvent:
    """Normalize ``data`` and check the rules that need no database."""
    problems: list[FieldError] = []

    title = data.title.strip()
    if not title or len(title) > TITLE_MAX:
        problems.append(FieldError("title", MSG_TITLE))

    end_date = data.end_date if data.end_date != data.start_date else None
    if end_date is not None and end_date < data.start_date:
        problems.append(FieldError("end_date", MSG_END_BEFORE_START_DATE))
    elif end_date is not None and (end_date - data.start_date).days + 1 > MAX_DAYS:
        problems.append(FieldError("end_date", MSG_TOO_LONG))

    start_time = end_time = None
    if not data.all_day:
        start_time = (data.start_time or "").strip() or None
        end_time = (data.end_time or "").strip() or None
        if start_time is None:
            problems.append(FieldError("start_time", MSG_START_TIME))
        elif not _TIME.match(start_time):
            problems.append(FieldError("start_time", MSG_TIME_FORMAT))
        if end_time is not None and not _TIME.match(end_time):
            problems.append(FieldError("end_time", MSG_TIME_FORMAT))
        elif (
            end_time is not None
            and start_time is not None
            and _TIME.match(start_time)
            and end_date is None
            and end_time <= start_time
        ):
            problems.append(FieldError("end_time", MSG_END_BEFORE_START_TIME))

    place = data.place.strip()
    if len(place) > PLACE_MAX:
        problems.append(FieldError("place", MSG_PLACE))

    # Line breaks inside are the user's; only the ends are trimmed.
    notes = data.notes.strip()
    if len(notes) > NOTES_MAX:
        problems.append(FieldError("notes", MSG_NOTES))

    group_ids = _unique(data.group_ids)
    if not group_ids:
        problems.append(FieldError("group_ids", MSG_NO_GROUP))
    category_ids = _unique(data.category_ids)
    if not category_ids:
        problems.append(FieldError("category_ids", MSG_NO_CATEGORY))

    if problems:
        raise InvalidFields(problems)
    return CleanEvent(
        title=title,
        start_date=data.start_date,
        end_date=end_date,
        all_day=data.all_day,
        start_time=start_time,
        end_time=end_time,
        place=place,
        notes=notes,
        group_ids=group_ids,
        category_ids=category_ids,
    )


def check_references(
    session: Session,
    event: CleanEvent,
    *,
    had_groups: Iterable[int] = (),
    had_categories: Iterable[int] = (),
) -> None:
    """Every id must exist; archived ones only if the event already had them."""
    problems: list[FieldError] = []
    groups = {g.id: g for g in session.scalars(select(Group).where(Group.id.in_(event.group_ids)))}
    categories = {
        c.id: c
        for c in session.scalars(select(Category).where(Category.id.in_(event.category_ids)))
    }
    kept_groups = set(had_groups)
    kept_categories = set(had_categories)
    for group_id in event.group_ids:
        group = groups.get(group_id)
        if group is None:
            problems.append(FieldError("group_ids", f"Gruppo inesistente: {group_id}."))
        elif group.archived and group_id not in kept_groups:
            problems.append(
                FieldError(
                    "group_ids",
                    f"Il gruppo “{group.name}” è archiviato: ripristinalo per usarlo.",
                )
            )
    for category_id in event.category_ids:
        category = categories.get(category_id)
        if category is None:
            problems.append(FieldError("category_ids", f"Categoria inesistente: {category_id}."))
        elif category.archived and category_id not in kept_categories:
            problems.append(
                FieldError(
                    "category_ids",
                    f"La categoria “{category.name}” è archiviata: ripristinala per usarla.",
                )
            )
    if problems:
        raise InvalidFields(problems)
