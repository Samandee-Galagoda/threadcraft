"""Give each material a photographic swatch.

Materials were shown as CSS gradients — `linear-gradient(135deg,#e8ddf0,#d4c8e8)`
for silk, a flat beige for cotton. Those distinguish the *colours* of the
catalogue but not the fabrics: a customer choosing between chiffon and satin was
picking between two pale rectangles, and the whole point of the material step is
deciding what the garment will feel and drape like.

The gradient stays as `swatch_css` and remains the fallback, so a material
without a photograph still renders rather than showing a broken image — and an
admin adding a fabric gets something usable before they have a photo for it.

Revision ID: f7c1d40e2b83
Revises: e6b2f9d3a710
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7c1d40e2b83"
down_revision: str | None = "e6b2f9d3a710"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Shipped with the frontend, so they are referenced by path rather than uploaded.
SWATCHES = ("cotton", "linen", "silk", "chiffon", "satin", "denim", "velvet")


def upgrade() -> None:
    op.add_column("materials", sa.Column("swatch_image_url", sa.String(500), nullable=True))

    materials = sa.table(
        "materials",
        sa.column("slug", sa.String),
        sa.column("swatch_image_url", sa.String),
    )
    connection = op.get_bind()
    for slug in SWATCHES:
        connection.execute(
            sa.update(materials)
            .where(materials.c.slug == slug)
            .values(swatch_image_url=f"/img/materials/{slug}.jpg")
        )


def downgrade() -> None:
    op.drop_column("materials", "swatch_image_url")
