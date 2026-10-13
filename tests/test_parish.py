# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Parish name and logo: test 25 of SPEC §15 (§8.8). The logo in the PDF: test_export_jobs."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from cp.db.models import Asset
from cp.db.session import session_scope


def image_bytes(size, fmt="PNG", mode="RGB"):
    out = io.BytesIO()
    Image.new(mode, size, (200, 30, 40)).save(out, format=fmt)
    return out.getvalue()


def upload(api, data, name="logo.png", mime="image/png"):
    return api.post("/api/parish/logo", files={"logo": (name, data, mime)})


def stored():
    with session_scope() as session:
        asset = session.get(Asset, "parish.logo")
        return None if asset is None else (asset.mime, asset.data)


@pytest.mark.parametrize(("fmt", "size"), [("PNG", (1200, 800)), ("JPEG", (500, 1500))])
def test_raster_logo_reduced_to_600_and_stored_as_png(api, fmt, size):
    response = upload(api, image_bytes(size, fmt))
    assert response.status_code == 200, response.text
    assert response.json()["logo"]["mime"] == "image/png"
    mime, data = stored()
    image = Image.open(io.BytesIO(data))
    assert (mime, image.format) == ("image/png", "PNG")
    assert max(image.size) == 600
    assert image.size[0] / image.size[1] == pytest.approx(size[0] / size[1], rel=0.01)


def test_small_logo_is_not_enlarged_and_keeps_transparency(api):
    assert upload(api, image_bytes((120, 60), mode="RGBA")).status_code == 200
    image = Image.open(io.BytesIO(stored()[1]))
    assert image.size == (120, 60) and image.mode == "RGBA"


def test_svg_stored_as_it_is(api):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
    assert upload(api, svg, "logo.svg", "image/svg+xml").status_code == 200
    assert stored() == ("image/svg+xml", svg)
    logo = api.get("/api/parish/logo")
    assert logo.headers["content-type"].startswith("image/svg+xml")
    assert "sandbox" in logo.headers["content-security-policy"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (image_bytes((50, 50), "GIF"), "Il logo deve essere un'immagine PNG, JPEG o SVG."),
        (b"testo qualsiasi", "Il logo deve essere un'immagine PNG, JPEG o SVG."),
        (b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024), "Il logo può pesare al massimo 2 MB."),
        (
            b'<svg xmlns="http://www.w3.org/2000/svg">' + b" " * (512 * 1024) + b"</svg>",
            "Un logo SVG può pesare al massimo 512 KB.",
        ),
    ],
)
def test_refused_logos_change_nothing(api, data, message):
    response = upload(api, data)
    assert response.status_code == 422
    assert response.json()["error"]["message"] == message
    assert stored() is None


def test_replace_and_remove(api):
    upload(api, image_bytes((100, 100)))
    upload(api, image_bytes((300, 100)))
    assert Image.open(io.BytesIO(stored()[1])).size == (300, 100)
    assert api.delete("/api/parish/logo").status_code == 204
    assert stored() is None
    assert api.get("/api/parish").json()["logo"] is None
    assert api.get("/api/parish/logo").status_code == 404


def test_name(api):
    response = api.put("/api/parish", json={"name": "  Parrocchia   San Luca  "})
    assert response.json()["name"] == "Parrocchia San Luca"
    assert api.get("/api/settings").json()["parish.name"] == "Parrocchia San Luca"
    too_long = api.put("/api/parish", json={"name": "x" * 81})
    assert too_long.status_code == 422
    assert api.put("/api/parish", json={"name": ""}).json()["name"] == ""
