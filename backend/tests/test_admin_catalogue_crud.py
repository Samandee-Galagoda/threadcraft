"""Admin CRUD for fabrics and design options.

These tables previously had no admin endpoints — only stock could be edited on
a material, and design options had nothing at all. Adding a fabric or a
neckline meant editing seed.py and redeploying, which contradicted the
proposal's claim that the catalogue is manageable without code changes.

The tests that matter are the round-trips: creating something here and then
seeing it priced through the *customer* endpoints. An admin endpoint that
writes a row nobody reads proves nothing.
"""

from decimal import Decimal

from tests.conftest import auth_headers


def _admin(client):
    return auth_headers(client, "admin@example.com", "adminpass123")


# ── fabrics ──────────────────────────────────────────────────────────────────


def test_a_new_fabric_reaches_the_customer_catalogue_and_prices_correctly(client, admin_user, seeded_catalog):
    """The whole point of the feature: add a fabric in admin, and a customer
    can immediately choose it and be quoted using its cost per metre — no code
    change, no redeploy."""
    headers = _admin(client)
    created = client.post(
        "/api/admin/catalog/materials",
        json={
            "slug": "tweed",
            "name": "Tweed",
            "cost_per_metre": "1200",
            "stock_metres": "50",
            "ai_prompt_term": "woven wool tweed",
        },
        headers=headers,
    )
    assert created.status_code == 201
    material_id = created.json()["id"]

    public = client.get("/api/catalog/materials").json()
    assert any(m["id"] == material_id for m in public), "new fabric must appear to customers"

    quote = client.post(
        "/api/quote",
        json={
            "cloth_type_id": seeded_catalog["cloth_type"].id,
            "material_id": material_id,
            "material_color_id": None,
            "design_option_ids": [],
            "measurements": {"chest": 96},
        },
    ).json()
    # base 2200 + stitching 300 + material (1.4m x 1200) 1680 + delivery 350
    assert Decimal(quote["total"]) == Decimal("4530.00")


def test_repricing_a_fabric_changes_future_quotes_only(client, admin_user, seeded_catalog):
    """An order stores its own price breakdown, so a fabric going up in price
    must never retroactively change what a customer already agreed to pay."""
    headers = _admin(client)
    payload = {
        "cloth_type_id": seeded_catalog["cloth_type"].id,
        "material_id": seeded_catalog["material"].id,
        "material_color_id": seeded_catalog["color"].id,
        "design_option_ids": [],
        "measurements": {"chest": 96},
    }
    order = client.post("/api/orders", json={**payload, "guest_email": "g@example.com"}).json()
    original_total = Decimal(order["price_total"])

    client.patch(
        f"/api/admin/catalog/materials/{seeded_catalog['material'].id}",
        json={"cost_per_metre": "1300"},
        headers=headers,
    )

    new_quote = client.post("/api/quote", json=payload).json()
    assert Decimal(new_quote["total"]) > original_total

    unchanged = client.get(f"/api/orders/track/{order['order_number']}").json()
    assert Decimal(unchanged["price_total"]) == original_total


def test_deactivated_fabric_disappears_for_customers_but_not_for_admin(client, admin_user):
    headers = _admin(client)
    created = client.post(
        "/api/admin/catalog/materials",
        json={"slug": "hessian", "name": "Hessian", "cost_per_metre": "200", "ai_prompt_term": "hessian"},
        headers=headers,
    ).json()

    client.delete(f"/api/admin/catalog/materials/{created['id']}", headers=headers)

    assert not any(m["id"] == created["id"] for m in client.get("/api/catalog/materials").json())
    admin_view = client.get("/api/admin/catalog/materials", headers=headers).json()
    row = next(m for m in admin_view if m["id"] == created["id"])
    assert row["is_active"] is False


def test_duplicate_material_slug_rejected(client, admin_user):
    headers = _admin(client)
    body = {"slug": "denim", "name": "Denim", "cost_per_metre": "700", "ai_prompt_term": "denim"}
    assert client.post("/api/admin/catalog/materials", json=body, headers=headers).status_code == 201
    assert client.post("/api/admin/catalog/materials", json=body, headers=headers).status_code == 400


