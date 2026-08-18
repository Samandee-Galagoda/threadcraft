"""Correct the measurement ranges to published body-measurement charts.

The seeded bounds were far too wide at the bottom end, and the cause was a unit
slip: real garment sizing is quoted in inches — denim waists start at 26-28",
bra bands at 28" — and those numbers had been carried across as if they were
centimetres. The result was minimums no adult body reaches:

    waist  50 cm = 20"   (smallest published women's UK 4 is 58 cm)
    chest  60 cm = 24"   (men's XS is 32" = 81 cm)
    bust   65 cm = 26"   (UK 4 is 76 cm)
    hip    70 cm = 28"   (UK 4 is 82 cm)

Nothing was rejected by this — the bounds only widened what the validator would
accept — but a guide that prints "50-130 cm" as the typical waist is telling a
customer something untrue, and the wizard would happily take a 20-inch waist
without comment.

New bounds span women's UK 4 to roughly UK 32 and men's XS to 5XL, so the same
body part carries the same range on every garment it appears on.

Only rows still holding the old seeded value are updated. An admin who has
deliberately retuned a range through the catalogue screen keeps their change.

Revision ID: d4a8b1c6e905
Revises: c9d3e7a1f402
"""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision: str = "d4a8b1c6e905"
down_revision: str | None = "c9d3e7a1f402"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (field_key, old_min, old_max) -> (new_min, new_max)
CORRECTIONS = {
    ("bust", 65, 140): (76, 150),
    ("bust", 65, 145): (76, 150),
    ("chest", 60, 140): (76, 150),
    ("chest", 70, 150): (76, 150),
    ("waist", 50, 120): (58, 135),
    ("waist", 50, 130): (58, 135),
    ("waist", 50, 135): (58, 135),
    ("hip", 70, 155): (82, 160),
    ("hip", 70, 160): (82, 160),
    ("shoulder", 28, 58): (32, 56),
    ("shoulder", 28, 60): (32, 56),
    ("shoulder", 32, 62): (32, 56),
    ("collar", 30, 52): (32, 52),
    ("thigh", 40, 100): (42, 90),
    ("knee", 30, 60): (30, 55),
    ("leg_opening", 25, 60): (28, 70),
    ("inseam", 50, 100): (60, 95),
    ("outseam", 80, 130): (85, 125),
    ("hem", 0, 300): (50, 300),
    ("neckline_depth", 4, 22): (2, 25),
    ("kameez_length", 80, 130): (80, 135),
    ("shalwar_length", 80, 115): (85, 115),
    # Lengths differ legitimately by garment, so these are keyed by their old
    # pair rather than by field name alone.
    ("total_length", 40, 165): (80, 165),  # dress: 40 cm is a crop top, not a dress
    ("total_length", 50, 90): (55, 90),  # t-shirt
    ("total_length", 25, 120): (30, 120),  # skirt
    ("total_length", 70, 120): (70, 130),  # kurta
}


def _apply(mapping: dict) -> None:
    fields = sa.table(
        "measurement_fields",
        sa.column("id", sa.Integer),
        sa.column("field_key", sa.String),
        sa.column("min_value", sa.Numeric),
        sa.column("max_value", sa.Numeric),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(fields.c.id, fields.c.field_key, fields.c.min_value, fields.c.max_value)
    )
    for row in rows:
        key = (row.field_key, int(Decimal(str(row.min_value))), int(Decimal(str(row.max_value))))
        target = mapping.get(key)
        if not target:
            continue
        connection.execute(
            sa.update(fields)
            .where(fields.c.id == row.id)
            .values(min_value=Decimal(target[0]), max_value=Decimal(target[1]))
        )


def upgrade() -> None:
    _apply(CORRECTIONS)


def downgrade() -> None:
    # Not reversible in general: several old ranges collapse onto one new range
    # (three different `shoulder` bounds all became 32-56), so the original
    # value cannot be recovered from the new one.
    pass
