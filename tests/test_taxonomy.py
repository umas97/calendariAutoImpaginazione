# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Groups and categories: tests 2, 3, 9, 10 and 11 of SPEC §15."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cp.domain.palette import PALETTE

KINDS = ["groups", "categories"]


def names(api, kind, **params):
    return [item["name"] for item in api.get(f"/api/{kind}", params=params).json()]


# --- test 2: names, uniqueness, limits, order --------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_name_is_cleaned(api, kind):
    response = api.post(f"/api/{kind}", json={"name": "  5ª   elementare \t"})
    assert response.status_code == 201
    assert response.json()["name"] == "5ª elementare"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
def test_name_length_limits(api, kind, name):
    response = api.post(f"/api/{kind}", json={"name": name})
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "name"


@pytest.mark.parametrize("kind", KINDS)
def test_sixty_characters_are_fine(api, kind):
    assert api.post(f"/api/{kind}", json={"name": "x" * 60}).status_code == 201


@pytest.mark.parametrize("kind", KINDS)
def test_names_are_unique_ignoring_case_archived_included(api, kind):
    first = api.post(f"/api/{kind}", json={"name": "Coro"}).json()["id"]
    assert api.post(f"/api/{kind}", json={"name": "CORO"}).status_code == 409
    api.patch(f"/api/{kind}/{first}", json={"archived": True})
    response = api.post(f"/api/{kind}", json={"name": "  coro "})
    assert response.status_code == 409
    assert "Coro" in response.json()["error"]["message"]


@pytest.mark.parametrize("kind", KINDS)
def test_rename_checks_uniqueness_but_not_against_itself(api, kind):
    a = api.post(f"/api/{kind}", json={"name": "Coro"}).json()["id"]
    api.post(f"/api/{kind}", json={"name": "Oratorio"})
    assert api.patch(f"/api/{kind}/{a}", json={"name": "oratorio"}).status_code == 409
    response = api.patch(f"/api/{kind}/{a}", json={"name": "CORO"})
    assert response.status_code == 200
    assert response.json()["name"] == "CORO"


@pytest.mark.parametrize("kind", KINDS)
def test_new_items_go_last_and_reorder_takes_the_full_list(api, kind):
    ids = [api.post(f"/api/{kind}", json={"name": n}).json()["id"] for n in "ABC"]
    assert names(api, kind) == ["A", "B", "C"]
    api.patch(f"/api/{kind}/{ids[1]}", json={"archived": True})

    assert api.post(f"/api/{kind}/reorder", json={"ids": [ids[2], ids[0]]}).status_code == 422
    assert (
        api.post(f"/api/{kind}/reorder", json={"ids": [ids[2], ids[0], ids[0]]}).status_code == 422
    )
    response = api.post(f"/api/{kind}/reorder", json={"ids": [ids[2], ids[1], ids[0]]})
    assert response.status_code == 204
    assert names(api, kind, include_archived=True) == ["C", "B", "A"]
    assert names(api, kind) == ["C", "A"]


@pytest.mark.parametrize("kind", KINDS)
def test_unknown_id_is_404(api, kind):
    assert api.patch(f"/api/{kind}/999", json={"name": "X"}).status_code == 404
    assert api.delete(f"/api/{kind}/999").status_code == 404
    assert api.get(f"/api/{kind}/999/usage").status_code == 404


def test_event_counts(api):
    g1, g2 = api.group("A"), api.group("B")
    c = api.category()
    api.event([g1], [c])
    api.event([g1, g2], [c])
    counts = {g["name"]: g["event_count"] for g in api.get("/api/groups").json()}
    assert counts == {"A": 2, "B": 1}
    assert api.get("/api/categories").json()[0]["event_count"] == 2


# --- test 3: colours -------------------------------------------------------------


def test_colour_is_validated_and_stored_upper_case(api):
    response = api.post("/api/categories", json={"name": "Messa", "color": "#2a9d8f"})
    assert response.json()["color"] == "#2A9D8F"
    for bad in ("2A9D8F", "#2A9D8", "#2A9D8FF", "#GGGGGG", "rosso"):
        response = api.post("/api/categories", json={"name": f"X{bad}", "color": bad})
        assert response.status_code == 422, bad
        assert response.json()["error"]["field"] == "color"
    cid = api.category("Ritiro")
    assert api.patch(f"/api/categories/{cid}", json={"color": "nero"}).status_code == 422
    assert api.patch(f"/api/categories/{cid}", json={"color": "#abcdef"}).json()["color"] == (
        "#ABCDEF"
    )


def test_colours_are_assigned_from_the_palette_then_start_again(api):
    api.post("/api/categories", json={"name": "Manuale", "color": PALETTE[1]})
    archived = api.category("Vecchia")
    api.patch(f"/api/categories/{archived}", json={"archived": True})
    # PALETTE[1] is taken by hand, PALETTE[0] by an archived category.
    colors = [
        api.post("/api/categories", json={"name": f"C{i}"}).json()["color"] for i in range(11)
    ]
    assert colors[:10] == list(PALETTE[2:])
    assert colors[10] == PALETTE[0]


def test_palette_is_served_in_assignment_order(api):
    assert api.get("/api/categories/palette").json() == list(PALETTE)


# --- test 9 and 10: deletion and orphans ---------------------------------------------


@pytest.fixture
def setup(api):
    """Two groups, two categories, and events with one or both of each."""
    g1, g2 = api.group("Cresimandi"), api.group("Coro")
    c1, c2 = api.category("Catechesi"), api.category("Messa")
    shared = api.event([g1, g2], [c1, c2], title="Condiviso")["id"]
    only_g1 = api.event([g1], [c2, c1], title="Solo G1")["id"]
    only_c1 = api.event([g2], [c1], title="Solo C1")["id"]
    return {"g1": g1, "g2": g2, "c1": c1, "c2": c2,
            "shared": shared, "only_g1": only_g1, "only_c1": only_c1}  # fmt: skip


