# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The SQLite database: engine, pragmas, migrations, short sessions (SPEC §10.1).

There is one database per program, opened by :func:`open_database` when the
server is created. Sessions are short: :func:`session_scope` commits or rolls
back and closes. Nothing holds a session while doing slow work (the export
reads its data, closes the session, then composes).

Every session holds the database's :class:`Gate` shared; a restore holds it
exclusive while it swaps the file underneath (``backup.py``, SPEC §10.4).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ..config import APP_ID
from .models import Setting

__all__ = ["Database", "Gate", "get_database", "open_database", "session_scope"]

_log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

#: Rows of ``setting`` that identify the file: a backup is checked against them.
APP_KEY = "app"
SCHEMA_VERSION_KEY = "schema_version"


def _set_pragmas(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def head_schema_version() -> int:
    """The schema version this program writes: the number of the newest migration."""
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    return int(head or 0)


class Gate:
    """Many sessions at once, or one owner alone: a shared/exclusive lock.

    Shared is re-entrant within a thread, so a session opened inside another
    never waits for an owner that is itself waiting for the outer one to end.
    """

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._shared = 0
        self._exclusive = False
        self._local = threading.local()

    @contextmanager
    def shared(self) -> Iterator[None]:
        depth = getattr(self._local, "depth", 0)
        if depth == 0:
            with self._cond:
                self._cond.wait_for(lambda: not self._exclusive)
                self._shared += 1
        self._local.depth = depth + 1
        try:
            yield
        finally:
            self._local.depth = depth
            if depth == 0:
                with self._cond:
                    self._shared -= 1
                    self._cond.notify_all()

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        with self._cond:
            self._cond.wait_for(lambda: not self._exclusive)
            # Claimed first: no new session starts while the open ones finish.
            self._exclusive = True
            self._cond.wait_for(lambda: self._shared == 0)
        try:
            yield
        finally:
            with self._cond:
                self._exclusive = False
                self._cond.notify_all()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.gate = Gate()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(
            f"sqlite:///{path}", connect_args={"check_same_thread": False}
        )
        event.listen(self.engine, "connect", _set_pragmas)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def migrate(self) -> None:
        """Bring the schema to the newest migration, then stamp the file as ours."""
        config = alembic_config()
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with self.session() as session:
            session.merge(Setting(key=APP_KEY, value=APP_ID))
            session.merge(Setting(key=SCHEMA_VERSION_KEY, value=head_schema_version()))

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.gate.shared():
            session = self.sessions()
            try:
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise
            finally:
                session.close()

    def dispose(self) -> None:
        self.engine.dispose()


_lock = threading.Lock()
_current: Database | None = None


def open_database(path: Path) -> Database:
    """Open (creating and migrating if needed) the program's database."""
    global _current
    with _lock:
        if _current is not None and _current.path == path:
            return _current
        if _current is not None:
            _current.dispose()
        database = Database(path)
        database.migrate()
        _log.info("database aperto: %s", path)
        _current = database
        return database


def get_database() -> Database:
    if _current is None:
        raise RuntimeError("database not opened")
    return _current


@contextmanager
def session_scope() -> Iterator[Session]:
    """A short session on the program's database: commit on success, else roll back."""
    with get_database().session() as session:
        yield session
