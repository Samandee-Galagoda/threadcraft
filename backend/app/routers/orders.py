from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_optional_user
from app.db.session import get_db
from app.models.order import Order, OrderReferenceImage
from app.models.settings import AppSetting
from app.models.user import User
from app.schemas.order import OrderCreate, OrderOut
from app.services import catalog as catalog_service
from app.services import email as email_service
from app.services import orders as orders_service
from app.services.pricing import calculate_price

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _setting(db: Session, key: str, default: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return str(row.value) if row else default


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    cloth_type = catalog_service.get_cloth_type_or_404(db, payload.cloth_type_id)
    if not cloth_type:
        raise HTTPException(status_code=404, detail="Cloth type not found")

    material = catalog_service.get_material_or_404(db, payload.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    color = next((c for c in material.colors if c.id == payload.material_color_id), None)
    options = catalog_service.get_design_options(db, payload.design_option_ids)

    # Price is ALWAYS recomputed server-side from the current catalogue state.
    # A client-supplied price is never trusted — the wizard's sidebar total is
    # a preview, not the value that gets charged.
    primary_field = next((f for f in cloth_type.measurement_fields if f.affects_fabric), None)
    primary_body_cm = None
    if primary_field and primary_field.field_key in payload.measurements:
        primary_body_cm = Decimal(str(payload.measurements[primary_field.field_key]))

    delivery_fee = Decimal(_setting(db, "delivery_fee", "350"))
    free_threshold = Decimal(_setting(db, "free_delivery_threshold", "15000"))

    pricing_input = catalog_service.build_pricing_input(
        cloth_type, material, color, options, primary_body_cm, delivery_fee, free_threshold
    )
    breakdown = calculate_price(pricing_input)

    if not current_user and not payload.guest_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_email is required for orders placed without an account",
        )

    if material.stock_metres < breakdown.fabric_metres:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough {material.name} in stock for this order",
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
    material.stock_metres = Decimal(str(material.stock_metres)) - breakdown.fabric_metres

    if payload.draft_id:
        db.query(OrderReferenceImage).filter(
            OrderReferenceImage.draft_id == payload.draft_id, OrderReferenceImage.order_id.is_(None)
        ).update({"order_id": order.id})

    db.commit()
    db.refresh(order)

    # Queued rather than awaited: a slow or unreachable email provider must not
    # delay the response to a customer who has just placed an order.
    background_tasks.add_task(email_service.send_order_confirmation, order, order.mockup_url)

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
