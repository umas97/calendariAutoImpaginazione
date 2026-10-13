# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which events go on which sheet: test 12 of SPEC §15 (§5.1, §8.1)."""

from __future__ import annotations

import datetime as dt

import pytest

from cp.domain.palette import text_color
from cp.export.request import ExportRequest, check_request
from cp.export.selection import build_sheets, event_counts

TODAY = dt.date(2026, 10, 13)


def request(selections, mode="per_group", first="2026-10-01", last="2026-12-31", **extra):
    return check_request(
        ExportRequest.model_validate(
            {"period": {"from": first, "to": last}, "mode": mode, "selections": selections} | extra
        ),
        needs_output=False,
    )


@pytest.fixture
def parish(api):
    """Two groups, three categories, events that exercise the rule."""
    ids = {
        "cresimandi": api.group("Cresimandi"),
        "coro": api.group("Coro"),
        "catechesi": api.category("Catechesi", "#E63946"),
        "messa": api.category("Messa", "#E9C46A"),
        "festa": api.category("Festa", "#43AA8B"),
    }
    g, c = ids["cresimandi"], ids["coro"]
    cat, messa, festa = ids["catechesi"], ids["messa"], ids["festa"]
    ids["incontro"] = api.event(
        [g], [cat], title="Incontro", start_date="2026-10-17", notes="SEGRETO-1"
    )["id"]
    ids["messa_insieme"] = api.event(
        [g, c], [messa, cat], title="Messa insieme", start_date="2026-10-18", start_time="10:30"
    )["id"]
    ids["prove"] = api.event([c], [messa], title="Prove", start_date="2026-11-05")["id"]
    ids["festa_coro"] = api.event([c], [festa], title="Festa del coro", start_date="2026-12-20")[
        "id"
    ]
    ids["fuori"] = api.event([g], [cat], title="Fuori periodo", start_date="2027-02-01")["id"]
    # Began in September, still on in October: it sits under October.
    ids["campo"] = api.event(
        [g],
        [festa],
        title="Campo",
        start_date="2026-09-29",
        end_date="2026-10-02",
        all_day=True,
    )["id"]
    return ids


def rows(sheet):
    return [row for month in sheet.months for row in month.rows]


def test_rule_group_and_category(parish):
    p = parish
    sheets = build_sheets(
        request(
            [
                {"group_id": p["cresimandi"], "category_ids": [p["catechesi"], p["festa"]]},
                {"group_id": p["coro"], "category_ids": [p["messa"]]},
            ]
        ),
        today=TODAY,
    )
    cresimandi, coro = sheets
    assert [r.event_id for r in rows(cresimandi)] == [p["campo"], p["incontro"], p["messa_insieme"]]
    assert [r.event_id for r in rows(coro)] == [p["messa_insieme"], p["prove"]]
    assert coro.title == "Coro" and cresimandi.period == "ottobre – dicembre 2026"
    assert cresimandi.updated == "aggiornato al 13/10/2026"


def test_unselected_categories_leave_bars_and_legend(parish):
    p = parish
    (sheet,) = build_sheets(
        request([{"group_id": p["cresimandi"], "category_ids": [p["catechesi"]]}]), today=TODAY
    )
    messa_insieme = next(r for r in rows(sheet) if r.event_id == p["messa_insieme"])
    # Its main category (Messa) is not selected: Catechesi alone colours it.
    assert messa_insieme.colors == ("#E63946",)
    assert messa_insieme.day_color == text_color("#E63946")
    assert [s.name for s in sheet.legend] == ["Catechesi"]


def test_bar_segments_follow_the_events_order_and_legend_the_categories_order(parish):
    p = parish
    (sheet,) = build_sheets(
        request(
            [
                {
                    "group_id": p["cresimandi"],
                    "category_ids": [p["festa"], p["catechesi"], p["messa"]],
                }
            ]
        ),
        today=TODAY,
    )
    messa_insieme = next(r for r in rows(sheet) if r.event_id == p["messa_insieme"])
    assert messa_insieme.colors == ("#E9C46A", "#E63946")  # Messa first, as in the event
    assert messa_insieme.day_color == text_color("#E9C46A")
    assert [s.name for s in sheet.legend] == ["Catechesi", "Messa", "Festa"]


