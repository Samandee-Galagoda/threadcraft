"""Email template and send-path tests.

No API key is configured in CI, so these exercise the console fallback — which
is the path that must keep working when Resend is unreachable, and the one that
lets the templates be reviewed without an account.

The templates are rendered rather than mocked, because the failure mode here is
a broken f-string or a missing field producing a mangled email that still
"sends" successfully.
"""

from decimal import Decimal

import pytest

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


def test_provider_status_says_nothing_is_configured_by_default():
    """CI has no keys, so this is the state the console fallback reports."""
    status = email_service.provider_status()
    assert status["mode"] == "console"
    assert status["configured"] is False
    assert "resend.dev" in status["from_address"]
    assert "not sent" in status["note"].lower()


# ── media URLs ───────────────────────────────────────────────────────────────
# Regression: confirmations were sent with the raw stored path, which the local
# storage backend writes as "/static/generated/...". An email has no origin to
# resolve that against, so every recipient saw a broken image. The template
# test above passed a literal https:// URL and so could never have caught it.


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("/static/generated/mockups/abc.png", "http://localhost:8000/static/generated/mockups/abc.png"),
        ("static/generated/mockups/abc.png", "http://localhost:8000/static/generated/mockups/abc.png"),
        # Already absolute (the R2 backend) — untouched.
        ("https://cdn.example.com/m.png", "https://cdn.example.com/m.png"),
        ("http://cdn.example.com/m.png", "http://cdn.example.com/m.png"),
        (None, None),
        ("", ""),
    ],
)
def test_media_urls_are_absolutised_for_email(stored, expected):
    assert email_service.absolute_media_url(stored) == expected


def test_public_api_url_trailing_slash_does_not_double_up(monkeypatch):
    monkeypatch.setattr(email_service.settings, "public_api_url", "https://api.example.com/")
    assert email_service.absolute_media_url("/static/x.png") == "https://api.example.com/static/x.png"


def test_confirmation_email_embeds_a_fetchable_image(monkeypatch):
    """End of the chain: what a recipient's client actually receives."""
    sent = {}
    monkeypatch.setattr(email_service, "send_email", lambda to, subject, html: sent.update(to=to, html=html))
    order = _order()
    order.mockup_url = "/static/generated/mockups/abc.png"
    email_service.send_order_confirmation(order, order.mockup_url)

    assert 'src="http://localhost:8000/static/generated/mockups/abc.png"' in sent["html"]
    assert 'src="/static' not in sent["html"]


# ── provider selection ───────────────────────────────────────────────────────
# The two providers are restricted in opposite ways (see the module docstring),
# so which one is chosen decides whether a given recipient can be reached at
# all. Every failure here is silent from the customer's side.


@pytest.fixture()
def mail_settings(monkeypatch):
    """Configure the mail settings for one test, without touching the rest."""

    def configure(*, provider="auto", resend=None, brevo=None, mail_from=None):
        monkeypatch.setattr(email_service.settings, "mail_provider", provider)
        monkeypatch.setattr(email_service.settings, "resend_api_key", resend)
        monkeypatch.setattr(email_service.settings, "brevo_api_key", brevo)
        if mail_from is not None:
            monkeypatch.setattr(email_service.settings, "mail_from", mail_from)

    return configure


def test_auto_falls_back_to_console_with_no_keys(mail_settings):
    mail_settings()
    assert email_service.active_provider() == "console"


@pytest.mark.parametrize(
    ("resend", "brevo", "expected"),
    [("re_x", None, "resend"), (None, "xkeysib-x", "brevo")],
)
def test_auto_uses_whichever_provider_is_configured(mail_settings, resend, brevo, expected):
    mail_settings(resend=resend, brevo=brevo)
    assert email_service.active_provider() == expected


def test_auto_prefers_brevo_while_resend_is_on_the_sandbox_sender(mail_settings):
    """Resend's shared sender can only mail the account owner, so with both
    configured the one that can actually reach a customer wins."""
    mail_settings(resend="re_x", brevo="xkeysib-x", mail_from="ThreadCraft <onboarding@resend.dev>")
    assert email_service.active_provider() == "brevo"


def test_auto_switches_back_to_resend_once_a_domain_is_verified(mail_settings):
    """Verifying a domain is the whole signal — there is no second setting to
    remember, which is exactly the step someone would forget."""
    mail_settings(resend="re_x", brevo="xkeysib-x", mail_from="ThreadCraft <orders@threadcraft.lk>")
    assert email_service.active_provider() == "resend"


def test_an_explicit_choice_overrides_auto(mail_settings):
    mail_settings(provider="resend", resend="re_x", brevo="xkeysib-x")
    assert email_service.active_provider() == "resend"


def test_choosing_a_provider_with_no_key_falls_back_rather_than_firing_blind(mail_settings):
    """A half-finished config must not send unauthenticated requests at an API."""
    mail_settings(provider="brevo", resend="re_x")
    assert email_service.active_provider() == "console"


