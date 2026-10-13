# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Backup and restore: tests 23 and 24 of SPEC §15 (§10.4)."""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
import threading
import time

import pytest
from alembic import command

from cp import backup
from cp.config import APP_ID
from cp.db import session as db_session
from cp.db.session import Database, Gate, head_schema_version

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360f8cfc0f01f0005000201e2a9a3"
    "ba0000000049454e44ae426082"
)


@pytest.fixture
def filled(api, xdg_home):
    """Two groups, a category, three events, a parish name and a logo."""
    coro, cresimandi = api.group("Coro"), api.group("Cresimandi")
    catechesi = api.category("Catechesi")
    for day in ("2026-10-18", "2026-10-25"):
        api.event([cresimandi], [catechesi], start_date=day, notes="interna")
    api.event([coro, cresimandi], [catechesi], title="Prove", start_date="2026-11-01")
    assert api.put("/api/settings/parish.name", json={"value": "San Luigi"}).status_code == 200
    logo = api.post("/api/parish/logo", files={"logo": ("l.png", PNG_1PX, "image/png")})
    assert logo.status_code == 200, logo.text
    (xdg_home / "Documenti").mkdir()
    return api


def snapshot(api) -> dict:
    """Everything the user can see of their data, through the API."""
    return {
        "groups": api.get("/api/groups?include_archived=true").json(),
        "categories": api.get("/api/categories?include_archived=true").json(),
        "events": api.get("/api/events?from=2026-01-01&to=2027-12-31").json(),
        "settings": api.get("/api/settings").json(),
        "parish": api.get("/api/parish").json(),
        "logo": api.get("/api/parish/logo").content,
    }


def data_dir(xdg_home):
    return xdg_home / "share" / APP_ID


def make_backup(api, folder, **body):
    response = api.post("/api/backup", json={"folder": str(folder)} | body)
    assert response.status_code == 201, response.text
    return response.json()["path"]


# --- test 23: backup ---------------------------------------------------------------


def test_backup_is_a_valid_database_with_the_same_data(filled, xdg_home):
    before = snapshot(filled)
    path = make_backup(filled, xdg_home / "Documenti")
    assert path == str(xdg_home / "Documenti" / backup.default_name(dt.date.today()))
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("SELECT count(*) FROM event").fetchone() == (3,)
        assert db.execute("SELECT data FROM asset WHERE key = 'parish.logo'").fetchone()
    assert snapshot(filled) == before


def test_backup_never_overwrites_and_cleans_the_name(filled, xdg_home):
    folder = xdg_home / "Documenti"
    first = make_backup(filled, folder, name="copia")
    (folder / "altro.db").write_bytes(b"mio")
    second = make_backup(filled, folder, name="copia.db")
    third = make_backup(filled, folder, name="altro.db")
    odd = make_backup(filled, folder, name='a/b:"c"')
    assert [os.path.basename(p) for p in (first, second, third, odd)] == [
        "copia.db",
        "copia (2).db",
        "altro (2).db",
        "abc.db",
    ]
    assert (folder / "altro.db").read_bytes() == b"mio"


def test_backup_refuses_folders_outside_home_or_missing(filled, xdg_home):
    assert filled.post("/api/backup", json={"folder": "/tmp"}).status_code == 403
    missing = filled.post("/api/backup", json={"folder": str(xdg_home / "manca")})
    assert missing.status_code == 404


def test_backup_options(api, xdg_home):
    options = api.get("/api/backup").json()
    assert options["default_name"] == f"calendariParrocchia backup {dt.date.today()}.db"
    assert options["default_folder"] == str(xdg_home)  # no ~/Documenti yet
    assert options["auto_dir"] == str(data_dir(xdg_home) / "backups")
    assert options["last_auto"] is None
    (xdg_home / "Documenti").mkdir()
    assert api.get("/api/backup").json()["default_folder"] == str(xdg_home / "Documenti")


# --- test 23: restore --------------------------------------------------------------