def test_months_and_events_begun_before_the_period(parish):
    p = parish
    (sheet,) = build_sheets(
        request([{"group_id": p["coro"], "category_ids": [p["messa"], p["festa"]]}]), today=TODAY
    )
    assert [m.heading for m in sheet.months] == ["OTTOBRE 2026", "NOVEMBRE 2026", "DICEMBRE 2026"]
    (cresimandi,) = build_sheets(
        request([{"group_id": p["cresimandi"], "category_ids": [p["festa"]]}]), today=TODAY
    )
    (campo,) = rows(cresimandi)
    assert cresimandi.months[0].heading == "OTTOBRE 2026"
    # The text keeps the real dates.
    assert (campo.weekday, campo.day, campo.time) == (
        "mar–ven",
        "29 set – 2 ott",
        "tutto il giorno",
    )


def test_combined_once_with_group_labels(parish):
    p = parish
    (sheet,) = build_sheets(
        request(
            [
                {"group_id": p["coro"], "category_ids": [p["messa"]]},
                {"group_id": p["cresimandi"], "category_ids": [p["catechesi"]]},
            ],
            mode="combined",
        ),
        today=TODAY,
    )
    assert sheet.title == "Calendario" and sheet.multipage
    assert sheet.groups_line == "Cresimandi, Coro"  # the groups' order, not the request's
    ids = [r.event_id for r in rows(sheet)]
    assert ids == [p["incontro"], p["messa_insieme"], p["prove"]]
    labels = {r.event_id: r.groups for r in rows(sheet)}
    assert labels[p["messa_insieme"]] == ("Cresimandi", "Coro")
    assert labels[p["incontro"]] == ("Cresimandi",)
    # Messa insieme: Messa (selected for Coro) and Catechesi (for Cresimandi), event order.
    messa_insieme = next(r for r in rows(sheet) if r.event_id == p["messa_insieme"])
    assert messa_insieme.colors == ("#E9C46A", "#E63946")


def test_group_without_events_gives_an_empty_sheet(parish, api):
    empty = api.group("Vuoto")
    sheets = build_sheets(request([{"group_id": empty, "category_ids": [parish["messa"]]}]))
    assert sheets[0].event_count == 0 and sheets[0].months == ()


def test_notes_never_reach_a_sheet(parish):
    p = parish
    for mode in ("per_group", "combined"):
        sheets = build_sheets(
            request([{"group_id": p["cresimandi"], "category_ids": [p["catechesi"]]}], mode=mode)
        )
        assert "SEGRETO" not in repr(sheets)
        assert not any(hasattr(row, "notes") for sheet in sheets for row in rows(sheet))


def test_counts(parish):
    p = parish
    counts = event_counts(
        request(
            [
                {"group_id": p["cresimandi"], "category_ids": [p["catechesi"], p["festa"]]},
                {"group_id": p["coro"], "category_ids": [p["messa"], p["festa"]]},
            ]
        )
    )
    assert counts == {"groups": {p["cresimandi"]: 3, p["coro"]: 3}, "combined": 5}


def test_selection_errors(parish, api):
    p = parish
    from cp.domain.errors import Invalid

    with pytest.raises(Invalid, match="Gruppo inesistente: 999"):
        build_sheets(request([{"group_id": 999, "category_ids": [p["messa"]]}]))
    with pytest.raises(Invalid, match="Categoria inesistente: 999"):
        build_sheets(request([{"group_id": p["coro"], "category_ids": [999]}]))
    with pytest.raises(Invalid, match="almeno una categoria per “Coro”"):
        build_sheets(request([{"group_id": p["coro"], "category_ids": []}]))


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"period": {"from": "2026-10-02", "to": "2026-10-01"}}, "period.to"),
        ({"period": {"from": "2026-01-01", "to": "2027-02-05"}}, "period.to"),
        ({"formats": []}, "formats"),
        ({"selections": []}, "selections"),
    ],
)
def test_request_rules(body, field):
    from cp.domain.errors import InvalidFields

    base = {
        "period": {"from": "2026-10-01", "to": "2026-10-31"},
        "selections": [{"group_id": 1, "category_ids": [1]}],
        "output_dir": "/tmp/x",
    }
    with pytest.raises(InvalidFields) as info:
        check_request(ExportRequest.model_validate(base | body), needs_output=True)
    assert info.value.field == field


def test_request_period_of_400_days_is_fine_and_duplicates_collapse():
    clean = check_request(
        ExportRequest.model_validate(
            {
                "period": {"from": "2026-01-01", "to": "2027-02-04"},
                "formats": ["pdf", "pdf", "png"],
                "selections": [
                    {"group_id": 1, "category_ids": [2, 2, 3]},
                    {"group_id": 1, "category_ids": [4]},
                ],
            }
        ),
        needs_output=False,
    )
    assert clean.formats == ["pdf", "png"]
    assert [(s.group_id, s.category_ids) for s in clean.selections] == [(1, [2, 3])]
