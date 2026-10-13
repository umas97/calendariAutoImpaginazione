# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The preview: the very PDF of the export, as small images kept in memory (SPEC §5.1, §8.7).

Each preview gets a new generation number. A newer request makes the older
one stop at its next composition, and throws its images away; images also go
five minutes after the preview began. Nothing is written to disk (SPEC §10.5).
"""

from __future__ import annotations

import threading
from typing import Any

from ..domain.errors import Conflict, NotFound
from .autofit import fit_sheet, layouts
from .raster import png_pages
from .render import MULTIPAGE, Layout, compose, pdf_bytes
from .request import ExportRequest, check_request
from .selection import Sheet, build_sheets

PREVIEW_DPI = 110
#: Seconds a preview's images stay available.
LIFETIME = 300.0


class Superseded(Conflict):
    code = "superseded"


class PreviewStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        #: One preview composes at a time; a newer one waits for the older to give up.
        self._work = threading.Lock()
        self.generation = 0
        self._images: dict[int, bytes] = {}

    def begin(self) -> int:
        with self._lock:
            self.generation += 1
            self._images = {}
            timer = threading.Timer(LIFETIME, self._expire, args=(self.generation,))
            timer.daemon = True
            timer.start()
            return self.generation

    def _expire(self, generation: int) -> None:
        with self._lock:
            if generation == self.generation:
                self._images = {}

    def check(self, generation: int) -> None:
        if generation != self.generation:
            raise Superseded("Anteprima sostituita da una più recente.")

    def add(self, generation: int, image: bytes) -> int:
        with self._lock:
            self.check(generation)
            index = len(self._images)
            self._images[index] = image
            return index

    def image(self, generation: int, index: int) -> bytes:
        with self._lock:
            if generation != self.generation or index not in self._images:
                raise NotFound("Anteprima scaduta: aggiornala.")
            return self._images[index]

    def preview(self, request: ExportRequest) -> dict[str, Any]:
        request = check_request(request, needs_output=False)
        generation = self.begin()
        sheets = build_sheets(request)
        with self._work:
            self.check(generation)

            def composer(sheet: Sheet, layout: Layout) -> Any:
                self.check(generation)
                return compose(sheet, layout)

            items = [self._sheet(generation, sheet, composer) for sheet in sheets]
        return {"generation": generation, "sheets": items}

    def _sheet(self, generation: int, sheet: Sheet, composer: Any) -> dict[str, Any]:
        item: dict[str, Any] = {
            "group_id": sheet.group_id,
            "title": sheet.title,
            "event_count": sheet.event_count,
            "layout": None,
            "fits": True,
            "pages": [],
        }
        if sheet.event_count == 0:
            return item
        if sheet.multipage:
            document, layout = composer(sheet, MULTIPAGE), MULTIPAGE
        else:
            fitted = fit_sheet(sheet, composer, layouts)
            if fitted is None:
                item["fits"] = False
                return item
            document, layout = fitted.document, fitted.layout
        item["layout"] = layout.label() | {"multipage": layout.multipage}
        pdf = pdf_bytes([document], sheet.title)
        for image in png_pages(pdf, PREVIEW_DPI, compress_level=1):
            index = self.add(generation, image)
            item["pages"].append(f"/api/export/preview/{generation}/{index}.png")
        return item


store = PreviewStore()
