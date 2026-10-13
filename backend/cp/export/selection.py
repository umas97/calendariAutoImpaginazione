# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which events go on which sheet, in which order, with which colours (SPEC §5.1, §8.1).

This is the one place that filters and orders events for an export: the counts
of the Export screen, the preview and the files all come from
:func:`build_sheets`. A :class:`Sheet` holds finished text only -- dates already
written in Italian, colours already chosen -- and no internal notes: the
renderer cannot show what it is never given (test 12).

The rule, the same in every mode: an event belongs on group G's sheet when G is
one of its groups *and* at least one of its categories is selected for G. The
complete calendar takes every event that belongs on at least one selected
group's sheet, once, labelled with those groups.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Category, Event, Group
from ..db.session import session_scope
from ..domain.errors import FieldError, InvalidFields
from ..domain.events import chronological_key, events_in_range
from ..domain.palette import text_color
from ..domain.parish import get_logo
from ..domain.settings import get_settings
from . import formatting as fmt
from .request import ExportRequest, GroupSelection

COMBINED_TITLE = "Calendario"


@dataclass(frozen=True)
class Swatch:
    name: str
    color: str


@dataclass(frozen=True)
class Row:
    """One event on a sheet: text ready to print, colours of the selected categories."""

    event_id: int
    weekday: str
    day: str
    time: str
    title: str
    place: str
    #: The bar: one segment per selected category, in the event's order.
    colors: tuple[str, ...]
    #: The day number's colour: the first segment, darkened to read on white.
    day_color: str
    #: Complete calendar only: the selected groups the event is for.
    groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class Month:
    heading: str
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class Logo:
    mime: str
    data: bytes = field(repr=False)


@dataclass(frozen=True)
class Letterhead:
    parish: str
    logo: Logo | None


@dataclass(frozen=True)
class Sheet:
    #: ``None`` for the complete calendar.
    group_id: int | None
    title: str
    period: str
    #: Complete calendar only: the groups it covers.
    groups_line: str
    legend: tuple[Swatch, ...]
    months: tuple[Month, ...]
    letterhead: Letterhead
    updated: str
    #: Laid out over as many pages as it needs, instead of fitted to one.
    multipage: bool = False

    @property
    def event_count(self) -> int:
        return sum(len(month.rows) for month in self.months)


@dataclass
class _Lookup:
    groups: dict[int, Group]
    categories: dict[int, Category]

    def group_order(self, group_id: int) -> tuple[int, int]:
        return (self.groups[group_id].position, group_id)

    def category_order(self, category_id: int) -> tuple[int, int]:
        return (self.categories[category_id].position, category_id)


def build_sheets(
    request: ExportRequest, *, session: Session | None = None, today: dt.date | None = None
) -> list[Sheet]:
    """The sheets of an export, empty ones included (the caller reports them as skipped).

    ``per_group`` and ``single_pdf`` give one sheet per selected group, in the
    groups' order; ``combined`` gives one sheet. The request must have passed
    ``request.check_request``.
    """
    if session is None:
        with session_scope() as own:
            return build_sheets(request, session=own, today=today)
    today = today or dt.date.today()
    lookup = _Lookup(
        groups={g.id: g for g in session.scalars(select(Group))},
        categories={c.id: c for c in session.scalars(select(Category))},
    )
    selections = _check_selections(request.selections, lookup)
    first, last = request.period.first, request.period.last
    events = sorted(
        events_in_range(session, first, last), key=lambda e: chronological_key(e, first)
    )
    letterhead = _letterhead(session)
    common = {
        "period": fmt.period_label(first, last),
        "letterhead": letterhead,
        "updated": fmt.updated_label(today),
    }
    if request.mode == "combined":
        return [_combined_sheet(events, selections, lookup, first, common)]
    multipage = set(request.multipage)
    return [
        _group_sheet(events, selection, lookup, first, common, selection.group_id in multipage)
        for selection in selections
    ]


def _check_selections(
    selections: Sequence[GroupSelection], lookup: _Lookup
) -> list[GroupSelection]:
    problems: list[FieldError] = []
    for selection in selections:
        group = lookup.groups.get(selection.group_id)
        if group is None:
            problems.append(FieldError("selections", f"Gruppo inesistente: {selection.group_id}."))
            continue
        if not selection.category_ids:
            problems.append(
                FieldError("selections", f"Scegli almeno una categoria per “{group.name}”.")
            )
        problems.extend(
            FieldError("selections", f"Categoria inesistente: {cid}.")
            for cid in selection.category_ids
            if cid not in lookup.categories
        )
    if problems:
        raise InvalidFields(problems)
    return sorted(selections, key=lambda s: lookup.group_order(s.group_id))


