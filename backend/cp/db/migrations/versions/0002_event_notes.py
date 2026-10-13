# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Internal notes on events: seen only in the program, never exported (SPEC §7.1).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("event") as batch:
        batch.add_column(sa.Column("notes", sa.Text, nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("event") as batch:
        batch.drop_column("notes")
