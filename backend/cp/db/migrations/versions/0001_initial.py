# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Initial schema: groups, categories, events and their links, settings, assets.

Revision ids are plain numbers: the newest one is the ``schema_version`` that a
backup is compared against (SPEC §10.4).

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("name_key", sa.String(60), nullable=False, unique=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("archived", sa.Boolean, nullable=False),
    )
    op.create_table(
        "category",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("name_key", sa.String(60), nullable=False, unique=True),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("archived", sa.Boolean, nullable=False),
    )
    op.create_table(
        "event",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("all_day", sa.Boolean, nullable=False),
        sa.Column("start_time", sa.String(5), nullable=True),
        sa.Column("end_time", sa.String(5), nullable=True),
        sa.Column("place", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_event_start_date", "event", ["start_date"])
    op.create_index("ix_event_end_date", "event", ["end_date"])
    op.create_table(
        "event_group",
        sa.Column(
            "event_id",
            sa.Integer,
            sa.ForeignKey("event.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("group.id"), primary_key=True),
    )
    op.create_index("ix_event_group_group_id", "event_group", ["group_id"])
    op.create_table(
        "event_category",
        sa.Column(
            "event_id",
            sa.Integer,
            sa.ForeignKey("event.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("category.id"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False),
    )
    op.create_index("ix_event_category_category_id", "event_category", ["category_id"])
    op.create_table(
        "setting",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.JSON, nullable=False),
    )
    op.create_table(
        "asset",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("mime", sa.String(64), nullable=False),
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    for table in ("asset", "setting", "event_category", "event_group", "event"):
        op.drop_table(table)
    op.drop_table("category")
    op.drop_table("group")
