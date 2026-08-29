"""Scope the design tags to the garment they belong on.

All four tag groups — Fit, Neckline, Sleeve, Pattern — were seeded with
`cloth_type_id = NULL`, which the catalogue serves to every cloth type. So the
wizard asked someone designing trousers to choose a neckline and a sleeve
length, and the prompt builder passed both to the image model. A skirt was
offered a collar. The schema has supported per-garment groups since it was
written; nothing had ever used it.

After this:

  - Fit and Pattern stay global. They apply to anything made of fabric.
  - Neckline and Sleeve stop being global and are recreated per garment, with
    vocabulary suited to each — a t-shirt gets a crew neck and a henley, a
    dress gets a sweetheart and a halter.
  - Garments that had no relevant group gain one: trousers get a leg cut, a
    rise and a waistband; a skirt gets a shape, a length and a waistband; a
    saree blouse gets a back style; a salwar kameez gets a salwar style.

**On existing orders.** Nothing is lost. An order records its design choices as
a snapshot of codes and labels (`design_options_snapshot`), not as foreign keys,
so past orders read exactly as they did before. The reorder endpoint resolves
those snapshot codes against the live catalogue and already names anything it
cannot find in `unavailable`, so a reordered garment whose sleeve option moved
is reported rather than silently altered.

**On admin edits.** The old global Neckline and Sleeve groups are deleted, and
their options with them via the cascade. An administrator who had retuned a
premium on one of those options loses that edit — worth stating plainly. The
groups being replaced are the seeded ones, and the tags each garment now offers
differ enough that merging the old rows in would have produced a worse
catalogue than rebuilding it.

Revision ID: a1f5c83d7b02
Revises: f7c1d40e2b83
"""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa

from alembic import op

# Imported rather than copied: 130 options duplicated into this file would be a
# second place to get them wrong. The trade-off is that this migration reflects
# the module as it stands rather than as it stood when written — acceptable
# because it runs once, against a database holding the four original global
# groups, and any database created after it is seeded from the same module.
from app.db.design_tags import CLOTH_TYPE_GROUPS, GLOBAL_GROUPS

revision: str = "a1f5c83d7b02"
down_revision: str | None = "f7c1d40e2b83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

groups_table = sa.table(
    "design_option_groups",
    sa.column("id", sa.Integer),
    sa.column("cloth_type_id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("label", sa.String),
    sa.column("selection_type", sa.String),
    sa.column("is_required", sa.Boolean),
    sa.column("sort_order", sa.Integer),
    sa.column("is_active", sa.Boolean),
)

options_table = sa.table(
    "design_options",
    sa.column("id", sa.Integer),
    sa.column("group_id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("label", sa.String),
    sa.column("ai_prompt_term", sa.String),
    sa.column("stitching_premium", sa.Numeric),
    sa.column("fabric_multiplier", sa.Numeric),
    sa.column("sort_order", sa.Integer),
    sa.column("is_active", sa.Boolean),
)

# The two that were never garment-agnostic.
SCOPED_AWAY = ("neckline", "sleeve")


def _insert_group(bind, *, cloth_type_id, code, label, options, sort_order):
    result = bind.execute(
        groups_table.insert()
        .values(
            cloth_type_id=cloth_type_id,
            code=code,
            label=label,
            selection_type="single",
            is_required=False,
            sort_order=sort_order,
            is_active=True,
        )
        .returning(groups_table.c.id)
    )
    group_id = result.scalar_one()
    bind.execute(
        options_table.insert(),
        [
            {
                "group_id": group_id,
                "code": opt_code,
                "label": opt_label,
                "ai_prompt_term": prompt_term,
                "stitching_premium": Decimal(premium),
                "fabric_multiplier": Decimal(str(multiplier)),
                "sort_order": index,
                "is_active": True,
            }
            for index, (opt_code, opt_label, prompt_term, premium, multiplier) in enumerate(options)
        ],
    )


def upgrade() -> None:
    bind = op.get_bind()

    # Drop the global groups that were never universal. design_options cascades
    # on the foreign key, so their options go with them.
    bind.execute(
        groups_table.delete().where(
            groups_table.c.cloth_type_id.is_(None),
            groups_table.c.code.in_(SCOPED_AWAY),
        )
    )

    cloth_type_ids = dict(bind.execute(sa.text("SELECT slug, id FROM cloth_types")).all())

    for slug, groups in CLOTH_TYPE_GROUPS.items():
        cloth_type_id = cloth_type_ids.get(slug)
        # A catalogue that has withdrawn a garment simply has nothing to attach.
        if cloth_type_id is None:
            continue
        for order, (code, label, options) in enumerate(groups):
            _insert_group(
                bind,
                cloth_type_id=cloth_type_id,
                code=code,
                label=label,
                options=options,
                sort_order=len(GLOBAL_GROUPS) + order,
            )


def downgrade() -> None:
    """Put the two global groups back and remove the per-garment ones.

    The restored Neckline and Sleeve lists are the union used across garments,
    which is close to but not identical to the original seeded pair — the
    original rows were deleted, and a downgrade cannot invent the premiums an
    administrator may since have tuned.
    """
    bind = op.get_bind()

    bind.execute(groups_table.delete().where(groups_table.c.cloth_type_id.isnot(None)))

    restored = {
        "neckline": [
            ("v_neck", "V-neck", "V-neck", 0, 1.00),
            ("round_neck", "Round neck", "round neckline", 0, 1.00),
            ("square_neck", "Square neck", "square neckline", 50, 1.00),
            ("off_shoulder", "Off-shoulder", "off-shoulder neckline", 200, 1.05),
            ("collar", "Collar", "collared neckline", 150, 1.05),
            ("halter", "Halter", "halter neckline", 200, 1.03),
        ],
        "sleeve": [
            ("sleeveless", "Sleeveless", "sleeveless", 0, 0.90),
            ("short_sleeve", "Short sleeve", "short sleeves", 0, 1.00),
            ("three_quarter_sleeve", "3/4 sleeve", "three-quarter length sleeves", 100, 1.08),
            ("long_sleeve", "Long sleeve", "long sleeves", 150, 1.15),
            ("puffed_sleeve", "Puffed sleeve", "puffed sleeves", 300, 1.20),
            ("bell_sleeve", "Bell sleeve", "flowing bell sleeves", 350, 1.22),
        ],
    }
    for order, (code, options) in enumerate(restored.items()):
        _insert_group(
            bind,
            cloth_type_id=None,
            code=code,
            label=code.title(),
            options=options,
            sort_order=order + 1,
        )
