import secrets
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.catalog import Material
from app.models.order import Order, OrderStatusHistory

# Cancelling after this stage no longer returns fabric to stock — by then it
# has been cut and cannot go back on the roll.
_STAGE_FABRIC_IS_CUT = "fabric_cut"

# Forward-only fulfilment workflow. 'cancelled' is reachable from any
# non-terminal state; nothing is reachable from a terminal state.
_STATUS_ORDER = ["received", "fabric_cut", "stitching", "qc", "dispatched"]
_TERMINAL_STATES = {"dispatched", "cancelled"}


class InvalidStatusTransition(Exception):
    pass


def next_valid_statuses(current: str) -> list[str]:
    if current in _TERMINAL_STATES:
        return []
    idx = _STATUS_ORDER.index(current)
    options = []
    if idx + 1 < len(_STATUS_ORDER):
        options.append(_STATUS_ORDER[idx + 1])
    options.append("cancelled")
    return options


def validate_transition(current: str, target: str) -> None:
    if target not in next_valid_statuses(current):
        raise InvalidStatusTransition(f"Cannot move an order from '{current}' to '{target}'")


def generate_order_number() -> str:
    year = datetime.now(UTC).year
    suffix = secrets.token_hex(3).upper()  # 6 hex chars, effectively unguessable
    return f"TC-{year}-{suffix}"


def record_status_change(
    db: Session,
    order: Order,
    to_status: str,
    changed_by_user_id: int | None = None,
    note: str | None = None,
) -> None:
    """Low-level: records a history row and sets the status, with NO transition
    validation. Used for establishing initial state (order creation, seeding).
    Anything moving an order from one real state to another must go through
    transition_status() below instead."""
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=to_status,
            changed_by_user_id=changed_by_user_id,
            note=note,
        )
    )
    order.status = to_status


def return_fabric_to_stock(db: Session, order: Order) -> Decimal:
    """Put an order's fabric back on the roll. Returns the metres restored.

    Order creation decrements stock, and until now nothing ever reversed it:
    a cancelled order permanently consumed cloth that was never cut, so stock
    drifted downward with every cancellation and the low-stock alert fired on
    fabric that was still sitting there.

    Only meaningful before the fabric is actually cut. Cancelling later is a
    write-off, not a restock, so the metres stay consumed.
    """
    if order.status != "received":
        return Decimal("0")

    material = db.query(Material).filter(Material.id == order.material_id).first()
    if not material:  # material hard-deleted out from under a live order
        return Decimal("0")

    metres = Decimal(str(order.fabric_metres_used or 0))
    material.stock_metres = Decimal(str(material.stock_metres)) + metres
    return metres


def transition_status(
    db: Session,
    order: Order,
    to_status: str,
    changed_by_user_id: int | None = None,
    note: str | None = None,
) -> None:
    """Validated state change — use this for every status update, admin or
    customer. Raises InvalidStatusTransition on any backwards/skipped/terminal
    move.

    Stock restoration lives here rather than in the routers so that it cannot
    be forgotten by whichever surface cancels next; `cancelled` being terminal
    is what makes it safe to do unconditionally, since an order can never be
    cancelled twice.
    """
    validate_transition(order.status, to_status)
    if to_status == "cancelled":
        return_fabric_to_stock(db, order)
    record_status_change(db, order, to_status, changed_by_user_id=changed_by_user_id, note=note)
