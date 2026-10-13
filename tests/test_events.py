# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Events: tests 4-8 of SPEC §15, plus places (§7.5)."""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest

from cp.domain.events import chronological_key


@pytest.fixture
def gc(api):
    return api.group(), api.category()


def body(gc, **fields):
    g, c = gc
    return {
        "title": "Incontro",
        "start_date": "2026-10-18",
        "start_time": "15:00",
        "group_ids": [g],
        "category_ids": [c],
    } | fields


def post(api, payload):
    return api.post("/api/events", json=payload)


def error(response, status=422):
    assert response.status_code == status, response.text
    return response.json()["error"]


# --- test 4: every row of SPEC §7.2 ------------------------------------------------


@pytest.mark.parametrize("title", ["", "   ", "x" * 121])
def test_title_required_and_limited(api, gc, title):
    e = error(post(api, body(gc, title=title)))
    assert e["field"] == "title"
    assert e["message"] == "Il titolo è obbligatorio (massimo 120 caratteri)."


def test_title_is_stripped_and_120_is_fine(api, gc):
    assert post(api, body(gc, title="  Messa  ")).json()["title"] == "Messa"
    assert post(api, body(gc, title="x" * 120)).status_code == 201


def test_start_time_needed_unless_all_day(api, gc):
    e = error(post(api, body(gc, start_time=None)))
    assert e["field"] == "start_time"
    assert e["message"] == "Indica l'ora di inizio, oppure scegli “Tutto il giorno”."
    created = post(api, body(gc, start_time="10:00", end_time="11:00", all_day=True)).json()
    assert created["all_day"] is True
    assert created["start_time"] is None and created["end_time"] is None


@pytest.mark.parametrize("value", ["9:00", "24:00", "12:60", "mezzogiorno", "12.30"])
def test_time_format(api, gc, value):
    assert error(post(api, body(gc, start_time=value)))["field"] == "start_time"
    assert error(post(api, body(gc, end_time=value)))["field"] == "end_time"


@pytest.mark.parametrize("end", ["15:00", "14:30"])
def test_same_day_end_time_after_start(api, gc, end):
    e = error(post(api, body(gc, end_time=end)))
    assert e["field"] == "end_time"
    assert e["message"] == "L'ora di fine deve essere dopo l'inizio."


def test_end_time_alone_on_the_same_day_is_fine(api, gc):
    created = post(api, body(gc, end_time="16:30")).json()
    assert (created["start_time"], created["end_time"]) == ("15:00", "16:30")
    assert post(api, body(gc, end_time=None)).json()["end_time"] is None


def test_multi_day_with_times_is_allowed_whatever_the_hours(api, gc):
    created = post(
        api, body(gc, end_date="2026-10-20", start_time="18:00", end_time="16:00")
    ).json()
    assert created["end_date"] == "2026-10-20"
    assert (created["start_time"], created["end_time"]) == ("18:00", "16:00")


def test_end_date_equal_to_start_is_normalized_away(api, gc):
    assert post(api, body(gc, end_date="2026-10-18")).json()["end_date"] is None


def test_end_date_before_start(api, gc):
    e = error(post(api, body(gc, end_date="2026-10-17")))
    assert e["field"] == "end_date"
    assert e["message"] == "La data di fine è prima della data di inizio."


def test_at_most_31_days(api, gc):
    assert post(api, body(gc, start_date="2026-10-01", end_date="2026-10-31")).status_code == 201
    e = error(post(api, body(gc, start_date="2026-10-01", end_date="2026-11-01")))
    assert e["field"] == "end_date"
    assert e["message"] == "Un evento può durare al massimo 31 giorni."


def test_place_is_optional_stripped_and_limited(api, gc):
    assert post(api, body(gc)).json()["place"] == ""
    assert post(api, body(gc, place="  Oratorio ")).json()["place"] == "Oratorio"
    assert error(post(api, body(gc, place="x" * 121)))["field"] == "place"


def test_all_problems_are_listed(api, gc):
    e = error(post(api, body(gc, title="", start_time=None, group_ids=[], category_ids=[])))
    fields = [p["field"] for p in e["errors"]]
    assert fields == ["title", "start_time", "group_ids", "category_ids"]
    assert e["field"] == "title"


def test_malformed_date_is_a_422_in_italian(api, gc):
    e = error(post(api, body(gc, start_date="18/10/2026")))
    assert e["field"] == "start_date"
    assert "AAAA-MM-GG" in e["message"]


# --- test 5: groups and categories ---------------------------------------------------


def test_groups_and_categories_are_required(api, gc):
    assert error(post(api, body(gc, group_ids=[])))["message"] == "Scegli almeno un gruppo."
    assert error(post(api, body(gc, category_ids=[])))["message"] == "Scegli almeno una categoria."