def _letterhead(session: Session) -> Letterhead:
    parish = get_settings(session)["parish.name"] or ""
    asset = get_logo(session)
    logo = Logo(asset.mime, asset.data) if asset is not None else None
    return Letterhead(parish=parish, logo=logo)


def _row(
    event: Event, chosen: set[int], lookup: _Lookup, groups: tuple[str, ...] = ()
) -> Row | None:
    """The event's row, or ``None`` if none of its categories is chosen."""
    colors = tuple(lookup.categories[c].color for c in event.category_ids if c in chosen)
    if not colors:
        return None
    weekday, day = fmt.date_column(event)
    return Row(
        event_id=event.id,
        weekday=weekday,
        day=day,
        time=fmt.time_column(event),
        title=event.title,
        place=event.place,
        colors=colors,
        day_color=text_color(colors[0]),
        groups=groups,
    )


def _months(pairs: list[tuple[Event, Row]], first: dt.date) -> tuple[Month, ...]:
    """Rows under the month they start in; an event begun earlier sits under the first."""
    months: list[Month] = []
    current: tuple[int, int] | None = None
    rows: list[Row] = []
    for event, row in pairs:
        start = max(event.start_date, first)
        key = (start.year, start.month)
        if key != current:
            if current is not None:
                months.append(Month(fmt.month_heading(*current), tuple(rows)))
            current, rows = key, []
        rows.append(row)
    if current is not None:
        months.append(Month(fmt.month_heading(*current), tuple(rows)))
    return tuple(months)


def _legend(used: set[int], lookup: _Lookup) -> tuple[Swatch, ...]:
    ordered = sorted(used, key=lookup.category_order)
    return tuple(Swatch(lookup.categories[c].name, lookup.categories[c].color) for c in ordered)


def _group_sheet(
    events: list[Event],
    selection: GroupSelection,
    lookup: _Lookup,
    first: dt.date,
    common: dict,
    multipage: bool,
) -> Sheet:
    chosen = set(selection.category_ids)
    pairs: list[tuple[Event, Row]] = []
    used: set[int] = set()
    for event in events:
        if selection.group_id not in event.group_ids:
            continue
        row = _row(event, chosen, lookup)
        if row is not None:
            pairs.append((event, row))
            used.update(c for c in event.category_ids if c in chosen)
    return Sheet(
        group_id=selection.group_id,
        title=lookup.groups[selection.group_id].name,
        groups_line="",
        legend=_legend(used, lookup),
        months=_months(pairs, first),
        multipage=multipage,
        **common,
    )


def _combined_sheet(
    events: list[Event],
    selections: list[GroupSelection],
    lookup: _Lookup,
    first: dt.date,
    common: dict,
) -> Sheet:
    pairs: list[tuple[Event, Row]] = []
    used: set[int] = set()
    for event in events:
        own = set(event.category_ids)
        # The groups whose sheet the event would be on, and what each selects of it.
        matched = [s for s in selections if s.group_id in event.group_ids]
        matched = [s for s in matched if own.intersection(s.category_ids)]
        if not matched:
            continue
        chosen = {c for s in matched for c in s.category_ids}
        names = tuple(lookup.groups[s.group_id].name for s in matched)
        row = _row(event, chosen, lookup, names)
        assert row is not None
        pairs.append((event, row))
        used.update(own & chosen)
    return Sheet(
        group_id=None,
        title=COMBINED_TITLE,
        groups_line=", ".join(lookup.groups[s.group_id].name for s in selections),
        legend=_legend(used, lookup),
        months=_months(pairs, first),
        multipage=True,
        **common,
    )


def event_counts(
    request: ExportRequest,
    included: Sequence[int] | None = None,
    *,
    session: Session | None = None,
) -> dict[str, object]:
    """How many events each sheet would have: the numbers next to the groups (SPEC §9.1).

    Every group in the request gets its number, so the screen can show it next
    to groups not ticked yet; a group with no category chosen has none. The
    complete calendar counts only the ``included`` groups (all when ``None``).
    """
    if session is None:
        with session_scope() as own:
            return event_counts(request, included, session=own)
    chosen = [s for s in request.selections if s.category_ids]
    counts = {s.group_id: 0 for s in request.selections}
    if chosen:
        per_group = request.model_copy(update={"mode": "per_group", "selections": chosen})
        counts |= {
            sheet.group_id: sheet.event_count for sheet in build_sheets(per_group, session=session)
        }
    wanted = set(included) if included is not None else None
    in_combined = [s for s in chosen if wanted is None or s.group_id in wanted]
    combined = 0
    if in_combined:
        whole = request.model_copy(update={"mode": "combined", "selections": in_combined})
        combined = build_sheets(whole, session=session)[0].event_count
    return {"groups": counts, "combined": combined}
