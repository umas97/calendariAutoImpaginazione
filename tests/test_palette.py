# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test 21: colours used for text read on white; palette colours that stay apart."""

from __future__ import annotations

import itertools
import math

import pytest

from cp.domain.palette import PALETTE, contrast_on_white, next_color, text_color


@pytest.mark.parametrize("color", [*PALETTE, "#FFF59D"])
def test_text_color_reaches_aa_contrast(color):
    assert contrast_on_white(text_color(color)) >= 4.5


def test_a_dark_colour_stays_the_same():
    assert text_color("#1F2328") == "#1F2328"
    assert text_color("#277da1") == "#277DA1"


def test_next_color_takes_the_first_free_then_starts_again():
    assert next_color([]) == PALETTE[0]
    assert next_color([PALETTE[0], PALETTE[2]]) == PALETTE[1]
    assert next_color(PALETTE) == PALETTE[0]
    assert next_color([*PALETTE, PALETTE[0]]) == PALETTE[1]  # the least used
    assert next_color([*PALETTE, PALETTE[0].lower(), PALETTE[1]]) == PALETTE[2]


def _lab(hex_color: str) -> tuple[float, float, float]:
    """CIELAB (D65) of an sRGB colour."""
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)
    xyz = (
        (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047,
        0.2126 * r + 0.7152 * g + 0.0722 * b,
        (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883,
    )
    fx, fy, fz = (t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in xyz)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _closest(colors) -> float:
    return min(math.dist(_lab(a), _lab(b)) for a, b in itertools.combinations(colors, 2))


@pytest.mark.parametrize("paint", [str, text_color], ids=["bars", "day numbers"])
def test_palette_colours_stay_apart_on_paper(paint):
    """The first categories differ the most; no two colours are near (CIE76 ΔE)."""
    colors = [paint(color) for color in PALETTE]
    assert len(set(PALETTE)) == 12
    assert _closest(colors[:6]) >= 30
    assert _closest(colors) >= 20
