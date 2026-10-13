# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The folder picker: test 20 of SPEC §15 (§10.3)."""

from __future__ import annotations

import pytest

from cp import folders


@pytest.fixture
def tree(xdg_home, tmp_path):
    (xdg_home / "Documenti" / "Calendari").mkdir(parents=True)
    (xdg_home / "Documenti" / "archivio").mkdir()
    (xdg_home / "Documenti" / ".nascosta").mkdir()
    (xdg_home / "Documenti" / "nota.txt").write_text("x")
    outside = tmp_path / "fuori"
    outside.mkdir()
    (xdg_home / "Documenti" / "scorciatoia").symlink_to(outside)
    (xdg_home / "Documenti" / "dentro").symlink_to(xdg_home / "Documenti" / "Calendari")
    return xdg_home


def names(api, path, **params):
    response = api.get("/api/folders", params={"path": str(path)} | params)
    assert response.status_code == 200, response.text
    return [f["name"] for f in response.json()["folders"]]


def test_lists_only_subfolders(api, tree):
    assert names(api, tree / "Documenti") == ["archivio", "Calendari", "dentro"]
    assert names(api, tree / "Documenti", hidden=1) == [
        ".nascosta",
        "archivio",
        "Calendari",
        "dentro",
    ]


def test_default_is_home_and_parent_stops_there(api, tree):
    listing = api.get("/api/folders").json()
    assert listing["path"] == str(tree) and listing["parent"] is None
    inner = api.get("/api/folders", params={"path": str(tree / "Documenti")}).json()
    assert inner["parent"] == str(tree)


@pytest.mark.parametrize(
    "path",
    ["/", "/etc", "{home}/..", "{home}/Documenti/../../..", "{home}/Documenti/scorciatoia"],
)
def test_outside_home_is_403(api, tree, path):
    response = api.get("/api/folders", params={"path": path.format(home=tree)})
    assert response.status_code == 403
    assert response.json()["error"]["message"] == folders.OUTSIDE


def test_symlink_inside_home_is_fine(api, tree):
    response = api.get("/api/folders", params={"path": str(tree / "Documenti" / "dentro")})
    assert response.status_code == 200


def test_create_folder(api, tree):
    response = api.post("/api/folders", json={"path": str(tree / "Documenti"), "name": "Nuova"})
    assert response.status_code == 201
    assert (tree / "Documenti" / "Nuova").is_dir()
    again = api.post("/api/folders", json={"path": str(tree / "Documenti"), "name": "Nuova"})
    assert again.status_code == 409
    for bad in ("", "..", "a/b"):
        response = api.post("/api/folders", json={"path": str(tree / "Documenti"), "name": bad})
        assert response.status_code == 422
    response = api.post("/api/folders", json={"path": "/tmp", "name": "x"})
    assert response.status_code == 403


def test_open_folder(api, tree, monkeypatch):
    launched = []
    monkeypatch.setattr(folders, "_launcher", lambda: ["gio", "open"])
    monkeypatch.setattr(folders.subprocess, "Popen", lambda args, **_: launched.append(args))
    response = api.post("/api/folders/open", json={"path": str(tree / "Documenti")})
    assert response.status_code == 200
    assert launched == [["gio", "open", str(tree / "Documenti")]]
    assert api.post("/api/folders/open", json={"path": "/etc"}).status_code == 403
    assert api.post("/api/folders/open", json={"path": str(tree / "manca")}).status_code == 404


def test_db_files_only_on_request_newest_first(api, tree):
    documents = tree / "Documenti"
    (documents / "vecchio.db").write_bytes(b"a")
    (documents / "NUOVO.DB").write_bytes(b"bb")
    import os

    os.utime(documents / "vecchio.db", (1_700_000_000, 1_700_000_000))
    (tree / "fuori.db").symlink_to("/etc/hostname")
    plain = api.get("/api/folders", params={"path": str(documents)}).json()
    assert "files" not in plain
    listing = api.get("/api/folders", params={"path": str(documents), "files": "db"}).json()
    assert [(f["name"], f["size"]) for f in listing["files"]] == [
        ("NUOVO.DB", 2),
        ("vecchio.db", 1),
    ]
    assert listing["files"][1]["modified"].startswith("2023-11-14T")
    # A link to a file outside the home is not offered; neither is any other suffix.
    home = api.get("/api/folders", params={"path": str(tree), "files": "db"}).json()
    assert home["files"] == []
    assert api.get("/api/folders", params={"files": "txt"}).status_code == 422
