"""Admin fabric management.

The catalogue previously had admin CRUD for garments but not for fabrics: only
stock could be edited, so adding a new material or repricing an existing one
meant editing seed.py and redeploying. That undercut the proposal's claim that
the catalogue is manageable without code changes — it was true for garments
only.

Deactivation is soft throughout, for the same reason it is on cloth types:
orders snapshot the material name and price at purchase time, but the row is
still referenced by material_id, and hard deletion would break the admin order
view for every historical order that used it.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.catalog import Material, MaterialColor
from app.schemas.catalog import AdminMaterialOut, MaterialColorOut

router = APIRouter(
    prefix="/api/admin/catalog/materials",
    tags=["admin:catalog"],
    dependencies=[Depends(require_admin)],
)


class MaterialCreate(BaseModel):
    slug: str
    name: str
    cost_per_metre: Decimal = Field(ge=0)
    stock_metres: Decimal = Field(default=Decimal("0"), ge=0)
    low_stock_threshold: Decimal = Field(default=Decimal("20"), ge=0)
    swatch_css: str | None = None
    swatch_image_url: str | None = None
    ai_prompt_term: str
    care_notes: str | None = None


class MaterialUpdate(BaseModel):
    name: str | None = None
    cost_per_metre: Decimal | None = Field(default=None, ge=0)
    stock_metres: Decimal | None = Field(default=None, ge=0)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    swatch_css: str | None = None
    swatch_image_url: str | None = None
    ai_prompt_term: str | None = None
    care_notes: str | None = None
    is_active: bool | None = None


class ColorCreate(BaseModel):
    name: str
    hex_code: str = Field(pattern=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
    ai_prompt_term: str
    surcharge: Decimal = Field(default=Decimal("0"), ge=0)


def _get(db: Session, material_id: int) -> Material:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.get("", response_model=list[AdminMaterialOut])
def list_materials(db: Session = Depends(get_db)):
    """Every material including inactive ones — the customer endpoint filters
    those out, so this is the only place a deactivated fabric is visible."""
    return db.query(Material).options(joinedload(Material.colors)).order_by(Material.name).all()


@router.post("", response_model=AdminMaterialOut, status_code=201)
def create_material(payload: MaterialCreate, db: Session = Depends(get_db)):
    if db.query(Material).filter(Material.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="A material with this slug already exists")
    material = Material(**payload.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.patch("/{material_id}", response_model=AdminMaterialOut)
def update_material(material_id: int, payload: MaterialUpdate, db: Session = Depends(get_db)):
    """Repricing here changes future quotes immediately.

    Existing orders are unaffected: they store price_total and a full
    price_breakdown snapshot at purchase time, so a fabric going up in price
    never retroactively alters what a customer already agreed to pay.
    """
    material = _get(db, material_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(material, key, value)
    db.commit()
    db.refresh(material)
    return material


@router.delete("/{material_id}", status_code=204)
def deactivate_material(material_id: int, db: Session = Depends(get_db)):
    material = _get(db, material_id)
    material.is_active = False
    db.commit()


@router.post("/{material_id}/colors", response_model=MaterialColorOut, status_code=201)
def add_color(material_id: int, payload: ColorCreate, db: Session = Depends(get_db)):
    _get(db, material_id)
    color = MaterialColor(material_id=material_id, **payload.model_dump())
    db.add(color)
    db.commit()
    db.refresh(color)
    return color


@router.delete("/colors/{color_id}", status_code=204)
def deactivate_color(color_id: int, db: Session = Depends(get_db)):
    color = db.query(MaterialColor).filter(MaterialColor.id == color_id).first()
    if not color:
        raise HTTPException(status_code=404, detail="Colour not found")
    color.is_active = False
    db.commit()
