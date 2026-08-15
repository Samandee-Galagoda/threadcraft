from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.settings import AppSetting
from app.schemas.order import LineItemOut, QuoteRequest, QuoteResponse
from app.services import catalog as catalog_service
from app.services.pricing import calculate_price

router = APIRouter(prefix="/api/quote", tags=["pricing"])


def _setting(db: Session, key: str, default: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return str(row.value) if row else default


@router.post("", response_model=QuoteResponse)
def get_quote(payload: QuoteRequest, db: Session = Depends(get_db)):
    cloth_type = catalog_service.get_cloth_type_or_404(db, payload.cloth_type_id)
    if not cloth_type:
        raise HTTPException(status_code=404, detail="Cloth type not found")

    material = catalog_service.get_material_or_404(db, payload.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    color = next((c for c in material.colors if c.id == payload.material_color_id), None)
    options = catalog_service.get_design_options(db, payload.design_option_ids)

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

    return QuoteResponse(
        lines=[LineItemOut(label=li.label, amount=li.amount, category=li.category) for li in breakdown.lines],
        fabric_metres=breakdown.fabric_metres,
        base=breakdown.base,
        stitching=breakdown.stitching,
        material=breakdown.material,
        delivery=breakdown.delivery,
        total=breakdown.total,
    )
