# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The API's request and response models.

Input models are deliberately loose (plain ``str``, no length limits): the rules
live in ``validation.py`` and ``taxonomy.py``, which answer in Italian and name
the field. Pydantic only turns JSON into Python types.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field

# --- groups and categories ---------------------------------------------------


class GroupIn(BaseModel):
    name: str


class GroupPatch(BaseModel):
    name: str | None = None
    archived: bool | None = None


class GroupOut(BaseModel):
    id: int
    name: str
    position: int
    archived: bool
    event_count: int


class CategoryIn(BaseModel):
    name: str
    #: Omitted: the first palette colour no category uses yet.
    color: str | None = None


class CategoryPatch(BaseModel):
    name: str | None = None
    color: str | None = None
    archived: bool | None = None


class CategoryOut(GroupOut):
    color: str


class ReorderIn(BaseModel):
    """Every id of the kind, archived included, in the new order."""

    ids: list[int]


class UsageOut(BaseModel):
    #: Events linked to the item.
    events: int
    #: Of those, the events that have no other group (or category).
    orphans: int


# --- events --------------------------------------------------------------------


class EventIn(BaseModel):
    title: str = ""
    start_date: dt.date
    end_date: dt.date | None = None
    all_day: bool = False
    start_time: str | None = None
    end_time: str | None = None
    place: str = ""
    #: Internal, never exported.
    notes: str = ""
    group_ids: list[int] = Field(default_factory=list)
    #: In the user's order: the first is the main category.
    category_ids: list[int] = Field(default_factory=list)


class EventOut(BaseModel):
    id: int
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
    created_at: dt.datetime
    updated_at: dt.datetime


class DuplicateIn(BaseModel):
    dates: list[dt.date]


class DuplicateOut(BaseModel):
    ids: list[int]


# --- settings --------------------------------------------------------------------


class SettingIn(BaseModel):
    value: Any = None
