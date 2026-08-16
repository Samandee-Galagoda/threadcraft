"""Payment tests.

The theme throughout: the client must never be able to make an order paid by
saying so. Every test here is either about the payload Stripe receives or about
what the server does with a claim it cannot verify.
"""

from decimal import Decimal

import pytest

from app.services import payments as payments_service
from tests.conftest import auth_headers  # noqa: F401  (kept for symmetry with sibling modules)


class FakeOrder:
    def __init__(self, **kwargs):
        self.order_number = kwargs.get("order_number", "TC-000123")
        self.cloth_type_name = kwargs.get("cloth_type_name", "Shirt")
        self.material_name = kwargs.get("material_name", "Linen")
        self.color_name = kwargs.get("color_name", "Ivory")
        self.price_total = kwargs.get("price_total", Decimal("4235.00"))
        self.currency = kwargs.get("currency", "LKR")


# ── amount conversion ────────────────────────────────────────────────────────
# Off-by-100 is the classic Stripe integration bug and is invisible in test mode
# until someone reads the dashboard.


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("4235.00"), 423500),
        (Decimal("0.01"), 1),
        (Decimal("1"), 100),
        (Decimal("12999.99"), 1299999),
        # Half-up at the minor unit, matching the pricing engine's rounding.
        (Decimal("10.005"), 1001),
        (Decimal("10.004"), 1000),
    ],
)
def test_amount_converts_to_minor_units(amount, expected):
    assert payments_service.to_minor_units(amount) == expected


def test_charged_amount_matches_the_order_total(monkeypatch):
    """The charge is derived from order.price_total, not from anything a client
    sent — this is what makes server-side pricing meaningful."""
    order = FakeOrder(price_total=Decimal("7890.50"))
    params = dict(payments_service.build_session_params(order, "https://s", "https://c"))
    assert params["line_items[0][price_data][unit_amount]"] == "789050"
    assert params["line_items[0][price_data][currency]"] == "lkr"


def test_success_url_keeps_the_stripe_placeholder_literal():
    """Stripe substitutes {CHECKOUT_SESSION_ID} on redirect. If it were escaped
    or interpolated away, the success page would come back with no session id
    and no payment could ever be verified."""
    order = FakeOrder()
    params = dict(payments_service.build_session_params(order, "https://app/success", "https://app/cancel"))
    assert "session_id={CHECKOUT_SESSION_ID}" in params["success_url"]
    assert "order=TC-000123" in params["success_url"]
    # Cancelling leaves a real, unpaid order behind, so that URL has to carry
    # the order number too or the customer cannot get back to it.
    assert params["cancel_url"] == "https://app/cancel?order=TC-000123"


def test_order_number_travels_on_the_session():
    """verify() checks this back against the order it is about to mark paid."""
    params = dict(payments_service.build_session_params(FakeOrder(), "https://s", "https://c"))
    assert params["metadata[order_number]"] == "TC-000123"
    assert params["client_reference_id"] == "TC-000123"


# ── verification trust boundary ──────────────────────────────────────────────


def test_simulated_session_is_accepted_only_without_a_key(monkeypatch):
    order = FakeOrder()
    monkeypatch.setattr(payments_service.settings, "stripe_secret_key", None)
    assert payments_service.verify(order, "sim_TC-000123").paid is True


def test_simulated_session_is_rejected_once_stripe_is_configured(monkeypatch):
    """Otherwise anyone could post `sim_<order>` against a live deployment and
    mark their own order paid."""
    order = FakeOrder()
    monkeypatch.setattr(payments_service.settings, "stripe_secret_key", "sk_test_x")
    verdict = payments_service.verify(order, "sim_TC-000123")
    assert verdict.paid is False