def test_restore_brings_back_the_data_and_sets_the_old_database_aside(filled, xdg_home):
    before = snapshot(filled)
    path = make_backup(filled, xdg_home / "Documenti")

    # Changes after the backup: a new event, a group gone, another name.
    filled.event([filled.group("Oratorio")], [before["categories"][0]["id"]], title="Dopo")
    coro = before["groups"][0]["id"]
    assert filled.delete(f"/api/groups/{coro}").status_code == 204
    filled.put("/api/settings/parish.name", json={"value": "Altro"})
    changed = snapshot(filled)

    info = filled.post("/api/restore/inspect", json={"path": path}).json()
    assert (info["events"], info["groups"], info["categories"]) == (3, 2, 1)
    assert snapshot(filled) == changed  # inspecting changes nothing

    response = filled.post("/api/restore", json={"path": path})
    assert response.status_code == 200, response.text
    assert snapshot(filled) == before

    aside = response.json()["aside"]
    assert os.path.dirname(aside) == str(data_dir(xdg_home))
    assert os.path.basename(aside).startswith("catalog-prima-del-ripristino-")
    with sqlite3.connect(aside) as db:
        titles = {row[0] for row in db.execute("SELECT title FROM event")}
    assert "Dopo" in titles
    # The restore leaves no copy of its own behind.
    leftovers = [p.name for p in data_dir(xdg_home).iterdir() if p.name.startswith(".ripristino")]
    assert leftovers == []
    # And the program goes on writing to the restored database.
    filled.event([before["groups"][1]["id"]], [before["categories"][0]["id"]], title="Ancora")
    assert len(snapshot(filled)["events"]) == 4


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", backup.NOT_OURS),
        (b"non sono un database" * 100, backup.NOT_OURS),
        (PNG_1PX, backup.NOT_OURS),
    ],
)
def test_restore_refuses_any_file(filled, xdg_home, content, message):
    before = snapshot(filled)
    path = xdg_home / "Documenti" / "file.db"
    path.write_bytes(content)
    for endpoint in ("/api/restore/inspect", "/api/restore"):
        response = filled.post(endpoint, json={"path": str(path)})
        assert response.status_code == 422
        assert response.json()["error"]["message"] == message
    assert snapshot(filled) == before
    names = {p.name for p in data_dir(xdg_home).iterdir()}
    assert not any(n.startswith(("catalog-prima", ".ripristino")) for n in names)


def test_restore_refuses_another_sqlite_database(filled, xdg_home):
    path = xdg_home / "Documenti" / "altro.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE setting (key TEXT, value JSON)")
        db.execute("INSERT INTO setting VALUES ('app', '\"altraapp\"')")
    response = filled.post("/api/restore", json={"path": str(path)})
    assert response.json()["error"]["message"] == backup.NOT_OURS


def test_restore_refuses_a_newer_schema(filled, xdg_home):
    before = snapshot(filled)
    path = make_backup(filled, xdg_home / "Documenti")
    with sqlite3.connect(path) as db:
        db.execute("UPDATE setting SET value = 99 WHERE key = 'schema_version'")
    response = filled.post("/api/restore", json={"path": path})
    assert response.status_code == 422
    assert response.json()["error"]["message"] == backup.TOO_NEW
    assert snapshot(filled) == before


def test_restore_migrates_an_older_backup(api, xdg_home):
    path = xdg_home / "vecchio.db"
    old = Database(path)
    config = db_session.alembic_config()
    with old.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0001")
        run = connection.exec_driver_sql
        run(f"INSERT INTO setting VALUES ('app', '\"{APP_ID}\"'), ('schema_version', '1')")
        run(
            'INSERT INTO "group" (name, name_key, position, archived)'
            " VALUES ('Coro', 'coro', 0, 0)"
        )
        run(
            "INSERT INTO category (name, name_key, color, position, archived)"
            " VALUES ('Messa', 'messa', '#E63946', 0, 0)"
        )
        run(
            "INSERT INTO event (title, start_date, all_day, start_time, place, created_at,"
            " updated_at) VALUES ('Messa', '2026-10-18', 0, '10:30', '', '2026-10-13',"
            " '2026-10-13')"
        )
        run("INSERT INTO event_group VALUES (1, 1)")
        run("INSERT INTO event_category VALUES (1, 1, 0)")
    old.dispose()

    response = api.post("/api/restore", json={"path": str(path)})
    assert response.status_code == 200, response.text
    assert response.json()["schema_version"] == head_schema_version()
    events = api.get("/api/events?from=2026-10-01&to=2026-10-31").json()
    assert [(e["title"], e["notes"]) for e in events] == [("Messa", "")]
    with sqlite3.connect(data_dir(xdg_home) / "catalog.db") as db:
        version = db.execute("SELECT value FROM setting WHERE key = 'schema_version'").fetchone()
    assert version == (head_schema_version(),)
    # The chosen file itself is never modified.
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("0001",)


def test_restore_refuses_the_database_in_use_and_paths_outside_home(filled, xdg_home):
    in_use = data_dir(xdg_home) / "catalog.db"
    response = filled.post("/api/restore", json={"path": str(in_use)})
    assert response.status_code == 422
    assert response.json()["error"]["message"] == backup.IN_USE
    assert filled.post("/api/restore", json={"path": "/etc/hostname"}).status_code == 403
    missing = filled.post("/api/restore", json={"path": str(xdg_home / "manca.db")})
    assert missing.status_code == 404


