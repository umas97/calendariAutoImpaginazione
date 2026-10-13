# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The three modes, the job, the API and the network ban: tests 17 and 19 of SPEC §15."""

from __future__ import annotations

import datetime as dt
import io
import logging
import socket
import threading
import time
import urllib.request
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import pytest
from PIL import Image

from cp.db.session import session_scope
from cp.domain import parish
from cp.export import jobs, samples
from cp.export.request import ExportRequest

FIRST, LAST = dt.date(2026, 10, 1), dt.date(2026, 12, 31)
SPAN = "2026-10-01_2026-12-31"


@pytest.fixture
def data(api):
    """Three groups: 4 and 6 events, and one with none."""
    with session_scope() as session:
        groups, categories = samples.seed_taxonomy(session)
        for group, count in ((groups[0], 4), (groups[1], 6)):
            samples.add_events(
                session, samples.sample_events(count, FIRST, LAST, [group], categories, seed=count)
            )
    return groups[:3], categories


def export(data, xdg_home, mode="per_group", formats=("pdf",), **extra):
    groups, categories = data
    body = {
        "period": {"from": FIRST, "to": LAST},
        "mode": mode,
        "formats": list(formats),
        "dpi": 150,
        "selections": [{"group_id": g, "category_ids": categories} for g in groups],
        "output_dir": str(xdg_home / "Documenti" / "Calendari parrocchia"),
    } | extra
    return jobs.run_export(ExportRequest.model_validate(body))


def pages(path: Path) -> int:
    return len(pdfium.PdfDocument(path))


def text(path: Path) -> str:
    return "\n".join(p.get_textpage().get_text_range() for p in pdfium.PdfDocument(path))


# --- test 17: modes ----------------------------------------------------------------


def test_per_group_one_file_per_group_and_the_empty_one_skipped(data, xdg_home):
    job = export(data, xdg_home, formats=("pdf", "png"))
    assert job.status == "done" and (job.done, job.total) == (3, 3)
    assert job.folder.parent == xdg_home / "Documenti" / "Calendari parrocchia"
    assert job.folder.name.startswith("Export ")
    assert sorted(job.files) == sorted(
        [
            f"Cresimandi {SPAN}.pdf",
            f"Cresimandi {SPAN}.png",
            f"5ª elementare {SPAN}.pdf",
            f"5ª elementare {SPAN}.png",
        ]
    )
    for name in job.files:
        if name.endswith(".pdf"):
            assert pages(job.folder / name) == 1
    assert job.skipped == [
        {
            "group_id": data[0][2],
            "group": "Giovanissimi",
            "reason": "empty",
            "message": "saltato: nessun evento",
            "events": 0,
        }
    ]


def test_single_pdf_one_page_per_group(data, xdg_home):
    job = export(data, xdg_home, mode="single_pdf", formats=("pdf", "png"))
    assert f"Calendari per gruppo {SPAN}.pdf" in job.files
    assert f"Cresimandi {SPAN}.png" in job.files and f"5ª elementare {SPAN}.png" in job.files
    merged = job.folder / f"Calendari per gruppo {SPAN}.pdf"
    assert pages(merged) == 2
    first, second = (p.get_textpage().get_text_range() for p in pdfium.PdfDocument(merged))
    assert "Cresimandi" in first and "5ª elementare" in second
    assert pdfium.PdfDocument(merged).get_metadata_dict()["Title"] == "Calendari per gruppo"


def test_combined_on_several_pages(api, xdg_home):
    with session_scope() as session:
        groups, categories = samples.seed_taxonomy(session)
        samples.add_events(session, samples.sample_events(90, FIRST, LAST, groups[:2], categories))
    job = export((groups[:2], categories), xdg_home, mode="combined", formats=("pdf", "png"))
    pdf = job.folder / f"Calendario completo {SPAN}.pdf"
    count = pages(pdf)
    assert count >= 2
    assert f"pagina 1 di {count}" in text(pdf)
    pngs = sorted(n for n in job.files if n.endswith(".png"))
    assert pngs == [f"Calendario completo {SPAN} p{n}.png" for n in range(1, count + 1)]


