"""Customer-initiated cancellation, and the stock that goes with it.

Two things are being established here.

The feature: only an admin could cancel, so a customer who ordered by mistake
had no recourse in the product at all.

The bug it exposed: order creation decrements stock and *nothing* ever put it
back. Every cancelled order — including every admin cancellation already
shipped — permanently consumed fabric that was never cut, so stock drifted down
and the low-stock alert fired on cloth still sitting on the shelf.
"""

from decimal import Decimal

from tests.conftest import auth_headers


def _payload(seeded_catalog, **overrides):
    payload = {
        "cloth_type_id": seeded_catalog["cloth_type"].id,
        "material_id": seeded_catalog["material"].id,
        "material_color_id": seeded_catalog["color"].id,
        "design_option_ids": [],
        "measurements": {"chest": 96},
    }
    payload.update(overrides)
    return payload


def _stock(db_session, colour_id):
    """Stock is held on the colourway, so that is what a cancellation must
    credit back."""
    from app.models.catalog import MaterialColor

    db_session.expire_all()
    return Decimal(
        str(db_session.query(MaterialColor).filter(MaterialColor.id == colour_id).first().stock_metres)
    )


# ── stock restoration ────────────────────────────────────────────────────────


def test_cancelling_returns_the_fabric_to_stock(client, seeded_catalog, db_session):
    material_id = seeded_catalog["color"].id
    before = _stock(db_session, material_id)

    order = client.post("/api/orders", json=_payload(seeded_catalog, guest_email="guest@example.com")).json()
    assert _stock(db_session, material_id) == before - Decimal("1.40")

    resp = client.post(
        f"/api/orders/{order['order_number']}/cancel",
        json={"guest_email": "guest@example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert _stock(db_session, material_id) == before


def test_admin_cancellation_also_returns_stock(client, seeded_catalog, admin_user, db_session):
    """The restock lives in transition_status rather than in either router, so
    it cannot be implemented for one cancellation surface and forgotten by the
    other. This asserts the admin path gets it for free."""
    from app.models.order import Order

    material_id = seeded_catalog["color"].id
    before = _stock(db_session, material_id)

    order_number = client.post(
        "/api/orders", json=_payload(seeded_catalog, guest_email="guest@example.com")
    ).json()["order_number"]
    order_id = db_session.query(Order).filter(Order.order_number == order_number).first().id

    client.patch(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "cancelled"},
        headers=auth_headers(client, "admin@example.com", "adminpass123"),
    )
    assert _stock(db_session, material_id) == before


def test_cancelling_after_cutting_does_not_restock(client, seeded_catalog, admin_user, db_session):
    """Cloth already cut cannot go back on the roll, so a late cancellation is
    a write-off. Restocking it would silently inflate inventory."""
    from app.models.order import Order

    material_id = seeded_catalog["color"].id
    headers = auth_headers(client, "admin@example.com", "adminpass123")

    order_number = client.post(
        "/api/orders", json=_payload(seeded_catalog, guest_email="guest@example.com")
    ).json()["order_number"]
    order_id = db_session.query(Order).filter(Order.order_number == order_number).first().id

    client.patch(f"/api/admin/orders/{order_id}/status", json={"status": "fabric_cut"}, headers=headers)
    after_cut = _stock(db_session, material_id)

    client.patch(f"/api/admin/orders/{order_id}/status", json={"status": "cancelled"}, headers=headers)
    assert _stock(db_session, material_id) == after_cut


# ── authorisation ────────────────────────────────────────────────────────────


def test_guest_must_confirm_the_email_to_cancel(client, seeded_catalog):
    """The order number is enough to *view* an order, but it appears on printed
    paperwork — so on its own it must not be enough to destroy one."""
    order = client.post("/api/orders", json=_payload(seeded_catalog, guest_email="guest@example.com")).json()

    assert client.post(f"/api/orders/{order['order_number']}/cancel", json={}).status_code == 403
    assert (
        client.post(
            f"/api/orders/{order['order_number']}/cancel",
            json={"guest_email": "someone-else@example.com"},
        ).status_code
        == 403
    )
    # Still cancellable by the person who actually placed it.
    assert (
        client.post(
            f"/api/orders/{order['order_number']}/cancel",
            json={"guest_email": "GUEST@Example.com"},  # case-insensitive
        ).status_code
        == 200
    )


def test_a_signed_in_customer_cannot_cancel_someone_elses_order(
    client, seeded_catalog, registered_user, admin_user
):
    owner = auth_headers(client, "test@example.com", "password123")
    order = client.post("/api/orders", json=_payload(seeded_catalog), headers=owner).json()

    intruder = auth_headers(client, "admin@example.com", "adminpass123")
    resp = client.post(f"/api/orders/{order['order_number']}/cancel", json={}, headers=intruder)
    assert resp.status_code == 403


def test_owner_can_cancel_their_own_order(client, seeded_catalog, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    order = client.post("/api/orders", json=_payload(seeded_catalog), headers=headers).json()

    resp = client.post(f"/api/orders/{order['order_number']}/cancel", json={}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_a_guest_email_cannot_cancel_an_account_order(client, seeded_catalog, registered_user):
    """An account order is never cancellable by supplying an email — the guest
    path must not be a way around ownership."""
    headers = auth_headers(client, "test@example.com", "password123")
    order = client.post("/api/orders", json=_payload(seeded_catalog), headers=headers).json()

    resp = client.post(
        f"/api/orders/{order['order_number']}/cancel", json={"guest_email": "test@example.com"}
    )
    assert resp.status_code == 403


# ── window ───────────────────────────────────────────────────────────────────


def test_cannot_cancel_once_production_has_started(client, seeded_catalog, admin_user, db_session):
    from app.models.order import Order

    order = client.post("/api/orders", json=_payload(seeded_catalog, guest_email="guest@example.com")).json()
    order_id = db_session.query(Order).filter(Order.order_number == order["order_number"]).first().id

    client.patch(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "fabric_cut"},
        headers=auth_headers(client, "admin@example.com", "adminpass123"),
    )

    resp = client.post(
        f"/api/orders/{order['order_number']}/cancel", json={"guest_email": "guest@example.com"}
    )
    assert resp.status_code == 409


def test_cancelling_twice_is_rejected(client, seeded_catalog, db_session):
    """Guards the restock: cancelled is terminal, which is what makes returning
    fabric unconditional in transition_status safe. If a second cancellation
    succeeded, the stock would be credited twice."""
    material_id = seeded_catalog["color"].id
    order = client.post("/api/orders", json=_payload(seeded_catalog, guest_email="guest@example.com")).json()
    body = {"guest_email": "guest@example.com"}

    assert client.post(f"/api/orders/{order['order_number']}/cancel", json=body).status_code == 200
    restored = _stock(db_session, material_id)

    assert client.post(f"/api/orders/{order['order_number']}/cancel", json=body).status_code == 409
    assert _stock(db_session, material_id) == restored


def test_cancellation_is_recorded_in_the_status_history(client, seeded_catalog, db_session):
    from app.models.order import Order, OrderStatusHistory

    order = client.post("/api/orders", json=_payload(seeded_catalog, guest_email="guest@example.com")).json()
    client.post(
        f"/api/orders/{order['order_number']}/cancel",
        json={"guest_email": "guest@example.com", "reason": "Ordered the wrong size"},
    )

    row = db_session.query(Order).filter(Order.order_number == order["order_number"]).first()
    history = (
        db_session.query(OrderStatusHistory)
        .filter(OrderStatusHistory.order_id == row.id, OrderStatusHistory.to_status == "cancelled")
        .first()
    )
    assert history is not None
    assert history.note == "Ordered the wrong size"


def test_cancelling_an_unknown_order_404s(client):
    resp = client.post("/api/orders/TC-2026-NOPE/cancel", json={"guest_email": "x@example.com"})
    assert resp.status_code == 404


# ── saved designs ────────────────────────────────────────────────────────────


def test_a_customer_can_delete_their_saved_design(client, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    design = client.post(
        "/api/designs", json={"name": "Summer dress", "payload": {"note": "draft"}}, headers=headers
    ).json()

    assert client.delete(f"/api/designs/{design['id']}", headers=headers).status_code == 204
    assert client.get("/api/designs", headers=headers).json() == []


def test_deleting_another_users_design_is_a_404_not_a_403(client, registered_user, admin_user):
    """404 rather than 403 deliberately: a 403 would confirm that a design with
    that id exists on another account."""
    owner = auth_headers(client, "test@example.com", "password123")
    design = client.post("/api/designs", json={"name": "Mine", "payload": {}}, headers=owner).json()

    intruder = auth_headers(client, "admin@example.com", "adminpass123")
    assert client.delete(f"/api/designs/{design['id']}", headers=intruder).status_code == 404
    # And it is still there for its owner.
    assert len(client.get("/api/designs", headers=owner).json()) == 1


def test_deleting_a_saved_design_requires_signing_in(client, registered_user):
    headers = auth_headers(client, "test@example.com", "password123")
    design = client.post("/api/designs", json={"name": "Mine", "payload": {}}, headers=headers).json()
    assert client.delete(f"/api/designs/{design['id']}").status_code in (401, 403)
