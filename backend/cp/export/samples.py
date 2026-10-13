# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic events for the tests and for the sample sheets (SPEC §8.4, §16 phase 4).

Titles average about 30 characters and places about 20, as the SPEC's
targets assume. Nothing here is real data. ``python -m cp.export.samples DIR``
writes the sample sheets the user approves before phase 5: a temporary
database, 10, 30 and 80 events on one sheet each, and a complete calendar.
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import sys
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from ..domain import events as event_ops
from ..domain import taxonomy
from ..domain.schemas import EventIn
from ..domain.settings import put_setting

TITLES = (
    "Incontro di catechesi del sabato",
    "Messa con le famiglie dei ragazzi",
    "Ritiro spirituale di Avvento",
    "Prove del coro per la Messa solenne",
    "Festa di inizio anno pastorale",
    "Celebrazione penitenziale",
    "Incontro genitori e catechisti",
    "Castagnata in oratorio",
    "Adorazione eucaristica serale",
    "Veglia di preghiera per la pace",
    "Uscita al santuario della Madonna",
    "Cena di condivisione",
    "Laboratorio di Natale per i bambini",
    "Via Crucis per le vie del paese",
    "Prima confessione",
    "Gita di fine anno ad Assisi",
    "Incontro con il vescovo in cattedrale",
    "Tombolata della Befana",
    "Prove della recita di Natale",
    "Pellegrinaggio diocesano dei giovani",
)

PLACES = (
    "Oratorio San Luigi",
    "Chiesa parrocchiale",
    "Salone parrocchiale",
    "Cappella feriale",
    "Santuario della Madonna",
    "Campo sportivo dell'oratorio",
    "Casa canonica",
    "Aula 3 del catechismo",
)

GROUPS = ("Cresimandi", "5ª elementare", "Giovanissimi", "Coro", "Oratorio")
CATEGORIES = ("Catechesi", "Messa", "Ritiro", "Festa")


def sample_events(
    count: int,
    first: dt.date,
    last: dt.date,
    group_ids: list[int],
    category_ids: list[int],
    seed: int = 7,
) -> list[EventIn]:
    """``count`` plausible events spread over ``[first, last]``, all for ``group_ids[0]``.

    Some also belong to a second group, some have a second category, a few
    last all day or several days.
    """
    rng = random.Random(seed)
    days = (last - first).days
    out = []
    for i in range(count):
        start = first + dt.timedelta(days=(days * i) // max(count, 1) + rng.randint(0, 1))
        start = min(start, last)
        kind = rng.random()
        all_day = kind < 0.08
        end_date = start + dt.timedelta(days=2) if 0.08 <= kind < 0.13 else None
        hour = rng.choice((9, 10, 15, 16, 18, 20, 21))
        start_time = None if all_day else f"{hour:02d}:{rng.choice((0, 30)):02d}"
        end_time = None
        if not all_day and rng.random() < 0.7:
            end_time = f"{min(hour + rng.choice((1, 2)), 23):02d}:{rng.choice((0, 30)):02d}"
        groups = [group_ids[0]]
        if len(group_ids) > 1 and rng.random() < 0.3:
            groups.append(rng.choice(group_ids[1:]))
        categories = [rng.choice(category_ids)]
        if len(category_ids) > 1 and rng.random() < 0.15:
            categories.append(rng.choice([c for c in category_ids if c != categories[0]]))
        out.append(
            EventIn(
                title=TITLES[(i * 7 + rng.randint(0, 3)) % len(TITLES)],
                start_date=start,
                end_date=end_date,
                all_day=all_day,
                start_time=start_time,
                end_time=end_time,
                place=rng.choice(PLACES),
                notes=f"nota interna {i}",
                group_ids=groups,
                category_ids=categories,
            )
        )
    return out


def seed_taxonomy(session: Session) -> tuple[list[int], list[int]]:
    groups = [taxonomy.create_item(session, taxonomy.GROUPS, n).id for n in GROUPS]
    categories = [taxonomy.create_item(session, taxonomy.CATEGORIES, n).id for n in CATEGORIES]
    return groups, categories


def add_events(session: Session, items: list[EventIn]) -> None:
    for item in items:
        event_ops.create_event(session, item)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cp.export.samples",
        description="Scrive i fogli di prova (10, 30, 80 eventi e calendario completo).",
    )
    parser.add_argument("cartella", type=Path, help="dove scrivere (sotto la home)")
    parser.add_argument("--parrocchia", default="Parrocchia San Giovanni Battista")
    parser.add_argument("--png", action="store_true", help="anche le immagini PNG a 200 dpi")
    args = parser.parse_args(argv)

    from ..db.session import open_database, session_scope
    from .jobs import run_export
    from .request import ExportRequest

    with tempfile.TemporaryDirectory() as tmp:
        open_database(Path(tmp) / "samples.db")
        first, last = dt.date(2026, 9, 1), dt.date(2027, 6, 30)
        with session_scope() as session:
            put_setting(session, "parish.name", args.parrocchia)
            groups, categories = seed_taxonomy(session)
            # Shared events go to the two groups not exported, so each sheet
            # gets exactly its count; the complete calendar labels them.
            for group, count in zip(groups[:3], (10, 30, 80), strict=True):
                others = groups[3:]
                add_events(
                    session,
                    sample_events(count, first, last, [group, *others], categories, seed=count),
                )
        formats = ["pdf", "png"] if args.png else ["pdf"]
        selections = [{"group_id": g, "category_ids": categories} for g in groups[:3]]
        for mode in ("per_group", "combined"):
            request = ExportRequest.model_validate(
                {
                    "period": {"from": first, "to": last},
                    "mode": mode,
                    "formats": formats,
                    "selections": selections,
                    "output_dir": str(args.cartella.resolve()),
                }
            )
            job = run_export(request)
            for name in job.files:
                print(name)
            for item in job.skipped:
                print(f"{item['group']}: {item['message']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
