"""Analytics and settings endpoint tests.

The revenue figures matter: an admin dashboard that overstates income by
counting unpaid orders is worse than one showing nothing, because it looks
authoritative. Several tests below exist specifically to pin that behaviour.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.order import Order, OrderStatusHistory
from tests.conftest import auth_headers


def _make_order(
    db,
    *,
    status="received",
    payment_status="paid",
    total="5000",
    days_ago=0,
    cloth_type="Dress",
    material="Cotton",
    number=None,
):
    order = Order(
        order_number=number or f"TC-TEST-{db.query(Order).count() + 1:05d}",
        guest_email="g@example.com",
        cloth_type_name=cloth_type,
        material_name=material,
        design_options_snapshot=[],
        measurements_snapshot={},
        fabric_metres_used=Decimal("2.00"),
        price_base=Decimal("1000"),
        price_stitching=Decimal("500"),
        price_material=Decimal("3150"),
        price_delivery=Decimal("350"),
        price_total=Decimal(total),
        price_breakdown=[],
        status=status,
        payment_status=payment_status,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )
    db.add(order)
    db.commit()
    return order


def _admin(client):
    return auth_headers(client, "admin@example.com", "adminpass123")


def test_summary_requires_admin(client, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    assert client.get("/api/admin/analytics/summary", headers=headers).status_code == 403


def test_summary_on_an_empty_database(client, admin_user):
    """A fresh deployment must render, not divide by zero."""
    resp = client.get("/api/admin/analytics/summary", headers=_admin(client))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_orders"] == 0
    assert Decimal(body["total_revenue"]) == 0
    assert Decimal(body["average_order_value"]) == 0
    assert body["average_fulfilment_days"] is None


def test_revenue_counts_only_paid_orders(client, admin_user, db_session):
    """Unpaid orders are not income. Counting them would inflate every figure
    on the dashboard while looking perfectly plausible."""
    _make_order(db_session, payment_status="paid", total="5000")
    _make_order(db_session, payment_status="pending", total="9999")
    _make_order(db_session, payment_status="failed", total="8888")

    body = client.get("/api/admin/analytics/summary", headers=_admin(client)).json()
    assert body["total_orders"] == 3
    assert body["paid_orders"] == 1
    assert Decimal(body["total_revenue"]) == Decimal("5000")


def test_average_order_value_uses_paid_orders_only(client, admin_user, db_session):
    _make_order(db_session, payment_status="paid", total="4000")
    _make_order(db_session, payment_status="paid", total="6000")
    _make_order(db_session, payment_status="pending", total="100000")

    body = client.get("/api/admin/analytics/summary", headers=_admin(client)).json()
    assert Decimal(body["average_order_value"]) == Decimal("5000.00")


def test_active_orders_exclude_terminal_states(client, admin_user, db_session):
    for status in ["received", "fabric_cut", "stitching", "qc"]:
        _make_order(db_session, status=status)
    _make_order(db_session, status="dispatched")
    _make_order(db_session, status="cancelled")

    body = client.get("/api/admin/analytics/summary", headers=_admin(client)).json()
    assert body["active_orders"] == 4
    assert body["dispatched_orders"] == 1
    assert body["cancelled_orders"] == 1


def test_fulfilment_time_measures_received_to_dispatched(client, admin_user, db_session):
    """Derived from status history rather than created_at/updated_at, so it
    reflects real production time instead of when a row was last touched."""
    order = _make_order(db_session, status="dispatched")
    start = datetime.now(UTC) - timedelta(days=6)
    db_session.add_all(
        [
            OrderStatusHistory(order_id=order.id, to_status="received", created_at=start),
            OrderStatusHistory(
                order_id=order.id, to_status="dispatched", created_at=start + timedelta(days=6)
            ),
        ]
    )
    db_session.commit()

    body = client.get("/api/admin/analytics/summary", headers=_admin(client)).json()
    assert body["average_fulfilment_days"] == 6.0


def test_fulfilment_time_ignores_orders_still_in_progress(client, admin_user, db_session):
    """Including unfinished orders would make fulfilment look faster than it is."""
    order = _make_order(db_session, status="stitching")
    db_session.add(
        OrderStatusHistory(
            order_id=order.id,
            to_status="received",
            created_at=datetime.now(UTC) - timedelta(days=30),
        )
    )
    db_session.commit()

    body = client.get("/api/admin/analytics/summary", headers=_admin(client)).json()
    assert body["average_fulfilment_days"] is None


def test_revenue_trend_is_zero_filled(client, admin_user, db_session):
    """Missing days must appear as zeros, or a chart's x-axis silently
    compresses and misrepresents the time period."""
    _make_order(db_session, payment_status="paid", total="5000", days_ago=3)

    body = client.get("/api/admin/analytics/revenue?days=7", headers=_admin(client)).json()
    assert len(body["trend"]) == 7
    assert sum(Decimal(d["revenue"]) for d in body["trend"]) == Decimal("5000")
    # Ascending, oldest first.
    dates = [d["date"] for d in body["trend"]]
    assert dates == sorted(dates)


def test_popular_lists_are_ranked_by_order_count(client, admin_user, db_session):
    for _ in range(3):
        _make_order(db_session, cloth_type="Dress")
    _make_order(db_session, cloth_type="Kurta")

    body = client.get("/api/admin/analytics/popular", headers=_admin(client)).json()
    assert body["cloth_types"][0]["name"] == "Dress"
    assert body["cloth_types"][0]["orders"] == 3


def test_status_breakdown_includes_statuses_with_no_orders(client, admin_user, db_session):
    """A fixed set keeps the chart stable between refreshes."""
    _make_order(db_session, status="received")
    body = client.get("/api/admin/analytics/status-breakdown", headers=_admin(client)).json()
    statuses = {s["status"] for s in body["statuses"]}
    assert statuses == {"received", "fabric_cut", "stitching", "qc", "dispatched", "cancelled"}


def test_combined_endpoint_returns_every_section(client, admin_user, db_session):
    _make_order(db_session)
    body = client.get("/api/admin/analytics", headers=_admin(client)).json()
    assert set(body) == {
        "summary",
        "revenue_trend",
        "popular_cloth_types",
        "popular_materials",
        "status_breakdown",
        "catalogue_health",
    }


def test_catalogue_health_flags_a_cloth_type_with_no_measurement_fields(client, admin_user, seeded_catalog):
    """This is a real misconfiguration: the wizard's Step 4 would be empty."""
    headers = _admin(client)
    client.post(
        "/api/admin/catalog/cloth-types",
        json={
            "slug": "waistcoat",
            "name": "Waistcoat",
            "base_price": "2500",
            "base_fabric_metres": "1.1",
            "ai_prompt_noun": "waistcoat",
        },
        headers=headers,
    )
    body = client.get("/api/admin/analytics/catalogue-health", headers=headers).json()
    assert "Waistcoat" in body["cloth_types_without_measurement_fields"]