def test_unknown_ids_are_named(api, gc):
    e = error(post(api, body(gc, group_ids=[gc[0], 404])))
    assert e["field"] == "group_ids" and "404" in e["message"]
    e = error(post(api, body(gc, category_ids=[405])))
    assert e["field"] == "category_ids" and "405" in e["message"]


def test_repeated_ids_count_once_and_category_order_is_kept(api, gc):
    g, c = gc
    c2, c3 = api.category("Messa"), api.category("Festa")
    created = post(api, body(gc, group_ids=[g, g], category_ids=[c3, c, c3, c2])).json()
    assert created["group_ids"] == [g]
    assert created["category_ids"] == [c3, c, c2]


def test_archived_refused_on_new_events_but_kept_on_existing_ones(api, gc):
    g, c = gc
    created = post(api, body(gc)).json()
    api.patch(f"/api/groups/{g}", json={"archived": True})
    api.patch(f"/api/categories/{c}", json={"archived": True})

    e = error(post(api, body(gc)))
    assert [p["field"] for p in e["errors"]] == ["group_ids", "category_ids"]
    assert "archiviato" in e["message"]

    updated = api.put(f"/api/events/{created['id']}", json=body(gc, title="Rinominato"))
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Rinominato"

    # Another archived item, which the event did not have, is still refused.
    g2 = api.group("Vecchio")
    api.patch(f"/api/groups/{g2}", json={"archived": True})
    e = error(api.put(f"/api/events/{created['id']}", json=body(gc, group_ids=[g, g2])))
    assert "Vecchio" in e["message"]


def test_update_replaces_links_and_moves_updated_at(api, gc):
    g, c = gc
    g2, c2 = api.group("Coro"), api.category("Messa")
    created = post(api, body(gc)).json()
    updated = api.put(
        f"/api/events/{created['id']}", json=body(gc, group_ids=[g2], category_ids=[c2, c])
    ).json()
    assert updated["group_ids"] == [g2]
    assert updated["category_ids"] == [c2, c]
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] >= created["updated_at"]


def test_get_update_delete_unknown_event(api, gc):
    assert api.get("/api/events/999").status_code == 404
    assert api.put("/api/events/999", json=body(gc)).status_code == 404
    assert api.delete("/api/events/999").status_code == 404


def test_delete_event(api, gc):
    created = post(api, body(gc)).json()
    assert api.delete(f"/api/events/{created['id']}").status_code == 204
    assert api.get(f"/api/events/{created['id']}").status_code == 404
    assert api.get("/api/groups").json()[0]["event_count"] == 0


# --- test 6: range queries -------------------------------------------------------------


def titles_between(api, first, last):
    response = api.get("/api/events", params={"from": first, "to": last})
    assert response.status_code == 200, response.text
    return [e["title"] for e in response.json()]


def test_overlap_with_multi_day_events_and_inclusive_ends(api, gc):
    post(api, body(gc, title="prima", start_date="2026-09-30"))
    post(api, body(gc, title="a cavallo di from", start_date="2026-09-28", end_date="2026-10-01"))
    post(api, body(gc, title="primo giorno", start_date="2026-10-01"))
    post(api, body(gc, title="ultimo giorno", start_date="2026-10-31"))
    post(api, body(gc, title="a cavallo di to", start_date="2026-10-31", end_date="2026-11-02"))
    post(api, body(gc, title="dopo", start_date="2026-11-01"))
    post(api, body(gc, title="tutto il mese", start_date="2026-10-01", end_date="2026-10-31"))
    post(api, body(gc, title="lungo", start_date="2026-09-05", end_date="2026-10-05"))

    found = titles_between(api, "2026-10-01", "2026-10-31")
    assert set(found) == {
        "a cavallo di from",
        "primo giorno",
        "ultimo giorno",
        "a cavallo di to",
        "tutto il mese",
        "lungo",
    }
    assert titles_between(api, "2026-10-01", "2026-10-01") == [
        "lungo",
        "a cavallo di from",
        "primo giorno",
        "tutto il mese",
    ]
    assert titles_between(api, "2026-09-29", "2026-09-29") == ["lungo", "a cavallo di from"]


def test_range_must_be_in_order_and_complete(api):
    e = error(api.get("/api/events", params={"from": "2026-10-31", "to": "2026-10-01"}))
    assert e["field"] == "to"
    assert error(api.get("/api/events", params={"from": "2026-10-01"}))["field"] == "to"


# --- test 7: chronological order ---------------------------------------------------------


def ev(id, title, day=18, all_day=False, start=None, end=None):  # noqa: A002
    return SimpleNamespace(
        id=id,
        title=title,
        start_date=dt.date(2026, 10, day),
        all_day=all_day,
        start_time=start,
        end_time=end,
    )


