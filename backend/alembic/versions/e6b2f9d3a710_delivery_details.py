"""Capture the delivery details an order actually needs.

An order carried an email and optionally a name. Nothing recorded *where* the
garment should be sent or how to reach the customer about it — the checkout
took payment for a physical item with no address attached, which the admin
order screen then could not show because it was never asked for.

`guest_name` is widened into `customer_name` and applies to signed-in customers
too: the name on the parcel is not necessarily the name on the account.

Deliberately absent: anything resembling card data. Card details are handled by
Stripe in production and are never sent to this server, so there is no column
here for them and no possibility of one being filled in by accident.

Revision ID: e6b2f9d3a710
Revises: d4a8b1c6e905
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6b2f9d3a710"
down_revision: str | None = "d4a8b1c6e905"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("customer_name", sa.String(200), nullable=True))
    op.add_column("orders", sa.Column("customer_phone", sa.String(40), nullable=True))
    op.add_column("orders", sa.Column("delivery_address", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("delivery_city", sa.String(120), nullable=True))
    op.add_column("orders", sa.Column("delivery_postcode", sa.String(20), nullable=True))

    orders = sa.table(
        "orders",
        sa.column("customer_name", sa.String),
        sa.column("guest_name", sa.String),
    )
    # Carry across what was already recorded rather than losing it.
    op.get_bind().execute(
        sa.update(orders)
        .where(orders.c.guest_name.isnot(None))
        .values(customer_name=orders.c.guest_name)
    )


def downgrade() -> None:
    for column in (
        "delivery_postcode",
        "delivery_city",
        "delivery_address",
        "customer_phone",
        "customer_name",
    ):
        op.drop_column("orders", column)
