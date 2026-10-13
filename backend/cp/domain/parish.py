# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The parish letterhead: its name and its logo (SPEC §8.8; test 25).

The logo lives in the database (table ``asset``), so a backup is one file.
PNG and JPEG are reduced to 600 px on the long side and stored as PNG; an SVG
is stored as it is, and whatever it points to is blocked when it is drawn
(``export/render.py``). The type comes from the bytes, never from the name.
"""

from __future__ import annotations

import io
import warnings
from typing import Any

from sqlalchemy.orm import Session

from ..db.models import Asset
from .errors import Invalid
from .settings import get_settings, put_setting

LOGO_KEY = "parish.logo"
MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_SVG_BYTES = 512 * 1024
#: Long side of a stored raster logo.
LOGO_PIXELS = 600
#: Refuse images that would take too much memory to open, whatever their file size.
MAX_SOURCE_PIXELS = 40_000_000

WRONG_TYPE = "Il logo deve essere un'immagine PNG, JPEG o SVG."
TOO_LARGE = "Il logo può pesare al massimo 2 MB."
SVG_TOO_LARGE = "Un logo SVG può pesare al massimo 512 KB."


def _looks_like_svg(data: bytes) -> bool:
    head = data[:2048].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if not (head.startswith(b"<?xml") or head.startswith(b"<svg") or head.startswith(b"<!--")):
        return False
    return b"<svg" in data[:4096].lower()


def _raster_to_png(data: bytes) -> bytes:
    from PIL import Image, ImageOps

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
            if image.format not in ("PNG", "JPEG"):
                raise Invalid(WRONG_TYPE, field="logo")
            if image.width * image.height > MAX_SOURCE_PIXELS:
                raise Invalid("Il logo ha troppi pixel: riducilo prima di caricarlo.", field="logo")
            image = ImageOps.exif_transpose(image)
            image.load()
    except Invalid:
        raise
    except Exception as exc:
        raise Invalid(WRONG_TYPE, field="logo") from exc
    if image.mode not in ("RGB", "RGBA"):
        transparent = "A" in image.getbands() or "transparency" in image.info
        image = image.convert("RGBA" if transparent else "RGB")
    image.thumbnail((LOGO_PIXELS, LOGO_PIXELS), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def save_logo(session: Session, data: bytes) -> Asset:
    if len(data) > MAX_LOGO_BYTES:
        raise Invalid(TOO_LARGE, field="logo")
    if _looks_like_svg(data):
        if len(data) > MAX_SVG_BYTES:
            raise Invalid(SVG_TOO_LARGE, field="logo")
        mime, stored = "image/svg+xml", data
    else:
        mime, stored = "image/png", _raster_to_png(data)
    asset = session.get(Asset, LOGO_KEY) or Asset(key=LOGO_KEY)
    asset.mime, asset.data = mime, stored
    session.add(asset)
    session.flush()
    return asset


def get_logo(session: Session) -> Asset | None:
    return session.get(Asset, LOGO_KEY)


def delete_logo(session: Session) -> None:
    asset = session.get(Asset, LOGO_KEY)
    if asset is not None:
        session.delete(asset)
        session.flush()


def parish_info(session: Session) -> dict[str, Any]:
    logo = get_logo(session)
    return {
        "name": get_settings(session)["parish.name"],
        "logo": None
        if logo is None
        else {
            "mime": logo.mime,
            "bytes": len(logo.data),
            "updated_at": logo.updated_at.isoformat(),
        },
    }


NAME_MAX = 80


def set_name(session: Session, name: str) -> str:
    """0-80 characters; empty leaves the line out of the sheets."""
    name = " ".join(name.split())
    if len(name) > NAME_MAX:
        raise Invalid(
            f"Il nome della parrocchia può avere al massimo {NAME_MAX} caratteri.", field="name"
        )
    return put_setting(session, "parish.name", name)
