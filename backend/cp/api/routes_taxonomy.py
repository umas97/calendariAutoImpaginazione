# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``/api/groups`` and ``/api/categories``: the same routes for both kinds (SPEC §6)."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from ..db.models import Category, Group
from ..db.session import session_scope
from ..domain import taxonomy
from ..domain.palette import PALETTE
from ..domain.schemas import ItemIn, ItemOut, ItemPatch, ReorderIn, UsageOut
from ..domain.taxonomy import CATEGORIES, GROUPS, Kind, OrphanPolicy


def _out(item: Group | Category, count: int) -> ItemOut:
    return ItemOut(
        id=item.id,
        name=item.name,
        color=item.color,
        position=item.position,
        archived=item.archived,
        event_count=count,
    )


def _router(kind: Kind, prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("")
    def list_items(include_archived: bool = False) -> list[ItemOut]:
        with session_scope() as session:
            return [_out(*row) for row in taxonomy.list_items(session, kind, include_archived)]

    @router.get("/palette")
    def palette() -> list[str]:
        """The default colours, in assignment order: the colour picker offers these first."""
        return list(PALETTE)

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_item(body: ItemIn) -> ItemOut:
        with session_scope() as session:
            return _out(taxonomy.create_item(session, kind, body.name, body.color), 0)

    @router.patch("/{item_id}")
    def update_item(item_id: int, body: ItemPatch) -> ItemOut:
        with session_scope() as session:
            item = taxonomy.update_item(
                session, kind, item_id, name=body.name, color=body.color, archived=body.archived
            )
            return _out(item, taxonomy.event_counts(session, kind).get(item.id, 0))

    @router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
    def reorder(body: ReorderIn) -> Response:
        with session_scope() as session:
            taxonomy.reorder(session, kind, body.ids)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/{item_id}/usage")
    def usage(item_id: int) -> UsageOut:
        with session_scope() as session:
            events, orphans = taxonomy.usage(session, kind, item_id)
            return UsageOut(events=events, orphans=orphans)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(
        item_id: int, orphans: OrphanPolicy | None = None, to: int | None = None
    ) -> Response:
        """With orphan events and no ``orphans=reassign&to=<id>`` or ``orphans=delete``: 409."""
        with session_scope() as session:
            taxonomy.delete_item(session, kind, item_id, orphans, to)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router


groups = _router(GROUPS, "/api/groups", "groups")
categories = _router(CATEGORIES, "/api/categories", "categories")
