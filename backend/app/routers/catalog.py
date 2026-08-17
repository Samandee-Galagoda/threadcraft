from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.catalog import ClothType, DesignOptionGroup, Material
from app.schemas.catalog import ClothTypeOut, DesignOptionGroupOut, MaterialOut

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


def _serialize_group(group: DesignOptionGroup) -> DesignOptionGroupOut:
    """Serialise a group, dropping its deactivated options.

    The group-level is_active filter is applied in the query, but individual
    options were never filtered at all: DesignOption.is_active existed on the
    model and no read path consulted it, so deactivating a single option left
    it visible and selectable in the wizard — and priceable, since /api/quote
    resolves options by id. Filtering here rather than on the relationship
    keeps deactivated rows visible to the admin, which is the whole point of a
    soft delete.
    """
    out = DesignOptionGroupOut.model_validate(group)
    active_ids = {o.id for o in group.options if o.is_active}
    out.options = [o for o in out.options if o.id in active_ids]
    return out


def _global_option_groups(db: Session) -> list[DesignOptionGroupOut]:
    """Design-option groups seeded with cloth_type_id=None apply to every
    garment (fit/neckline/sleeve/pattern) — they must be merged into each
    cloth type's response alongside any garment-specific groups, since the
    ORM relationship on ClothType only sees groups tied to that specific id."""
    groups = (
        db.query(DesignOptionGroup)
        .options(joinedload(DesignOptionGroup.options))
        .filter(DesignOptionGroup.cloth_type_id.is_(None), DesignOptionGroup.is_active.is_(True))
        .order_by(DesignOptionGroup.sort_order)
        .all()
    )
    return [_serialize_group(g) for g in groups]


def _serialize_cloth_type(cloth_type: ClothType, global_groups: list[DesignOptionGroupOut]) -> ClothTypeOut:
    out = ClothTypeOut.model_validate(cloth_type)
    specific_groups = [_serialize_group(g) for g in cloth_type.option_groups if g.is_active]
    out.option_groups = global_groups + specific_groups
    return out


def _serialize_material(material: Material) -> MaterialOut:
    """Same omission as options: MaterialColor.is_active was never read, so a
    withdrawn colourway stayed selectable and kept applying its surcharge."""
    out = MaterialOut.model_validate(material)
    active_ids = {c.id for c in material.colors if c.is_active}
    out.colors = [c for c in out.colors if c.id in active_ids]
    return out


@router.get("/cloth-types", response_model=list[ClothTypeOut])
def list_cloth_types(db: Session = Depends(get_db)):
    cloth_types = (
        db.query(ClothType)
        .options(
            joinedload(ClothType.measurement_fields),
            joinedload(ClothType.option_groups).joinedload(DesignOptionGroup.options),
        )
        .filter(ClothType.is_active.is_(True))
        .order_by(ClothType.sort_order)
        .all()
    )
    global_groups = _global_option_groups(db)
    return [_serialize_cloth_type(ct, global_groups) for ct in cloth_types]


@router.get("/cloth-types/{slug}", response_model=ClothTypeOut)
def get_cloth_type(slug: str, db: Session = Depends(get_db)):
    cloth_type = (
        db.query(ClothType)
        .options(
            joinedload(ClothType.measurement_fields),
            joinedload(ClothType.option_groups).joinedload(DesignOptionGroup.options),
        )
        .filter(ClothType.slug == slug, ClothType.is_active.is_(True))
        .first()
    )
    if not cloth_type:
        raise HTTPException(status_code=404, detail="Cloth type not found")
    return _serialize_cloth_type(cloth_type, _global_option_groups(db))


@router.get("/materials", response_model=list[MaterialOut])
def list_materials(db: Session = Depends(get_db)):
    materials = (
        db.query(Material).options(joinedload(Material.colors)).filter(Material.is_active.is_(True)).all()
    )
    return [_serialize_material(m) for m in materials]
