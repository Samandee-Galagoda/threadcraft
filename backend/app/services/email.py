"""Transactional email via Resend.

Sends through Resend's HTTP API when `RESEND_API_KEY` is set, and otherwise
renders the message to stdout. The console fallback is not a stub — it produces
the exact same HTML, so the templates can be developed, screenshotted for the
report, and reviewed without an account or a verified domain.

Every send is best-effort. Email must never be able to fail an order: the
customer has paid, the order is in the database, and a bounced confirmation is
an inconvenience rather than a reason to lose the sale. Callers dispatch these
through FastAPI's BackgroundTasks so a slow API can't hold up the response.

**Deliverability caveat.** Resend's shared `onboarding@resend.dev` sender only
delivers to the address that owns the Resend account. Sending to a real
customer requires verifying a domain and changing `MAIL_FROM`. Until then this
works end-to-end for a demo but will not reach arbitrary recipients.
"""

from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.core.config import settings

# Plain module constants rather than a dict: these appear inside long HTML
# f-strings, and `{BRAND["taupe"]}` forces the formatter to break every line
# around the subscript, which makes the templates unreadable.
CREAM = "#FAF7F2"
WARM = "#F5EFE6"
SAND = "#E8D5C0"
TAUPE = "#C4A882"
BROWN = "#8B6B4A"
DARK = "#2C1F14"
TEXT = "#5C4A35"

# Reusable inline style fragments. Email clients strip <style> blocks, so every
# rule has to be inline — naming the repeated ones keeps the templates legible.
LABEL_CELL = f"padding:4px 0;font-size:13px;color:{TAUPE};"
VALUE_CELL = f"padding:4px 0;font-size:13px;color:{TEXT};"
SECTION_HEADING = (
    f"font-size:11px;letter-spacing:2px;color:{BROWN};text-transform:uppercase;margin-bottom:10px;"
)

STAGE_LABELS = {
    "received": "Received",
    "fabric_cut": "Fabric cut",
    "stitching": "Stitching",
    "qc": "Quality check",
    "dispatched": "Dispatched",
    "cancelled": "Cancelled",
}


@dataclass
class EmailResult:
    sent: bool
    provider: str
    detail: str


def _shell(title: str, body_html: str) -> str:
    """Table-based layout with inline CSS — email clients strip <style> blocks
    and have no meaningful flexbox support."""
    page = f"margin:0;padding:0;background:{WARM};font-family:Helvetica,Arial,sans-serif;"
    outer = f"background:{WARM};padding:32px 12px;"
    card = f"max-width:560px;background:{CREAM};border:1px solid {SAND};"
    header = f"padding:28px 32px;border-bottom:1px solid {SAND};text-align:center;"
    wordmark = f"font-family:Georgia,serif;font-size:24px;letter-spacing:3px;color:{DARK};"
    tagline = f"font-size:10px;letter-spacing:3px;color:{TAUPE};margin-top:4px;"
    footer = (
        f"padding:20px 32px;border-top:1px solid {SAND};text-align:center;"
        f"font-size:11px;color:{TAUPE};line-height:1.7;"
    )
    return f"""<!DOCTYPE html>
<html><body style="{page}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="{outer}">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="{card}">
  <tr><td style="{header}">
    <div style="{wordmark}">THREADCRAFT</div>
    <div style="{tagline}">CUSTOM CLOTHING &middot; SRI LANKA</div>
  </td></tr>
  <tr><td style="padding:32px;">{body_html}</td></tr>
  <tr><td style="{footer}">{title}<br/>Questions? Just reply to this email.</td></tr>
</table>
</td></tr></table>
</body></html>"""


def _row(label: str, value: str) -> str:
    return (
        f'<tr><td style="{LABEL_CELL}">{label}</td><td align="right" style="{VALUE_CELL}">{value}</td></tr>'
    )


def _price_rows(order) -> str:
    cell = f"padding:7px 0;font-size:13px;color:{TEXT};"
    rows = ""
    for line in order.price_breakdown or []:
        amount = Decimal(str(line.get("amount", 0)))
        rows += (
            f'<tr><td style="{cell}">{line.get("label", "")}</td>'
            f'<td align="right" style="{cell}">LKR {amount:,.2f}</td></tr>'
        )
    return rows