def test_chronological_key_mixed_cases():
    events = [
        ev(1, "b", start="15:00", end="16:00"),
        ev(2, "a", start="15:00", end=None),
        ev(3, "Festa", all_day=True),
        ev(4, "a", start="15:00", end="16:00"),
        ev(5, "A", start="15:00", end="16:00"),
        ev(6, "presto", start="09:00", end="18:00"),
        ev(7, "il giorno prima", day=17, start="20:00"),
        ev(8, "a", start="15:00", end="15:30"),
    ]
    ordered = [e.id for e in sorted(events, key=chronological_key)]
    assert ordered == [7, 3, 6, 8, 4, 5, 1, 2]
    # Deterministic whatever the starting order.
    assert [e.id for e in sorted(reversed(events), key=chronological_key)] == ordered


def test_clip_from_moves_earlier_events_to_the_period_start():
    long = ev(1, "z ritiro", day=10, all_day=True)
    first = ev(2, "a", day=15, all_day=True)
    clip = dt.date(2026, 10, 15)
    assert [e.id for e in sorted([first, long], key=chronological_key)] == [1, 2]
    assert [e.id for e in sorted([long, first], key=lambda e: chronological_key(e, clip))] == [
        2,
        1,
    ]


def test_api_returns_events_in_chronological_order(api, gc):
    post(api, body(gc, title="sera", start_time="20:00"))
    post(api, body(gc, title="festa", all_day=True))
    post(api, body(gc, title="mattina", start_time="09:00"))
    assert titles_between(api, "2026-10-18", "2026-10-18") == ["festa", "mattina", "sera"]


# --- test 8: duplicate ---------------------------------------------------------------------


def test_duplicate_keeps_everything_and_shifts_the_end(api, gc):
    g, c = gc
    g2, c2 = api.group("Coro"), api.category("Messa")
    source = post(
        api,
        body(
            gc,
            title="Ritiro",
            start_date="2026-10-16",
            end_date="2026-10-18",
            start_time="18:00",
            end_time="16:00",
            place="Casa alpina",
            group_ids=[g2, g],
            category_ids=[c2, c],
        ),
    ).json()
    response = api.post(
        f"/api/events/{source['id']}/duplicate",
        json={"dates": ["2026-11-13", "2026-12-11", "2026-11-13"]},
    )
    assert response.status_code == 201
    ids = response.json()["ids"]
    assert len(ids) == 2
    copies = [api.get(f"/api/events/{i}").json() for i in ids]
    assert [(e["start_date"], e["end_date"]) for e in copies] == [
        ("2026-11-13", "2026-11-15"),
        ("2026-12-11", "2026-12-13"),
    ]
    for copy in copies:
        for field in ("title", "all_day", "start_time", "end_time", "place", "group_ids"):
            assert copy[field] == source[field]
        assert copy["category_ids"] == [c2, c]


def test_duplicate_limits(api, gc):
    source = post(api, body(gc)).json()["id"]
    days = [str(dt.date(2027, 1, 1) + dt.timedelta(days=i)) for i in range(101)]
    e = error(api.post(f"/api/events/{source}/duplicate", json={"dates": days}))
    assert e["field"] == "dates"
    assert (
        len(api.get("/api/events", params={"from": "2027-01-01", "to": "2027-12-31"}).json()) == 0
    )
    assert error(api.post(f"/api/events/{source}/duplicate", json={"dates": []}))["field"] == (
        "dates"
    )
    response = api.post(f"/api/events/{source}/duplicate", json={"dates": days[:100]})
    assert len(response.json()["ids"]) == 100
    assert api.post("/api/events/999/duplicate", json={"dates": days[:1]}).status_code == 404


# --- places ----------------------------------------------------------------------------------


def test_places_by_frequency_case_folded_with_a_query(api, gc):
    for place, n in [("Oratorio", 3), ("oratorio", 1), ("Chiesa parrocchiale", 2), ("Casa", 1)]:
        for _ in range(n):
            post(api, body(gc, place=place))
    post(api, body(gc, place=""))
    assert api.get("/api/places").json() == ["Oratorio", "Chiesa parrocchiale", "Casa"]
    assert api.get("/api/places", params={"q": "ORAT"}).json() == ["Oratorio"]
    # A prefix match comes before a more frequent match inside the name.
    for _ in range(5):
        post(api, body(gc, place="Sala oratorio"))
    assert api.get("/api/places", params={"q": "ora"}).json() == ["Oratorio", "Sala oratorio"]


def test_places_at_most_ten(api, gc):
    for i in range(12):
        post(api, body(gc, place=f"Sala {i:02d}"))
    assert len(api.get("/api/places").json()) == 10
