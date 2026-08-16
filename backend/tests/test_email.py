"""Email template and send-path tests.

No API key is configured in CI, so these exercise the console fallback — which
is the path that must keep working when Resend is unreachable, and the one that
lets the templates be reviewed without an account.

The templates are rendered rather than mocked, because the failure mode here is
a broken f-string or a missing field producing a mangled email that still
"sends" successfully.
"""

from decimal import Decimal

from app.models.order import Order
from app.services import email as email_service


def _order(**overrides):
    defaults = dict(
        order_number="TC-2026-ABCDEF",
        guest_email="customer@example.com",
        cloth_type_name="Dress",
        material_name="Silk",
        color_name="Burgundy",
        design_options_snapshot=[{"code": "v_neck", "label": "V-neck"}],
        measurements_snapshot={"bust": 92.0, "waist": 76.0},
        fabric_metres_used=Decimal("2.60"),
        price_base=Decimal("3500"),
        price_stitching=Decimal("600"),
        price_material=Decimal("4680"),
        price_delivery=Decimal("350"),
        price_total=Decimal("9130"),
        price_breakdown=[
            {"label": "Base price (Dress)", "amount": "3500.00", "category": "base"},
            {"label": "Delivery", "amount": "350.00", "category": "delivery"},
        ],
        currency="LKR",
        status="received",
        payment_status="paid",
    )
    defaults.update(overrides)
    return Order(**defaults)


def test_confirmation_includes_the_order_reference():
    subject, html = email_service.render_order_confirmation(_order())
    assert "TC-2026-ABCDEF" in subject
    assert "TC-2026-ABCDEF" in html


def test_confirmation_includes_garment_material_and_colour():
    _, html = email_service.render_order_confirmation(_order())
    assert "Dress" in html
    assert "Silk" in html
    assert "Burgundy" in html


def test_confirmation_includes_the_itemised_breakdown_and_total():
    _, html = email_service.render_order_confirmation(_order())
    assert "Base price (Dress)" in html
    assert "3,500.00" in html
    assert "9,130.00" in html


def test_confirmation_includes_measurements():
    _, html = email_service.render_order_confirmation(_order())
    assert "Bust" in html
    assert "92.0" in html


def test_confirmation_labels_the_mockup_as_ai_generated():
    """The proposal commits to labelling AI output, and it is simply honest."""
    _, html = email_service.render_order_confirmation(_order(), mockup_url="https://example.com/m.png")
    assert "https://example.com/m.png" in html
    assert "AI-GENERATED PREVIEW" in html


def test_confirmation_omits_the_mockup_block_when_there_is_none():
    _, html = email_service.render_order_confirmation(_order(), mockup_url=None)
    assert "AI-GENERATED PREVIEW" not in html


def test_confirmation_survives_an_order_with_no_optional_data():
    """A guest order with no colour, options or measurements must still render."""
    _, html = email_service.render_order_confirmation(
        _order(color_name=None, design_options_snapshot=[], measurements_snapshot={})
    )
    assert "TC-2026-ABCDEF" in html
    assert "None" in html  # the details row falls back rather than breaking


def test_status_update_names_the_new_stage():
    subject, html = email_service.render_status_update(_order(), "stitching")
    assert "Stitching" in subject
    assert "Stitching" in html


def test_status_update_renders_every_workflow_stage():
    _, html = email_service.render_status_update(_order(), "qc")
    for label in ["RECEIVED", "FABRIC CUT", "STITCHING", "QUALITY CHECK", "DISPATCHED"]:
        assert label in html


def test_send_falls_back_to_console_without_an_api_key(capsys):
    result = email_service.send_email("a@example.com", "Subject", "<p>Body</p>")
    assert result.sent is False
    assert result.provider == "console"
    assert "a@example.com" in capsys.readouterr().out


def test_send_reports_a_missing_recipient_rather_than_raising():
    """A guest order with no email must not take down order creation."""
    result = email_service.send_email("", "Subject", "<p>Body</p>")
    assert result.sent is False
    assert "recipient" in result.detail.lower()


def test_send_order_confirmation_never_raises_on_a_bad_order():
    """Belt-and-braces: the caller runs this in a background task after the
    order is already committed, so an exception here would be logged noise at
    best and a crashed worker at worst."""
    result = email_service.send_order_confirmation(_order(guest_email=None))
    assert result.sent is False


def test_provider_status_flags_the_shared_sender_limitation():
    status = email_service.provider_status()
    assert status["mode"] == "console"
    assert "resend.dev" in status["from_address"]
    assert "own" in status["note"].lower() or "verify" in status["note"].lower()
