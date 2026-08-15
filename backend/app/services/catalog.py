from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.catalog import ClothType, DesignOption, Material, MaterialColor
from app.services.pricing import OptionInput, PricingInput
from app.services.prompt import PromptSpec


def get_active_cloth_types(db: Session) -> list[ClothType]:
    return db.query(ClothType).filter(ClothType.is_active.is_(True)).order_by(ClothType.sort_order).all()


def get_cloth_type_or_404(db: Session, cloth_type_id: int) -> ClothType | None:
    return db.query(ClothType).filter(ClothType.id == cloth_type_id).first()


def get_material_or_404(db: Session, material_id: int) -> Material | None:
    return db.query(Material).filter(Material.id == material_id).first()


def get_design_options(db: Session, option_ids: list[int]) -> list[DesignOption]:
    if not option_ids:
        return []
    return db.query(DesignOption).filter(DesignOption.id.in_(option_ids)).all()


def build_pricing_input(
    cloth_type: ClothType,
    material: Material,
    color: MaterialColor | None,
    options: list[DesignOption],
    primary_body_cm: Decimal | None,
    delivery_fee: Decimal,
    free_delivery_threshold: Decimal,
) -> PricingInput:
    return PricingInput(
        cloth_type_name=cloth_type.name,
        base_price=Decimal(str(cloth_type.base_price)),
        base_stitching_cost=Decimal(str(cloth_type.base_stitching_cost)),
        base_fabric_metres=Decimal(str(cloth_type.base_fabric_metres)),
        reference_body_cm=Decimal(str(cloth_type.reference_body_cm)),
        material_name=material.name,
        material_cost_per_metre=Decimal(str(material.cost_per_metre)),
        colour_surcharge=Decimal(str(color.surcharge)) if color else Decimal("0"),
        options=tuple(
            OptionInput(
                code=o.code,
                label=o.label,
                stitching_premium=Decimal(str(o.stitching_premium)),
                fabric_multiplier=Decimal(str(o.fabric_multiplier)),
            )
            for o in options
        ),
        primary_body_cm=primary_body_cm,
        delivery_fee=delivery_fee,
        free_delivery_threshold=free_delivery_threshold,
    )


def build_prompt_spec(
    cloth_type: ClothType,
    material: Material,
    color: MaterialColor | None,
    options: list[DesignOption],
    custom_description: str,
) -> PromptSpec:
    return PromptSpec(
        cloth_type_term=cloth_type.ai_prompt_noun,
        option_terms=tuple(o.ai_prompt_term for o in options),
        material_term=material.ai_prompt_term,
        colour_term=color.ai_prompt_term if color else "",
        custom_description=custom_description or "",
    )
