# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared fixtures: a temporary home for every test, and a live server.

Every test runs with the XDG directories pointed at a temporary folder, so no
test can read or write the real user's data, lock or log.
"""

from __future__ import annotations

import http.client
import json
import socket
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from cp.config import get_settings
from cp.controls import AppControls
from cp.server import LocalServer


@pytest.fixture(autouse=True)
def xdg_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    home = tmp_path / "home"
    for variable, sub in (
        ("XDG_DATA_HOME", "share"),
        ("XDG_STATE_HOME", "state"),
        ("XDG_RUNTIME_DIR", "run"),
        ("XDG_CONFIG_HOME", "config"),
    ):
        (home / sub).mkdir(parents=True)
        monkeypatch.setenv(variable, str(home / sub))
    # The export and the folder picker live inside $HOME: never the real one.
    monkeypatch.setenv("HOME", str(home))
    for name in ("PORT", "LOG_LEVEL", "BROWSER", "DEV"):
        monkeypatch.delenv(f"CP_{name}", raising=False)
    get_settings.cache_clear()
    yield home
    get_settings.cache_clear()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@dataclass
class Recorder:
    """Fake controls that remember what the API asked of them."""

    calls: list[str] = field(default_factory=list)
    token: str | None = None

    def controls(self) -> AppControls:
        return AppControls(
            quit=lambda: self.calls.append("quit"),
            show_window=lambda: self.calls.append("show") or {"shown": True},
            window_info=lambda: {"mode": "app", "note": None},
            token=self.token,
        )


@dataclass
class Live:
    """A running server and a small client that can forge headers."""

    port: int
    recorder: Recorder
    static: Path

    def request(
        self,
        method: str,
        path: str,
        *,
        host: str | None = None,
        origin: str | None = None,
        token: str | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Host": host or f"127.0.0.1:{self.port}"}
        if origin is not None:
            headers["Origin"] = origin
        if token is not None:
            headers["X-App-Token"] = token
        connection.request(method, path, body=b"" if method == "POST" else None, headers=headers)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, {k.lower(): v for k, v in response.getheaders()}, body

    def json(self, method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
        status, _headers, body = self.request(method, path, **kwargs)
        return status, json.loads(body)


def start_live(tmp_path: Path, token: str | None = None) -> tuple[Live, LocalServer]:
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<!doctype html><title>shell</title>", encoding="utf-8")
    (static / "assets" / "app-1234.js").write_text("console.log(1)", encoding="utf-8")
    recorder = Recorder(token=token)
    server = LocalServer(recorder.controls(), "127.0.0.1", 0, static_dir=static)
    port = server.start()
    return Live(port, recorder, static), server


@pytest.fixture
def live(tmp_path: Path) -> Iterator[Live]:
    running, server = start_live(tmp_path)
    yield running
    server.stop()


@pytest.fixture
def live_with_token(tmp_path: Path) -> Iterator[Live]:
    running, server = start_live(tmp_path, token="segreto")
    yield running
    server.stop()


# --- the project's API, in process ---------------------------------------------


class Api:
    """A TestClient on a fresh database, with helpers that build the usual fixtures."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.client.get(path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.client.post(path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.client.put(path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        return self.client.patch(path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.client.delete(path, **kwargs)

    def group(self, name: str = "Cresimandi") -> int:
        response = self.post("/api/groups", json={"name": name})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def category(self, name: str = "Catechesi", color: str | None = None) -> int:
        body: dict[str, Any] = {"name": name}
        if color is not None:
            body["color"] = color
        response = self.post("/api/categories", json=body)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def event(self, groups: list[int], categories: list[int], **fields: Any) -> dict[str, Any]:
        body = {
            "title": "Incontro",
            "start_date": "2026-10-18",
            "start_time": "15:00",
            "group_ids": groups,
            "category_ids": categories,
        } | fields
        response = self.post("/api/events", json=body)
        assert response.status_code == 201, response.text
        return response.json()


@pytest.fixture
def api(xdg_home: Path) -> Iterator[Api]:
    from fastapi.testclient import TestClient

    from cp.server import create_app

    app = create_app(static_dir=xdg_home / "no-interface")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield Api(client)


# --- test 27: the budgets of SPEC §14 (tests/bench/, only with -m bench) ------------

_measures: list[tuple[str, float, float, str]] = []


@pytest.fixture
def measure():
    """``measure(name, value, target, unit)``: record it and check it is within the target.

    The bench modules set ``pytestmark = pytest.mark.bench``, which the quick suite
    deselects (``pyproject.toml``); run them on a machine at rest with
    ``uv run pytest -m bench tests/bench``. Every measure is printed at the end,
    next to its target, so the numbers can go into STATO.md.
    """

    def record(name: str, value: float, target: float, unit: str) -> None:
        _measures.append((name, value, target, unit))
        assert value < target, f"{name}: {value:.3g} {unit} (target < {target:g} {unit})"

    return record


def pytest_terminal_summary(terminalreporter) -> None:
    if not _measures:
        return
    terminalreporter.section("budget di SPEC §14")
    for name, value, target, unit in _measures:
        mark = "ok " if value < target else "NO "
        line = f"{mark} {name}: {value:.3g} {unit} (target < {target:g} {unit})"
        terminalreporter.write_line(line)
