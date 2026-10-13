# calendariParrocchia -- parish group calendars with printable A4 sheets
# SPDX-License-Identifier: GPL-3.0-or-later
"""Alembic environment: migrations run on the connection the program hands over.

``db/session.py`` opens the connection and puts it in ``config.attributes``;
there is no ``alembic.ini`` and no URL here. SQLite cannot alter most column
definitions in place, hence batch mode.
"""

from alembic import context

from cp.db.models import Base

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    target_metadata=Base.metadata,
    render_as_batch=True,
)
with context.begin_transaction():
    context.run_migrations()
