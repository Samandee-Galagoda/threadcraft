from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_optional_user
from app.db.session import get_db
from app.models.order import Order, OrderReferenceImage
from app.models.user import User
from app.schemas.order import OrderCancel, OrderCreate, OrderOut
from app.services import catalog as catalog_service
from app.services import orders as orders_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    # Price is ALWAYS recomputed server-side from the current catalogue state.
    # A client-supplied price is never trusted — the wizard's sidebar total is
    # a preview, not the value that gets charged. Same call as /api/quote, so
    # the preview and the charge cannot drift apart.
    priced = catalog_service.price_request(
        db,
        payload.cloth_type_id,
        payload.material_id,
        payload.material_color_id,
        payload.design_option_ids,
        payload.measurements,
    )
    cloth_type, material = priced.cloth_type, priced.material
    color, options, breakdown = priced.color, priced.options, priced.breakdown

    if not current_user and not payload.guest_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_email is required for orders placed without an account",
        )

    # Checked and decremented against the colourway when one was chosen, since
    # that is where the cloth actually is.
    holder = orders_service.stock_holder(material, color)
    holder_name = f"{color.name} {material.name}" if color else material.name
    if holder.stock_metres < breakdown.fabric_metres:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough {holder_name} in stock for this order",
        )

    order = Order(
        order_number=orders_service.generate_order_number(),
        user_id=current_user.id if current_user else None,
        guest_email=None if current_user else payload.guest_email,
        guest_name=None if current_user else payload.guest_name,
        cloth_type_id=cloth_type.id,
        material_id=material.id,
        material_color_id=color.id if color else None,
        cloth_type_name=cloth_type.name,
        material_name=material.name,
        color_name=color.name if color else None,
        color_hex=color.hex_code if color else None,
        design_options_snapshot=[{"code": o.code, "label": o.label} for o in options],
        measurements_snapshot=payload.measurements,
        custom_description=payload.custom_description,
        fabric_metres_used=breakdown.fabric_metres,
        price_base=breakdown.base,
        price_stitching=breakdown.stitching,
        price_material=breakdown.material,
        price_delivery=breakdown.delivery,
        price_total=breakdown.total,
        price_breakdown=[
            {"label": li.label, "amount": str(li.amount), "category": li.category} for li in breakdown.lines
        ],
        mockup_url=payload.mockup_url,
        mockup_prompt=payload.mockup_prompt,
        mockup_model=payload.mockup_model,
        mockup_generated_at=datetime.now(UTC) if payload.mockup_url else None,
        status="received",
        payment_status="pending",
    )
    db.add(order)
    db.flush()  # assigns order.id without committing, so status history + stock updates are atomic

    orders_service.record_status_change(db, order, "received", changed_by_user_id=None)
    holder.stock_metres = Decimal(str(holder.stock_metres)) - breakdown.fabric_metres

    if payload.draft_id:
        db.query(OrderReferenceImage).filter(
            OrderReferenceImage.draft_id == payload.draft_id, OrderReferenceImage.order_id.is_(None)
        ).update({"order_id": order.id})

    db.commit()
    db.refresh(order)

    # No confirmation email here. The order exists but is unpaid at this point,
    # and the template says "is confirmed" — sending it now would both mislead
    # the customer and duplicate the one /api/payments/verify sends once the
    # payment actually clears. A customer who abandons checkout gets no email,
    # which is the same behaviour as an abandoned cart anywhere else.
    return order


@router.get("/track/{order_number}", response_model=OrderOut)
def track_order(order_number: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/me", response_model=list[OrderOut])
def my_orders(
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()


@router.post("/{order_number}/cancel", response_model=OrderOut)
def cancel_my_order(
    order_number: str,
    payload: OrderCancel,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Let a customer cancel their own order before work starts.

    Previously only an admin could cancel, so a customer who ordered by mistake
    had no recourse in the product at all.

    **Authorisation.** Viewing an order needs only its number, but cancelling
    is destructive, so the number alone is not enough. A signed-in customer
    must own the order; a guest must also supply the email the order was placed
    with. Without that second factor, anyone who saw a printed order number
    could cancel someone else's garment.

    **Window.** Only while `received`. Once fabric is cut the cloth is
    committed, which is exactly why transition_status only restocks from that
    state — the two rules are the same rule.
    """
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id is not None:
        if not current_user or current_user.id != order.user_id:
            raise HTTPException(status_code=403, detail="This order belongs to another account")
    else:
        supplied = (payload.guest_email or "").strip().lower()
        if not supplied or supplied != (order.guest_email or "").lower():
            raise HTTPException(
                status_code=403,
                detail="Confirm the email address this order was placed with to cancel it",
            )

    if order.status != "received":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This order has already gone into production and can no longer be "
                "cancelled online. Please contact us."
            ),
        )

    orders_service.transition_status(
        db,
        order,
        "cancelled",
        changed_by_user_id=current_user.id if current_user else None,
        note=payload.reason or "Cancelled by customer",
    )
    db.commit()
    db.refresh(order)
    return order
