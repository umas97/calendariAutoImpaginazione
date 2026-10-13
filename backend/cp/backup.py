# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Backups: made now, made every day, and restored (SPEC §10.4; tests 23-24).

A backup is ``VACUUM INTO``: a consistent copy of the whole database, logo
included, taken while the program keeps running. The manual one goes where
the user chooses, under a name nobody else has (``reserve_path``: an existing
file is never replaced). The automatic one goes to ``backups/`` in the data
directory, at most one a day, the newest 14 kept.

A restore never touches the database in use until the chosen file has been
copied aside, recognised as ours, checked and brought to the current schema.
Only then, with the database's gate held exclusive (no session open, none
starting), the current file is moved to ``catalog-prima-del-ripristino-…``
and the copy takes its place. Anything wrong before that point leaves
everything as it was.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import shutil
import sqlite3
import uuid
from contextlib import closing, suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import folders
from .config import APP_ID, LEGACY_APP_IDS, get_settings
from .db.session import APP_KEY, SCHEMA_VERSION_KEY, Database, get_database, head_schema_version
from .domain.errors import Conflict, Forbidden, Invalid, NotFound
from .export.output import clean_name, reserve_path

_log = logging.getLogger(__name__)

AUTO_KEEP = 14
AUTO_EVERY = dt.timedelta(hours=24)
_AUTO_NAME = re.compile(r"^auto-\d{4}-\d{2}-\d{2}\.db$")
#: What a crash in the middle of an automatic backup can leave behind.
_PARTIAL = ".partial"
_SIDECARS = ("-wal", "-shm", "-journal")

NOT_OURS = "Il file scelto non è un backup di calendariAutoImpaginazione."
DAMAGED = "Il file scelto è danneggiato: non si può ripristinare."
TOO_NEW = (
    "Questo backup è stato fatto con una versione più recente di calendariAutoImpaginazione: "
    "aggiorna il programma prima di ripristinarlo."
)
IN_USE = "Questo è il database in uso, non un backup: scegli un altro file."
EXPORT_RUNNING = "C'è un export in corso: aspetta che finisca, poi riprova."
NO_WRITE = "Non hai il permesso di scrivere in questa cartella."


def backups_dir() -> Path:
    """Where the automatic backups go: ``~/.local/share/calendariautoimpaginazione/backups/``."""
    return get_settings().data_dir / "backups"


def default_name(today: dt.date) -> str:
    return f"calendariAutoImpaginazione backup {today.isoformat()}.db"


def default_folder() -> Path:
    """Where «Backup ora» proposes to write: ``~/Documenti`` if there is one, else the home."""
    documents = folders.home() / "Documenti"
    return documents if documents.is_dir() else folders.home()


def _vacuum_into(database: Database, target: Path) -> None:
    """Copy the whole database into ``target``, which must not exist or be empty."""
    with database.gate.shared(), closing(sqlite3.connect(database.path, timeout=15)) as db:
        db.execute("VACUUM INTO ?", (str(target),))


# --- «Backup ora» ----------------------------------------------------------------


def backup_now(folder: str | Path, name: str = "", today: dt.date | None = None) -> Path:
    """Write a backup into ``folder`` (inside the home); a taken name becomes `` (2)``…"""
    directory = folders.existing_folder(folder)
    fallback = default_name(today or dt.date.today())
    name = clean_name(name, fallback=fallback)
    if not name.lower().endswith(".db"):
        name += ".db"
    try:
        target = reserve_path(directory, name)
    except PermissionError as exc:
        raise Forbidden(NO_WRITE, field="folder") from exc
    try:
        _vacuum_into(get_database(), target)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    _log.info("backup scritto: %s", target)
    return target


# --- the automatic backup ----------------------------------------------------------


def _auto_backups(directory: Path) -> list[Path]:
    """The automatic backups, oldest first (the date in the name sorts them)."""
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if _AUTO_NAME.match(p.name) and p.is_file())


def last_auto_backup() -> dt.datetime | None:
    found = _auto_backups(backups_dir())
    if not found:
        return None
    return dt.datetime.fromtimestamp(found[-1].stat().st_mtime).replace(microsecond=0)


def auto_backup(database: Database | None = None, now: dt.datetime | None = None) -> Path | None:
    """At start: a backup if the last one is more than 24 hours old; keep the newest 14.

    Returns the new file, or ``None`` when none was due.
    """
    database = database or get_database()
    now = now or dt.datetime.now()
    directory = backups_dir()
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob(f".auto-*{_PARTIAL}"):
        stale.unlink(missing_ok=True)
    existing = _auto_backups(directory)
    target = directory / f"auto-{now:%Y-%m-%d}.db"
    if existing:
        age = now - dt.datetime.fromtimestamp(existing[-1].stat().st_mtime)
        # A negative age is a clock that went back: no backup either.
        if age < AUTO_EVERY or target.exists():
            return None
    partial = directory / f".{target.name}{_PARTIAL}"
    try:
        _vacuum_into(database, partial)
        partial.rename(target)
    finally:
        partial.unlink(missing_ok=True)
    os.utime(target, (now.timestamp(), now.timestamp()))
    for old in _auto_backups(directory)[:-AUTO_KEEP]:
        old.unlink(missing_ok=True)
        _log.info("backup automatico eliminato: %s", old.name)
    _log.info("backup automatico: %s", target)
    return target


