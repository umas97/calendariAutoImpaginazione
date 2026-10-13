# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings the interface remembers (SPEC §10.2; test 22).

Only the keys in :data:`_WRITABLE` can be written, each through its own model;
an unknown key is a 404, a wrong value a 422. Reading drops ids of groups and
categories that no longer exist, so a deleted group never comes back as a
selected filter. The ``app`` and ``schema_version`` rows that identify the
database (``db/session.py``) are not settings and are never exposed.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Category, Group, Setting
from .errors import Invalid, NotFound


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CalendarView(_Strict):
    value: Literal["month", "week", "list"]


class CalendarFilters(_Strict):
    #: ``None`` means every group (or category), including the ones created later.
    group_ids: list[int] | None = None
    category_ids: list[int] | None = None


class Period(_Strict):
    from_: dt.date = Field(alias="from")
    to: dt.date

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class GroupSelection(_Strict):
    group_id: int
    #: ``None`` means every category, including the ones created later.
    category_ids: list[int] | None = None


class ExportLast(_Strict):
    period: Period | None = None
    mode: Literal["per_group", "single_pdf", "combined"] = "per_group"
    formats: list[Literal["pdf", "png"]] = Field(default_factory=lambda: ["pdf"])
    dpi: Literal[150, 200, 300] = 200
    selections: list[GroupSelection] = Field(default_factory=list)
    output_dir: str | None = None


class ParishName(_Strict):
    value: str = Field(max_length=80)


def _plain(model: type[BaseModel]):
    """For keys whose value is a scalar: wrap it, validate, unwrap."""

    def validate(value: Any) -> Any:
        return model.model_validate({"value": value}).model_dump(mode="json")["value"]

    return validate


def _object(model: type[BaseModel]):
    def validate(value: Any) -> Any:
        return model.model_validate(value).model_dump(mode="json", by_alias=True)

    return validate


def _parish_name(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
    return _plain(ParishName)(value)


_WRITABLE = {
    "calendar.view": _plain(CalendarView),
    "calendar.filters": _object(CalendarFilters),
    "export.last": _object(ExportLast),
    "parish.name": _parish_name,
}

DEFAULTS: dict[str, Any] = {
    "calendar.view": "month",
    "calendar.filters": {"group_ids": None, "category_ids": None},
    "export.last": None,
    "parish.name": "",
}


def put_setting(session: Session, key: str, value: Any) -> Any:
    validator = _WRITABLE.get(key)
    if validator is None:
        raise NotFound(f"Impostazione sconosciuta: {key}.")
    try:
        clean = validator(value)
    except ValidationError as exc:
        raise Invalid(f"Valore non valido per “{key}”.", field="value") from exc
    session.merge(Setting(key=key, value=clean))
    session.flush()
    return _sanitize(session, key, clean)


def get_settings(session: Session) -> dict[str, Any]:
    stored = {
        row.key: row.value
        for row in session.scalars(select(Setting).where(Setting.key.in_(_WRITABLE)))
    }
    return {key: _sanitize(session, key, stored.get(key, DEFAULTS[key])) for key in _WRITABLE}


def _sanitize(session: Session, key: str, value: Any) -> Any:
    """Drop the ids of groups and categories that are gone."""
    if value is None or key not in ("calendar.filters", "export.last"):
        return value
    groups = set(session.scalars(select(Group.id)))
    categories = set(session.scalars(select(Category.id)))
    value = dict(value)
    if key == "calendar.filters":
        if value.get("group_ids") is not None:
            value["group_ids"] = [i for i in value["group_ids"] if i in groups]
        if value.get("category_ids") is not None:
            value["category_ids"] = [i for i in value["category_ids"] if i in categories]
    else:
        value["selections"] = [
            {
                **s,
                "category_ids": None
                if s.get("category_ids") is None
                else [i for i in s["category_ids"] if i in categories],
            }
            for s in value.get("selections", [])
            if s["group_id"] in groups
        ]
    return value
