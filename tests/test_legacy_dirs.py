# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The program was called ``calendariparrocchia``: its folders move to the new name once."""

from __future__ import annotations

import json
import os

import pytest

from cp.config import APP_ID, LEGACY_APP_IDS, LegacyRunning, get_settings
from cp.db.session import Database

OLD = LEGACY_APP_IDS[0]


def old_install(xdg_home):
    """What the old version leaves: a database in its data folder, a log in its state."""
    data = xdg_home / "share" / OLD
    Database(data / "catalog.db").migrate()
    (data / "window-profile").mkdir()
    (xdg_home / "state" / OLD / "logs").mkdir(parents=True)
    (xdg_home / "state" / OLD / "logs" / f"{OLD}.log").write_text("vecchio\n")
    return data


def test_the_old_folders_become_the_new_ones(xdg_home):
    old_install(xdg_home)
    moved = get_settings().ensure_dirs()
    assert [(a.name, b.name) for a, b in moved] == [(OLD, APP_ID), (OLD, APP_ID)]
    assert not (xdg_home / "share" / OLD).exists()
    assert not (xdg_home / "state" / OLD).exists()
    data = xdg_home / "share" / APP_ID
    assert (data / "catalog.db").is_file() and (data / "window-profile").is_dir()
    assert (xdg_home / "state" / APP_ID / "logs" / f"{OLD}.log").read_text() == "vecchio\n"
    # Opened under the new name, the database is stamped with it.
    Database(data / "catalog.db").migrate()
    # A second start finds nothing left to move.
    assert get_settings().ensure_dirs() == []


def test_existing_new_folders_are_never_replaced(xdg_home):
    old_install(xdg_home)
    (xdg_home / "share" / APP_ID).mkdir()
    (xdg_home / "share" / APP_ID / "catalog.db").write_bytes(b"nuovo")
    moved = get_settings().ensure_dirs()
    assert [a.parent.name for a, _ in moved] == ["state"]
    assert (xdg_home / "share" / APP_ID / "catalog.db").read_bytes() == b"nuovo"
    assert (xdg_home / "share" / OLD / "catalog.db").is_file()


def test_nothing_moves_while_the_old_version_runs(xdg_home):
    old_install(xdg_home)
    lock = xdg_home / "run" / f"{OLD}.lock"
    lock.write_text(json.dumps({"pid": os.getpid(), "port": 8746}))
    with pytest.raises(LegacyRunning):
        get_settings().ensure_dirs()
    assert (xdg_home / "share" / OLD / "catalog.db").is_file()
    assert not (xdg_home / "share" / APP_ID).exists()


def test_a_stale_old_lock_does_not_block(xdg_home):
    old_install(xdg_home)
    (xdg_home / "run" / f"{OLD}.lock").write_text(json.dumps({"pid": 2**22 + 12345, "port": 1}))
    assert len(get_settings().ensure_dirs()) == 2
