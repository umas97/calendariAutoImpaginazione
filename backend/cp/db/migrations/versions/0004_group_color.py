# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Groups get a colour: the bars and legend of a sheet per category (SPEC §6.2, §8.3).

Existing groups take the palette in list order, archived ones included, and
start again from the first colour after the twelfth. The palette is written out
here: the migration must not follow later changes.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

PALETTE = (
    "#1976D2",
    "#D32F2F",
    "#2E7D32",
    "#F57C00",
    "#8E24AA",
    "#00838F",
    "#C2185B",
    "#6D4C41",
    "#FBC02D",
    "#283593",
    "#C0CA33",
    "#757575",
)


def upgrade() -> None:
    with op.batch_alter_table("group") as batch:
        batch.add_column(
            sa.Column("color", sa.String(7), nullable=False, server_default=PALETTE[0])
        )
    connection = op.get_bind()
    ids = connection.execute(sa.text('SELECT id FROM "group" ORDER BY position, id')).scalars()
    for index, group_id in enumerate(list(ids)):
        connection.execute(
            sa.text('UPDATE "group" SET color = :color WHERE id = :id'),
            {"color": PALETTE[index % len(PALETTE)], "id": group_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("group") as batch:
        batch.drop_column("color")
