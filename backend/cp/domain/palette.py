# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Category colours: the default palette, its assignment, and readable text (SPEC §6.2)."""

from __future__ import annotations

import colorsys
import re
from collections.abc import Iterable

#: Twelve colours that stay apart from one another and survive a printer.
PALETTE: tuple[str, ...] = (
    "#E63946",  # rosso
    "#F4A261",  # arancio
    "#E9C46A",  # ocra
    "#43AA8B",  # verde
    "#2A9D8F",  # verde acqua
    "#00A6ED",  # azzurro
    "#277DA1",  # blu
    "#577590",  # ardesia
    "#9B5DE5",  # viola
    "#F15BB5",  # rosa
    "#8D6E63",  # marrone
    "#6C757D",  # grigio
)

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

#: WCAG AA for normal text.
MIN_CONTRAST = 4.5


def normalize_color(value: str) -> str | None:
    """``#RRGGBB`` in upper case, or ``None`` if ``value`` is not one."""
    value = value.strip()
    return value.upper() if _HEX.match(value) else None


def next_color(used: Iterable[str]) -> str:
    """The first palette colour no category uses yet; the first one when all are taken."""
    taken = {color.upper() for color in used}
    return next((color for color in PALETTE if color not in taken), PALETTE[0])


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
