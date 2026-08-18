"""Customer account portal: measurements, reorder, and profile.

The measurement tests carry the most weight. `user_measurements` used to have
eight fixed columns while the config-driven catalogue defines eighteen keys
across its eight garments — so ten were unstorable, and an admin adding a
measurement field created a key no column existed for. Storing a map is what
makes "save every measurement you might need" possible at all.
"""

from decimal import Decimal

from tests.conftest import auth_headers


def _customer(client):
    return auth_headers(client, "test@example.com", "password123")


# ── measurements ─────────────────────────────────────────────────────────────


def test_measurements_start_empty_rather_than_404(client, registered_user):
    """ "You haven't measured yourself yet" is a normal state for the profile
    screen, not an error."""
    body = client.get("/api/measurements", headers=_customer(client)).json()
    assert body["values"] == {}
    assert body["updated_at"] is None


def test_any_catalogue_field_key_is_storable(client, registered_user, seeded_catalog):
    """The point of the change: keys the old fixed columns had no room for."""
    headers = _customer(client)
    values = {"chest": 96, "collar": 40, "kameez_length": 105, "leg_opening": 18, "hem": 60}
    saved = client.put("/api/measurements", json={"values": values}, headers=headers).json()
    assert saved["values"] == {k: float(v) for k, v in values.items()}


def test_a_field_an_admin_adds_today_is_storable_immediately(
    client, registered_user, admin_user, seeded_catalog
):
    """The property that actually matters. Fixed columns could never satisfy
    this: a measurement field created through the catalogue screen produced a
    key no column existed for, so the schema could not keep up by construction.
    """
    admin = auth_headers(client, "admin@example.com", "adminpass123")
    created = client.post(
        f"/api/admin/catalog/cloth-types/{seeded_catalog['cloth_type'].id}/measurement-fields",
        json={
            "field_key": "wrist_girth",
            "label": "Wrist girth",
            "min_value": "12",
            "max_value": "25",
        },
        headers=admin,
    )
    assert created.status_code == 201

    # The customer can now save it, with no migration in between.
    saved = client.put(
        "/api/measurements", json={"values": {"wrist_girth": 17.5}}, headers=_customer(client)
    ).json()
    assert saved["values"] == {"wrist_girth": 17.5}


def test_blank_measurements_are_dropped_not_stored_as_zero(client, registered_user):
    """A measurement nobody took is missing, not zero. Storing 0 would look
    measured in the UI and skew the ML validator, which compares fields against
    one another."""
    headers = _customer(client)
    saved = client.put(
        "/api/measurements", json={"values": {"chest": 96, "waist": 0}}, headers=headers
    ).json()
    assert saved["values"] == {"chest": 96.0}


def test_saving_replaces_the_whole_profile(client, registered_user):
    headers = _customer(client)
    client.put("/api/measurements", json={"values": {"chest": 96, "waist": 76}}, headers=headers)
    saved = client.put("/api/measurements", json={"values": {"chest": 98}}, headers=headers).json()
    assert saved["values"] == {"chest": 98.0}


def test_measurements_require_signing_in(client):
    assert client.get("/api/measurements").status_code in (401, 403)
    assert client.put("/api/measurements", json={"values": {}}).status_code in (401, 403)


# ── reorder ──────────────────────────────────────────────────────────────────


def _place(client, seeded_catalog, headers=None):
    payload = {
        "cloth_type_id": seeded_catalog["cloth_type"].id,
        "material_id": seeded_catalog["material"].id,
        "material_color_id": seeded_catalog["color"].id,
        "design_option_ids": [seeded_catalog["option"].id],
        "measurements": {"chest": 96},
    }
    if headers is None:
        payload["guest_email"] = "guest@example.com"
    return client.post("/api/orders", json=payload, headers=headers or {}).json()


def test_reorder_resolves_a_past_order_against_the_live_catalogue(client, registered_user, seeded_catalog):
    headers = _customer(client)
    order = _place(client, seeded_catalog, headers)

    plan = client.get(f"/api/orders/{order['order_number']}/reorder", headers=headers).json()
    assert plan["cloth_type_id"] == seeded_catalog["cloth_type"].id
    assert plan["material_id"] == seeded_catalog["material"].id
    assert plan["material_color_id"] == seeded_catalog["color"].id
    assert plan["design_option_ids"] == [seeded_catalog["option"].id]
    assert plan["measurements"] == {"chest": 96}
    assert plan["unavailable"] == []


