# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""PDF pages to PNG images with pypdfium2 (SPEC §8.5; test 16).

The images are opaque, on white: a transparent PNG turns black in WhatsApp.
"""

from __future__ import annotations

import io

import pypdfium2 as pdfium

#: Points per inch, the PDF unit.
POINTS = 72


def page_count(pdf: bytes) -> int:
    document = pdfium.PdfDocument(pdf)
    try:
        return len(document)
    finally:
        document.close()


def png_pages(pdf: bytes, dpi: int, *, compress_level: int = 6) -> list[bytes]:
    """Every page of ``pdf`` as a PNG at ``dpi`` (A4 at 200 dpi is 1654 × 2339 px)."""
    document = pdfium.PdfDocument(pdf)
    images = []
    try:
        for page in document:
            bitmap = page.render(scale=dpi / POINTS, fill_color=(255, 255, 255, 255))
            image = bitmap.to_pil().convert("RGB")
            out = io.BytesIO()
            image.save(out, format="PNG", compress_level=compress_level, dpi=(dpi, dpi))
            images.append(out.getvalue())
            page.close()
    finally:
        document.close()
    return images
