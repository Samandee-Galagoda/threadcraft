from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.order import LineItemOut, QuoteRequest, QuoteResponse
from app.services import catalog as catalog_service

router = APIRouter(prefix="/api/quote", tags=["pricing"])


@router.post("", response_model=QuoteResponse)
def get_quote(payload: QuoteRequest, db: Session = Depends(get_db)):
    """Price a design without committing to it.

    Deliberately thin: every step from selections to a number lives in
    catalog_service.price_request, which POST /api/orders also calls. Anything
    computed here instead would be a second implementation of the price, and
    the quote could then disagree with the charge.
    """
    priced = catalog_service.price_request(
        db,
        payload.cloth_type_id,
        payload.material_id,
        payload.material_color_id,
        payload.design_option_ids,
        payload.measurements,
    )
    breakdown = priced.breakdown

    return QuoteResponse(
        lines=[LineItemOut(label=li.label, amount=li.amount, category=li.category) for li in breakdown.lines],
        fabric_metres=breakdown.fabric_metres,
        base=breakdown.base,
        stitching=breakdown.stitching,
        material=breakdown.material,
        delivery=breakdown.delivery,
        total=breakdown.total,
    )
