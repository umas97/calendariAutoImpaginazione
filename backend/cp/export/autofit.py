# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fit a group's sheet on one A4 page (SPEC §8.4; test 14).

The layouts are tried from the most readable to the most compact, and the
first that fits on one page wins: one column from 11 pt down to 8.5 pt, then
two columns from 9.5 pt down to 7.5 pt, in steps of 0.5 pt. Within a phase the
page count only grows with the size, so a binary search finds the largest size
that fits with at most three compositions; seven in all at worst.

A :class:`LayoutMemory` remembers what the search found for recent sheets.
The preview and the export share one, so exporting what was just previewed
costs one composition per sheet, and none for a sheet known not to fit.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .render import Layout, compose
from .selection import Sheet

if TYPE_CHECKING:
    from weasyprint import Document


def _sizes(high: float, low: float) -> tuple[float, ...]:
    count = round((high - low) / 0.5) + 1
    return tuple(high - 0.5 * i for i in range(count))


#: The phases, each from its largest size to its smallest.
PHASES: tuple[tuple[int, tuple[float, ...]], ...] = (
    (1, _sizes(11.0, 8.5)),
    (2, _sizes(9.5, 7.5)),
)


@dataclass(frozen=True)
class Fitted:
    layout: Layout
    document: Document
    #: How many compositions it took: for the tests and the log.
    attempts: int


Composer = Callable[[Sheet, Layout], "Document"]


def _largest_fitting(
    sheet: Sheet, columns: int, sizes: tuple[float, ...], composer: Composer
) -> tuple[Fitted | None, int]:
    """Binary search for the first size (the largest) whose layout is one page."""
    attempts = 0
    found: dict[int, Document] = {}
    low, high = 0, len(sizes)
    while low < high:
        middle = (low + high) // 2
        attempts += 1
        document = composer(sheet, Layout(columns, sizes[middle]))
        if len(document.pages) == 1:
            found[middle] = document
            high = middle
        else:
            low = middle + 1
    if low == len(sizes):
        return None, attempts
    return Fitted(Layout(columns, sizes[low]), found[low], attempts), attempts


#: What a :class:`LayoutMemory` holds for a sheet that fits no layout.
NO_FIT = "no fit"


class LayoutMemory:
    """The layouts found for the latest sheets.

    A sheet carries every text and colour it shows, so an equal sheet lays out
    the same way: the search need not run again.
    """

    def __init__(self, size: int = 64) -> None:
        self._lock = threading.Lock()
        self._size = size
        self._known: OrderedDict[Sheet, Layout | str] = OrderedDict()

    def get(self, sheet: Sheet) -> Layout | str | None:
        with self._lock:
            known = self._known.get(sheet)
            if known is not None:
                self._known.move_to_end(sheet)
            return known

    def put(self, sheet: Sheet, layout: Layout | str) -> None:
        with self._lock:
            self._known[sheet] = layout
            self._known.move_to_end(sheet)
            while len(self._known) > self._size:
                self._known.popitem(last=False)


#: Shared by the preview and the export.
layouts = LayoutMemory()


def fit_sheet(
    sheet: Sheet, composer: Composer = compose, memory: LayoutMemory | None = None
) -> Fitted | None:
    """The most readable one-page layout of ``sheet``, or ``None`` if none exists."""
    known = memory.get(sheet) if memory is not None else None
    if known == NO_FIT:
        return None
    if isinstance(known, Layout):
        document = composer(sheet, known)
        if len(document.pages) == 1:
            return Fitted(known, document, 1)
    attempts = 0
    for columns, sizes in PHASES:
        fitted, spent = _largest_fitting(sheet, columns, sizes, composer)
        attempts += spent
        if fitted is not None:
            if memory is not None:
                memory.put(sheet, fitted.layout)
            return Fitted(fitted.layout, fitted.document, attempts)
    if memory is not None:
        memory.put(sheet, NO_FIT)
    return None
