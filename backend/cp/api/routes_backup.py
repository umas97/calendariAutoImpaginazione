# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""``/api/backup`` and ``/api/restore``: the backup entries of the «⋯» menu (SPEC §10.4)."""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel

from .. import backup, folders

router = APIRouter(tags=["backup"])


class BackupIn(BaseModel):
    folder: str
    #: Empty: ``calendariParrocchia backup AAAA-MM-GG.db``.
    name: str = ""


class RestoreIn(BaseModel):
    path: str


@router.get("/api/backup")
def backup_options() -> dict[str, Any]:
    """What «Backup ora» proposes, and where the automatic backups are."""
    last = backup.last_auto_backup()
    return {
        "default_name": backup.default_name(dt.date.today()),
        "default_folder": str(backup.default_folder()),
        "auto_dir": str(backup.backups_dir()),
        "last_auto": last.isoformat() if last else None,
        "home": str(folders.home()),
    }


@router.post("/api/backup", status_code=status.HTTP_201_CREATED)
def backup_now(body: BackupIn) -> dict[str, str]:
    return {"path": str(backup.backup_now(body.folder, body.name))}


@router.post("/api/backup/open")
def open_backups() -> dict[str, str]:
    """«Apri cartella dei backup»: the program's own folder, created if needed."""
    directory = backup.backups_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return {"path": str(folders.show_in_file_manager(directory))}


@router.post("/api/restore/inspect")
def inspect_backup(body: RestoreIn) -> dict[str, Any]:
    """What a restore would bring back; 422 if the file cannot be restored. Changes nothing."""
    return backup.inspect(body.path)


@router.post("/api/restore")
def restore_backup(body: RestoreIn) -> dict[str, Any]:
    return backup.restore(body.path)
