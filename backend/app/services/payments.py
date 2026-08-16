"""Stripe Checkout, in test mode.

Two deliberate design choices, both defensible under questioning:

**No webhooks.** Payment is confirmed by return-URL verification: the browser
comes back with a `session_id`, and the server then asks Stripe what that
session's `payment_status` actually is. The client never tells us it paid, so
the trust boundary is the same as a webhook's. What is lost is the case where
the customer closes the tab mid-redirect — the order stays `pending` until
someone reconciles it. That is an acceptable trade for a project that cannot
expose a public webhook endpoint to a free-tier host reliably, and the admin
order screen can still see and correct such orders.

**No `stripe` SDK.** httpx is already a hard dependency for the image and email
integrations, and Checkout Session create/retrieve is two form-encoded POSTs.
Adding an SDK for that costs a dependency and buys nothing.

**Simulated mode.** With no `STRIPE_SECRET_KEY` the service returns a session
whose `mode` is `simulated`, and `verify()` will mark such an order paid
without contacting Stripe. This keeps `git clone && uvicorn` a complete working
app, matching every other optional integration here — but it means a simulated
session is, by construction, not evidence of payment. It is recorded as
`sim_...` in `stripe_session_id` so the two can never be confused in the data.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import httpx

from app.core.config import settings

STRIPE_API = "https://api.stripe.com/v1"
TIMEOUT = 20.0

# Stripe takes amounts in the currency's minor unit. LKR is a two-decimal
# currency, so this is cents-equivalent; getting it wrong by 100x is the
# classic integration bug, hence it being a named, tested function.
MINOR_UNITS = 100


class PaymentError(RuntimeError):
    """Raised when Stripe is configured but the call failed. Distinct from the
    unconfigured case, which is not an error — it falls back to simulation."""


@dataclass
class CheckoutSession:
    session_id: str
    url: str | None
    mode: str  # "stripe" | "simulated"
    publishable_key: str | None = None


@dataclass
class PaymentVerdict:
    paid: bool
    mode: str
    detail: str


def is_configured() -> bool:
    return bool(settings.stripe_secret_key)


def to_minor_units(amount: Decimal) -> int:
    """LKR 4,235.005 -> 423501. Rounds half-up at the minor unit, matching the
    pricing engine, so the charged total can never disagree with the quote by
    a rounding direction."""
    return int((Decimal(amount) * MINOR_UNITS).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _post(path: str, data: list[tuple[str, str]]) -> dict:
    response = httpx.post(
        f"{STRIPE_API}{path}",
        data=data,
        auth=(settings.stripe_secret_key or "", ""),
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        detail = response.json().get("error", {}).get("message", response.text[:200])
        raise PaymentError(f"Stripe {response.status_code}: {detail}")
    return response.json()


def _get(path: str) -> dict:
    response = httpx.get(
        f"{STRIPE_API}{path}",
        auth=(settings.stripe_secret_key or "", ""),
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        detail = response.json().get("error", {}).get("message", response.text[:200])
        raise PaymentError(f"Stripe {response.status_code}: {detail}")
    return response.json()


def build_session_params(order, success_url: str, cancel_url: str) -> list[tuple[str, str]]:
    """Form fields for POST /v1/checkout/sessions.

    Split out from the request so the payload is unit-testable without a
    network call or an API key — the same reason build_cloudflare_payload
    exists in the mockup service, and for the same reason: a silently
    malformed payload here fails only in production.
    """
    description = order.material_name
    if order.color_name:
        description = f"{order.color_name} {description.lower()}"

    return [
        ("mode", "payment"),
        # `{CHECKOUT_SESSION_ID}` is substituted by Stripe on redirect. It must
        # reach the URL literally, so it is never percent-encoded or f-string
        # interpolated by us.
        ("success_url", f"{success_url}?order={order.order_number}&session_id={{CHECKOUT_SESSION_ID}}"),
        # The order number rides on the cancel URL as well. The order already
        # exists and is unpaid by the time Checkout opens, so a customer who
        # backs out needs to land somewhere that can identify and resume it —
        # otherwise the order is stranded with nothing linking the customer
        # back to it.
        ("cancel_url", f"{cancel_url}?order={order.order_number}"),
        ("client_reference_id", order.order_number),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][currency]", (order.currency or "LKR").lower()),
        ("line_items[0][price_data][unit_amount]", str(to_minor_units(order.price_total))),
        ("line_items[0][price_data][product_data][name]", f"Custom {order.cloth_type_name}"),
        ("line_items[0][price_data][product_data][description]", description),
        # Echoed back on retrieve, so verification can confirm the session it
        # was handed actually belongs to the order being marked paid.
        ("metadata[order_number]", order.order_number),
    ]


def create_checkout_session(
    order, success_url: str | None = None, cancel_url: str | None = None
) -> CheckoutSession:
    success = success_url or settings.checkout_success_url
    cancel = cancel_url or settings.checkout_cancel_url

    if not is_configured():
        return CheckoutSession(
            session_id=f"sim_{order.order_number}",
            url=None,
            mode="simulated",
        )

    payload = _post("/checkout/sessions", build_session_params(order, success, cancel))
    return CheckoutSession(
        session_id=payload["id"],
        url=payload.get("url"),
        mode="stripe",
        publishable_key=settings.stripe_publishable_key,
    )


def verify(order, session_id: str) -> PaymentVerdict:
    """Ask Stripe whether this session was actually paid.

    The order is passed in so the session's recorded order number can be
    checked against it: without that, a valid session id from *any* order
    would mark *this* order paid.
    """
    if session_id.startswith("sim_"):
        if is_configured():
            # A real key is present, so a simulated id here is either stale
            # state from before the key was added or someone hand-crafting one.
            return PaymentVerdict(False, "simulated", "Simulated session rejected: Stripe is configured.")
        return PaymentVerdict(True, "simulated", "Simulated payment — no Stripe key configured.")

    if not is_configured():
        return PaymentVerdict(False, "stripe", "Cannot verify: Stripe is not configured on this server.")

    session = _get(f"/checkout/sessions/{session_id}")
    claimed = (session.get("metadata") or {}).get("order_number") or session.get("client_reference_id")
    if claimed != order.order_number:
        return PaymentVerdict(False, "stripe", "This payment session belongs to a different order.")

    if session.get("payment_status") == "paid":
        return PaymentVerdict(True, "stripe", "Payment confirmed by Stripe.")
    return PaymentVerdict(False, "stripe", f"Stripe reports payment_status={session.get('payment_status')}.")


def provider_status() -> dict:
    return {
        "configured": is_configured(),
        "mode": "stripe_test" if is_configured() else "simulated",
        "publishable_key": settings.stripe_publishable_key,
        "note": (
            "Test mode. Use card 4242 4242 4242 4242 with any future expiry and CVC."
            if is_configured()
            else "No STRIPE_SECRET_KEY — checkout is simulated and marks orders paid without charging."
        ),
    }
