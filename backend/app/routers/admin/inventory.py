from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.catalog import Material, MaterialColor
from app.schemas.catalog import MaterialColorOut, MaterialOut

router = APIRouter(
    prefix="/api/admin/inventory", tags=["admin:inventory"], dependencies=[Depends(require_admin)]
)


class StockUpdate(BaseModel):
    stock_metres: Decimal = Field(ge=0)


class ColourStockUpdate(BaseModel):
    stock_metres: Decimal = Field(ge=0)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)


@router.get("/materials", response_model=list[MaterialOut])
def list_materials(db: Session = Depends(get_db)):
    return db.query(Material).options(joinedload(Material.colors)).all()


@router.get("/low-stock", response_model=list[MaterialOut])
def low_stock_materials(db: Session = Depends(get_db)):
    """Materials with at least one colourway at or below its threshold.

    Checked per colour rather than on the material total, because 100 m of silk
    spread across six colours still cannot fulfil an order for the one colour
    that has run out.
    """
    materials = db.query(Material).options(joinedload(Material.colors)).all()
    return [
        m
        for m in materials
        if (
            any(c.stock_metres <= c.low_stock_threshold for c in m.colors)
            if m.colors
            else m.stock_metres <= m.low_stock_threshold
        )
    ]


@router.patch("/colors/{color_id}/stock", response_model=MaterialColorOut)
def update_colour_stock(color_id: int, payload: ColourStockUpdate, db: Session = Depends(get_db)):
    """Correct the stock held for one colourway.

    This is the figure orders are actually checked and decremented against, so
    it is the number a tailor doing a stock-take needs to be able to fix.
    """
    colour = db.query(MaterialColor).filter(MaterialColor.id == color_id).first()
    if not colour:
        raise HTTPException(status_code=404, detail="Colour not found")
    colour.stock_metres = payload.stock_metres
    if payload.low_stock_threshold is not None:
        colour.low_stock_threshold = payload.low_stock_threshold
    db.commit()
    db.refresh(colour)
    return colour


@router.patch("/materials/{material_id}/stock", response_model=MaterialOut)
def update_stock(material_id: int, payload: StockUpdate, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    material.stock_metres = payload.stock_metres
    db.commit()
    db.refresh(material)
    return material
