# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The folder picker inside the program, and the one rule about paths (SPEC §10.3; test 20).

Every path from the interface is resolved -- ``..`` and symlinks followed --
and must land inside the user's home, or the answer is 403. The export uses
the same check for its output folder (SPEC §2.2), the backup for its file.

The picker lists folders, never files -- except the ones with a given suffix
when asked: choosing a backup to restore lists the ``.db`` files.
"""

from __future__ import annotations

import datetime as dt
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .domain.errors import Conflict, Forbidden, Invalid, NotFound

_log = logging.getLogger(__name__)

OUTSIDE = "Si possono usare solo cartelle dentro la tua cartella personale."
#: Where exports go unless the user picks another folder (SPEC §9.1).
DEFAULT_EXPORT_DIR = ("Documenti", "calendariAutoImpaginazione")


def home() -> Path:
    return Path.home().resolve()


def default_export_dir() -> Path:
    return home().joinpath(*DEFAULT_EXPORT_DIR)


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def inside_home(raw: str | Path) -> Path:
    """``raw`` resolved; 403 unless it is the home or below it. It need not exist."""
    text = str(raw).strip()
    if not text:
        raise Invalid("Indica una cartella.", field="path")
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = home() / path
    resolved = path.resolve()
    if not _inside(resolved, home()):
        raise Forbidden(OUTSIDE, field="path")
    return resolved


def existing_folder(raw: str | Path) -> Path:
    path = inside_home(raw)
    if not path.is_dir():
        raise NotFound("La cartella non esiste più.", field="path")
    return path


def _file_entry(entry: Path) -> dict[str, Any]:
    info = entry.stat()
    modified = dt.datetime.fromtimestamp(info.st_mtime).replace(microsecond=0)
    return {
        "name": entry.name,
        "path": str(entry),
        "size": info.st_size,
        "modified": modified.isoformat(),
    }


def list_folders(
    raw: str | Path | None, hidden: bool = False, suffix: str | None = None
) -> dict[str, Any]:
    """The subfolders of a folder, alphabetical, hidden ones on request.

    With ``suffix`` (``".db"``) also the files ending with it, newest first;
    otherwise never a file. A link that leads outside the home is left out:
    opening it would be refused.
    """
    path = existing_folder(raw) if raw else home()
    root = home()
    folders: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    try:
        entries = list(path.iterdir())
    except PermissionError as exc:
        raise Forbidden("Non hai il permesso di leggere questa cartella.", field="path") from exc
    for entry in entries:
        if entry.name.startswith(".") and not hidden:
            continue
        try:
            if not _inside(entry.resolve(), root):
                continue
            if entry.is_dir():
                folders.append({"name": entry.name, "path": str(entry)})
            elif suffix and entry.is_file() and entry.name.lower().endswith(suffix):
                files.append(_file_entry(entry))
        except OSError:
            continue
    folders.sort(key=lambda f: (f["name"].casefold(), f["name"]))
    files.sort(key=lambda f: (f["modified"], f["name"]), reverse=True)
    listing = {
        "path": str(path),
        "parent": str(path.parent) if path != root else None,
        "home": str(root),
        "folders": folders,
    }
    if suffix:
        listing["files"] = files
    return listing


def create_folder(parent: str | Path, name: str) -> Path:
    """«Nuova cartella»: one level, inside an existing folder."""
    base = existing_folder(parent)
    name = name.strip()
    if not name or name in (".", "..") or "/" in name or "\x00" in name:
        raise Invalid("Nome di cartella non valido.", field="name")
    target = inside_home(base / name)
    try:
        target.mkdir()
    except FileExistsError as exc:
        raise Conflict(f"Esiste già una cartella chiamata “{name}”.", field="name") from exc
    except PermissionError as exc:
        raise Forbidden("Non hai il permesso di creare cartelle qui.", field="path") from exc
    return target


def _launcher() -> list[str] | None:
    if shutil.which("gio"):
        return ["gio", "open"]
    if shutil.which("xdg-open"):
        return ["xdg-open"]
    return None


def open_folder(raw: str | Path) -> Path:
    """Show a folder in the file manager: ``gio open``, else ``xdg-open``."""
    return show_in_file_manager(existing_folder(raw))


def show_in_file_manager(path: Path) -> Path:
    """Open ``path`` -- already checked, or the program's own -- in the file manager."""
    command = _launcher()
    if command is None:
        raise NotFound("Non trovo un programma per aprire le cartelle (gio o xdg-open).")
    subprocess.Popen(
        [*command, str(path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _log.info("cartella aperta: %s", path)
    return path
