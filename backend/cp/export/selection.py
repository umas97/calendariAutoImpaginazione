# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
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

Sheets per category mirror it: an event belongs on category C's sheet when C is
one of its categories *and* at least one of its groups is selected for C. There
the colours are the groups' and every row names its groups. A complete calendar
chosen by category is the same as one chosen by group once the choices are
turned round (:func:`_by_group`).
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
from .request import CategorySelection, ExportRequest, GroupSelection

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
    #: The bar: one segment per selected category, in the event's order (on a
    #: sheet per category: per selected group, in the groups' order).
    colors: tuple[str, ...]
    #: The day number's colour: the first segment, darkened to read on white.
    day_color: str
    #: Complete calendar and sheets per category: the selected groups the event is for.
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
    #: The group (or the category, by category) the sheet is for; ``None`` for
    #: the complete calendar.
    subject_id: int | None
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

    ``per_group`` and ``single_pdf`` give one sheet per selected group (or
    category), in the user's order; ``combined`` gives one sheet. The request
    must have passed ``request.check_request``.
    """
    if session is None:
        with session_scope() as own:
            return build_sheets(request, session=own, today=today)
    today = today or dt.date.today()
    lookup = _Lookup(
        groups={g.id: g for g in session.scalars(select(Group))},
        categories={c.id: c for c in session.scalars(select(Category))},
    )
    if request.by == "category":
        chosen = _check_category_selections(request.category_selections, lookup)
        selections = _by_group(chosen, lookup)
    else:
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
    if request.by == "category":
        return [
            _category_sheet(events, c, lookup, first, common, c.category_id in multipage)
            for c in chosen
        ]
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


def _check_category_selections(
    selections: Sequence[CategorySelection], lookup: _Lookup
) -> list[CategorySelection]:
    problems: list[FieldError] = []
    for selection in selections:
        category = lookup.categories.get(selection.category_id)
        if category is None:
            problems.append(
                FieldError(
                    "category_selections", f"Categoria inesistente: {selection.category_id}."
                )
            )
            continue
        if not selection.group_ids:
            problems.append(
                FieldError("category_selections", f"Scegli almeno un gruppo per “{category.name}”.")
            )
        problems.extend(
            FieldError("category_selections", f"Gruppo inesistente: {gid}.")
            for gid in selection.group_ids
            if gid not in lookup.groups
        )
    if problems:
        raise InvalidFields(problems)
    return sorted(selections, key=lambda s: lookup.category_order(s.category_id))


def _by_group(selections: Sequence[CategorySelection], lookup: _Lookup) -> list[GroupSelection]:
    """The same choices seen from the groups: each group with the categories that chose it.

    "C chose G and the event has both" is the rule of either side, so the
    complete calendar needs no code of its own for a choice by category.
    """
    categories: dict[int, list[int]] = {}
    for selection in selections:
        for group_id in selection.group_ids:
            categories.setdefault(group_id, []).append(selection.category_id)
    return [
        GroupSelection(group_id=g, category_ids=categories[g])
        for g in sorted(categories, key=lookup.group_order)
    ]


def _letterhead(session: Session) -> Letterhead:
    parish = get_settings(session)["parish.name"] or ""
    asset = get_logo(session)
    logo = Logo(asset.mime, asset.data) if asset is not None else None
    return Letterhead(parish=parish, logo=logo)


def _category_colors(event: Event, chosen: set[int], lookup: _Lookup) -> tuple[str, ...]:
    """The colours of the event's chosen categories, in its order; none: not on the sheet."""
    return tuple(lookup.categories[c].color for c in event.category_ids if c in chosen)


def _row(event: Event, colors: tuple[str, ...], groups: tuple[str, ...] = ()) -> Row:
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


def _group_legend(used: set[int], lookup: _Lookup) -> tuple[Swatch, ...]:
    ordered = sorted(used, key=lookup.group_order)
    return tuple(Swatch(lookup.groups[g].name, lookup.groups[g].color) for g in ordered)


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
        colors = _category_colors(event, chosen, lookup)
        if colors:
            pairs.append((event, _row(event, colors)))
            used.update(c for c in event.category_ids if c in chosen)
    return Sheet(
        subject_id=selection.group_id,
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
        pairs.append((event, _row(event, _category_colors(event, chosen, lookup), names)))
        used.update(own & chosen)
    return Sheet(
        subject_id=None,
        title=COMBINED_TITLE,
        groups_line=", ".join(lookup.groups[s.group_id].name for s in selections),
        legend=_legend(used, lookup),
        months=_months(pairs, first),
        multipage=True,
        **common,
    )


def _category_sheet(
    events: list[Event],
    selection: CategorySelection,
    lookup: _Lookup,
    first: dt.date,
    common: dict,
    multipage: bool,
) -> Sheet:
    pairs: list[tuple[Event, Row]] = []
    used: set[int] = set()
    for event in events:
        if selection.category_id not in event.category_ids:
            continue
        matched = sorted(set(event.group_ids) & set(selection.group_ids), key=lookup.group_order)
        if not matched:
            continue
        colors = tuple(lookup.groups[g].color for g in matched)
        names = tuple(lookup.groups[g].name for g in matched)
        pairs.append((event, _row(event, colors, names)))
        used.update(matched)
    return Sheet(
        subject_id=selection.category_id,
        title=lookup.categories[selection.category_id].name,
        groups_line="",
        legend=_group_legend(used, lookup),
        months=_months(pairs, first),
        multipage=multipage,
        **common,
    )