def auto_backup_quietly() -> None:
    """The start-up backup: a failure is logged, never in the user's way."""
    try:
        auto_backup()
    except Exception:
        _log.exception("backup automatico non riuscito")


# --- restore -------------------------------------------------------------------------


@dataclass(frozen=True)
class BackupInfo:
    schema_version: int
    events: int
    groups: int
    categories: int


def _setting(raw: Any) -> Any:
    # ``value`` is JSON, but SQLite hands back numbers already converted.
    if isinstance(raw, str):
        with suppress(ValueError):
            return json.loads(raw)
    return raw


def identify(path: Path) -> BackupInfo:
    """What the file at ``path`` holds, or 422 if it is not a backup that can be restored."""
    try:
        with closing(sqlite3.connect(path)) as db:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise Invalid(DAMAGED, field="path")
            rows = dict(
                db.execute(
                    "SELECT key, value FROM setting WHERE key IN (?, ?)",
                    (APP_KEY, SCHEMA_VERSION_KEY),
                ).fetchall()
            )
            if _setting(rows.get(APP_KEY)) not in (APP_ID, *LEGACY_APP_IDS):
                raise Invalid(NOT_OURS, field="path")
            version = _setting(rows.get(SCHEMA_VERSION_KEY))
            if not isinstance(version, int):
                raise Invalid(NOT_OURS, field="path")
            if version > head_schema_version():
                raise Invalid(TOO_NEW, field="path")
            count = lambda table: db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]  # noqa: E731
            return BackupInfo(version, count("event"), count("group"), count("category"))
    except sqlite3.DatabaseError as exc:
        raise Invalid(NOT_OURS, field="path") from exc


def _source(raw: str | Path, database: Database) -> Path:
    path = folders.inside_home(raw)
    if not path.is_file():
        raise NotFound("Il file non esiste più.", field="path")
    in_use = database.path.resolve()
    if path in (in_use, *(in_use.with_name(in_use.name + s) for s in _SIDECARS)):
        raise Invalid(IN_USE, field="path")
    return path


def _stage(source: Path, directory: Path) -> Path:
    """A private copy of ``source`` next to the database: only the copy is ever opened."""
    staged = directory / f".ripristino-{uuid.uuid4().hex[:8]}.db"
    try:
        shutil.copyfile(source, staged)
    except PermissionError as exc:
        staged.unlink(missing_ok=True)
        raise Forbidden("Non hai il permesso di leggere questo file.", field="path") from exc
    return staged


def _settle(path: Path) -> None:
    """Fold any write-ahead log into the file itself: one file, nothing beside it to lose."""
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA journal_mode=DELETE")


def _discard(path: Path) -> None:
    for name in (path, *(path.with_name(path.name + s) for s in _SIDECARS)):
        name.unlink(missing_ok=True)


def inspect(raw: str | Path) -> dict[str, Any]:
    """What a restore of ``raw`` would bring back, without restoring it."""
    database = get_database()
    source = _source(raw, database)
    staged = _stage(source, database.path.parent)
    try:
        info = identify(staged)
    finally:
        _discard(staged)
    modified = dt.datetime.fromtimestamp(source.stat().st_mtime).replace(microsecond=0)
    return {"path": str(source), "modified": modified.isoformat(), **asdict(info)}


def _export_running() -> bool:
    from .export.jobs import runner

    return runner.busy()


def _set_aside(path: Path, now: dt.datetime) -> Path:
    """Move the database in use (and what SQLite keeps beside it) out of the way."""
    aside = reserve_path(path.parent, f"catalog-prima-del-ripristino-{now:%Y-%m-%d-%H%M%S}.db")
    os.replace(path, aside)
    for suffix in _SIDECARS:
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists():
            os.replace(sidecar, aside.with_name(aside.name + suffix))
    return aside


def restore(raw: str | Path, now: dt.datetime | None = None) -> dict[str, Any]:
    """Replace the database with the backup at ``raw``; the old one is kept aside."""
    database = get_database()
    source = _source(raw, database)
    if _export_running():
        raise Conflict(EXPORT_RUNNING)
    staged = _stage(source, database.path.parent)
    try:
        info = identify(staged)
        if info.schema_version < head_schema_version():
            older = Database(staged)
            older.migrate()
            older.dispose()
            _settle(staged)
        with database.gate.exclusive():
            if _export_running():
                raise Conflict(EXPORT_RUNNING)
            database.dispose()
            aside = _set_aside(database.path, now or dt.datetime.now())
            try:
                os.replace(staged, database.path)
            except BaseException:
                os.replace(aside, database.path)
                raise
    finally:
        _discard(staged)
    # The engine reconnects by itself, to the new file; stamping it also proves it opens.
    database.migrate()
    _log.info("ripristinato %s; il database precedente è in %s", source, aside)
    return {"aside": str(aside), **asdict(info), "schema_version": head_schema_version()}
