"""Track stock per colourway rather than per material.

A tailor does not run out of "silk", they run out of burgundy silk. Stock lived
on `materials`, so the admin could see 42 m of silk remaining with no way to
know it was all ivory — and an order for burgundy would be accepted against it.

Backfill splits each material's existing stock evenly across its active
colours. That is an assumption, not a measurement: there is no record of the
real per-colour split, and dividing is the only distribution that preserves the
material total. The admin inventory screen exists precisely so these can be
corrected to the real counts.

Revision ID: b2f1a9c4d7e3
Revises: 724c990b797a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2f1a9c4d7e3"
down_revision: str | None = "724c990b797a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "material_colors",
        sa.Column("stock_metres", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "material_colors",
        sa.Column("low_stock_threshold", sa.Numeric(10, 2), nullable=False, server_default="5"),
    )

    # Split each material's stock evenly across its active colours. Written as
    # a correlated UPDATE so it works identically on SQLite and PostgreSQL.
    op.execute(
        """
        UPDATE material_colors
           SET stock_metres = COALESCE((
                   SELECT m.stock_metres / (
                       SELECT COUNT(*) FROM material_colors c
                        WHERE c.material_id = m.id AND c.is_active = 1
                   )
                     FROM materials m
                    WHERE m.id = material_colors.material_id
               ), 0)
         WHERE is_active = 1
        """
    )
    op.execute(
        """
        UPDATE material_colors
           SET low_stock_threshold = COALESCE((
                   SELECT m.low_stock_threshold / (
                       SELECT COUNT(*) FROM material_colors c
                        WHERE c.material_id = m.id AND c.is_active = 1
                   )
                     FROM materials m
                    WHERE m.id = material_colors.material_id
               ), 5)
         WHERE is_active = 1
        """
    )


def downgrade() -> None:
    op.drop_column("material_colors", "low_stock_threshold")
    op.drop_column("material_colors", "stock_metres")
