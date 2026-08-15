import secrets
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatusHistory

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


def transition_status(
    db: Session,
    order: Order,
    to_status: str,
    changed_by_user_id: int | None = None,
    note: str | None = None,
) -> None:
    """Validated state change — use this for every admin-driven status update.
    Raises InvalidStatusTransition on any backwards/skipped/terminal move."""
    validate_transition(order.status, to_status)
    record_status_change(db, order, to_status, changed_by_user_id=changed_by_user_id, note=note)
