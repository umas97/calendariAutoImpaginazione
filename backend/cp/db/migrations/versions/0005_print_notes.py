# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Per event, whether its notes are printed on the exported sheets (SPEC §7.1, §8.3).

Existing events keep their notes internal: the switch starts off.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A plain ALTER TABLE: SQLite adds the column in place. Batch mode would
    # rebuild the table, dropping the old one.
    op.add_column(
        "event", sa.Column("print_notes", sa.Boolean, nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    with op.batch_alter_table("event") as batch:
        batch.drop_column("print_notes")
