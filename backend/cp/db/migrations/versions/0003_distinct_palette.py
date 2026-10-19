# calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Categories still on a colour of the first palette move to the new one (SPEC §6.2).

The first palette handed out neighbouring hues one after the other (red,
orange, ochre, green, teal): on paper the first categories looked alike. Every
category whose colour came from it is given, in list order, the first colour of
the new palette that no category uses yet; colours chosen freely stay. Both
palettes are written out here: the migration must not follow later changes.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

OLD = (
    "#E63946",
    "#F4A261",
    "#E9C46A",
    "#43AA8B",
    "#2A9D8F",
    "#00A6ED",
    "#277DA1",
    "#577590",
    "#9B5DE5",
    "#F15BB5",
    "#8D6E63",
    "#6C757D",
)
NEW = (
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
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, color FROM category ORDER BY position, id")).all()
    used = {color for _, color in rows if color not in OLD}
    for category_id, color in rows:
        if color not in OLD:
            continue
        # With more than twelve to recolour, the same old colour gives the same new one.
        new = next((c for c in NEW if c not in used), NEW[OLD.index(color)])
        used.add(new)
        connection.execute(
            sa.text("UPDATE category SET color = :color WHERE id = :id"),
            {"color": new, "id": category_id},
        )


def downgrade() -> None:
    # The old colours are not kept anywhere: the categories stay as they are.
    pass
