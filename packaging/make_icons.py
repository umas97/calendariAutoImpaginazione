#!/usr/bin/env python3
# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Draw the application icons.

Three A4 sheets fanned out on a blue-violet plate; the front one carries the grid
of a month with two coloured days -- the sheets the program prints. The drawing is
described once, in a 512 px space (the constants below), and turned both into an
SVG and into PNGs drawn with Pillow. Keep the file names -- install.sh and the
interface look for exactly these:

* ``packaging/icons/calendariautoimpaginazione-{48,128,256}.png`` and ``calendariautoimpaginazione.svg`` for
  the desktop (hicolor theme);
* ``icons/icon.svg``, ``icon-192.png``, ``icon-512.png``, ``icon-512-maskable.png``
  for the interface (favicon, PWA manifest).

The maskable variant is the same drawing at 80% on a full-bleed plate: some
desktops crop icons to their own shape, and only the centre circle is safe.

Run with ``uv run python packaging/make_icons.py``.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

APP_ID = "calendariautoimpaginazione"

GRADIENT = ("#5b6cf0", "#8b4fd8")  # top-left -> bottom-right
PAPER = "#ffffff"
CELL = "#dcdff5"
PLATE = (31, 31, 481, 481)
PLATE_RADIUS = 99
# A sheet: A4 proportions, centred on CENTRE before turning around PIVOT.
CENTRE = (256, 268)
SHEET_W, SHEET_H, SHEET_RADIUS = 208, 294, 14
PIVOT = (256, 408)
# (clockwise degrees, opacity), back to front.
SHEETS = ((-14, 0.55), (-6, 0.8), (5, 1.0))
# The front sheet, relative to its centre: (x, y, w, h, radius, colour).
HEADER = (-80, -122, 112, 22, 11, GRADIENT[0])
CELL_W, CELL_H, CELL_RADIUS = 40, 34, 6
CELL_XS = (-80, -20, 40)
CELL_YS = (-76, -30, 16, 62)
MARKED = {(-20, -30): "#f59e42", (40, 62): GRADIENT[1]}

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT / "packaging" / "icons"
WEB = (
    ROOT / "frontend" / "public" / "icons"
    if (ROOT / "frontend").is_dir()
    else ROOT / "backend" / "cp" / "static" / "icons"
)


def _front() -> list[tuple[int, int, int, int, int, str]]:
    cells = [
        (x, y, CELL_W, CELL_H, CELL_RADIUS, MARKED.get((x, y), CELL))
        for y in CELL_YS
        for x in CELL_XS
    ]
    return [HEADER, *cells]


def _rgba(colour: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
    value = int(colour[1:], 16)
    return (value >> 16, (value >> 8) & 0xFF, value & 0xFF, round(255 * opacity))


def _gradient(size: int) -> Image.Image:
    """A square filled with GRADIENT along its diagonal."""
    down = Image.linear_gradient("L").resize((size, size))
    across = down.rotate(90)
    mask = ImageChops.add(down, across, scale=2.0)
    start = Image.new("RGBA", (size, size), _rgba(GRADIENT[0]))
    end = Image.new("RGBA", (size, size), _rgba(GRADIENT[1]))
    return Image.composite(end, start, mask)


def draw(size: int, *, maskable: bool = False) -> Image.Image:
    """The icon at ``size`` px, drawn at 4x and scaled down for clean edges."""
    big = size * 4
    unit = big / 512
    scale, offset = (0.8, big * 0.1) if maskable else (1.0, 0.0)

    def at(x: float, y: float) -> tuple[float, float]:
        return offset + x * unit * scale, offset + y * unit * scale

    def length(v: float) -> float:
        return v * unit * scale

    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    if maskable:
        image = _gradient(big)
    else:
        left, top = at(*PLATE[:2])
        right, bottom = at(*PLATE[2:])
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (left, top, right, bottom), radius=length(PLATE_RADIUS), fill=255
        )
        side = round(right - left)
        plate = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        plate.paste(_gradient(side), (round(left), round(top)))
        image.paste(plate, mask=mask)

    cx, cy = CENTRE
    for degrees, opacity in SHEETS:
        layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        pen = ImageDraw.Draw(layer)
        pen.rounded_rectangle(
            (*at(cx - SHEET_W / 2, cy - SHEET_H / 2), *at(cx + SHEET_W / 2, cy + SHEET_H / 2)),
            radius=length(SHEET_RADIUS),
            fill=_rgba(PAPER, opacity),
        )
        if opacity == 1.0:
            for x, y, w, h, r, colour in _front():
                pen.rounded_rectangle(
                    (*at(cx + x, cy + y), *at(cx + x + w, cy + y + h)),
                    radius=length(r),
                    fill=_rgba(colour),
                )
        # Pillow turns counter-clockwise, SVG clockwise.
        layer = layer.rotate(-degrees, center=at(*PIVOT), resample=Image.Resampling.BICUBIC)
        image.alpha_composite(layer)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def svg() -> str:
    cx, cy = CENTRE
    px, py = PIVOT[0] - cx, PIVOT[1] - cy
    sheet = (
        f'<rect x="{-SHEET_W // 2}" y="{-SHEET_H // 2}" width="{SHEET_W}" height="{SHEET_H}"'
        f' rx="{SHEET_RADIUS}" fill="{PAPER}"/>'
    )
    front = "\n".join(
        f'      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{colour}"/>'
        for x, y, w, h, r, colour in _front()
    )
    back = "\n".join(
        f'    <g transform="rotate({degrees} {px} {py})" opacity="{opacity}">{sheet}</g>'
        for degrees, opacity in SHEETS[:-1]
    )
    left, top, right, bottom = PLATE
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="plate" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{GRADIENT[0]}"/><stop offset="1" stop-color="{GRADIENT[1]}"/>
    </linearGradient>
  </defs>
  <rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" rx="{PLATE_RADIUS}"
        fill="url(#plate)"/>
  <g transform="translate({cx} {cy})">
{back}
    <g transform="rotate({SHEETS[-1][0]} {px} {py})">
      {sheet}
{front}
    </g>
  </g>
</svg>
"""


def main() -> None:
    DESKTOP.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)
    for size in (48, 128, 256):
        draw(size).save(DESKTOP / f"{APP_ID}-{size}.png")
    (DESKTOP / f"{APP_ID}.svg").write_text(svg(), encoding="utf-8")
    draw(192).save(WEB / "icon-192.png")
    draw(512).save(WEB / "icon-512.png")
    draw(512, maskable=True).save(WEB / "icon-512-maskable.png")
    (WEB / "icon.svg").write_text(svg(), encoding="utf-8")
    print(f"icone scritte in {DESKTOP} e {WEB}")


if __name__ == "__main__":
    main()