def test_restore_waits_for_no_export(filled, xdg_home, monkeypatch):
    path = make_backup(filled, xdg_home / "Documenti")
    monkeypatch.setattr(backup, "_export_running", lambda: True)
    response = filled.post("/api/restore", json={"path": path})
    assert response.status_code == 409
    assert response.json()["error"]["message"] == backup.EXPORT_RUNNING


def test_open_backups_folder(api, xdg_home, monkeypatch):
    from cp import folders

    launched = []
    monkeypatch.setattr(folders, "_launcher", lambda: ["gio", "open"])
    monkeypatch.setattr(folders.subprocess, "Popen", lambda args, **_: launched.append(args))
    assert api.post("/api/backup/open").status_code == 200
    assert launched == [["gio", "open", str(data_dir(xdg_home) / "backups")]]
    assert (data_dir(xdg_home) / "backups").is_dir()


# --- the gate the restore holds ----------------------------------------------------


def test_exclusive_waits_for_open_sessions_and_holds_new_ones():
    gate, order = Gate(), []
    entered = threading.Event()

    def reader():
        with gate.shared():
            entered.set()
            time.sleep(0.2)
            order.append("lettura finita")

    def writer():
        with gate.exclusive():
            order.append("esclusivo")
            time.sleep(0.2)

    def late_reader():
        with gate.shared():
            order.append("lettura tardiva")

    first = threading.Thread(target=reader)
    first.start()
    entered.wait()
    second = threading.Thread(target=writer)
    second.start()
    time.sleep(0.05)
    third = threading.Thread(target=late_reader)
    third.start()
    for thread in (first, second, third):
        thread.join(5)
    assert order == ["lettura finita", "esclusivo", "lettura tardiva"]


def test_shared_is_reentrant_while_an_exclusive_waits():
    gate, done = Gate(), threading.Event()

    def nested():
        with gate.shared():
            time.sleep(0.1)  # the exclusive claims the gate meanwhile
            with gate.shared():
                done.set()

    thread = threading.Thread(target=nested)
    thread.start()
    time.sleep(0.05)
    with gate.exclusive():
        pass
    thread.join(5)
    assert done.is_set()


# --- test 24: the automatic backup -------------------------------------------------


def autos(xdg_home) -> list[str]:
    return sorted(p.name for p in (data_dir(xdg_home) / "backups").iterdir())


def test_one_automatic_backup_a_day(api, xdg_home):
    database = db_session.get_database()
    day = dt.datetime(2026, 10, 13, 9, 0)
    made = backup.auto_backup(database, day)
    assert made is not None and made.name == "auto-2026-10-13.db"
    with sqlite3.connect(made) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    # Restarted the same day, or the next morning before 24 hours: nothing new.
    assert backup.auto_backup(database, day + dt.timedelta(hours=3)) is None
    assert backup.auto_backup(database, day + dt.timedelta(hours=23)) is None
    # A clock gone back does not make one either.
    assert backup.auto_backup(database, day - dt.timedelta(days=2)) is None
    assert backup.auto_backup(database, day + dt.timedelta(hours=25)) is not None
    assert autos(xdg_home) == ["auto-2026-10-13.db", "auto-2026-10-14.db"]
    last = api.get("/api/backup").json()["last_auto"]
    assert last == "2026-10-14T10:00:00"


def test_the_newest_fourteen_are_kept(api, xdg_home):
    database = db_session.get_database()
    folder = data_dir(xdg_home) / "backups"
    folder.mkdir(parents=True)
    (folder / "mio-backup.db").write_bytes(b"dell'utente")
    (folder / ".auto-2026-09-01.db.partial").write_bytes(b"interrotto")
    start = dt.datetime(2026, 9, 1, 8, 0)
    for n in range(20):
        assert backup.auto_backup(database, start + dt.timedelta(days=n)) is not None
    names = autos(xdg_home)
    assert names[0] == "auto-2026-09-07.db" and names[-2] == "auto-2026-09-20.db"
    assert len([n for n in names if n.startswith("auto-")]) == 14
    # Only its own files: the user's stays, the interrupted one goes.
    assert names[-1] == "mio-backup.db"
    assert not (folder / ".auto-2026-09-01.db.partial").exists()


def test_an_automatic_backup_can_be_restored(filled, xdg_home):
    before = snapshot(filled)
    made = backup.auto_backup(db_session.get_database())
    filled.event([before["groups"][0]["id"]], [before["categories"][0]["id"]], title="Dopo")
    response = filled.post("/api/restore", json={"path": str(made)})
    assert response.status_code == 200, response.text
    assert snapshot(filled) == before
