# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tables (SPEC §6.1, §7.1, §10.1).

Dates and times are wall-clock values without a time zone (SPEC §4, decision
11): dates are ``DATE`` columns, times are ``HH:MM`` strings, so daylight saving
time can never move an event.

The bridge tables cascade only from the event side: deleting an event removes
its links. Deleting a group or a category never cascades -- ``domain/taxonomy.py``
decides what happens to the events left without one (SPEC §6.3).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> dt.datetime:
    """Local wall-clock time, to the second."""
    return dt.datetime.now().replace(microsecond=0)


class Base(DeclarativeBase):
    pass


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    #: ``casefold()`` of the name: uniqueness ignores case, archived items included.
    name_key: Mapped[str] = mapped_column(String(60), unique=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    name_key: Mapped[str] = mapped_column(String(60), unique=True)
    color: Mapped[str] = mapped_column(String(7))
    position: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class EventGroup(Base):
    __tablename__ = "event_group"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), primary_key=True, index=True)


class EventCategory(Base):
    __tablename__ = "event_category"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.id"), primary_key=True, index=True
    )
    #: 0 is the main category: its colour is the event's colour in the calendar.
    position: Mapped[int] = mapped_column(Integer, default=0)


class Event(Base):
    __tablename__ = "event"
    __table_args__ = (
        Index("ix_event_start_date", "start_date"),
        Index("ix_event_end_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[dt.date] = mapped_column(Date)
    end_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    place: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now, onupdate=now)

    group_links: Mapped[list[EventGroup]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, lazy="selectin"
    )
    category_links: Mapped[list[EventCategory]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by=EventCategory.position,
    )

    @property
    def group_ids(self) -> list[int]:
        return sorted(link.group_id for link in self.group_links)

    @property
    def category_ids(self) -> list[int]:
        """In the user's order: the first is the main category."""
        return [link.category_id for link in self.category_links]


class Setting(Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)


class Asset(Base):
    __tablename__ = "asset"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    mime: Mapped[str] = mapped_column(String(64))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now, onupdate=now)
