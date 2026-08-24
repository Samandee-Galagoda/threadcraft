"""Public gallery endpoint.

The two things worth testing here are both about what *doesn't* come out: no
personal data, and no URL pointing at an image that has since vanished with the
instance's disk.
"""

from decimal import Decimal

import pytest

from app.models.order import Order
from app.services import storage


@pytest.fixture()
def make_order(db_session):
    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        defaults = dict(
            order_number=f"TC-2026-GAL{counter['n']:03d}",
            guest_email="customer@example.com",
            customer_name="Priya Fernando",
            customer_phone="0771234567",
            delivery_address="12 Temple Road",
            delivery_city="Colombo",
            cloth_type_name="Dress",
            material_name="Silk",
            color_name="Burgundy",
            custom_description="something personal about my body",
            mockup_url="https://cdn.example.com/mockups/a.png",
            design_options_snapshot=[],
            measurements_snapshot={"bust": 92.0},
            fabric_metres_used=Decimal("2.60"),
            price_base=Decimal("3500"),
            price_stitching=Decimal("600"),
            price_material=Decimal("4680"),
            price_delivery=Decimal("350"),
            price_total=Decimal("9130"),
            currency="LKR",
            status="received",
            payment_status="paid",
        )
        defaults.update(overrides)
        order = Order(**defaults)
        db_session.add(order)
        db_session.commit()
        return order

    return _make


def test_gallery_is_empty_before_anyone_orders(client):
    assert client.get("/api/gallery").json() == []


def test_gallery_returns_the_garment_fabric_and_colour(client, make_order):
    make_order()
    (item,) = client.get("/api/gallery").json()

    assert item["image_url"] == "https://cdn.example.com/mockups/a.png"
    assert item["cloth_type"] == "Dress"
    assert item["material"] == "Silk"
    assert item["colour"] == "Burgundy"


def test_gallery_leaks_nothing_that_identifies_the_customer(client, make_order):
    """A shop window, not an order book."""
    make_order()
    body = client.get("/api/gallery").text

    for private in [
        "Priya Fernando",
        "customer@example.com",
        "0771234567",
        "12 Temple Road",
        "TC-2026-GAL001",
        "something personal about my body",
    ]:
        assert private not in body


def test_orders_without_a_mockup_are_skipped(client, make_order):
    make_order(mockup_url=None)
    make_order(mockup_url="")
    assert client.get("/api/gallery").json() == []


def test_newest_designs_come_first(client, make_order):
    make_order(cloth_type_name="Shirt", mockup_url="https://cdn.example.com/1.png")
    make_order(cloth_type_name="Skirt", mockup_url="https://cdn.example.com/2.png")

    assert [i["cloth_type"] for i in client.get("/api/gallery").json()] == ["Skirt", "Shirt"]


def test_one_cached_mockup_shared_by_several_orders_appears_once(client, make_order):
    """Identical selections reuse a cached generation, which would otherwise
    show the same picture repeatedly and make a small gallery look smaller."""
    make_order(mockup_url="https://cdn.example.com/same.png")
    make_order(mockup_url="https://cdn.example.com/same.png")

    assert len(client.get("/api/gallery").json()) == 1


def test_limit_is_honoured_and_bounded(client, make_order):
    for index in range(5):
        make_order(mockup_url=f"https://cdn.example.com/{index}.png")

    assert len(client.get("/api/gallery?limit=3").json()) == 3
    assert client.get("/api/gallery?limit=0").status_code == 422
    assert client.get("/api/gallery?limit=999").status_code == 422


def test_a_locally_stored_image_that_no_longer_exists_is_dropped(client, make_order):
    """Render's free tier hands each deploy a fresh disk, so rows outlive files.
    Listing them anyway fills the page with broken thumbnails."""
    make_order(mockup_url="/static/generated/mockups/vanished.png")
    assert client.get("/api/gallery").json() == []


def test_a_locally_stored_image_that_still_exists_is_listed(client, make_order, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LOCAL_STATIC_DIR", tmp_path)
    (tmp_path / "mockups").mkdir()
    (tmp_path / "mockups" / "here.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    make_order(mockup_url="/static/generated/mockups/here.png")
    assert len(client.get("/api/gallery").json()) == 1


# ── storage.media_exists ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    ["https://cdn.example.com/a.png", "http://cdn.example.com/a.png", "data:image/png;base64,AAAA"],
)
def test_absolute_urls_are_trusted_without_touching_the_disk(url):
    assert storage.media_exists(url) is True


@pytest.mark.parametrize("url", [None, "", "/uploads/elsewhere.png", "not-a-url"])
def test_unknown_or_missing_urls_are_not_servable(url):
    assert storage.media_exists(url) is False


def test_a_path_escaping_the_media_directory_is_refused(tmp_path, monkeypatch):
    """The URL comes from the database; a traversal has no business being probed."""
    monkeypatch.setattr(storage, "LOCAL_STATIC_DIR", tmp_path / "generated")
    (tmp_path / "generated").mkdir()
    (tmp_path / "secret.env").write_text("KEY=1")

    assert storage.media_exists("/static/generated/../secret.env") is False
