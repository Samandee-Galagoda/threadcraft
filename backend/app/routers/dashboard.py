from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.order import Order, SavedDesign
from app.models.user import User
from app.schemas.common import DashboardData, DashboardUser

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardData)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_orders = db.query(Order).filter(Order.user_id == current_user.id).count()
    active_orders_count = (
        db.query(Order)
        .filter(
            Order.user_id == current_user.id,
            Order.status.in_(["received", "fabric_cut", "stitching", "qc"]),
        )
        .count()
    )

    recent_orders = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )
    saved_designs = (
        db.query(SavedDesign)
        .filter(SavedDesign.user_id == current_user.id)
        .order_by(SavedDesign.created_at.desc())
        .all()
    )

    return DashboardData(
        user=DashboardUser(
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            created_at=current_user.created_at.strftime("Member since %b %Y"),
        ),
        total_orders=total_orders,
        active_orders_count=active_orders_count,
        measurements_saved=current_user.measurements is not None,
        measurements=current_user.measurements,
        recent_orders=recent_orders,
        saved_designs=saved_designs,
    )
