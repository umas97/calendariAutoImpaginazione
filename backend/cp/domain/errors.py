# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Errors the domain raises, and the uniform shape the API gives them (SPEC §12).

Every API error is ``{"error": {"code", "message", "field"?}}``, with a message
in Italian written for the person using the program. A validation error that
concerns several fields also lists them all in ``errors``, so the dialog can
show each message next to its field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str


class DomainError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message: str, *, field: str | None = None, **extra: Any) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.extra = extra

    def body(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field is not None:
            error["field"] = self.field
        error.update(self.extra)
        return {"error": error}


class Forbidden(DomainError):
    status = 403
    code = "forbidden"


class NotFound(DomainError):
    status = 404
    code = "not_found"


class Conflict(DomainError):
    status = 409
    code = "conflict"


class Invalid(DomainError):
    status = 422
    code = "invalid"


class InvalidFields(Invalid):
    """Several field errors at once; the first one is the headline."""

    def __init__(self, problems: list[FieldError]) -> None:
        super().__init__(problems[0].message, field=problems[0].field)
        self.problems = problems

    def body(self) -> dict[str, Any]:
        body = super().body()
        body["error"]["errors"] = [{"field": p.field, "message": p.message} for p in self.problems]
        return body


def error_body(code: str, message: str, field: str | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if field is not None:
        error["field"] = field
    return {"error": error}
