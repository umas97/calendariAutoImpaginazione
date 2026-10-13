# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``/api/folders``: the folder picker, always inside the home (SPEC §10.3)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, status
from pydantic import BaseModel

from .. import folders

router = APIRouter(prefix="/api/folders", tags=["folders"])


class NewFolderIn(BaseModel):
    path: str
    name: str


class FolderIn(BaseModel):
    path: str


@router.get("")
def list_folders(
    path: str = "", hidden: bool = False, files: Literal["db"] | None = None
) -> dict[str, Any]:
    """Subfolders of ``path`` (default: the home); hidden ones only with ``hidden=1``.

    ``files=db`` adds the ``.db`` files, for choosing a backup to restore.
    """
    return folders.list_folders(path or None, hidden, f".{files}" if files else None)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_folder(body: NewFolderIn) -> dict[str, str]:
    return {"path": str(folders.create_folder(body.path, body.name))}


@router.post("/open")
def open_folder(body: FolderIn) -> dict[str, str]:
    return {"path": str(folders.open_folder(body.path))}
