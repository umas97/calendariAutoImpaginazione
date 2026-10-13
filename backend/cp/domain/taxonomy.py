# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Groups and categories (SPEC §6; tests 2-3, 9-11).

The two kinds behave the same -- names, order, archive, deletion with orphans --
so one set of functions serves both, driven by a :class:`Kind`. Categories add
a colour, and their links have an order (the first is the main category), which
deletion must keep contiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from ..db.models import Category, Event, EventCategory, EventGroup, Group
from .errors import Conflict, Invalid, NotFound
from .palette import next_color, normalize_color

NAME_MAX = 60

OrphanPolicy = Literal["reassign", "delete"]


@dataclass(frozen=True)
class Kind:
    model: type[Group] | type[Category]
    link: type[EventGroup] | type[EventCategory]
    link_column: str
    #: Italian wording, with the right gender.
    not_found: str
    duplicate: str
    orphans_one: str
    orphans_many: str
    bad_target: str

    def link_col(self) -> InstrumentedAttribute[int]:
        return getattr(self.link, self.link_column)


GROUPS = Kind(
    model=Group,
    link=EventGroup,
    link_column="group_id",
    not_found="Gruppo inesistente: {id}.",
    duplicate="Esiste già un gruppo chiamato “{name}”.",
    orphans_one="1 evento ha solo questo gruppo.",
    orphans_many="{n} eventi hanno solo questo gruppo.",
    bad_target="Scegli un altro gruppo esistente in cui spostare gli eventi.",
)

CATEGORIES = Kind(
    model=Category,
    link=EventCategory,
    link_column="category_id",
    not_found="Categoria inesistente: {id}.",
    duplicate="Esiste già una categoria chiamata “{name}”.",
    orphans_one="1 evento ha solo questa categoria.",
    orphans_many="{n} eventi hanno solo questa categoria.",
    bad_target="Scegli un'altra categoria esistente in cui spostare gli eventi.",
)

MSG_NAME = "Il nome è obbligatorio (massimo 60 caratteri)."
MSG_COLOR = "Colore non valido: usa il formato #RRGGBB."
MSG_REORDER = "L'elenco da riordinare non corrisponde agli elementi esistenti."


def clean_name(raw: str) -> str:
    """Stripped, inner runs of spaces collapsed to one, 1-60 characters."""
    name = " ".join(raw.split())
    if not name or len(name) > NAME_MAX:
        raise Invalid(MSG_NAME, field="name")
    return name


def clean_color(raw: str) -> str:
    color = normalize_color(raw)
    if color is None:
        raise Invalid(MSG_COLOR, field="color")
    return color


def _get(session: Session, kind: Kind, item_id: int) -> Group | Category:
    item = session.get(kind.model, item_id)
    if item is None:
        raise NotFound(kind.not_found.format(id=item_id))
    return item


def _check_unique(session: Session, kind: Kind, name: str, own_id: int | None = None) -> None:
    query = select(kind.model.name).where(kind.model.name_key == name.casefold())
    if own_id is not None:
        query = query.where(kind.model.id != own_id)
    existing = session.scalar(query)
    if existing is not None:
        raise Conflict(kind.duplicate.format(name=existing), field="name")


def event_counts(session: Session, kind: Kind) -> dict[int, int]:
    column = kind.link_col()
    return dict(session.execute(select(column, func.count()).group_by(column)).all())


def list_items(
    session: Session, kind: Kind, include_archived: bool = False
) -> list[tuple[Group | Category, int]]:
    """Items in the user's order, each with the number of events linked to it."""
    query = select(kind.model).order_by(kind.model.position, kind.model.id)
    if not include_archived:
        query = query.where(kind.model.archived.is_(False))
    counts = event_counts(session, kind)
    return [(item, counts.get(item.id, 0)) for item in session.scalars(query)]


