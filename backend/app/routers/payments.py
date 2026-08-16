from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.order import Order
from app.services import email as email_service
from app.services import payments as payments_service

router = APIRouter(prefix="/api/payments", tags=["payments"])


class CheckoutRequest(BaseModel):
    order_number: str


class CheckoutResponse(BaseModel):
    session_id: str
    url: str | None
    mode: str
    amount: str
    currency: str


class VerifyRequest(BaseModel):
    order_number: str
    session_id: str


class VerifyResponse(BaseModel):
    paid: bool
    mode: str
    payment_status: str
    detail: str


def _get_order(db: Session, order_number: str) -> Order:
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/checkout", response_model=CheckoutResponse)
def start_checkout(payload: CheckoutRequest, db: Session = Depends(get_db)):
    """Create a Checkout Session for an existing order.

    Keyed by order_number rather than taking an amount, so the charged total
    always comes from the server-side price the pricing engine computed. A
    client-supplied amount would make the whole server-side pricing design
    pointless.
    """
    order = _get_order(db, payload.order_number)

    if order.payment_status == "paid":
        raise HTTPException(status_code=409, detail="This order has already been paid.")
    if order.status == "cancelled":
        raise HTTPException(status_code=409, detail="This order was cancelled.")

    try:
        session = payments_service.create_checkout_session(order)
    except payments_service.PaymentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    order.stripe_session_id = session.session_id
    db.commit()

    return CheckoutResponse(
        session_id=session.session_id,
        url=session.url,
        mode=session.mode,
        amount=str(order.price_total),
        currency=order.currency or "LKR",
    )


@router.post("/verify", response_model=VerifyResponse)
def verify_payment(
    payload: VerifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Confirm a payment after the customer returns from Checkout.

    The client sends back the session id it was redirected with; the server
    then asks Stripe what that session's status actually is. The client's word
    is never taken for it — this is the whole reason the endpoint exists rather
    than a PATCH that sets payment_status directly.
    """
    order = _get_order(db, payload.order_number)

    if order.payment_status == "paid":
        # Idempotent: the success page may be refreshed or reopened, and that
        # must not re-send the confirmation email or 409.
        return VerifyResponse(
            paid=True,
            mode=payments_service.provider_status()["mode"],
            payment_status="paid",
            detail="Already recorded as paid.",
        )

    try:
        verdict = payments_service.verify(order, payload.session_id)
    except payments_service.PaymentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if verdict.paid:
        order.payment_status = "paid"
        order.stripe_session_id = payload.session_id
        db.commit()
        db.refresh(order)
        # Best-effort, in the background: the money is taken and the order is
        # committed, so a failing mail server must not fail this response.
        background_tasks.add_task(email_service.send_order_confirmation, order, order.mockup_url)

    return VerifyResponse(
        paid=verdict.paid,
        mode=verdict.mode,
        payment_status=order.payment_status,
        detail=verdict.detail,
    )


@router.get("/status")
def payment_status():
    """Which payment mode is live. Check before a demo — simulated mode marks
    orders paid without charging, which is invisible from the customer UI."""
    return payments_service.provider_status()
