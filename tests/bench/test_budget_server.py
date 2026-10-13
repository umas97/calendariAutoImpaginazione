# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test 27, the program as it runs: start, memory at rest, the export of 15 groups (SPEC §14).

The program is started for real (``python -m cp --no-window``) in a home of its
own, filled through its API, and measured from outside: time to the first
``/api/health``, then the resident memory of its process. The window is not
part of the measure (SPEC §14: Chromium is outside the backend's budget).
"""

from __future__ import annotations

import datetime as dt
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from cp.export.samples import sample_events

pytestmark = pytest.mark.bench

FIRST, LAST = dt.date(2026, 9, 1), dt.date(2027, 6, 30)
#: 15 groups with 15 to 57 events each, over a pastoral year (SPEC §1, §14).
COUNTS = [15 + 3 * n for n in range(15)]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Program:
    def __init__(self, home: Path) -> None:
        self.port = free_port()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("XDG_", "CP_"))}
        env.update(
            HOME=str(home),
            XDG_DATA_HOME=str(home / ".local/share"),
            XDG_STATE_HOME=str(home / ".local/state"),
            XDG_RUNTIME_DIR=str(home / "run"),
        )
        (home / "run").mkdir(parents=True)
        self.started = time.perf_counter()
        self.process = subprocess.Popen(
            [sys.executable, "-m", "cp", "--no-window", "--port", str(self.port)],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.ready_after = self._wait_ready()

    def _wait_ready(self, timeout: float = 20.0) -> float:
        deadline = self.started + timeout
        while time.perf_counter() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(self.process.stderr.read().decode())
            try:
                if self.call("GET", "/api/health")[0] == 200:
                    return time.perf_counter() - self.started
            except OSError:
                pass
            time.sleep(0.01)
        raise TimeoutError("il programma non ha risposto")

    def call(self, method: str, path: str, body: Any = None) -> tuple[int, Any]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        payload = json.dumps(body).encode() if body is not None else None
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, json.loads(data) if data else None

    def ok(self, method: str, path: str, body: Any = None) -> Any:
        status, data = self.call(method, path, body)
        assert 200 <= status < 300, (status, data)
        return data

    def rss_mb(self) -> float:
        status = Path(f"/proc/{self.process.pid}/status").read_text()
        kb = next(int(line.split()[1]) for line in status.splitlines() if line.startswith("VmRSS"))
        return kb / 1024

    def stop(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(10)
        except subprocess.TimeoutExpired:
            self.process.kill()


@pytest.fixture(scope="module")
def program(tmp_path_factory) -> Iterator[Program]:
    running = Program(tmp_path_factory.mktemp("bench") / "home")
    yield running
    running.stop()


def test_start_and_memory_at_rest(program, measure):
    measure("avvio fino a /api/health", program.ready_after, 2.0, "s")
    time.sleep(1.0)  # the start-up backup and the first requests settle
    measure("RSS a riposo", program.rss_mb(), 150, "MB")


def fill(program: Program) -> tuple[list[int], list[int]]:
    categories = [
        program.ok("POST", "/api/categories", {"name": name})["id"]
        for name in ("Catechesi", "Messa", "Ritiro", "Festa")
    ]
    groups = []
    for n, count in enumerate(COUNTS):
        group = program.ok("POST", "/api/groups", {"name": f"Gruppo {n + 1}"})["id"]
        groups.append(group)
        for item in sample_events(count, FIRST, LAST, [group], categories, seed=n):
            program.ok("POST", "/api/events", item.model_dump(mode="json"))
    return groups, categories


def test_export_of_fifteen_groups(program, measure, tmp_path_factory):
    groups, categories = fill(program)
    out = Path(program.ok("GET", "/api/export/options")["home"]) / "export"
    request = {
        "period": {"from": FIRST.isoformat(), "to": LAST.isoformat()},
        "mode": "per_group",
        "formats": ["pdf"],
        "dpi": 200,
        "selections": [{"group_id": g, "category_ids": categories} for g in groups],
        "output_dir": str(out),
    }
    time.sleep(2.0)  # the warm-up started by /options, as when the tab opens
    started = time.perf_counter()
    job = program.ok("POST", "/api/export", request)
    while job["status"] == "running":
        time.sleep(0.1)
        job = program.ok("GET", f"/api/export/jobs/{job['id']}")
    elapsed = time.perf_counter() - started
    assert job["status"] == "done", job
    assert len(job["files"]) + len(job["skipped"]) == len(groups)
    measure("export di 15 gruppi, PDF", elapsed, 30, "s")
    measure("RSS dopo l'export di 15 gruppi", program.rss_mb(), 300, "MB")
