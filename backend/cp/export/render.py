# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""A :class:`Sheet` becomes HTML, then a WeasyPrint document, then PDF bytes (SPEC §8.3, §8.5).

WeasyPrint is heavy (~80 MB) and imported only when the first preview or
export needs it (SPEC §8.7).

Nothing here touches the network or reads a file outside ``assets/`` (SPEC §2.1):
every URL the document mentions -- the font, the logo, whatever a logo SVG
points to -- goes through :class:`SafeFetcher`, which serves ``data:`` and the
package's own assets and refuses everything else with a warning in the log.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import threading
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple
from urllib.parse import urlsplit
from urllib.request import url2pathname

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from ..config import APP_NAME
from .selection import Sheet

if TYPE_CHECKING:
    from weasyprint import Document

_log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
ASSETS_DIR = HERE / "assets"
TEMPLATES_DIR = HERE / "templates"

#: Body size of the complete calendar and of a group laid out over several pages.
MULTIPAGE_FONT_PT = 10.0

#: WeasyPrint shares fontconfig and Pango state between threads; one
#: composition at a time keeps a preview and an export from meeting inside it.
_compose_lock = threading.Lock()


class Layout(NamedTuple):
    columns: int
    #: The size of an event's title; every other text scales with it.
    font_pt: float
    #: As many pages as needed, numbered, instead of one sheet.
    multipage: bool = False

    def label(self) -> dict[str, Any]:
        return {"columns": self.columns, "font_pt": self.font_pt}


MULTIPAGE = Layout(columns=1, font_pt=MULTIPAGE_FONT_PT, multipage=True)


# --- HTML -------------------------------------------------------------------------


def _css_string(value: str) -> Markup:
    """``value`` as a CSS string literal, for the page footer.

    Markup, because autoescaping would turn its quotes into ``&#34;`` inside
    ``<style>``, where HTML entities mean nothing and the rule is dropped.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("<", "\\3C ")
    return Markup('"' + escaped.replace("\n", " ") + '"')


def _bar(colors: Sequence[str]) -> str:
    """The bar's background: one equal segment per colour, top to bottom."""
    if len(colors) == 1:
        return colors[0]
    step = 100 / len(colors)
    # Two stops per colour: WeasyPrint does not read the "color a% b%" shorthand.
    stops = ", ".join(
        f"{color} {i * step:.3f}%, {color} {(i + 1) * step:.3f}%" for i, color in enumerate(colors)
    )
    return f"linear-gradient(to bottom, {stops})"


@cache
def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["css_string"] = _css_string
    env.filters["bar"] = _bar
    return env


def logo_uri(sheet: Sheet) -> str | None:
    logo = sheet.letterhead.logo
    if logo is None:
        return None
    return f"data:{logo.mime};base64,{base64.b64encode(logo.data).decode('ascii')}"


def sheet_html(sheet: Sheet, layout: Layout) -> str:
    template = _environment().get_template("sheet.html.j2")
    return template.render(
        sheet=sheet,
        layout=layout,
        logo=logo_uri(sheet),
        generator=APP_NAME,
        css=(TEMPLATES_DIR / "sheet.css").read_text(encoding="utf-8"),
    )


# --- resources ----------------------------------------------------------------------


def _inside_assets(url: str) -> Path | None:
    parts = urlsplit(url)
    if parts.netloc not in ("", "localhost"):
        return None
    path = Path(url2pathname(parts.path)).resolve()
    return path if ASSETS_DIR in path.parents and path.is_file() else None


@cache
def _fetcher_class() -> type:
    from weasyprint.urls import URLFetcher, URLFetcherResponse, URLFetchingError

    class SafeFetcher(URLFetcher):
        """``data:`` and the package's assets; nothing else, ever (SPEC §2.1)."""

        def fetch(self, url: str, headers: Any = None) -> Any:
            scheme = url.split(":", 1)[0].lower()
            if scheme == "data":
                return super().fetch(url, headers)
            if scheme == "file" and (path := _inside_assets(url)) is not None:
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                return URLFetcherResponse(
                    url, path.read_bytes(), headers={"Content-Type": mime}, status=200
                )
            _log.warning("export: risorsa esterna bloccata: %s", url[:200])
            raise URLFetchingError(f"risorsa bloccata: {url[:200]}")

    return SafeFetcher


def safe_fetcher() -> Any:
    return _fetcher_class()()


# --- documents --------------------------------------------------------------------


def compose(sheet: Sheet, layout: Layout) -> Document:
    """Lay the sheet out; the result knows its pages and can become PDF."""
    from weasyprint import HTML

    html = HTML(
        string=sheet_html(sheet, layout),
        base_url=ASSETS_DIR.as_uri() + "/",
        url_fetcher=safe_fetcher(),
    )
    with _compose_lock:
        return html.render()


_warm = threading.Event()


def warm_up() -> None:
    """Import WeasyPrint and load the fonts once, so the first real preview is not the slow one.

    Called in the background when the Export screen opens: the import stays lazy
    (nothing is loaded before someone is about to export), but off the clock.
    """
    if _warm.is_set():
        return
    _warm.set()

    def work() -> None:
        try:
            from weasyprint import HTML

            css = (TEMPLATES_DIR / "sheet.css").read_text(encoding="utf-8")
            html = f"<style>{css}</style><p class='title'>Calendario</p>"
            document = HTML(
                string=html, base_url=ASSETS_DIR.as_uri() + "/", url_fetcher=safe_fetcher()
            )
            with _compose_lock:
                document.render()
        except Exception:
            _log.exception("export: preparazione di WeasyPrint non riuscita")

    threading.Thread(target=work, name="export-warm-up", daemon=True).start()


def pdf_bytes(documents: Sequence[Document], title: str) -> bytes:
    """One PDF with the pages of every document, in order (SPEC §8.5 metadata)."""
    pages = [page for document in documents for page in document.pages]
    merged = documents[0].copy(pages)
    merged.metadata.title = title
    merged.metadata.generator = APP_NAME
    with _compose_lock:
        return merged.write_pdf()