def _section(heading: str, inner_rows: str) -> str:
    return (
        f'<tr><td style="padding-top:24px;">'
        f'<div style="{SECTION_HEADING}">{heading}</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        f"{inner_rows}</table></td></tr>"
    )


def render_order_confirmation(order, mockup_url: str | None = None) -> tuple[str, str]:
    """Returns (subject, html)."""
    subject = f"Your ThreadCraft order {order.order_number} is confirmed"

    mockup_block = ""
    if mockup_url:
        caption = f"font-size:10px;color:{TAUPE};margin-top:8px;letter-spacing:1px;"
        mockup_block = (
            f'<tr><td style="padding:20px 0;text-align:center;">'
            f'<img src="{mockup_url}" alt="Your design preview" '
            f'style="max-width:240px;border:1px solid {SAND};"/>'
            f'<div style="{caption}">AI-GENERATED PREVIEW &middot; NOT THE FINISHED GARMENT</div>'
            f"</td></tr>"
        )

    material = order.material_name
    if order.color_name:
        material += f" &middot; {order.color_name}"
    details = order.design_options_snapshot or []
    detail_text = ", ".join(d.get("label", "") for d in details) or "None"

    # Delivery block, so the customer can check the address while the order is
    # still cancellable rather than discovering a typo when nothing arrives.
    delivery_rows = ""
    if order.delivery_address:
        address = ", ".join(
            part for part in (order.delivery_address, order.delivery_city, order.delivery_postcode) if part
        )
        delivery_rows = (
            _row("Name", order.customer_name or "—")
            + _row("Address", address)
            + (_row("Phone", order.customer_phone) if order.customer_phone else "")
        )

    garment_rows = (
        _row("Garment", order.cloth_type_name) + _row("Material", material) + _row("Details", detail_text)
    )

    measurements = order.measurements_snapshot or {}
    measurement_rows = "".join(
        _row(key.replace("_", " ").title(), f"{value} cm") for key, value in measurements.items()
    )

    total_label = f"padding:12px 0 0;border-top:1px solid {SAND};font-size:15px;color:{DARK};"
    total_value = (
        f"padding:12px 0 0;border-top:1px solid {SAND};font-family:Georgia,serif;font-size:17px;color:{DARK};"
    )
    price_rows = (
        _price_rows(order)
        + f'<tr><td style="{total_label}">Total</td>'
        + f'<td align="right" style="{total_value}">'
        + f"{order.currency} {Decimal(str(order.price_total)):,.2f}</td></tr>"
    )

    heading = f"font-family:Georgia,serif;font-size:26px;color:{DARK};margin-bottom:8px;"
    intro = f"font-size:14px;color:{TEXT};line-height:1.8;margin:0 0 24px;"
    outro = f"font-size:12px;color:{TAUPE};line-height:1.8;margin:28px 0 0;"

    body = (
        f'<div style="{heading}">Thank you</div>'
        f'<p style="{intro}">We&rsquo;ve received your order and our tailors will begin '
        f"work shortly. Your reference is <strong>{order.order_number}</strong>.</p>"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        f"{mockup_block}"
        f"{_section('Your garment', garment_rows)}"
        f"{_section('Delivering to', delivery_rows) if delivery_rows else ''}"
        f"{_section('Your measurements', measurement_rows) if measurement_rows else ''}"
        f"{_section('Price breakdown', price_rows)}"
        f"</table>"
        f'<p style="{outro}">Track your order any time using reference '
        f"<strong>{order.order_number}</strong>.</p>"
    )
    return subject, _shell("Order confirmation", body)


