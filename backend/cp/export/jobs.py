# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exports run in a thread, one at a time, with a state the interface can ask for (SPEC §8.7).

:func:`run_export` does the work and can be called directly (the sample
command does); :class:`ExportRunner` runs it in the background. A failure on
one group never stops the others: it is logged and listed among the skipped.
Closing the program lets a running export finish (30 s at most), then asks it
to stop between two sheets, so no file is ever left half-written.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ..domain.errors import Conflict, NotFound
from ..folders import inside_home
from . import output
from .autofit import fit_sheet
from .raster import png_pages
from .render import MULTIPAGE, Layout, compose, pdf_bytes
from .request import ExportRequest, check_request
from .selection import Sheet, build_sheets

_log = logging.getLogger(__name__)

BUSY = "C'è già un export in corso."
EMPTY = "saltato: nessun evento"
FAILED = "errore imprevisto: il dettaglio è nel log."
SINGLE_PDF_TITLE = "Calendari per gruppo"


def too_big(count: int) -> str:
    return f"{count} eventi non entrano in un foglio A4. Riduci il periodo o le categorie."


Status = Literal["running", "done", "failed", "cancelled"]


@dataclass
class Job:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: Status = "running"
    #: Sheets, empty ones included: the progress bar counts them all.
    total: int = 0
    done: int = 0
    #: The new ``Export …`` folder, once created.
    folder: Path | None = None
    files: list[str] = field(default_factory=list)
    #: ``{group_id, group, reason, message, events}``; reason: empty, too_big, error.
    skipped: list[dict[str, Any]] = field(default_factory=list)
    #: Why the whole export failed (status ``failed``).
    message: str | None = None

    def skip(self, sheet: Sheet, reason: str, message: str) -> None:
        self.skipped.append(
            {
                "group_id": sheet.group_id,
                "group": sheet.title,
                "reason": reason,
                "message": message,
                "events": sheet.event_count,
            }
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "total": self.total,
            "done": self.done,
            "folder": str(self.folder) if self.folder else None,
            "files": list(self.files),
            "skipped": list(self.skipped),
            "message": self.message,
        }


@dataclass(frozen=True)
class Prepared:
    """A request checked against the rules and the database, ready to run."""

    request: ExportRequest
    sheets: list[Sheet]
    base: Path


def prepare(request: ExportRequest) -> Prepared:
    """Everything that can be refused before starting: 422, 403 (output outside the home)."""
    request = check_request(request, needs_output=True)
    base = inside_home(request.output_dir or "")
    return Prepared(request, build_sheets(request), base)


def lay_out(sheet: Sheet) -> tuple[Any, Layout] | None:
    """The sheet's document and layout; ``None`` if it does not fit one page."""
    if sheet.multipage:
        return compose(sheet, MULTIPAGE), MULTIPAGE
    fitted = fit_sheet(sheet)
    if fitted is None:
        return None
    _log.info(
        "export: %s, %d eventi: %d colonne a %s pt (%d composizioni)",
        sheet.title,
        sheet.event_count,
        fitted.layout.columns,
        fitted.layout.font_pt,
        fitted.attempts,
    )
    return fitted.document, fitted.layout


def _write(job: Job, name: str, data: bytes) -> None:
    assert job.folder is not None
    job.files.append(output.write_new(job.folder, name, data).name)


def _pngs(job: Job, pdf: bytes, dpi: int, name_for: Any, numbered: bool) -> None:
    for number, image in enumerate(png_pages(pdf, dpi), start=1):
        _write(job, name_for(number if numbered else 0), image)


def _run(job: Job, prepared: Prepared, cancel: threading.Event) -> None:
    request = prepared.request
    first, last = request.period.first, request.period.last
    pdfs, pngs = "pdf" in request.formats, "png" in request.formats
    job.folder = output.export_folder(prepared.base, dt.datetime.now())
    collected: list[Any] = []
    for sheet in prepared.sheets:
        if cancel.is_set():
            job.status = "cancelled"
            return
        try:
            if sheet.event_count == 0:
                job.skip(sheet, "empty", EMPTY)
                continue
            if request.mode == "combined":
                pdf = pdf_bytes([compose(sheet, MULTIPAGE)], sheet.title)
                if pdfs:
                    _write(job, output.combined_file(first, last, "pdf"), pdf)
                if pngs:
                    names = lambda n: output.combined_file(first, last, "png", n)  # noqa: E731
                    _pngs(job, pdf, request.dpi, names, True)
                continue
            laid = lay_out(sheet)
            if laid is None:
                job.skip(sheet, "too_big", too_big(sheet.event_count))
                continue
            document, _layout = laid
            pdf = pdf_bytes([document], sheet.title)
            if request.mode == "single_pdf":
                collected.append(document)
            elif pdfs:
                _write(job, output.group_file(sheet.title, first, last, "pdf"), pdf)
            if pngs:
                name = sheet.title
                _pngs(
                    job,
                    pdf,
                    request.dpi,
                    lambda n, name=name: output.group_file(name, first, last, "png", n),
                    sheet.multipage,
                )
        except Exception:
            _log.exception("export: errore sul foglio %s", sheet.title)
            job.skip(sheet, "error", FAILED)
        finally:
            job.done += 1
    if collected and pdfs:
        _write(job, output.single_pdf_file(first, last), pdf_bytes(collected, SINGLE_PDF_TITLE))
    job.status = "done"


def run_export(
    request: ExportRequest | Prepared,
    job: Job | None = None,
    cancel: threading.Event | None = None,
) -> Job:
    """Run an export to the end, here and now; the job says what came of it."""
    prepared = request if isinstance(request, Prepared) else prepare(request)
    job = job or Job()
    job.total = len(prepared.sheets)
    try:
        _run(job, prepared, cancel or threading.Event())
    except Exception:
        _log.exception("export non riuscito")
        job.status = "failed"
        job.message = "L'export non è riuscito: il dettaglio è nel log."
    return job


class ExportRunner:
    """One export at a time, in a thread; the last job stays readable."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._job: Job | None = None
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()

    def busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, request: ExportRequest) -> Job:
        with self._lock:
            if self.busy():
                raise Conflict(BUSY)
            prepared = prepare(request)
            job = Job(total=len(prepared.sheets))
            self._job, self._cancel = job, threading.Event()
            self._thread = threading.Thread(
                target=run_export, args=(prepared, job, self._cancel), name="export", daemon=True
            )
            self._thread.start()
            return job

    def get(self, job_id: str) -> Job:
        if self._job is None or self._job.id != job_id:
            raise NotFound(f"Export inesistente: {job_id}.")
        return self._job

    def shutdown(self, timeout: float = 30.0, grace: float = 10.0) -> None:
        """Let a running export finish; past ``timeout`` ask it to stop after the current sheet."""
        thread = self._thread
        if thread is None or not thread.is_alive():
            return
        _log.info("chiusura: attendo la fine dell'export in corso")
        thread.join(timeout)
        if thread.is_alive():
            self._cancel.set()
            thread.join(grace)


runner = ExportRunner()
