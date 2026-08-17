"""Admin management of design options — necklines, sleeves, fits, patterns.

These had no admin endpoints at all, so adding a neckline meant editing seed.py
and redeploying. They are also the most interesting part of the catalogue to
manage, because each option carries three things at once:

  - stitching_premium  -> a line item in the price breakdown
  - fabric_multiplier  -> more or less cloth, so it moves the material cost too
  - ai_prompt_term     -> the words handed to the image model

That last column is what makes the prompt pipeline database-driven rather than
a hardcoded string, so exposing it here is the point rather than an extra.

A group with cloth_type_id NULL applies to every garment; one with an id is
specific to that garment. The customer catalogue endpoint merges both.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.catalog import ClothType, DesignOption, DesignOptionGroup
from app.schemas.catalog import AdminDesignOptionGroupOut, AdminDesignOptionOut

router = APIRouter(
    prefix="/api/admin/catalog/design-options",
    tags=["admin:catalog"],
    dependencies=[Depends(require_admin)],
)


class GroupCreate(BaseModel):
    code: str
    label: str
    selection_type: str = Field(default="single", pattern="^(single|multi)$")
    is_required: bool = False
    cloth_type_id: int | None = None
    sort_order: int = 0


class GroupUpdate(BaseModel):
    label: str | None = None
    selection_type: str | None = Field(default=None, pattern="^(single|multi)$")
    is_required: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class OptionCreate(BaseModel):
    code: str
    label: str
    ai_prompt_term: str
    stitching_premium: Decimal = Field(default=Decimal("0"), ge=0)
    # Bounded deliberately. This multiplies fabric usage, so a typo of 12
    # instead of 1.2 would quote a customer twelve times the cloth — and the
    # order would then fail on stock, or succeed at an absurd price.
    fabric_multiplier: Decimal = Field(default=Decimal("1.000"), gt=0, le=3)
    sort_order: int = 0


class OptionUpdate(BaseModel):
    label: str | None = None
    ai_prompt_term: str | None = None
    stitching_premium: Decimal | None = Field(default=None, ge=0)
    fabric_multiplier: Decimal | None = Field(default=None, gt=0, le=3)
    sort_order: int | None = None
    is_active: bool | None = None


@router.get("/groups", response_model=list[AdminDesignOptionGroupOut])
def list_groups(db: Session = Depends(get_db)):
    return (
        db.query(DesignOptionGroup)
        .options(joinedload(DesignOptionGroup.options))
        .order_by(DesignOptionGroup.sort_order)
        .all()
    )


@router.post("/groups", response_model=AdminDesignOptionGroupOut, status_code=201)
def create_group(payload: GroupCreate, db: Session = Depends(get_db)):
    if payload.cloth_type_id is not None:
        if not db.query(ClothType).filter(ClothType.id == payload.cloth_type_id).first():
            raise HTTPException(status_code=404, detail="Cloth type not found")
    group = DesignOptionGroup(**payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.patch("/groups/{group_id}", response_model=AdminDesignOptionGroupOut)
def update_group(group_id: int, payload: GroupUpdate, db: Session = Depends(get_db)):
    group = db.query(DesignOptionGroup).filter(DesignOptionGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Option group not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}", status_code=204)
def deactivate_group(group_id: int, db: Session = Depends(get_db)):
    """Soft delete. Orders snapshot the option labels they used, but the group
    row is still what the wizard reads, so removing it outright would change
    what past orders appear to have been built from."""
    group = db.query(DesignOptionGroup).filter(DesignOptionGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Option group not found")
    group.is_active = False
    db.commit()


@router.post("/groups/{group_id}/options", response_model=AdminDesignOptionOut, status_code=201)
def create_option(group_id: int, payload: OptionCreate, db: Session = Depends(get_db)):
    if not db.query(DesignOptionGroup).filter(DesignOptionGroup.id == group_id).first():
        raise HTTPException(status_code=404, detail="Option group not found")
    option = DesignOption(group_id=group_id, **payload.model_dump())
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


@router.patch("/options/{option_id}", response_model=AdminDesignOptionOut)
def update_option(option_id: int, payload: OptionUpdate, db: Session = Depends(get_db)):
    option = db.query(DesignOption).filter(DesignOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Design option not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(option, key, value)
    db.commit()
    db.refresh(option)
    return option


@router.delete("/options/{option_id}", status_code=204)
def deactivate_option(option_id: int, db: Session = Depends(get_db)):
    option = db.query(DesignOption).filter(DesignOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Design option not found")
    option.is_active = False
    db.commit()
