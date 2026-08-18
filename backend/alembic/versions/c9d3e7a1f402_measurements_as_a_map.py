"""Store a customer's measurements as a key/value map.

`user_measurements` had eight fixed columns — bust, waist, hip, shoulder,
sleeve, total_length, chest, inseam — a leftover from the original prototype,
written before the catalogue became config-driven.

The seeded catalogue already uses **eighteen** distinct measurement keys across
its eight garments, so ten of them (collar, cuff, hem, kameez_length, knee,
leg_opening, neckline_depth, outseam, shalwar_length, thigh) had nowhere to go.
Worse, an admin adding a measurement field through the catalogue screen creates
a key no column exists for, so the fixed schema could never keep up by
construction.

Values move into a JSON map keyed by the catalogue's own `field_key`. Same
`JSON().with_variant(JSONB, "postgresql")` approach used by every other snapshot
column here, so CI keeps running on SQLite.

Zero values are dropped rather than carried over: the old columns defaulted to
0.0, so an untouched profile is eight zeros, and importing those would present
"0 cm" as if the customer had measured themselves.

Revision ID: c9d3e7a1f402
Revises: b2f1a9c4d7e3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

LEGACY_COLUMNS = (
    "bust",
    "waist",
    "hip",
    "shoulder",
    "sleeve",
    "total_length",
    "chest",
    "inseam",
)

revision: str = "c9d3e7a1f402"
down_revision: str | None = "b2f1a9c4d7e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_measurements",
        sa.Column("values", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True),
    )

    table = sa.table(
        "user_measurements",
        sa.column("id", sa.Integer),
        sa.column("values", sa.JSON),
        *[sa.column(name, sa.Float) for name in LEGACY_COLUMNS],
    )

    connection = op.get_bind()
    rows = connection.execute(sa.select(table.c.id, *[table.c[name] for name in LEGACY_COLUMNS]))
    for row in rows:
        mapping = row._mapping
        # A zero here means "never filled in", not "measured as zero".
        values = {name: float(mapping[name]) for name in LEGACY_COLUMNS if mapping[name]}
        connection.execute(sa.update(table).where(table.c.id == row.id).values(values=values))

    for name in LEGACY_COLUMNS:
        op.drop_column("user_measurements", name)


def downgrade() -> None:
    for name in LEGACY_COLUMNS:
        op.add_column("user_measurements", sa.Column(name, sa.Float, server_default="0"))
    op.drop_column("user_measurements", "values")