def test_negative_price_rejected(client, admin_user):
    headers = _admin(client)
    resp = client.post(
        "/api/admin/catalog/materials",
        json={"slug": "x", "name": "X", "cost_per_metre": "-5", "ai_prompt_term": "x"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_colour_surcharge_reaches_the_quote(client, admin_user, seeded_catalog):
    headers = _admin(client)
    colour = client.post(
        f"/api/admin/catalog/materials/{seeded_catalog['material'].id}/colors",
        json={"name": "Gold", "hex_code": "#D4AF37", "ai_prompt_term": "gold", "surcharge": "100"},
        headers=headers,
    )
    assert colour.status_code == 201

    payload = {
        "cloth_type_id": seeded_catalog["cloth_type"].id,
        "material_id": seeded_catalog["material"].id,
        "design_option_ids": [],
        "measurements": {"chest": 96},
    }
    plain = client.post("/api/quote", json={**payload, "material_color_id": None}).json()
    gold = client.post("/api/quote", json={**payload, "material_color_id": colour.json()["id"]}).json()
    # Surcharge is per metre, so 1.4m x 100.
    assert Decimal(gold["total"]) - Decimal(plain["total"]) == Decimal("140.00")


def test_malformed_hex_colour_rejected(client, admin_user, seeded_catalog):
    resp = client.post(
        f"/api/admin/catalog/materials/{seeded_catalog['material'].id}/colors",
        json={"name": "Bad", "hex_code": "not-a-colour", "ai_prompt_term": "bad"},
        headers=_admin(client),
    )
    assert resp.status_code == 422


# ── design options ───────────────────────────────────────────────────────────


def test_a_new_design_option_reaches_the_wizard_and_moves_the_price(client, admin_user, seeded_catalog):
    """A design option carries three effects at once — a stitching line item,
    a fabric multiplier, and a prompt term. This asserts the first two land in
    a customer quote."""
    headers = _admin(client)
    group = client.post(
        "/api/admin/catalog/design-options/groups",
        json={"code": "collar", "label": "Collar", "selection_type": "single"},
        headers=headers,
    )
    assert group.status_code == 201

    option = client.post(
        f"/api/admin/catalog/design-options/groups/{group.json()['id']}/options",
        json={
            "code": "mandarin",
            "label": "Mandarin collar",
            "ai_prompt_term": "mandarin collar",
            "stitching_premium": "450",
            "fabric_multiplier": "1.100",
        },
        headers=headers,
    )
    assert option.status_code == 201

    slug = seeded_catalog["cloth_type"].slug
    public = client.get(f"/api/catalog/cloth-types/{slug}").json()
    assert any(g["code"] == "collar" for g in public["option_groups"]), (
        "a group with no cloth_type_id applies to every garment"
    )

    payload = {
        "cloth_type_id": seeded_catalog["cloth_type"].id,
        "material_id": seeded_catalog["material"].id,
        "material_color_id": seeded_catalog["color"].id,
        "measurements": {"chest": 96},
    }
    plain = client.post("/api/quote", json={**payload, "design_option_ids": []}).json()
    fancy = client.post("/api/quote", json={**payload, "design_option_ids": [option.json()["id"]]}).json()

    assert Decimal(fancy["total"]) > Decimal(plain["total"])
    # 1.40m x 1.100, rounded by the engine.
    assert Decimal(fancy["fabric_metres"]) == Decimal("1.54")
    assert any("Mandarin collar" in line["label"] for line in fancy["lines"])


def test_absurd_fabric_multiplier_rejected(client, admin_user):
    """A typo of 12 instead of 1.2 would quote twelve times the cloth. Bounded
    at the schema so it can never reach the pricing engine."""
    headers = _admin(client)
    group = client.post(
        "/api/admin/catalog/design-options/groups",
        json={"code": "g", "label": "G"},
        headers=headers,
    ).json()
    resp = client.post(
        f"/api/admin/catalog/design-options/groups/{group['id']}/options",
        json={"code": "o", "label": "O", "ai_prompt_term": "o", "fabric_multiplier": "12"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_group_can_be_scoped_to_one_garment(client, admin_user, seeded_catalog):
    headers = _admin(client)
    resp = client.post(
        "/api/admin/catalog/design-options/groups",
        json={
            "code": "hem",
            "label": "Hem",
            "cloth_type_id": seeded_catalog["cloth_type"].id,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["cloth_type_id"] == seeded_catalog["cloth_type"].id


def test_group_scoped_to_an_unknown_garment_404s(client, admin_user):
    resp = client.post(
        "/api/admin/catalog/design-options/groups",
        json={"code": "x", "label": "X", "cloth_type_id": 999999},
        headers=_admin(client),
    )
    assert resp.status_code == 404


def test_deactivated_option_leaves_the_wizard(client, admin_user, seeded_catalog):
    headers = _admin(client)
    option_id = seeded_catalog["option"].id

    client.delete(f"/api/admin/catalog/design-options/options/{option_id}", headers=headers)

    slug = seeded_catalog["cloth_type"].slug
    public = client.get(f"/api/catalog/cloth-types/{slug}").json()
    offered = [o["id"] for g in public["option_groups"] for o in g["options"]]
    assert option_id not in offered


def test_admin_catalogue_writes_require_admin(client, registered_user, seeded_catalog):
    """Every one of these endpoints changes what customers are charged, so the
    role check is asserted rather than assumed."""
    headers = auth_headers(client, "test@example.com", "password123")
    material_id = seeded_catalog["material"].id
    for method, path, body in [
        (
            "post",
            "/api/admin/catalog/materials",
            {"slug": "x", "name": "X", "cost_per_metre": "1", "ai_prompt_term": "x"},
        ),
        ("patch", f"/api/admin/catalog/materials/{material_id}", {"cost_per_metre": "1"}),
        ("delete", f"/api/admin/catalog/materials/{material_id}", None),
        ("post", "/api/admin/catalog/design-options/groups", {"code": "x", "label": "X"}),
        ("get", "/api/admin/catalog/design-options/groups", None),
    ]:
        call = getattr(client, method)
        resp = call(path, json=body, headers=headers) if body else call(path, headers=headers)
        assert resp.status_code == 403, f"{method.upper()} {path} was not protected"


def test_withdrawn_colour_leaves_the_wizard(client, admin_user, seeded_catalog):
    """Companion to test_deactivated_option_leaves_the_wizard, covering the
    other half of the same omission: MaterialColor.is_active was on the model
    and read by nothing, so a withdrawn colourway stayed selectable and kept
    applying its surcharge."""
    headers = _admin(client)
    colour_id = seeded_catalog["color"].id

    client.delete(f"/api/admin/catalog/materials/colors/{colour_id}", headers=headers)

    materials = client.get("/api/catalog/materials").json()
    offered = [c["id"] for m in materials for c in m["colors"]]
    assert colour_id not in offered

    # Still there for the admin — soft delete, so historical orders remain
    # explicable.
    admin_view = client.get("/api/admin/catalog/materials", headers=headers).json()
    assert any(c["id"] == colour_id for m in admin_view for c in m["colors"])
