# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``/api/parish``: the name and logo at the top of every sheet (SPEC §8.8)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, UploadFile, status
from pydantic import BaseModel

from ..db.session import session_scope
from ..domain import parish
from ..domain.errors import Invalid, NotFound

router = APIRouter(prefix="/api/parish", tags=["parish"])


class ParishNameIn(BaseModel):
    name: str = ""


@router.get("")
def read_parish() -> dict[str, Any]:
    with session_scope() as session:
        return parish.parish_info(session)


@router.put("")
def write_parish(body: ParishNameIn) -> dict[str, Any]:
    with session_scope() as session:
        parish.set_name(session, body.name)
        return parish.parish_info(session)


@router.get("/logo")
def read_logo() -> Response:
    with session_scope() as session:
        logo = parish.get_logo(session)
        if logo is None:
            raise NotFound("Nessun logo impostato.")
        # An SVG shown on its own could run scripts: never as a document of ours.
        headers = {
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
            "X-Content-Type-Options": "nosniff",
        }
        return Response(logo.data, media_type=logo.mime, headers=headers)


@router.post("/logo")
async def upload_logo(logo: UploadFile) -> dict[str, Any]:
    data = await logo.read(parish.MAX_LOGO_BYTES + 1)
    if not data:
        raise Invalid("Il file del logo è vuoto.", field="logo")
    with session_scope() as session:
        parish.save_logo(session, data)
        return parish.parish_info(session)


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
def remove_logo() -> Response:
    with session_scope() as session:
        parish.delete_logo(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