# ── Brevo ────────────────────────────────────────────────────────────────────


class _Response:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _capture_brevo(monkeypatch, response):
    """Stand in for the HTTP call and record what would have been sent."""
    sent = {}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, headers=None, json=None):
            sent.update(url=url, headers=headers, json=json)
            return response

    monkeypatch.setattr(email_service.httpx, "Client", lambda **kw: _Client())
    return sent


def test_brevo_send_posts_the_rendered_html_and_reports_the_message_id(mail_settings, monkeypatch):
    mail_settings(provider="brevo", brevo="xkeysib-x", mail_from="ThreadCraft <me@gmail.com>")
    sent = _capture_brevo(monkeypatch, _Response(201, {"messageId": "<abc@brevo>"}))

    result = email_service.send_email("customer@example.com", "Subject", "<p>Body</p>")

    assert result.sent is True
    assert result.provider == "brevo"
    assert result.detail == "<abc@brevo>"
    assert sent["url"] == "https://api.brevo.com/v3/smtp/email"
    assert sent["headers"]["api-key"] == "xkeysib-x"
    assert sent["json"]["to"] == [{"email": "customer@example.com"}]
    assert sent["json"]["htmlContent"] == "<p>Body</p>"


def test_brevo_sender_is_split_into_name_and_address(mail_settings, monkeypatch):
    """Brevo rejects the combined "Name <addr>" form that Resend accepts."""
    mail_settings(provider="brevo", brevo="xkeysib-x", mail_from="ThreadCraft <me@gmail.com>")
    sent = _capture_brevo(monkeypatch, _Response(201, {"messageId": "id"}))

    email_service.send_email("customer@example.com", "Subject", "<p>Body</p>")

    assert sent["json"]["sender"] == {"name": "ThreadCraft", "email": "me@gmail.com"}


def test_brevo_bare_address_still_yields_a_sender_name(mail_settings, monkeypatch):
    mail_settings(provider="brevo", brevo="xkeysib-x", mail_from="me@gmail.com")
    sent = _capture_brevo(monkeypatch, _Response(201, {"messageId": "id"}))

    email_service.send_email("customer@example.com", "Subject", "<p>Body</p>")

    assert sent["json"]["sender"] == {"name": "ThreadCraft", "email": "me@gmail.com"}


def test_brevo_unverified_sender_error_says_how_to_fix_it(mail_settings, monkeypatch, capsys):
    """The most likely failure, and one that only appears at send time."""
    mail_settings(provider="brevo", brevo="xkeysib-x", mail_from="ThreadCraft <me@gmail.com>")
    _capture_brevo(
        monkeypatch,
        _Response(400, {"code": "invalid_parameter", "message": "sender is not valid"}),
    )

    result = email_service.send_email("customer@example.com", "Subject", "<p>Body</p>")

    assert result.sent is False
    assert result.provider == "brevo"
    assert "me@gmail.com" in result.detail
    assert "verify" in result.detail.lower()
    assert "brevo" in capsys.readouterr().out.lower()


def test_brevo_network_failure_is_reported_not_raised(mail_settings, monkeypatch):
    mail_settings(provider="brevo", brevo="xkeysib-x")

    def _boom(**kwargs):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(email_service.httpx, "Client", _boom)
    result = email_service.send_email("customer@example.com", "Subject", "<p>Body</p>")

    assert result.sent is False
    assert "connection reset" in result.detail


def test_brevo_non_json_error_body_does_not_break_reporting(mail_settings, monkeypatch):
    mail_settings(provider="brevo", brevo="xkeysib-x")
    _capture_brevo(monkeypatch, _Response(502, None, text="<html>bad gateway</html>"))

    result = email_service.send_email("customer@example.com", "Subject", "<p>Body</p>")

    assert result.sent is False
    assert "bad gateway" in result.detail


def test_provider_status_describes_the_brevo_restriction(mail_settings):
    mail_settings(provider="brevo", brevo="xkeysib-x", mail_from="ThreadCraft <me@gmail.com>")
    status = email_service.provider_status()

    assert status["mode"] == "brevo"
    assert status["configured"] is True
    assert "me@gmail.com" in status["note"]
    assert "spam" in status["note"].lower()


def test_provider_status_flags_the_shared_resend_sender_limitation(mail_settings):
    mail_settings(provider="resend", resend="re_x", mail_from="ThreadCraft <onboarding@resend.dev>")
    status = email_service.provider_status()

    assert status["mode"] == "resend"
    assert "own" in status["note"].lower()


def test_provider_status_stops_warning_once_a_domain_is_verified(mail_settings):
    mail_settings(provider="resend", resend="re_x", mail_from="ThreadCraft <orders@threadcraft.lk>")
    assert "Custom sending domain" in email_service.provider_status()["note"]
