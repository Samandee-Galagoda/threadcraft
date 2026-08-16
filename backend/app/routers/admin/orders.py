from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderOut, OrderStatusUpdate
from app.services import email as email_service
from app.services.orders import InvalidStatusTransition, transition_status

router = APIRouter(prefix="/api/admin/orders", tags=["admin:orders"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[OrderOut])
def list_orders(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    return query.order_by(Order.created_at.desc()).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        transition_status(db, order, payload.status, changed_by_user_id=admin.id, note=payload.note)
    except InvalidStatusTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(order)

    # Queued so the admin's UI responds immediately rather than waiting on an
    # email provider they have no reason to care about.
    background_tasks.add_task(email_service.send_status_update, order, payload.status)

    return order


@router.get("/email-status")
def email_status():
    """Whether transactional email is actually configured. Worth checking
    before a demo — the console fallback is silent from the UI's perspective."""
    return email_service.provider_status()