def test_too_big_is_skipped_and_can_go_on_several_pages(api, xdg_home):
    with session_scope() as session:
        groups, categories = samples.seed_taxonomy(session)
        samples.add_events(
            session,
            samples.sample_events(
                200, dt.date(2026, 9, 1), dt.date(2027, 6, 30), [groups[0]], categories
            ),
        )
    body = {"period": {"from": "2026-09-01", "to": "2027-06-30"}}
    job = export(([groups[0]], categories), xdg_home, **body)
    assert job.files == []
    (skipped,) = job.skipped
    assert skipped["reason"] == "too_big"
    assert skipped["message"] == (
        "200 eventi non entrano in un foglio A4. Riduci il periodo o le categorie."
    )
    job = export(
        ([groups[0]], categories), xdg_home, formats=("pdf", "png"), multipage=[groups[0]], **body
    )
    assert job.skipped == []
    pdf = job.folder / "Cresimandi 2026-09-01_2027-06-30.pdf"
    assert pages(pdf) >= 2
    assert "Cresimandi 2026-09-01_2027-06-30 p2.png" in job.files


def test_an_error_on_one_group_does_not_stop_the_others(data, xdg_home, monkeypatch, caplog):
    real = jobs.lay_out

    def flaky(sheet):
        if sheet.title == "Cresimandi":
            raise RuntimeError("guasto")
        return real(sheet)

    monkeypatch.setattr(jobs, "lay_out", flaky)
    job = export(data, xdg_home)
    assert job.status == "done"
    assert job.files == [f"5ª elementare {SPAN}.pdf"]
    assert job.skipped[0]["reason"] == "error"
    assert "guasto" in caplog.text


def test_a_second_export_never_overwrites(data, xdg_home):
    first = export(data, xdg_home)
    second = export(data, xdg_home)
    assert first.folder != second.folder
    assert second.folder.name.endswith("(2)")


# --- the API ----------------------------------------------------------------------------


def body_for(data, xdg_home, **extra):
    groups, categories = data
    return {
        "period": {"from": FIRST.isoformat(), "to": LAST.isoformat()},
        "selections": [{"group_id": g, "category_ids": categories} for g in groups],
        "output_dir": str(xdg_home / "out"),
    } | extra


def wait_job(api, job_id):
    for _ in range(300):
        state = api.get(f"/api/export/jobs/{job_id}").json()
        if state["status"] != "running":
            return state
        time.sleep(0.05)
    raise AssertionError("export non finito")


def test_api_export_job(api, data, xdg_home):
    response = api.post("/api/export", json=body_for(data, xdg_home))
    assert response.status_code == 202, response.text
    state = wait_job(api, response.json()["id"])
    assert state["status"] == "done" and state["done"] == state["total"] == 3
    assert len(state["files"]) == 2 and state["skipped"][0]["reason"] == "empty"
    assert api.get("/api/export/jobs/nessuno").status_code == 404


