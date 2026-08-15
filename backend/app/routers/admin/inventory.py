from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.catalog import Material
from app.schemas.catalog import MaterialOut

router = APIRouter(
    prefix="/api/admin/inventory", tags=["admin:inventory"], dependencies=[Depends(require_admin)]
)


class StockUpdate(BaseModel):
    stock_metres: Decimal


@router.get("/materials", response_model=list[MaterialOut])
def list_materials(db: Session = Depends(get_db)):
    return db.query(Material).options(joinedload(Material.colors)).all()


@router.get("/low-stock", response_model=list[MaterialOut])
def low_stock_materials(db: Session = Depends(get_db)):
    materials = db.query(Material).options(joinedload(Material.colors)).all()
    return [m for m in materials if m.stock_metres <= m.low_stock_threshold]


@router.patch("/materials/{material_id}/stock", response_model=MaterialOut)
def update_stock(material_id: int, payload: StockUpdate, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    material.stock_metres = payload.stock_metres
    db.commit()
    db.refresh(material)
    return material