# ── Settings ──────────────────────────────────────────────────────────────


def test_settings_require_admin(client, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    assert client.get("/api/admin/settings", headers=headers).status_code == 403


def test_update_a_numeric_setting(client, admin_user, db_session):
    from app.models.settings import AppSetting

    db_session.add(AppSetting(key="delivery_fee", value="350", value_type="number"))
    db_session.commit()

    resp = client.put("/api/admin/settings/delivery_fee", json={"value": "500"}, headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json()["value"] == "500"


def test_reject_a_non_numeric_value_for_a_numeric_setting(client, admin_user, db_session):
    """Without this the bad value only surfaces as a 500 on a customer's quote."""
    from app.models.settings import AppSetting

    db_session.add(AppSetting(key="delivery_fee", value="350", value_type="number"))
    db_session.commit()

    resp = client.put("/api/admin/settings/delivery_fee", json={"value": "abc"}, headers=_admin(client))
    assert resp.status_code == 400


def test_reject_inverted_size_factor_bounds(client, admin_user, db_session):
    """size_factor_min > 1 would collapse every quote to the minimum."""
    from app.models.settings import AppSetting

    db_session.add(AppSetting(key="size_factor_min", value="0.85", value_type="number"))
    db_session.commit()

    resp = client.put("/api/admin/settings/size_factor_min", json={"value": "1.5"}, headers=_admin(client))
    assert resp.status_code == 400


def test_updating_an_unknown_setting_404s(client, admin_user):
    resp = client.put("/api/admin/settings/nonexistent", json={"value": "1"}, headers=_admin(client))
    assert resp.status_code == 404