def event(api, event_id):
    return api.get(f"/api/events/{event_id}")


def test_group_without_orphans_is_deleted_at_once(api, setup):
    assert api.get(f"/api/groups/{setup['g2']}/usage").json() == {"events": 2, "orphans": 1}
    api.delete(f"/api/events/{setup['only_c1']}")
    assert api.get(f"/api/groups/{setup['g2']}/usage").json() == {"events": 1, "orphans": 0}
    assert api.delete(f"/api/groups/{setup['g2']}").status_code == 204
    assert event(api, setup["shared"]).json()["group_ids"] == [setup["g1"]]


def test_group_with_orphans_needs_a_choice(api, setup):
    response = api.delete(f"/api/groups/{setup['g1']}")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["orphans"] == 1
    assert "1 evento ha solo questo gruppo" in error["message"]
    # Nothing changed.
    assert names(api, "groups") == ["Cresimandi", "Coro"]
    assert event(api, setup["shared"]).json()["group_ids"] == sorted([setup["g1"], setup["g2"]])


def test_group_orphans_reassigned(api, setup):
    g3 = api.group("Oratorio")
    response = api.delete(f"/api/groups/{setup['g1']}", params={"orphans": "reassign", "to": g3})
    assert response.status_code == 204
    assert event(api, setup["only_g1"]).json()["group_ids"] == [g3]
    assert event(api, setup["shared"]).json()["group_ids"] == [setup["g2"]]


@pytest.mark.parametrize("target", [None, "self", 999])
def test_reassign_needs_another_existing_group(api, setup, target):
    params = {"orphans": "reassign"}
    if target is not None:
        params["to"] = setup["g1"] if target == "self" else target
    response = api.delete(f"/api/groups/{setup['g1']}", params=params)
    assert response.status_code == 422
    assert names(api, "groups") == ["Cresimandi", "Coro"]


def test_group_orphans_deleted(api, setup):
    response = api.delete(f"/api/groups/{setup['g1']}", params={"orphans": "delete"})
    assert response.status_code == 204
    assert event(api, setup["only_g1"]).status_code == 404
    assert event(api, setup["shared"]).json()["group_ids"] == [setup["g2"]]


def test_deletion_is_atomic(api, setup, monkeypatch):
    """A failure half way leaves events, links and the group as they were."""
    from cp.domain import taxonomy

    def boom(*_args, **_kwargs):
        raise RuntimeError("guasto simulato")

    monkeypatch.setattr(taxonomy, "_renumber", boom)
    tolerant = TestClient(
        api.client.app, base_url="http://127.0.0.1", raise_server_exceptions=False
    )
    response = tolerant.delete(f"/api/categories/{setup['c1']}", params={"orphans": "delete"})
    assert response.status_code == 500
    assert "log" in response.json()["error"]["message"]
    assert event(api, setup["only_c1"]).status_code == 200
    assert event(api, setup["shared"]).json()["category_ids"] == [setup["c1"], setup["c2"]]
    assert names(api, "categories") == ["Catechesi", "Messa"]


def test_category_orphans_and_main_category(api, setup):
    response = api.delete(f"/api/categories/{setup['c1']}")
    assert response.status_code == 409
    assert response.json()["error"]["orphans"] == 1

    response = api.delete(
        f"/api/categories/{setup['c1']}", params={"orphans": "reassign", "to": setup["c2"]}
    )
    assert response.status_code == 204
    # The first category is gone: the second becomes the main one.
    assert event(api, setup["shared"]).json()["category_ids"] == [setup["c2"]]
    assert event(api, setup["only_g1"]).json()["category_ids"] == [setup["c2"]]
    assert event(api, setup["only_c1"]).json()["category_ids"] == [setup["c2"]]


def test_category_orphans_deleted(api, setup):
    c3 = api.category("Festa")
    api.put(
        f"/api/events/{setup['shared']}",
        json={
            "title": "Condiviso",
            "start_date": "2026-10-18",
            "start_time": "15:00",
            "group_ids": [setup["g1"]],
            "category_ids": [setup["c1"], c3, setup["c2"]],
        },
    )
    response = api.delete(f"/api/categories/{setup['c1']}", params={"orphans": "delete"})
    assert response.status_code == 204
    assert event(api, setup["only_c1"]).status_code == 404
    assert event(api, setup["shared"]).json()["category_ids"] == [c3, setup["c2"]]
    assert event(api, setup["only_g1"]).json()["category_ids"] == [setup["c2"]]


# --- test 11: archive ----------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_archived_items_leave_the_lists_but_not_the_events(api, kind):
    g, c = api.group(), api.category()
    created = api.event([g], [c])
    target = g if kind == "groups" else c
    response = api.patch(f"/api/{kind}/{target}", json={"archived": True})
    assert response.json()["archived"] is True

    assert api.get(f"/api/{kind}").json() == []
    archived = api.get(f"/api/{kind}", params={"include_archived": True}).json()
    assert [(i["id"], i["archived"], i["event_count"]) for i in archived] == [(target, True, 1)]
    after = event(api, created["id"]).json()
    assert after["group_ids"] == [g] and after["category_ids"] == [c]

    api.patch(f"/api/{kind}/{target}", json={"archived": False})
    assert [i["id"] for i in api.get(f"/api/{kind}").json()] == [target]
