# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The numbers of the Export screen: events per sheet and in the complete calendar (SPEC §9.1).

They come from :func:`selection.build_sheets`, like the preview and the files.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from ..db.session import session_scope
from .request import CategorySelection, ExportRequest, GroupSelection
from .selection import build_sheets


def event_counts(
    request: ExportRequest,
    included: Sequence[int] | None = None,
    *,
    session: Session | None = None,
) -> dict[str, object]:
    """How many events each sheet would have: the numbers next to the groups (SPEC §9.1).

    Every group (or category, by category) in the request gets its number, so
    the screen can show it next to the ones not ticked yet; one with nothing
    chosen in it has none. The complete calendar counts only the ``included``
    ones (all when ``None``).
    """
    if session is None:
        with session_scope() as own:
            return event_counts(request, included, session=own)
    if request.by == "category":
        field, every = "category_selections", request.category_selections
        subject = [s.category_id for s in every]
        chosen = [s for s in every if s.group_ids]
    else:
        field, every = "selections", request.selections
        subject = [s.group_id for s in every]
        chosen = [s for s in every if s.category_ids]
    counts = dict.fromkeys(subject, 0)
    if chosen:
        sheets = request.model_copy(update={"mode": "per_group", field: chosen})
        counts |= {
            sheet.subject_id: sheet.event_count for sheet in build_sheets(sheets, session=session)
        }
    wanted = set(included) if included is not None else None

    def wanted_in_combined(s: GroupSelection | CategorySelection) -> bool:
        key = s.category_id if isinstance(s, CategorySelection) else s.group_id
        return wanted is None or key in wanted

    in_combined = [s for s in chosen if wanted_in_combined(s)]
    combined = 0
    if in_combined:
        whole = request.model_copy(update={"mode": "combined", field: in_combined})
        combined = build_sheets(whole, session=session)[0].event_count
    return {"sheets": counts, "combined": combined}
