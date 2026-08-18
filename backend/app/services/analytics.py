"""Admin analytics.

All aggregation happens in SQL rather than by loading rows into Python, so
these stay fast as the order table grows.

Two deliberate choices worth knowing:

- **Only paid orders count toward revenue.** A pending order is not money, and
  counting it would overstate every revenue figure on the dashboard.
- **Average fulfilment time comes from order_status_history**, not from
  `created_at` to `updated_at`. That table records when each stage actually
  happened, so the number reflects real production time rather than whenever a
  row was last touched. This is the reason the history table exists.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Numeric, case, cast, func
from sqlalchemy.orm import Session

from app.models.catalog import ClothType, Material
from app.models.order import Order, OrderStatusHistory

# Statuses that represent an order still moving through production.
ACTIVE_STATUSES = ["received", "fabric_cut", "stitching", "qc"]


@dataclass
class Summary:
    total_orders: int
    paid_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    active_orders: int
    dispatched_orders: int
    cancelled_orders: int
    average_fulfilment_days: float | None
    low_stock_materials: int


def _utc_today() -> date:
    return datetime.now(UTC).date()


def get_summary(db: Session) -> Summary:
    total_orders = db.query(func.count(Order.id)).scalar() or 0

    paid_orders, total_revenue = (
        db.query(func.count(Order.id), func.coalesce(func.sum(Order.price_total), 0))
        .filter(Order.payment_status == "paid")
        .one()
    )
    total_revenue = Decimal(str(total_revenue or 0))
    average_order_value = (
        (total_revenue / paid_orders).quantize(Decimal("0.01")) if paid_orders else Decimal("0.00")
    )

    status_counts = dict(db.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    active = sum(status_counts.get(s, 0) for s in ACTIVE_STATUSES)

    low_stock = (
        db.query(func.count(Material.id))
        .filter(
            Material.is_active.is_(True),
            Material.stock_metres <= Material.low_stock_threshold,
        )
        .scalar()
        or 0
    )

    return Summary(
        total_orders=total_orders,
        paid_orders=paid_orders or 0,
        total_revenue=total_revenue,
        average_order_value=average_order_value,
        active_orders=active,
        dispatched_orders=status_counts.get("dispatched", 0),
        cancelled_orders=status_counts.get("cancelled", 0),
        average_fulfilment_days=get_average_fulfilment_days(db),
        low_stock_materials=low_stock,
    )


def get_average_fulfilment_days(db: Session) -> float | None:
    """Mean days from an order being received to being dispatched.

    Derived from the status history, so it measures actual production time.
    Orders still in progress are excluded — including them would drag the
    average down and make fulfilment look faster than it is.
    """
    received = (
        db.query(
            OrderStatusHistory.order_id.label("order_id"),
            func.min(OrderStatusHistory.created_at).label("at"),
        )
        .filter(OrderStatusHistory.to_status == "received")
        .group_by(OrderStatusHistory.order_id)
        .subquery()
    )
    dispatched = (
        db.query(
            OrderStatusHistory.order_id.label("order_id"),
            func.min(OrderStatusHistory.created_at).label("at"),
        )
        .filter(OrderStatusHistory.to_status == "dispatched")
        .group_by(OrderStatusHistory.order_id)
        .subquery()
    )

    pairs = (
        db.query(received.c.at, dispatched.c.at)
        .join(dispatched, dispatched.c.order_id == received.c.order_id)
        .all()
    )
    if not pairs:
        return None

    # Computed in Python because date arithmetic differs between SQLite and
    # Postgres, and the row count here is bounded by completed orders.
    spans = [
        (finished - started).total_seconds() / 86400
        for started, finished in pairs
        if started and finished and finished >= started
    ]
    return round(sum(spans) / len(spans), 2) if spans else None


def get_revenue_trend(db: Session, days: int = 30) -> list[dict]:
    """Daily paid revenue for the last `days` days, with zero-filled gaps.

    Gaps are filled so a chart shows a continuous line — without this, days
    with no orders are simply absent and the x-axis silently compresses.
    """
    since = datetime.now(UTC) - timedelta(days=days - 1)

    rows = (
        db.query(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.price_total), 0).label("revenue"),
        )
        .filter(Order.payment_status == "paid", Order.created_at >= since)
        .group_by(func.date(Order.created_at))
        .all()
    )

    by_day = {}
    for day, orders, revenue in rows:
        # SQLite returns a string from date(); Postgres returns a date object.
        key = day if isinstance(day, str) else day.isoformat()
        by_day[key] = {"orders": orders, "revenue": Decimal(str(revenue or 0))}

    today = _utc_today()
    trend = []
    for offset in range(days - 1, -1, -1):
        key = (today - timedelta(days=offset)).isoformat()
        entry = by_day.get(key, {"orders": 0, "revenue": Decimal("0")})
        trend.append({"date": key, "orders": entry["orders"], "revenue": str(entry["revenue"])})
    return trend


def get_weekly_orders(db: Session, weeks: int = 8) -> list[dict]:
    """Orders and revenue bucketed into the last `weeks` calendar weeks.

    Weeks are derived from the daily series rather than grouped in SQL, because
    the week-number functions differ between SQLite (`strftime('%W')`) and
    PostgreSQL (`date_trunc`) — and CI runs on SQLite while production runs on
    Postgres, so a SQL-side grouping would be untested in exactly the
    environment it ships to.

    Counts every order, not just paid ones: this answers "how much work came
    in", which is a production-planning question, unlike the revenue series
    where an unpaid order is not income.
    """
    days = weeks * 7
    since = datetime.now(UTC) - timedelta(days=days - 1)

    rows = (
        db.query(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("orders"),
            func.coalesce(
                func.sum(case((Order.payment_status == "paid", Order.price_total), else_=0)), 0
            ).label("revenue"),
        )
        .filter(Order.created_at >= since)
        .group_by(func.date(Order.created_at))
        .all()
    )

    by_day = {}
    for day, orders, revenue in rows:
        key = day if isinstance(day, str) else day.isoformat()
        by_day[key] = (orders, Decimal(str(revenue or 0)))

    today = _utc_today()
    buckets = []
    for index in range(weeks - 1, -1, -1):
        end = today - timedelta(days=index * 7)
        start = end - timedelta(days=6)
        orders = 0
        revenue = Decimal("0")
        for offset in range(7):
            day_orders, day_revenue = by_day.get(
                (start + timedelta(days=offset)).isoformat(), (0, Decimal("0"))
            )
            orders += day_orders
            revenue += day_revenue
        buckets.append(
            {
                "week_start": start.isoformat(),
                "week_end": end.isoformat(),
                "label": start.strftime("%d %b"),
                "orders": orders,
                "revenue": str(revenue),
            }
        )
    return buckets


def get_popular_cloth_types(db: Session, limit: int = 8) -> list[dict]:
    rows = (
        db.query(
            Order.cloth_type_name,
            func.count(Order.id).label("orders"),
            func.coalesce(
                func.sum(case((Order.payment_status == "paid", Order.price_total), else_=0)),
                0,
            ).label("revenue"),
        )
        .group_by(Order.cloth_type_name)
        .order_by(func.count(Order.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {"name": name, "orders": orders, "revenue": str(Decimal(str(revenue or 0)))}
        for name, orders, revenue in rows
    ]


def get_popular_materials(db: Session, limit: int = 8) -> list[dict]:
    rows = (
        db.query(
            Order.material_name,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(cast(Order.fabric_metres_used, Numeric)), 0).label("metres"),
        )
        .group_by(Order.material_name)
        .order_by(func.count(Order.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {"name": name, "orders": orders, "metres_used": str(Decimal(str(metres or 0)))}
        for name, orders, metres in rows
    ]


def get_status_breakdown(db: Session) -> list[dict]:
    counts = dict(db.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    # Fixed order so the chart doesn't reshuffle between refreshes, and statuses
    # with no orders still appear rather than vanishing.
    ordered = ["received", "fabric_cut", "stitching", "qc", "dispatched", "cancelled"]
    return [{"status": status, "count": counts.get(status, 0)} for status in ordered]


def get_catalogue_health(db: Session) -> dict:
    """Configuration completeness — surfaces a cloth type that would break the
    wizard because nobody added its measurement fields."""
    cloth_types = db.query(ClothType).filter(ClothType.is_active.is_(True)).all()
    missing_fields = [c.name for c in cloth_types if not c.measurement_fields]
    return {
        "active_cloth_types": len(cloth_types),
        "cloth_types_without_measurement_fields": missing_fields,
        "active_materials": db.query(func.count(Material.id)).filter(Material.is_active.is_(True)).scalar()
        or 0,
    }
