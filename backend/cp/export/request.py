# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``ExportRequest``: what to export, for whom, in which form, where (SPEC §8.1).

Like the other input models the Pydantic part is loose: :func:`check_request`
applies the rules and answers in Italian, naming the field. The rules that need
the database (groups and categories that exist) live in ``selection.py``.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain.errors import FieldError, InvalidFields

#: The longest period, both ends counted (SPEC §8.1).
MAX_PERIOD_DAYS = 400

Mode = Literal["per_group", "single_pdf", "combined"]
Format = Literal["pdf", "png"]


class Period(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    first: dt.date = Field(alias="from")
    last: dt.date = Field(alias="to")


class GroupSelection(BaseModel):
    group_id: int
    category_ids: list[int] = Field(default_factory=list)


class ExportRequest(BaseModel):
    period: Period
    mode: Mode = "per_group"
    formats: list[Format] = Field(default_factory=lambda: ["pdf"])
    dpi: Literal[150, 200, 300] = 200
    selections: list[GroupSelection] = Field(default_factory=list)
    #: Absent only for a preview.
    output_dir: str | None = None
    #: Groups to lay out over several pages instead of one sheet: the answer to
    #: "non entra in un foglio A4" ("Esporta su più pagine", SPEC §8.4).
    multipage: list[int] = Field(default_factory=list)


def check_request(request: ExportRequest, *, needs_output: bool) -> ExportRequest:
    """Apply the rules of SPEC §8.1 that need no database; return a cleaned copy.

    A group chosen twice counts once (the first choice wins), and so does a
    category chosen twice for the same group.
    """
    problems: list[FieldError] = []
    first, last = request.period.first, request.period.last
    if last < first:
        problems.append(FieldError("period.to", "La fine del periodo è prima dell'inizio."))
    elif (last - first).days + 1 > MAX_PERIOD_DAYS:
        problems.append(
            FieldError("period.to", f"Il periodo può durare al massimo {MAX_PERIOD_DAYS} giorni.")
        )
    formats = list(dict.fromkeys(request.formats))
    if not formats:
        problems.append(FieldError("formats", "Scegli almeno un formato: PDF o PNG."))
    seen: set[int] = set()
    selections = []
    for selection in request.selections:
        if selection.group_id in seen:
            continue
        seen.add(selection.group_id)
        categories = list(dict.fromkeys(selection.category_ids))
        selections.append(GroupSelection(group_id=selection.group_id, category_ids=categories))
    if not selections:
        problems.append(FieldError("selections", "Scegli almeno un gruppo."))
    if needs_output and not (request.output_dir or "").strip():
        problems.append(FieldError("output_dir", "Scegli la cartella in cui salvare."))
    if problems:
        raise InvalidFields(problems)
    return request.model_copy(
        update={
            "formats": formats,
            "selections": selections,
            "multipage": [g for g in dict.fromkeys(request.multipage) if g in seen],
        }
    )
