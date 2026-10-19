# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Colours of categories and groups: the palette, its assignment, readable text (SPEC §6.2)."""

from __future__ import annotations

import colorsys
import re
from collections import Counter
from collections.abc import Iterable

#: Twelve colours that stay apart from one another and survive a printer, in the
#: order they are handed out: neighbouring hues never come one after the other,
#: so the first few categories differ the most. Mostly dark enough to read as
#: text on white, so the day numbers of the export match the bars (CIEDE2000
#: between any two of the first six, bars and numbers: >= 19; of all twelve: >= 13).
PALETTE: tuple[str, ...] = (
    "#1976D2",  # blu
    "#D32F2F",  # rosso
    "#2E7D32",  # verde
    "#F57C00",  # arancio
    "#8E24AA",  # viola
    "#00838F",  # ottanio
    "#C2185B",  # magenta
    "#6D4C41",  # marrone
    "#FBC02D",  # giallo
    "#283593",  # indaco
    "#C0CA33",  # lime
    "#757575",  # grigio
)

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

#: WCAG AA for normal text.
MIN_CONTRAST = 4.5


def normalize_color(value: str) -> str | None:
    """``#RRGGBB`` in upper case, or ``None`` if ``value`` is not one."""
    value = value.strip()
    return value.upper() if _HEX.match(value) else None


def next_color(used: Iterable[str]) -> str:
    """The first palette colour nobody uses yet; when all are taken, the least used.

    Ties go to the earlier colour, so past the twelfth the palette starts again
    from the first, then the second, and so on.
    """
    counts = Counter(color.upper() for color in used)
    return min(PALETTE, key=lambda color: counts[color])


def _rgb(hex_color: str) -> tuple[float, float, float]:
    return tuple(int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def relative_luminance(hex_color: str) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in _rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_on_white(hex_color: str) -> float:
    return 1.05 / (relative_luminance(hex_color) + 0.05)


def text_color(hex_color: str) -> str:
    """The colour darkened in 5% lightness steps until it reads on white (≥ 4.5:1).

    Bars and dots keep the original; only text coloured with it needs this.
    A colour already dark enough comes back unchanged.
    """
    color = hex_color.upper()
    h, lightness, s = colorsys.rgb_to_hls(*_rgb(color))
    while contrast_on_white(color) < MIN_CONTRAST and lightness > 0:
        lightness = max(0.0, lightness - 0.05)
        color = _hex(colorsys.hls_to_rgb(h, lightness, s))
    return color