def render_status_update(order, new_status: str) -> tuple[str, str]:
    label = STAGE_LABELS.get(new_status, new_status.replace("_", " ").title())
    subject = f"ThreadCraft order {order.order_number}: {label}"

    stages = ["received", "fabric_cut", "stitching", "qc", "dispatched"]
    current = stages.index(new_status) if new_status in stages else -1

    steps = ""
    for index, stage in enumerate(stages):
        done = index <= current
        colour = BROWN if done else SAND
        marker = "&#9679;" if done else "&#9675;"
        steps += (
            f'<td align="center" style="padding:6px 2px;font-size:10px;'
            f'letter-spacing:1px;color:{colour};">'
            f"{marker}<br/>{STAGE_LABELS[stage].upper()}</td>"
        )

    heading = f"font-family:Georgia,serif;font-size:24px;color:{DARK};margin-bottom:8px;"
    intro = f"font-size:14px;color:{TEXT};line-height:1.8;margin:0 0 24px;"
    strip = f"border:1px solid {SAND};background:{WARM};"

    body = (
        f'<div style="{heading}">{label}</div>'
        f'<p style="{intro}">Your {order.cloth_type_name.lower()} ({order.order_number}) '
        f"has moved to <strong>{label}</strong>.</p>"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="{strip}"><tr>{steps}</tr></table>'
    )
    return subject, _shell("Order update", body)


def send_email(to: str, subject: str, html: str) -> EmailResult:
    """Best-effort send. Never raises — the caller's transaction matters more
    than the notification."""
    if not to:
        return EmailResult(False, "none", "No recipient address on the order.")

    if not settings.resend_api_key:
        print("\n" + "=" * 70)
        print("EMAIL (console fallback — set RESEND_API_KEY to send for real)")
        print(f"  To      : {to}")
        print(f"  From    : {settings.mail_from}")
        print(f"  Subject : {subject}")
        print(f"  HTML    : {len(html):,} bytes")
        print("=" * 70 + "\n")
        return EmailResult(False, "console", "Rendered to stdout; no API key configured.")

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={"from": settings.mail_from, "to": [to], "subject": subject, "html": html},
            )
        if response.status_code in (200, 201):
            return EmailResult(True, "resend", response.json().get("id", "sent"))
        if response.status_code == 403:
            return _failed(
                to,
                "403 — the onboarding@resend.dev sender only delivers to your own "
                "account address. Verify a domain and update MAIL_FROM to reach customers.",
            )
        return _failed(to, f"HTTP {response.status_code}: {response.text[:200]}")
    except Exception as exc:  # noqa: BLE001
        return _failed(to, f"{type(exc).__name__}: {exc}")


def _failed(to: str, detail: str) -> EmailResult:
    """Record a failed send.

    These run as background tasks whose return value the caller discards, so
    without this a bounced confirmation is invisible everywhere: the customer
    gets nothing and no log line says why. Printing is enough — the deployment's
    log is the only place an operator would look.
    """
    print(f"[email] FAILED to {to}: {detail}")
    return EmailResult(False, "resend", detail)


def absolute_media_url(url: str | None) -> str | None:
    """Turn a stored media path into something an email client can fetch.

    The local storage backend records mockups as "/static/generated/...".
    That works in the browser, where the page supplies an origin, and is a
    broken image everywhere else. Email has no origin: an <img src="/static/…">
    resolves against nothing and every recipient sees a placeholder.

    R2-backed URLs are already absolute and pass through untouched, which is
    why this went unnoticed — and why the existing template test, which passed
    a literal https:// URL, could never have caught it.
    """
    if not url or url.startswith(("http://", "https://", "data:")):
        return url
    return f"{settings.public_api_url.rstrip('/')}/{url.lstrip('/')}"


def send_order_confirmation(order, mockup_url: str | None = None) -> EmailResult:
    recipient = order.guest_email or (order.user.email if order.user else None)
    subject, html = render_order_confirmation(order, absolute_media_url(mockup_url))
    return send_email(recipient, subject, html)


def send_status_update(order, new_status: str) -> EmailResult:
    recipient = order.guest_email or (order.user.email if order.user else None)
    subject, html = render_status_update(order, new_status)
    return send_email(recipient, subject, html)


def provider_status() -> dict:
    return {
        "configured": bool(settings.resend_api_key),
        "from_address": settings.mail_from,
        "mode": "resend" if settings.resend_api_key else "console",
        "note": (
            "Resend's shared onboarding@resend.dev sender only delivers to the address "
            "that owns the Resend account. Verify a domain to reach customers."
            if "resend.dev" in settings.mail_from
            else "Custom sending domain configured."
        ),
    }
