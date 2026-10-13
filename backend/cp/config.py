# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings, and where things live on disk.

Everything the program writes goes under the XDG base directories of the user
running it -- never next to the files it works on, never inside the source tree:

* ``$XDG_DATA_HOME/calendariautoimpaginazione/`` -- the user's data, what a backup must keep;
* ``$XDG_STATE_HOME/calendariautoimpaginazione/logs/`` -- the log;
* ``$XDG_RUNTIME_DIR/calendariautoimpaginazione.lock`` -- the single-instance lock. That
  directory is a tmpfs emptied at logout, so a lock can never outlive a reboot.

The program was called ``calendariparrocchia`` before: on the first start under
the current name its folders are moved over (``Settings.ensure_dirs``).

Every value can be overridden with a ``CP_*`` environment variable, and
the XDG variables are honoured: the tests run the whole program inside a
temporary home that way.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

APP_ID = "calendariautoimpaginazione"
APP_NAME = "calendariAutoImpaginazione"
DESCRIPTION = "Calendario dei gruppi parrocchiali con fogli A4 da distribuire"
ENV_PREFIX = "CP_"

#: The ids the program had before. Their folders become the current ones on the
#: first start, and a database or backup stamped with them is still ours.
LEGACY_APP_IDS = ("calendariparrocchia",)

#: Fixed, because the window's origin includes the port: another port is
#: another site to the browser, with its own storage and its own PWA install.
#: If it is taken the program says so and stops; it never wanders to another.
DEFAULT_PORT = 8746

#: Where the window opens. The server redirects it to ``/``; the path exists only
#: to give the window an identity in the dock that no other local app shares
#: (``window.py`` explains why the port cannot do that).
WINDOW_PATH = f"/{APP_ID}"


def env(name: str) -> str | None:
    """``CP_<name>`` from the environment, or ``None``."""
    return os.environ.get(ENV_PREFIX + name) or None


class LegacyRunning(RuntimeError):
    """The program is still running under an older name: its folders cannot move."""

    def __init__(self, legacy_id: str) -> None:
        super().__init__(
            f"è ancora aperta la versione precedente del programma ({legacy_id}): "
            "chiudila e riprova"
        )


def _pid_in(lock: Path) -> bool:
    """Does the lockfile at ``lock`` name a live process?"""
    try:
        pid = int(json.loads(lock.read_text(encoding="utf-8"))["pid"])
        os.kill(pid, 0)
    except PermissionError:
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return pid > 0


def _xdg(variable: str, fallback: str) -> Path:
    raw = os.environ.get(variable)
    base = Path(raw).expanduser() if raw else Path.home() / fallback
    return base / APP_ID


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    log_level: str
    data_dir: Path
    state_dir: Path
    runtime_dir: Path
    browser: str | None

    @property
    def log_dir(self) -> Path:
        return self.state_dir / "logs"

    @property
    def lock_path(self) -> Path:
        return self.runtime_dir / f"{APP_ID}.lock"

    def ensure_dirs(self) -> list[tuple[Path, Path]]:
        """Create the directories the program writes into; return the old ones moved.

        A folder left by an older name of the program becomes the current one, if
        the current one does not exist yet -- and never while that older version is
        running (``LegacyRunning``): it would go on writing into the moved files.
        """
        moved = []
        for path in (self.data_dir, self.state_dir):
            if path.exists():
                continue
            for legacy_id in LEGACY_APP_IDS:
                legacy = path.with_name(legacy_id)
                if not legacy.is_dir():
                    continue
                locks = (
                    self.runtime_dir / f"{legacy_id}.lock",
                    self.state_dir.with_name(legacy_id) / f"{legacy_id}.lock",
                )
                if any(_pid_in(lock) for lock in locks):
                    raise LegacyRunning(legacy_id)
                legacy.rename(path)
                moved.append((legacy, path))
                break
        for path in (self.data_dir, self.log_dir):
            path.mkdir(parents=True, exist_ok=True)
        return moved


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    state = _xdg("XDG_STATE_HOME", ".local/state")
    return Settings(
        # Loopback, and deliberately not a setting: there is no option to expose
        # the program to the network, so no one can turn it on by mistake.
        host="127.0.0.1",
        port=int(env("PORT") or DEFAULT_PORT),
        log_level=(env("LOG_LEVEL") or "INFO").upper(),
        data_dir=_xdg("XDG_DATA_HOME", ".local/share"),
        state_dir=state,
        runtime_dir=Path(runtime) if runtime else state,
        browser=env("BROWSER"),
    )