def test_a_session_belonging_to_another_order_is_rejected(monkeypatch):
    """A real, genuinely-paid session id is still not authorisation to mark a
    *different* order paid."""
    monkeypatch.setattr(payments_service.settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(
        payments_service,
        "_get",
        lambda path: {"payment_status": "paid", "metadata": {"order_number": "TC-999999"}},
    )
    verdict = payments_service.verify(FakeOrder(order_number="TC-000123"), "cs_test_abc")
    assert verdict.paid is False
    assert "different order" in verdict.detail


def test_unpaid_stripe_session_is_not_treated_as_paid(monkeypatch):
    monkeypatch.setattr(payments_service.settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(
        payments_service,
        "_get",
        lambda path: {"payment_status": "unpaid", "metadata": {"order_number": "TC-000123"}},
    )
    assert payments_service.verify(FakeOrder(), "cs_test_abc").paid is False


# ── endpoint behaviour ───────────────────────────────────────────────────────


def _place_order(client, seeded_catalog):
    return client.post(
        "/api/orders",
        json={
            "cloth_type_id": seeded_catalog["cloth_type"].id,
            "material_id": seeded_catalog["material"].id,
            "material_color_id": seeded_catalog["color"].id,
            "design_option_ids": [],
            "measurements": {"chest": 96},
            "guest_email": "guest@example.com",
        },
    ).json()


def test_checkout_charges_the_server_side_total(client, seeded_catalog):
    order = _place_order(client, seeded_catalog)
    resp = client.post("/api/payments/checkout", json={"order_number": order["order_number"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["amount"] == str(order["price_total"])
    assert body["mode"] == "simulated"  # no key in the test environment


def test_checkout_rejects_an_already_paid_order(client, seeded_catalog):
    order = _place_order(client, seeded_catalog)
    session = client.post("/api/payments/checkout", json={"order_number": order["order_number"]}).json()
    client.post(
        "/api/payments/verify",
        json={"order_number": order["order_number"], "session_id": session["session_id"]},
    )
    resp = client.post("/api/payments/checkout", json={"order_number": order["order_number"]})
    assert resp.status_code == 409


def test_verify_marks_the_order_paid_and_is_idempotent(client, seeded_catalog):
    """The success page can be refreshed or bookmarked; a second verify must
    not fail, and must not re-send the confirmation email."""
    order = _place_order(client, seeded_catalog)
    session = client.post("/api/payments/checkout", json={"order_number": order["order_number"]}).json()
    payload = {"order_number": order["order_number"], "session_id": session["session_id"]}

    first = client.post("/api/payments/verify", json=payload).json()
    assert first["paid"] is True
    assert first["payment_status"] == "paid"

    second = client.post("/api/payments/verify", json=payload).json()
    assert second["paid"] is True
    assert second["detail"] == "Already recorded as paid."

    tracked = client.get(f"/api/orders/track/{order['order_number']}").json()
    assert tracked["payment_status"] == "paid"


def test_verify_on_an_unknown_order_is_404(client):
    resp = client.post("/api/payments/verify", json={"order_number": "TC-NOPE", "session_id": "sim_TC-NOPE"})
    assert resp.status_code == 404


def test_paid_orders_reach_analytics_revenue(client, seeded_catalog, admin_user):
    """Closes the loop the analytics service depends on: only paid orders count
    toward revenue, so without a working verify step every chart reads zero."""
    order = _place_order(client, seeded_catalog)
    session = client.post("/api/payments/checkout", json={"order_number": order["order_number"]}).json()
    client.post(
        "/api/payments/verify",
        json={"order_number": order["order_number"], "session_id": session["session_id"]},
    )

    headers = auth_headers(client, "admin@example.com", "adminpass123")
    summary = client.get("/api/admin/analytics?days=30", headers=headers).json()["summary"]
    assert Decimal(summary["total_revenue"]) >= Decimal(order["price_total"])
    assert summary["paid_orders"] >= 1


def test_exactly_one_confirmation_email_across_the_whole_flow(client, seeded_catalog, monkeypatch):
    """Regression: order creation used to send the confirmation, and adding the
    payment step made it send a second one. Worse, the first arrived while the
    order was still unpaid, saying "is confirmed". Caught by reading the server
    log during a manual end-to-end run, not by any existing test."""
    sent = []
    monkeypatch.setattr(
        "app.services.email.send_order_confirmation",
        lambda order, mockup_url=None: sent.append(order.order_number),
    )

    order = _place_order(client, seeded_catalog)
    assert sent == [], "no email before payment — the order is not confirmed yet"

    session = client.post("/api/payments/checkout", json={"order_number": order["order_number"]}).json()
    payload = {"order_number": order["order_number"], "session_id": session["session_id"]}

    client.post("/api/payments/verify", json=payload)
    assert sent == [order["order_number"]]

    client.post("/api/payments/verify", json=payload)
    assert sent == [order["order_number"]], "refreshing the success page must not re-send"
