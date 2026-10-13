# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Where the files go and what they are called; nothing is ever overwritten (SPEC §2.2, §8.6).

Every export writes into a new ``Export AAAA-MM-GG HH-MM`` folder inside the
chosen one. :func:`reserve_path` is the only place that picks a file name: it
creates the file with ``open(path, "xb")``, which fails if anything already
has that name, so even a file appearing at the last moment cannot be replaced.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

#: Longest group name kept in a file name.
NAME_MAX = 80

_FORBIDDEN = re.compile(r'[/\\:*?"<>|\x00-\x1f\x7f]')
_SPACES = re.compile(r"\s+")


def clean_name(name: str, fallback: str = "Gruppo") -> str:
    """A group name made safe for a file name: no ``/ \\ : * ? " < > |``, no control characters.

    Spaces are collapsed and the name cut to 80 characters. Leading dots go too,
    so that no file comes out hidden.
    """
    name = _SPACES.sub(" ", _FORBIDDEN.sub("", _SPACES.sub(" ", name))).strip().lstrip(". ")
    return name[:NAME_MAX].rstrip() or fallback


def _numbered(name: str, n: int) -> str:
    if n == 1:
        return name
    stem, dot, suffix = name.rpartition(".")
    if not dot or not stem:
        return f"{name} ({n})"
    return f"{stem} ({n}).{suffix}"


def reserve_path(directory: Path, name: str) -> Path:
    """Create an empty file named ``name`` in ``directory`` -- or ``name (2)``, ``(3)``… if taken.

    The file exists when this returns, and belongs to the caller.
    """
    n = 1
    while True:
        path = directory / _numbered(name, n)
        try:
            with open(path, "xb"):
                return path
        except FileExistsError:
            n += 1


def write_new(directory: Path, name: str, data: bytes) -> Path:
    """Write ``data`` to a new file; a file left half-written by a failure is removed."""
    path = reserve_path(directory, name)
    try:
        # r+b: the file reserve_path just created, never another one.
        with open(path, "r+b") as file:
            file.write(data)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def export_folder(base: Path, when: dt.datetime) -> Path:
    """Create and return ``base/Export AAAA-MM-GG HH-MM`` (or `` (2)``…), and ``base`` if needed."""
    base.mkdir(parents=True, exist_ok=True)
    name = f"Export {when:%Y-%m-%d %H-%M}"
    n = 1
    while True:
        path = base / (name if n == 1 else f"{name} ({n})")
        try:
            path.mkdir()
            return path
        except FileExistsError:
            n += 1


def span(first: dt.date, last: dt.date) -> str:
    return f"{first.isoformat()}_{last.isoformat()}"


def group_file(group: str, first: dt.date, last: dt.date, suffix: str, page: int = 0) -> str:
    """``<Gruppo> <from>_<to>.pdf``; with ``page``, ``… p2.png``."""
    stem = f"{clean_name(group)} {span(first, last)}"
    return f"{stem} p{page}.{suffix}" if page else f"{stem}.{suffix}"


def single_pdf_file(first: dt.date, last: dt.date) -> str:
    return f"Calendari per gruppo {span(first, last)}.pdf"


def combined_file(first: dt.date, last: dt.date, suffix: str, page: int = 0) -> str:
    stem = f"Calendario completo {span(first, last)}"
    return f"{stem} p{page}.{suffix}" if page else f"{stem}.{suffix}"
