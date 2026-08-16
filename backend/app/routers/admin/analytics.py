from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.services import analytics as analytics_service

router = APIRouter(
    prefix="/api/admin/analytics",
    tags=["admin:analytics"],
    dependencies=[Depends(require_admin)],
)


class SummaryOut(BaseModel):
    total_orders: int
    paid_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    active_orders: int
    dispatched_orders: int
    cancelled_orders: int
    average_fulfilment_days: float | None
    low_stock_materials: int
    currency: str = "LKR"


@router.get("/summary", response_model=SummaryOut)
def summary(db: Session = Depends(get_db)):
    """Headline figures for the admin overview tiles."""
    result = analytics_service.get_summary(db)
    return SummaryOut(**result.__dict__)


@router.get("/revenue")
def revenue_trend(
    days: int = Query(30, ge=1, le=365, description="How many days back to report"),
    db: Session = Depends(get_db),
):
    """Daily paid revenue, zero-filled so a chart shows a continuous line."""
    return {"days": days, "currency": "LKR", "trend": analytics_service.get_revenue_trend(db, days)}


@router.get("/popular")
def popular(
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return {
        "cloth_types": analytics_service.get_popular_cloth_types(db, limit),
        "materials": analytics_service.get_popular_materials(db, limit),
    }


@router.get("/status-breakdown")
def status_breakdown(db: Session = Depends(get_db)):
    return {"statuses": analytics_service.get_status_breakdown(db)}


@router.get("/catalogue-health")
def catalogue_health(db: Session = Depends(get_db)):
    """Flags configuration gaps — e.g. a cloth type with no measurement fields,
    which would leave Step 4 of the wizard empty for that garment."""
    return analytics_service.get_catalogue_health(db)


@router.get("")
def everything(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """One call for the whole dashboard, so the admin page doesn't fan out into
    five requests on load."""
    result = analytics_service.get_summary(db)
    return {
        "summary": {**result.__dict__, "currency": "LKR"},
        "revenue_trend": analytics_service.get_revenue_trend(db, days),
        "popular_cloth_types": analytics_service.get_popular_cloth_types(db),
        "popular_materials": analytics_service.get_popular_materials(db),
        "status_breakdown": analytics_service.get_status_breakdown(db),
        "catalogue_health": analytics_service.get_catalogue_health(db),
    }
