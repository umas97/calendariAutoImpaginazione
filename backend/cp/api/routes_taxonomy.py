# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``/api/groups`` and ``/api/categories``: the same routes for both kinds (SPEC §6)."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from ..db.models import Category, Group
from ..db.session import session_scope
from ..domain import taxonomy
from ..domain.schemas import (
    CategoryIn,
    CategoryOut,
    CategoryPatch,
    GroupIn,
    GroupOut,
    GroupPatch,
    ReorderIn,
    UsageOut,
)
from ..domain.taxonomy import CATEGORIES, GROUPS, OrphanPolicy


def _group_out(item: Group, count: int) -> GroupOut:
    return GroupOut(
        id=item.id,
        name=item.name,
        position=item.position,
        archived=item.archived,
        event_count=count,
    )


def _category_out(item: Category, count: int) -> CategoryOut:
    return CategoryOut(
        id=item.id,
        name=item.name,
        position=item.position,
        archived=item.archived,
        event_count=count,
        color=item.color,
    )


groups = APIRouter(prefix="/api/groups", tags=["groups"])
categories = APIRouter(prefix="/api/categories", tags=["categories"])


# --- groups --------------------------------------------------------------------


@groups.get("")
def list_groups(include_archived: bool = False) -> list[GroupOut]:
    with session_scope() as session:
        return [_group_out(*row) for row in taxonomy.list_items(session, GROUPS, include_archived)]


@groups.post("", status_code=status.HTTP_201_CREATED)
def create_group(body: GroupIn) -> GroupOut:
    with session_scope() as session:
        return _group_out(taxonomy.create_item(session, GROUPS, body.name), 0)


@groups.patch("/{group_id}")
def update_group(group_id: int, body: GroupPatch) -> GroupOut:
    with session_scope() as session:
        item = taxonomy.update_item(
            session, GROUPS, group_id, name=body.name, archived=body.archived
        )
        return _group_out(item, taxonomy.event_counts(session, GROUPS).get(item.id, 0))


@groups.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_groups(body: ReorderIn) -> Response:
    with session_scope() as session:
        taxonomy.reorder(session, GROUPS, body.ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@groups.get("/{group_id}/usage")
def group_usage(group_id: int) -> UsageOut:
    with session_scope() as session:
        events, orphans = taxonomy.usage(session, GROUPS, group_id)
        return UsageOut(events=events, orphans=orphans)


@groups.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int, orphans: OrphanPolicy | None = None, to: int | None = None
) -> Response:
    """With orphan events and no ``orphans=reassign&to=<id>`` or ``orphans=delete``: 409."""
    with session_scope() as session:
        taxonomy.delete_item(session, GROUPS, group_id, orphans, to)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- categories ------------------------------------------------------------------


@categories.get("")
def list_categories(include_archived: bool = False) -> list[CategoryOut]:
    with session_scope() as session:
        rows = taxonomy.list_items(session, CATEGORIES, include_archived)
        return [_category_out(*row) for row in rows]


@categories.post("", status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryIn) -> CategoryOut:
    with session_scope() as session:
        return _category_out(taxonomy.create_item(session, CATEGORIES, body.name, body.color), 0)


@categories.patch("/{category_id}")
def update_category(category_id: int, body: CategoryPatch) -> CategoryOut:
    with session_scope() as session:
        item = taxonomy.update_item(
            session,
            CATEGORIES,
            category_id,
            name=body.name,
            color=body.color,
            archived=body.archived,
        )
        return _category_out(item, taxonomy.event_counts(session, CATEGORIES).get(item.id, 0))


@categories.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_categories(body: ReorderIn) -> Response:
    with session_scope() as session:
        taxonomy.reorder(session, CATEGORIES, body.ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@categories.get("/{category_id}/usage")
def category_usage(category_id: int) -> UsageOut:
    with session_scope() as session:
        events, orphans = taxonomy.usage(session, CATEGORIES, category_id)
        return UsageOut(events=events, orphans=orphans)


@categories.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int, orphans: OrphanPolicy | None = None, to: int | None = None
) -> Response:
    with session_scope() as session:
        taxonomy.delete_item(session, CATEGORIES, category_id, orphans, to)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
