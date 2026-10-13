# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``/api/settings``: what the interface remembers between sessions (SPEC §10.2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..db.session import session_scope
from ..domain.schemas import SettingIn
from ..domain.settings import get_settings, put_setting

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings() -> dict[str, Any]:
    with session_scope() as session:
        return get_settings(session)


@router.put("/{key}")
def write_setting(key: str, body: SettingIn) -> dict[str, Any]:
    with session_scope() as session:
        return {"key": key, "value": put_setting(session, key, body.value)}
