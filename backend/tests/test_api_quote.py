"""Tests for POST /api/quote.

This endpoint had no tests at all. The pricing *engine* is covered to 100%,
which is what made the gap easy to miss — the graded algorithm was well tested
while the endpoint exposing it to the wizard was not exercised once.

The load-bearing test here is test_quote_total_equals_the_price_charged: the
quote and the order used to be priced by two byte-identical copies of the same
assembly, so nothing stopped them drifting into showing one figure and charging
another.
"""

from decimal import Decimal

import pytest


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


def test_quote_matches_the_hand_computed_total(client, seeded_catalog):
    """Same arithmetic as the order test, asserted through the quote surface:
    base 2200 + stitching 300 + material (1.4m x 650) 910 + delivery 350."""
    resp = client.post("/api/quote", json=_payload(seeded_catalog))
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["total"]) == Decimal("3760.00")
    assert Decimal(body["fabric_metres"]) == Decimal("1.40")
    assert body["currency"] == "LKR"


def test_quote_total_equals_the_price_charged(client, seeded_catalog):
    """The regression this whole change exists for.

    A quote the customer accepts must be the amount the order commits. These
    were computed by two independent copies of the pricing assembly, so a
    change to one would silently make the wizard advertise a price the server
    never charges — visible to the customer, invisible to every existing test.
    """
    payload = _payload(seeded_catalog, design_option_ids=[seeded_catalog["option"].id])

    quoted = client.post("/api/quote", json=payload).json()
    ordered = client.post("/api/orders", json={**payload, "guest_email": "guest@example.com"}).json()

    assert Decimal(quoted["total"]) == Decimal(ordered["price_total"])
    assert Decimal(quoted["fabric_metres"]) == Decimal(ordered["fabric_metres_used"])

    # And the itemisation the customer read must be the itemisation stored.
    assert [(line["label"], line["amount"]) for line in quoted["lines"]] == [
        (line["label"], line["amount"]) for line in ordered["price_breakdown"]
    ]


def test_quote_never_touches_stock(client, seeded_catalog, db_session):
    """Quoting is a read. A customer comparing options must not consume fabric
    — only committing an order does that."""
    from app.models.catalog import Material

    before = Decimal(
        str(
            db_session.query(Material)
            .filter(Material.id == seeded_catalog["material"].id)
            .first()
            .stock_metres
        )
    )

    for _ in range(3):
        client.post("/api/quote", json=_payload(seeded_catalog))

    db_session.expire_all()
    after = Decimal(
        str(
            db_session.query(Material)
            .filter(Material.id == seeded_catalog["material"].id)
            .first()
            .stock_metres
        )
    )
    assert after == before


def test_quote_is_available_without_signing_in(client, seeded_catalog):
    """Pricing is public — a visitor has to see the cost before deciding to
    register. No Authorization header is sent here."""
    assert client.post("/api/quote", json=_payload(seeded_catalog)).status_code == 200


def test_options_change_the_quote(client, seeded_catalog):
    plain = client.post("/api/quote", json=_payload(seeded_catalog)).json()
    with_option = client.post(
        "/api/quote", json=_payload(seeded_catalog, design_option_ids=[seeded_catalog["option"].id])
    ).json()

    assert Decimal(with_option["total"]) > Decimal(plain["total"])
    # The premium is itemised, not folded into a single opaque total.
    assert any(seeded_catalog["option"].label in line["label"] for line in with_option["lines"])


def test_free_delivery_threshold_applies(client, seeded_catalog, db_session):
    from app.models.settings import AppSetting

    db_session.add(AppSetting(key="free_delivery_threshold", value="100", label="t"))
    db_session.commit()

    body = client.post("/api/quote", json=_payload(seeded_catalog)).json()
    assert Decimal(body["delivery"]) == Decimal("0")


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [("cloth_type_id", 999999), ("material_id", 999999)],
)
def test_unknown_catalogue_ids_404(client, seeded_catalog, field, bad_value):
    resp = client.post("/api/quote", json=_payload(seeded_catalog, **{field: bad_value}))
    assert resp.status_code == 404


def test_quote_without_measurements_still_prices(client, seeded_catalog):
    """Step 5 of the wizard shows a running total before measurements are
    entered, so an empty measurements dict must price at the reference size
    rather than error."""
    resp = client.post("/api/quote", json=_payload(seeded_catalog, measurements={}))
    assert resp.status_code == 200
    assert Decimal(resp.json()["total"]) > 0
