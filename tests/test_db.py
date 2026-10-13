# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test 1: the database is created by the migrations, and a second start changes nothing."""

from __future__ import annotations

import sqlite3

from alembic import command

from cp.config import APP_ID
from cp.db import session as db_session
from cp.db.session import Database, head_schema_version


def _schema(path) -> list[tuple]:
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY name"
        ).fetchall()


def _rows(path, table: str) -> list[tuple]:
    with sqlite3.connect(path) as connection:
        return connection.execute(f'SELECT * FROM "{table}" ORDER BY 1').fetchall()


def test_created_from_nothing_and_stable_on_second_start(tmp_path):
    path = tmp_path / "catalog.db"
    first = Database(path)
    first.migrate()
    first.dispose()

    tables = {row[1] for row in _schema(path) if row[0] == "table"}
    assert {
        "group",
        "category",
        "event",
        "event_group",
        "event_category",
        "setting",
        "asset",
        "alembic_version",
    } <= tables
    indexes = {row[1] for row in _schema(path) if row[0] == "index"}
    assert {"ix_event_start_date", "ix_event_end_date"} <= indexes

    schema, settings = _schema(path), _rows(path, "setting")
    assert ("app", f'"{APP_ID}"') in settings
    assert ("schema_version", head_schema_version()) in settings

    second = Database(path)
    second.migrate()
    second.dispose()
    assert _schema(path) == schema
    assert _rows(path, "setting") == settings
    assert _rows(path, "alembic_version") == [(f"{head_schema_version():04d}",)]


def test_upgrade_keeps_existing_events_and_adds_empty_notes(tmp_path):
    """A database written by an older version: its events survive the migrations."""
    path = tmp_path / "catalog.db"
    old = Database(path)
    config = db_session.alembic_config()
    with old.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0001")
        connection.exec_driver_sql(
            "INSERT INTO event (title, start_date, all_day, start_time, place, created_at,"
            " updated_at) VALUES ('Messa', '2026-10-18', 0, '10:30', '', '2026-10-13',"
            " '2026-10-13')"
        )
    old.dispose()

    new = Database(path)
    new.migrate()
    new.dispose()
    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT title, notes FROM event").fetchall()
    assert rows == [("Messa", "")]
    assert ("schema_version", head_schema_version()) in _rows(path, "setting")


def test_pragmas_on_every_connection(tmp_path):
    database = Database(tmp_path / "catalog.db")
    database.migrate()
    with database.engine.connect() as connection:
        raw = connection.exec_driver_sql
        assert raw("PRAGMA journal_mode").scalar() == "wal"
        assert raw("PRAGMA foreign_keys").scalar() == 1
        assert raw("PRAGMA busy_timeout").scalar() == 15000
        assert raw("PRAGMA synchronous").scalar() == 1  # NORMAL
    database.dispose()


def test_the_server_opens_the_database_in_the_data_directory(api, xdg_home):
    assert db_session.get_database().path == xdg_home / "share" / APP_ID / "catalog.db"
    assert api.get("/api/groups").json() == []
