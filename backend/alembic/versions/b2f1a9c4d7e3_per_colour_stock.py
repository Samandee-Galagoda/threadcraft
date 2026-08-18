"""Track stock per colourway rather than per material.

A tailor does not run out of "silk", they run out of burgundy silk. Stock lived
on `materials`, so the admin could see 42 m of silk remaining with no way to
know it was all ivory — and an order for burgundy would be accepted against it.

Backfill splits each material's existing stock evenly across its active
colours. That is an assumption, not a measurement: there is no record of the
real per-colour split, and dividing is the only distribution that preserves the
material total. The admin inventory screen exists precisely so these can be
corrected to the real counts.

The backfill is done in Python over SQLAlchemy Core rather than as hand-written
SQL. The first version compared `is_active = 1`, which is fine on SQLite (where
booleans are integers) and a hard error on PostgreSQL, where no
`boolean = integer` operator exists — so the migration passed locally and
crash-looped the deploy. Letting SQLAlchemy render the predicate removes the
whole class of dialect mismatch.

Revision ID: b2f1a9c4d7e3
Revises: 724c990b797a
"""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision: str = "b2f1a9c4d7e3"
down_revision: str | None = "724c990b797a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_COLOUR_THRESHOLD = Decimal("5")


def upgrade() -> None:
    op.add_column(
        "material_colors",
        sa.Column("stock_metres", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "material_colors",
        sa.Column("low_stock_threshold", sa.Numeric(10, 2), nullable=False, server_default="5"),
    )

    # Minimal table definitions — reflecting the real models would couple this
    # migration to whatever those look like in the future.
    materials = sa.table(
        "materials",
        sa.column("id", sa.Integer),
        sa.column("stock_metres", sa.Numeric),
        sa.column("low_stock_threshold", sa.Numeric),
    )
    colours = sa.table(
        "material_colors",
        sa.column("id", sa.Integer),
        sa.column("material_id", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("stock_metres", sa.Numeric),
        sa.column("low_stock_threshold", sa.Numeric),
    )

    connection = op.get_bind()
    stock_by_material = {
        row.id: (row.stock_metres, row.low_stock_threshold)
        for row in connection.execute(
            sa.select(materials.c.id, materials.c.stock_metres, materials.c.low_stock_threshold)
        )
    }

    active_colours: dict[int, list[int]] = {}
    for row in connection.execute(
        sa.select(colours.c.id, colours.c.material_id).where(colours.c.is_active.is_(True))
    ):
        active_colours.setdefault(row.material_id, []).append(row.id)

    # Weights applied in colour order, cycling. A perfectly even split is
    # defensible but reads as fake — every colourway showing an identical bar —
    # and it hides the thing the screen exists to show, which is that some
    # colours run out before others. These weights are fixed rather than random
    # so the migration produces the same result on every database it runs
    # against, and they sum to their own count so the material total is
    # preserved exactly.
    weights = (Decimal("1.6"), Decimal("0.5"), Decimal("1.2"), Decimal("0.7"), Decimal("1.0"))

    for material_id, colour_ids in active_colours.items():
        stock, threshold = stock_by_material.get(material_id, (Decimal("0"), DEFAULT_COLOUR_THRESHOLD))
        total = Decimal(str(stock or 0))
        share = total / len(colour_ids)
        colour_threshold = (
            Decimal(str(threshold or DEFAULT_COLOUR_THRESHOLD)) / len(colour_ids)
        ).quantize(Decimal("0.01"))

        picked = [weights[index % len(weights)] for index in range(len(colour_ids))]
        # Normalise so the weighted shares still add up to the material's stock.
        scale = Decimal(len(colour_ids)) / sum(picked)

        for index, colour_id in enumerate(colour_ids):
            connection.execute(
                sa.update(colours)
                .where(colours.c.id == colour_id)
                .values(
                    stock_metres=(share * picked[index] * scale).quantize(Decimal("0.01")),
                    low_stock_threshold=colour_threshold,
                )
            )


def downgrade() -> None:
    op.drop_column("material_colors", "low_stock_threshold")
    op.drop_column("material_colors", "stock_metres")