def test_api_one_export_at_a_time(api, data, xdg_home, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(jobs, "_run", lambda job, prepared, cancel: gate.wait(5))
    first = api.post("/api/export", json=body_for(data, xdg_home))
    assert first.status_code == 202
    second = api.post("/api/export", json=body_for(data, xdg_home))
    assert second.status_code == 409
    assert second.json()["error"]["message"] == "C'è già un export in corso."
    gate.set()
    jobs.runner.shutdown(5)


def test_api_refuses_folders_outside_home(api, data, xdg_home):
    response = api.post("/api/export", json=body_for(data, xdg_home, output_dir="/tmp"))
    assert response.status_code == 403
    response = api.post(
        "/api/export", json=body_for(data, xdg_home, output_dir=str(xdg_home / ".." / ".."))
    )
    assert response.status_code == 403


def test_api_validation_in_italian(api, data, xdg_home):
    response = api.post("/api/export", json=body_for(data, xdg_home, formats=[]))
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Scegli almeno un formato: PDF o PNG."


def test_api_counts_and_options(api, data):
    groups, categories = data
    response = api.post(
        "/api/export/counts",
        json={
            "period": {"from": FIRST.isoformat(), "to": LAST.isoformat()},
            "selections": [{"group_id": g, "category_ids": categories} for g in groups],
        },
    )
    assert response.json() == {
        "groups": {str(groups[0]): 4, str(groups[1]): 6, str(groups[2]): 0},
        "combined": 10,
    }
    options = api.get("/api/export/options").json()
    assert set(options["shortcuts"]) == {
        "this_month",
        "next_month",
        "next_3_months",
        "pastoral_year",
    }
    assert options["default_dir"].endswith("Documenti/Calendari parrocchia")
    assert options["default_dir"].startswith(options["home"])


def test_api_counts_for_unticked_groups_and_no_categories(api, data):
    groups, categories = data
    response = api.post(
        "/api/export/counts",
        json={
            "period": {"from": FIRST.isoformat(), "to": LAST.isoformat()},
            "selections": [
                {"group_id": groups[0], "category_ids": categories},
                {"group_id": groups[1], "category_ids": categories},
                {"group_id": groups[2], "category_ids": []},
            ],
            "included": [groups[0]],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "groups": {str(groups[0]): 4, str(groups[1]): 6, str(groups[2]): 0},
        "combined": 4,
    }
    nothing = api.post(
        "/api/export/counts",
        json={
            "period": {"from": FIRST.isoformat(), "to": LAST.isoformat()},
            "selections": [{"group_id": groups[0], "category_ids": []}],
        },
    )
    assert nothing.json() == {"groups": {str(groups[0]): 0}, "combined": 0}


def test_api_preview(api, data):
    groups, categories = data
    preview = {
        "period": {"from": FIRST.isoformat(), "to": LAST.isoformat()},
        "selections": [{"group_id": g, "category_ids": categories} for g in groups],
    }
    response = api.post("/api/export/preview", json=preview)
    assert response.status_code == 200, response.text
    sheets = response.json()["sheets"]
    assert [s["event_count"] for s in sheets] == [4, 6, 0]
    assert sheets[0]["layout"] == {"columns": 1, "font_pt": 11.0, "multipage": False}
    assert sheets[2]["pages"] == []
    image = api.get(sheets[0]["pages"][0])
    assert image.headers["content-type"] == "image/png"
    width, _height = Image.open(io.BytesIO(image.content)).size
    assert abs(width - 909) <= 1  # A4 at 110 dpi
    # A new preview throws the old images away.
    api.post("/api/export/preview", json=preview)
    assert api.get(sheets[0]["pages"][0]).status_code == 404


# --- test 19: no network ---------------------------------------------------------------


EVIL_SVG = b"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="100" height="40" viewBox="0 0 100 40">
  <style>@import url("https://example.com/style.css");</style>
  <rect width="100" height="40" fill="#277DA1"/>
  <image href="https://example.com/remote.png" width="10" height="10"/>
  <image xlink:href="file:///etc/passwd" width="10" height="10"/>
</svg>"""


def test_no_network_and_no_files_outside_the_assets(data, xdg_home, monkeypatch, caplog):
    with session_scope() as session:
        parish.save_logo(session, EVIL_SVG)
        parish.set_name(session, "Parrocchia di prova")

    def no_connect(*_args, **_kwargs):
        raise AssertionError("tentativo di connessione di rete")

    def no_file(*_args, **_kwargs):
        raise AssertionError("lettura di un file fuori dalle risorse")

    monkeypatch.setattr(socket.socket, "connect", no_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", no_connect)
    monkeypatch.setattr(urllib.request.FileHandler, "file_open", no_file)
    monkeypatch.setattr(urllib.request.HTTPHandler, "http_open", no_connect)
    monkeypatch.setattr(urllib.request.HTTPSHandler, "https_open", no_connect)
    with caplog.at_level(logging.WARNING, logger="cp.export.render"):
        for mode in ("per_group", "combined"):
            job = export(data, xdg_home, mode=mode, formats=("pdf", "png"))
            assert job.status == "done" and job.files
            assert all(s["reason"] == "empty" for s in job.skipped)
    blocked = caplog.text
    assert "https://example.com/remote.png" in blocked
    assert "file:///etc/passwd" in blocked


def test_logo_is_in_the_pdf(data, xdg_home):
    image = Image.new("RGB", (1200, 400), (39, 125, 161))
    raw = io.BytesIO()
    image.save(raw, format="PNG")
    with session_scope() as session:
        parish.save_logo(session, raw.getvalue())
    job = export(data, xdg_home)
    document = pdfium.PdfDocument(job.folder / f"Cresimandi {SPAN}.pdf")

    images = list(document[0].get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE]))
    assert len(images) == 1
