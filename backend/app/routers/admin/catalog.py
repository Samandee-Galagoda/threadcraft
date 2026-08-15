"""Admin catalogue management — this is what makes the proposal's
'add a new cloth type without modifying the code' requirement real rather
than just a claim. Demo sequence: create a cloth type + its measurement
fields here, then switch to the customer wizard — it's there."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.catalog import ClothType, MeasurementField
from app.schemas.catalog import ClothTypeOut, MeasurementFieldOut

router = APIRouter(prefix="/api/admin/catalog", tags=["admin:catalog"], dependencies=[Depends(require_admin)])


class ClothTypeCreate(BaseModel):
    slug: str
    name: str
    description: str | None = None
    image_url: str | None = None
    base_price: Decimal
    base_stitching_cost: Decimal = Decimal("0")
    base_fabric_metres: Decimal
    reference_body_cm: Decimal = Decimal("90")
    ai_prompt_noun: str
    production_days: int = 7
    sort_order: int = 0


class ClothTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    base_price: Decimal | None = None
    base_stitching_cost: Decimal | None = None
    base_fabric_metres: Decimal | None = None
    reference_body_cm: Decimal | None = None
    ai_prompt_noun: str | None = None
    production_days: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class MeasurementFieldCreate(BaseModel):
    field_key: str
    label: str
    letter: str | None = None
    unit: str = "cm"
    min_value: Decimal
    max_value: Decimal
    is_required: bool = True
    affects_fabric: bool = False
    instructions: str | None = None
    sort_order: int = 0


@router.get("/cloth-types", response_model=list[ClothTypeOut])
def admin_list_cloth_types(db: Session = Depends(get_db)):
    return (
        db.query(ClothType)
        .options(joinedload(ClothType.measurement_fields), joinedload(ClothType.option_groups))
        .order_by(ClothType.sort_order)
        .all()
    )


@router.post("/cloth-types", response_model=ClothTypeOut, status_code=201)
def create_cloth_type(payload: ClothTypeCreate, db: Session = Depends(get_db)):
    if db.query(ClothType).filter(ClothType.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="A cloth type with this slug already exists")
    cloth_type = ClothType(**payload.model_dump())
    db.add(cloth_type)
    db.commit()
    db.refresh(cloth_type)
    return cloth_type


@router.patch("/cloth-types/{cloth_type_id}", response_model=ClothTypeOut)
def update_cloth_type(cloth_type_id: int, payload: ClothTypeUpdate, db: Session = Depends(get_db)):
    cloth_type = db.query(ClothType).filter(ClothType.id == cloth_type_id).first()
    if not cloth_type:
        raise HTTPException(status_code=404, detail="Cloth type not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(cloth_type, key, value)
    db.commit()
    db.refresh(cloth_type)
    return cloth_type


@router.delete("/cloth-types/{cloth_type_id}", status_code=204)
def deactivate_cloth_type(cloth_type_id: int, db: Session = Depends(get_db)):
    """Soft delete — deactivates rather than removing, so historical orders
    that reference this cloth type keep their snapshot intact."""
    cloth_type = db.query(ClothType).filter(ClothType.id == cloth_type_id).first()
    if not cloth_type:
        raise HTTPException(status_code=404, detail="Cloth type not found")
    cloth_type.is_active = False
    db.commit()


@router.post(
    "/cloth-types/{cloth_type_id}/measurement-fields",
    response_model=MeasurementFieldOut,
    status_code=201,
)
def add_measurement_field(cloth_type_id: int, payload: MeasurementFieldCreate, db: Session = Depends(get_db)):
    cloth_type = db.query(ClothType).filter(ClothType.id == cloth_type_id).first()
    if not cloth_type:
        raise HTTPException(status_code=404, detail="Cloth type not found")
    field = MeasurementField(cloth_type_id=cloth_type_id, **payload.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.delete("/measurement-fields/{field_id}", status_code=204)
def delete_measurement_field(field_id: int, db: Session = Depends(get_db)):
    field = db.query(MeasurementField).filter(MeasurementField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Measurement field not found")
    db.delete(field)
    db.commit()