def create_item(
    session: Session, kind: Kind, name: str, color: str | None = None
) -> Group | Category:
    name = clean_name(name)
    _check_unique(session, kind, name)
    position = (session.scalar(select(func.max(kind.model.position))) or 0) + 1
    item = kind.model(name=name, name_key=name.casefold(), position=position, archived=False)
    if kind is CATEGORIES:
        if color is None:
            item.color = next_color(session.scalars(select(Category.color)))
        else:
            item.color = clean_color(color)
    session.add(item)
    session.flush()
    return item


def update_item(
    session: Session,
    kind: Kind,
    item_id: int,
    *,
    name: str | None = None,
    color: str | None = None,
    archived: bool | None = None,
) -> Group | Category:
    item = _get(session, kind, item_id)
    if name is not None:
        name = clean_name(name)
        _check_unique(session, kind, name, own_id=item_id)
        item.name = name
        item.name_key = name.casefold()
    if color is not None and kind is CATEGORIES:
        item.color = clean_color(color)
    if archived is not None:
        item.archived = archived
    session.flush()
    return item


def reorder(session: Session, kind: Kind, ids: list[int]) -> None:
    """``ids`` must be every item of the kind, archived included, each once."""
    existing = set(session.scalars(select(kind.model.id)))
    if len(ids) != len(existing) or set(ids) != existing:
        raise Invalid(MSG_REORDER, field="ids")
    items = {item.id: item for item in session.scalars(select(kind.model))}
    for position, item_id in enumerate(ids, start=1):
        items[item_id].position = position
    session.flush()


def _linked_events(session: Session, kind: Kind, item_id: int) -> list[int]:
    return list(session.scalars(select(kind.link.event_id).where(kind.link_col() == item_id)))


def _orphans(session: Session, kind: Kind, item_id: int) -> list[int]:
    """Events linked to the item and to no other item of the same kind."""
    column = kind.link_col()
    others = select(kind.link.event_id).where(column != item_id)
    query = select(kind.link.event_id).where(column == item_id, kind.link.event_id.not_in(others))
    return list(session.scalars(query))


def usage(session: Session, kind: Kind, item_id: int) -> tuple[int, int]:
    """``(linked events, orphans)``: what the deletion dialog tells the user."""
    _get(session, kind, item_id)
    return len(_linked_events(session, kind, item_id)), len(_orphans(session, kind, item_id))


def delete_item(
    session: Session,
    kind: Kind,
    item_id: int,
    policy: OrphanPolicy | None = None,
    to: int | None = None,
) -> None:
    """Delete an item; its orphans are moved to ``to`` or deleted, never left behind.

    With orphans and no policy nothing happens: 409 with their number. All in
    the caller's transaction, so a failure leaves everything as it was.
    """
    item = _get(session, kind, item_id)
    orphans = _orphans(session, kind, item_id)
    if orphans and policy is None:
        n = len(orphans)
        message = kind.orphans_one if n == 1 else kind.orphans_many.format(n=n)
        raise Conflict(message, orphans=n)
    linked = _linked_events(session, kind, item_id)

    if orphans and policy == "reassign":
        if to is None or to == item_id or session.get(kind.model, to) is None:
            raise Invalid(kind.bad_target, field="to")
        for event_id in orphans:
            session.add(kind.link(event_id=event_id, **{kind.link_column: to}))
    elif orphans and policy == "delete":
        session.execute(delete(Event).where(Event.id.in_(orphans)))

    session.execute(delete(kind.link).where(kind.link_col() == item_id))
    if kind is CATEGORIES:
        _renumber(session, [e for e in linked if e not in set(orphans)])
    session.delete(item)
    session.flush()
    session.expire_all()


def _renumber(session: Session, event_ids: list[int]) -> None:
    """Close the gap a removed category left: the next one becomes the main one."""
    if not event_ids:
        return
    links = session.scalars(
        select(EventCategory)
        .where(EventCategory.event_id.in_(event_ids))
        .order_by(EventCategory.event_id, EventCategory.position)
    )
    current, position = None, 0
    for link in links:
        if link.event_id != current:
            current, position = link.event_id, 0
        link.position = position
        position += 1
