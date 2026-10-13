# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every API error in one shape: ``{"error": {"code", "message", "field"?}}`` (SPEC §12).

The message is Italian and meant for a person; the technical detail of an
unexpected failure goes to the log, never to a dialog.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ..domain.errors import DomainError, error_body

_log = logging.getLogger(__name__)

_HTTP_MESSAGES = {
    404: "Risorsa inesistente.",
    405: "Operazione non consentita.",
}


def _field(loc: tuple[Any, ...]) -> str | None:
    names = [str(part) for part in loc if part not in ("body", "query", "path")]
    return names[0] if names else None


def _message(error: dict[str, Any]) -> str:
    kind = str(error.get("type", ""))
    if kind == "missing":
        return "Campo obbligatorio."
    if kind.startswith("date"):
        return "Data non valida: usa il formato AAAA-MM-GG."
    return "Valore non valido."


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=exc.body())

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": _field(tuple(e.get("loc", ()))), "message": _message(e)} for e in exc.errors()
        ]
        body = error_body("invalid", errors[0]["message"], errors[0]["field"])
        body["error"]["errors"] = errors
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(HTTPException)
    async def _http(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else None
        if detail is None or detail in ("Not Found", "Method Not Allowed"):
            detail = _HTTP_MESSAGES.get(exc.status_code, "Richiesta non valida.")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(f"http_{exc.status_code}", detail),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(ValueError)
    async def _bad_value(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content=error_body("bad_request", str(exc)))

    @app.exception_handler(FileNotFoundError)
    async def _not_found(_request: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content=error_body("not_found", str(exc)))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        _log.exception("errore inatteso su %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_body(
                "internal", "Si è verificato un errore inatteso: il dettaglio è nel log."
            ),
        )
