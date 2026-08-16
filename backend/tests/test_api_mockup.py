"""Mockup + upload endpoint tests.

These run with no image-provider credentials configured, which is deliberate:
CI must exercise the fallback path, because that path is what protects a live
demo when a free-tier provider is cold or rate-limited.
"""

import struct
import zlib


def _tiny_png() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(b"\x00" + b"\xff\x00\x00" * 8 for _ in range(8))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def test_mockup_status_reports_configuration(client):
    resp = client.get("/api/mockup/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "will_use_fallback" in body
    assert body["storage_backend"] in {"local", "r2"}


def test_mockup_generates_via_fallback_when_no_provider(client, seeded_catalog):
    resp = client.post(
        "/api/mockup",
        json={
            "cloth_type_id": seeded_catalog["cloth_type"].id,
            "material_id": seeded_catalog["material"].id,
            "material_color_id": seeded_catalog["color"].id,
            "design_option_ids": [seeded_catalog["option"].id],
            "custom_description": "test garment",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # No credentials in CI, so this must land on the placeholder — and must say so.
    assert body["is_fallback"] is True
    assert body["model_id"] == "fallback-placeholder"
    assert body["image_url"]
    assert body["disclaimer"]


def test_mockup_prompt_is_built_from_database_terms(client, seeded_catalog):
    """The prompt must come from each option's ai_prompt_term, not its UI label —
    that indirection is the point of the prompt-engineering pipeline."""
    resp = client.post(
        "/api/mockup",
        json={
            "cloth_type_id": seeded_catalog["cloth_type"].id,
            "material_id": seeded_catalog["material"].id,
            "design_option_ids": [seeded_catalog["option"].id],
        },
    )
    prompt = resp.json()["prompt"]
    assert "puffed sleeves" in prompt  # ai_prompt_term
    assert "t-shirt" in prompt  # cloth_type.ai_prompt_noun
    assert "cotton" in prompt  # material.ai_prompt_term
    assert resp.json()["negative_prompt"]


def test_mockup_is_cached_on_repeat_request(client, seeded_catalog):
    payload = {
        "cloth_type_id": seeded_catalog["cloth_type"].id,
        "material_id": seeded_catalog["material"].id,
        "design_option_ids": [],
    }
    first = client.post("/api/mockup", json=payload).json()
    second = client.post("/api/mockup", json=payload).json()
    assert first["cached"] is False
    assert second["cached"] is True
    assert first["image_url"] == second["image_url"]


def test_mockup_unknown_cloth_type_404s(client, seeded_catalog):
    resp = client.post(
        "/api/mockup",
        json={"cloth_type_id": 99999, "material_id": seeded_catalog["material"].id},
    )
    assert resp.status_code == 404


def test_upload_accepts_a_real_png(client):
    import uuid

    draft = str(uuid.uuid4())
    resp = client.post(
        "/api/uploads/reference",
        data={"draft_id": draft},
        files={"file": ("ref.png", _tiny_png(), "image/png")},
    )
    assert resp.status_code == 201
    assert resp.json()["draft_id"] == draft


def test_upload_rejects_non_image_regardless_of_declared_type(client):
    """Content-Type is client-supplied. A text file announcing itself as a PNG
    must still be rejected, on its actual bytes."""
    import uuid

    resp = client.post(
        "/api/uploads/reference",
        data={"draft_id": str(uuid.uuid4())},
        files={"file": ("evil.png", b"not an image at all", "image/png")},
    )
    assert resp.status_code == 400


def test_upload_enforces_the_three_image_limit(client):
    import uuid

    draft = str(uuid.uuid4())
    for _ in range(3):
        ok = client.post(
            "/api/uploads/reference",
            data={"draft_id": draft},
            files={"file": ("ref.png", _tiny_png(), "image/png")},
        )
        assert ok.status_code == 201

    fourth = client.post(
        "/api/uploads/reference",
        data={"draft_id": draft},
        files={"file": ("ref.png", _tiny_png(), "image/png")},
    )
    assert fourth.status_code == 400


def test_upload_rejects_a_non_uuid_draft_id(client):
    resp = client.post(
        "/api/uploads/reference",
        data={"draft_id": "not-a-uuid"},
        files={"file": ("ref.png", _tiny_png(), "image/png")},
    )
    assert resp.status_code == 400


def test_list_reference_images_for_a_draft(client):
    import uuid

    draft = str(uuid.uuid4())
    client.post(
        "/api/uploads/reference",
        data={"draft_id": draft},
        files={"file": ("ref.png", _tiny_png(), "image/png")},
    )
    resp = client.get(f"/api/uploads/reference/{draft}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
