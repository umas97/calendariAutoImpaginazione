# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""File names and never overwriting: test 18 of SPEC §15 (§2.2, §8.6)."""

from __future__ import annotations

import datetime as dt
import hashlib

import pytest

from cp.export import output

D = dt.date


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ('Cresimandi / 2026: "A" <b>?*|\\', "Cresimandi 2026 A b"),
        ("Coro\tdei   giovani\n", "Coro dei giovani"),
        ("..nascosto", "nascosto"),
        ("///", "Gruppo"),
        ("5ª elementare", "5ª elementare"),
    ],
)
def test_clean_name(raw, clean):
    assert output.clean_name(raw) == clean


def test_clean_name_truncates_to_80():
    assert len(output.clean_name("x" * 200)) == 80


def test_names_by_mode():
    first, last = D(2026, 10, 1), D(2027, 6, 30)
    assert output.group_file("Cresimandi", first, last, "pdf") == (
        "Cresimandi 2026-10-01_2027-06-30.pdf"
    )
    assert output.group_file("A/B", first, last, "png", 2) == "AB 2026-10-01_2027-06-30 p2.png"
    assert output.single_pdf_file(first, last) == "Calendari per gruppo 2026-10-01_2027-06-30.pdf"
    assert output.combined_file(first, last, "png", 1) == (
        "Calendario completo 2026-10-01_2027-06-30 p1.png"
    )


def test_collisions_get_a_number_and_never_overwrite(tmp_path):
    existing = tmp_path / "Coro.pdf"
    existing.write_bytes(b"originale")
    before = hashlib.sha256(existing.read_bytes()).hexdigest()
    second = output.write_new(tmp_path, "Coro.pdf", b"nuovo")
    third = output.write_new(tmp_path, "Coro.pdf", b"ancora")
    assert (second.name, third.name) == ("Coro (2).pdf", "Coro (3).pdf")
    assert hashlib.sha256(existing.read_bytes()).hexdigest() == before
    assert second.read_bytes() == b"nuovo"


def test_reserve_path_creates_the_file_exclusively(tmp_path):
    path = output.reserve_path(tmp_path, "a.png")
    assert path.exists() and path.read_bytes() == b""
    assert output.reserve_path(tmp_path, "a.png").name == "a (2).png"


def test_failed_write_leaves_no_file(tmp_path, monkeypatch):
    folder = tmp_path / "out"
    folder.mkdir()
    real_open = open

    def failing_open(path, mode="r", *args, **kwargs):
        file = real_open(path, mode, *args, **kwargs)
        if mode == "r+b":
            file.close()
            raise OSError("disco pieno")
        return file

    monkeypatch.setattr("builtins.open", failing_open)
    with pytest.raises(OSError):
        output.write_new(folder, "x.pdf", b"data")
    monkeypatch.undo()
    assert list(folder.iterdir()) == []


def test_export_folder_is_always_new(tmp_path):
    when = dt.datetime(2026, 10, 13, 9, 5)
    base = tmp_path / "Calendari parrocchia"
    first = output.export_folder(base, when)
    second = output.export_folder(base, when)
    assert first.name == "Export 2026-10-13 09-05"
    assert second.name == "Export 2026-10-13 09-05 (2)"
