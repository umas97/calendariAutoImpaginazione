# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test 22: settings -- known keys only, validated values, vanished ids dropped."""

from __future__ import annotations

import pytest


def test_defaults(api):
    settings = api.get("/api/settings").json()
    assert settings == {
        "calendar.view": "month",
        "calendar.filters": {"group_ids": None, "category_ids": None},
        "export.last": None,
        "parish.name": "",
    }


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("calendar.view", "week"),
        ("calendar.view", "list"),
        ("calendar.filters", {"group_ids": [], "category_ids": None}),
        ("parish.name", "Parrocchia San Giuseppe"),
    ],
)
def test_write_and_read_back(api, key, value):
    response = api.put(f"/api/settings/{key}", json={"value": value})
    assert response.status_code == 200, response.text
    assert api.get("/api/settings").json()[key] == value


def test_parish_name_is_trimmed(api):
    api.put("/api/settings/parish.name", json={"value": "  San Rocco  "})
    assert api.get("/api/settings").json()["parish.name"] == "San Rocco"


def test_export_last_round_trip(api):
    group, category = api.group(), api.category()
    value = {
        "period": {"from": "2026-09-01", "to": "2027-06-30"},
        "mode": "single_pdf",
        "formats": ["pdf", "png"],
        "dpi": 300,
        "selections": [{"group_id": group, "category_ids": [category]}],
        "output_dir": "/home/utente/Documenti/calendariAutoImpaginazione",
    }
    assert api.put("/api/settings/export.last", json={"value": value}).status_code == 200
    assert api.get("/api/settings").json()["export.last"] == value


def test_export_last_all_categories_is_null(api):
    """``null`` = every category, also those created later (like the calendar filters)."""
    group = api.group()
    value = {
        "period": None,
        "mode": "per_group",
        "formats": ["pdf"],
        "dpi": 200,
        "selections": [{"group_id": group, "category_ids": None}],
        "output_dir": None,
    }
    assert api.put("/api/settings/export.last", json={"value": value}).status_code == 200
    assert api.get("/api/settings").json()["export.last"] == value


def test_unknown_key_is_404(api):
    response = api.put("/api/settings/window.size", json={"value": 3})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("calendar.view", "year"),
        ("calendar.view", None),
        ("calendar.filters", {"group_ids": "tutti"}),
        ("calendar.filters", {"gruppi": [1]}),
        ("parish.name", "x" * 81),
        ("parish.name", 42),
        ("export.last", {"mode": "griglia"}),
        ("export.last", {"dpi": 72}),
        ("export.last", {"formats": ["docx"]}),
    ],
)
def test_invalid_value_is_422(api, key, value):
    response = api.put(f"/api/settings/{key}", json={"value": value})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["field"] == "value"
    assert key in error["message"]


def test_vanished_ids_are_ignored_on_read(api):
    kept, gone = api.group("Coro"), api.group("Oratorio")
    category = api.category()
    api.put(
        "/api/settings/calendar.filters",
        json={"value": {"group_ids": [kept, gone], "category_ids": [category, 999]}},
    )
    api.put(
        "/api/settings/export.last",
        json={
            "value": {
                "selections": [
                    {"group_id": kept, "category_ids": [category, 999]},
                    {"group_id": gone, "category_ids": [category]},
                ]
            }
        },
    )
    assert api.delete(f"/api/groups/{gone}").status_code == 204

    settings = api.get("/api/settings").json()
    assert settings["calendar.filters"] == {"group_ids": [kept], "category_ids": [category]}
    assert settings["export.last"]["selections"] == [{"group_id": kept, "category_ids": [category]}]


def test_identity_rows_are_not_settings(api):
    assert "app" not in api.get("/api/settings").json()
    assert api.put("/api/settings/schema_version", json={"value": 99}).status_code == 404
