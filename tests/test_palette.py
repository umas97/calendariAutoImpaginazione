# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test 21: colours used for text read on white."""

from __future__ import annotations

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