def test_a_discontinued_fabric_is_named_rather_than_replayed(
    client, registered_user, admin_user, seeded_catalog
):
    """A past order is a snapshot. Replaying a withdrawn fabric's id would 404
    at checkout or quietly reorder something we no longer sell — so the customer
    is told what changed."""
    headers = _customer(client)
    order = _place(client, seeded_catalog, headers)

    client.delete(
        f"/api/admin/catalog/materials/{seeded_catalog['material'].id}",
        headers=auth_headers(client, "admin@example.com", "adminpass123"),
    )

    plan = client.get(f"/api/orders/{order['order_number']}/reorder", headers=headers).json()
    assert plan["material_id"] is None
    assert seeded_catalog["material"].name in plan["unavailable"]
    # The garment is still fine, so the wizard can still be opened.
    assert plan["cloth_type_id"] == seeded_catalog["cloth_type"].id


def test_a_withdrawn_option_is_dropped_and_reported(client, registered_user, admin_user, seeded_catalog):
    headers = _customer(client)
    order = _place(client, seeded_catalog, headers)

    client.delete(
        f"/api/admin/catalog/design-options/options/{seeded_catalog['option'].id}",
        headers=auth_headers(client, "admin@example.com", "adminpass123"),
    )

    plan = client.get(f"/api/orders/{order['order_number']}/reorder", headers=headers).json()
    assert plan["design_option_ids"] == []
    assert seeded_catalog["option"].label in plan["unavailable"]


def test_reorder_refuses_another_customers_order(client, registered_user, admin_user, seeded_catalog):
    order = _place(client, seeded_catalog, _customer(client))
    intruder = auth_headers(client, "admin@example.com", "adminpass123")
    assert client.get(f"/api/orders/{order['order_number']}/reorder", headers=intruder).status_code == 403


def test_a_guest_order_can_still_be_reordered(client, seeded_catalog):
    """Guest orders have no owner to check against, and the order number is
    already the credential for viewing one."""
    order = _place(client, seeded_catalog)
    plan = client.get(f"/api/orders/{order['order_number']}/reorder").json()
    assert plan["cloth_type_id"] == seeded_catalog["cloth_type"].id


def test_the_reorder_plan_carries_no_price(client, registered_user, seeded_catalog):
    """Prices are re-quoted from the live catalogue. Carrying the old total
    forward would promise a price the shop may no longer offer."""
    order = _place(client, seeded_catalog, _customer(client))
    plan = client.get(f"/api/orders/{order['order_number']}/reorder", headers=_customer(client)).json()
    assert not any("price" in key or "total" in key for key in plan)
    assert Decimal(order["price_total"]) > 0  # the order itself still has one


# ── measurement guide ────────────────────────────────────────────────────────


def test_every_garment_has_letters_and_instructions_for_its_guide(client, seeded_catalog):
    """The measurement guide is driven by this payload rather than a hardcoded
    copy — the previous version had drifted, listing a "Blouse" the shop does
    not sell and leaving four of nine tabs empty. A field with no letter cannot
    be drawn on the body diagram, and one with no instructions is a guide entry
    that guides nobody."""
    from app.models.catalog import ClothType, MeasurementField
    from tests.conftest import TestSessionLocal

    db = TestSessionLocal()
    try:
        garments = db.query(ClothType).filter(ClothType.is_active.is_(True)).all()
        assert garments, "expected at least one garment"
        for garment in garments:
            fields = db.query(MeasurementField).filter(MeasurementField.cloth_type_id == garment.id).all()
            for field in fields:
                assert field.letter, f"{garment.slug}.{field.field_key} has no diagram letter"
                assert field.instructions, f"{garment.slug}.{field.field_key} has no instructions"
            letters = [f.letter for f in fields]
            assert len(letters) == len(set(letters)), f"{garment.slug} reuses a diagram letter"
    finally:
        db.close()


def test_the_guide_payload_is_public(client, seeded_catalog):
    """The guide is a marketing page — it must render for a visitor who has
    never signed in."""
    resp = client.get("/api/catalog/cloth-types")
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert "measurement_fields" in body[0]
