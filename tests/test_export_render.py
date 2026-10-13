# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fitting, PDF and PNG: tests 14-16 of SPEC §15 (§8.4, §8.5).

These compose real documents with WeasyPrint, on synthetic events of
realistic length (``cp.export.samples``): about a second each.
"""

from __future__ import annotations

import ctypes
import datetime as dt
import io
from types import SimpleNamespace

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import pytest
from PIL import Image

from cp.db.session import session_scope
from cp.export import samples
from cp.export.autofit import PHASES, LayoutMemory, fit_sheet
from cp.export.raster import page_count, png_pages
from cp.export.render import MULTIPAGE, Layout, compose, pdf_bytes
from cp.export.request import ExportRequest, check_request
from cp.export.selection import build_sheets

FIRST, LAST = dt.date(2026, 9, 1), dt.date(2027, 6, 30)


def sheet_with(count: int, mode: str = "per_group"):
    """A sheet of ``count`` events over a pastoral year, all categories selected."""
    with session_scope() as session:
        groups, categories = samples.seed_taxonomy(session)
        samples.add_events(
            session, samples.sample_events(count, FIRST, LAST, [groups[0]], categories)
        )
    request = ExportRequest.model_validate(
        {
            "period": {"from": FIRST, "to": LAST},
            "mode": mode,
            "selections": [{"group_id": groups[0], "category_ids": categories}],
        }
    )
    (sheet,) = build_sheets(check_request(request, needs_output=False))
    assert sheet.event_count == count
    return sheet


def one_page(fitted) -> bytes:
    pdf = pdf_bytes([fitted.document], "x")
    assert page_count(pdf) == 1
    return pdf


def text_of(pdf: bytes) -> str:
    document = pdfium.PdfDocument(pdf)
    return "\n".join(page.get_textpage().get_text_range() for page in document)


def font_names(pdf: bytes) -> set[tuple[str, bool]]:
    names = set()
    for page in pdfium.PdfDocument(pdf):
        for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_TEXT]):
            font = pdfium_c.FPDFTextObj_GetFont(obj.raw)
            size = pdfium_c.FPDFFont_GetBaseFontName(font, None, 0)
            buffer = ctypes.create_string_buffer(size)
            pdfium_c.FPDFFont_GetBaseFontName(font, buffer, size)
            embedded = bool(pdfium_c.FPDFFont_GetIsEmbedded(font))
            names.add((buffer.value.decode().split("+")[-1], embedded))
    return names


# --- test 14: fitting -------------------------------------------------------------


def test_phases_are_the_specs():
    assert PHASES == (
        (1, (11.0, 10.5, 10.0, 9.5, 9.0, 8.5)),
        (2, (9.5, 9.0, 8.5, 8.0, 7.5)),
    )


@pytest.mark.parametrize("limit", [0, 1, 4, 6, 7, 11, 12])
def test_binary_search_finds_the_most_readable_layout(limit):
    """A fake composer: layouts 0..10 in order, the first ``limit`` overflow."""
    order = [(c, s) for c, sizes in PHASES for s in sizes]
    calls = []

    def composer(_sheet, layout: Layout):
        calls.append(layout)
        overflow = order.index((layout.columns, layout.font_pt)) < limit
        return SimpleNamespace(pages=[1, 2] if overflow else [1])

    fitted = fit_sheet(None, composer)  # type: ignore[arg-type]
    if limit >= len(order):
        assert fitted is None
    else:
        assert (fitted.layout.columns, fitted.layout.font_pt) == order[limit]
    assert len(calls) <= 7


def test_layout_memory_spares_the_search():
    """What the preview found, the export reuses: one composition, none for a misfit."""
    memory = LayoutMemory()
    calls = []

    def composer(sheet, layout: Layout):
        calls.append(layout)
        return SimpleNamespace(pages=[1] if layout.columns == 2 or sheet == "small" else [1, 2])

    first = fit_sheet("big", composer, memory)  # type: ignore[arg-type]
    searched = len(calls)
    again = fit_sheet("big", composer, memory)  # type: ignore[arg-type]
    assert again.layout == first.layout and again.attempts == 1
    assert len(calls) == searched + 1

    def overflowing(_sheet, layout):
        calls.append(layout)
        return SimpleNamespace(pages=[1, 2])

    assert fit_sheet("huge", overflowing, memory) is None  # type: ignore[arg-type]
    before = len(calls)
    assert fit_sheet("huge", overflowing, memory) is None  # type: ignore[arg-type]
    assert len(calls) == before


def test_one_event_fits_at_the_largest_size(api):
    fitted = fit_sheet(sheet_with(1))
    assert fitted.layout == Layout(1, 11.0)
    one_page(fitted)


def test_thirty_events_fit_one_column_at_9pt_or_more(api):
    fitted = fit_sheet(sheet_with(30))
    assert fitted.layout.columns == 1 and fitted.layout.font_pt >= 9
    one_page(fitted)


def test_eighty_events_fit_two_columns_at_7_5pt_or_more(api):
    fitted = fit_sheet(sheet_with(80))
    assert fitted is not None and fitted.layout.font_pt >= 7.5
    one_page(fitted)


def test_two_hundred_events_do_not_fit(api):
    assert fit_sheet(sheet_with(200)) is None


# --- test 15: the PDF ------------------------------------------------------------


def test_pdf_is_a4_with_inter_embedded_and_real_text(api):
    sheet = sheet_with(12)
    pdf = pdf_bytes([fit_sheet(sheet).document], sheet.title)
    document = pdfium.PdfDocument(pdf)
    width, height = document[0].get_size()
    assert abs(width - 595) <= 1 and abs(height - 842) <= 1
    assert document.get_metadata_dict()["Title"] == sheet.title
    assert document.get_metadata_dict()["Creator"] == "calendariAutoImpaginazione"
    fonts = font_names(pdf)
    assert fonts and all(name.startswith("Inter") and embedded for name, embedded in fonts)
    text = text_of(pdf)
    row = sheet.months[0].rows[0]
    assert row.title in text and row.place in text and row.time in text
    assert sheet.period in text and "aggiornato al" in text


def test_long_titles_stop_at_two_lines(api):
    with session_scope() as session:
        groups, categories = samples.seed_taxonomy(session)
        long_title = " ".join(["Pellegrinaggio"] * 8)  # 119 characters
        samples.add_events(
            session,
            [
                item.model_copy(update={"title": long_title})
                for item in samples.sample_events(1, FIRST, LAST, [groups[0]], categories)
            ],
        )
    request = ExportRequest.model_validate(
        {
            "period": {"from": FIRST, "to": LAST},
            "selections": [{"group_id": groups[0], "category_ids": categories}],
        }
    )
    (sheet,) = build_sheets(request)
    document = compose(sheet, Layout(2, 7.5))
    text = text_of(pdf_bytes([document], "x"))
    assert "…" in text
    assert text.count("Pellegrinaggio") < 8


# --- test 16: PNG ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dpi", "size"), [(150, (1240, 1754)), (200, (1654, 2339)), (300, (2480, 3508))]
)
def test_png_sizes_and_opaque(api, dpi, size):
    pdf = one_page(fit_sheet(sheet_with(3)))
    (png,) = png_pages(pdf, dpi)
    image = Image.open(io.BytesIO(png))
    assert abs(image.width - size[0]) <= 1 and abs(image.height - size[1]) <= 1
    assert image.mode == "RGB"
    assert image.getpixel((5, 5)) == (255, 255, 255)


def test_multipage_gives_one_png_per_page(api):
    sheet = sheet_with(120, mode="combined")
    pdf = pdf_bytes([compose(sheet, MULTIPAGE)], sheet.title)
    pages = page_count(pdf)
    assert pages >= 2
    assert len(png_pages(pdf, 150)) == pages
    text = text_of(pdf)
    assert f"pagina 1 di {pages}" in text and f"pagina {pages} di {pages}" in text
