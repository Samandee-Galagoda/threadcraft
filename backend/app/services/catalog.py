from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.catalog import ClothType, DesignOption, Material, MaterialColor
from app.models.settings import AppSetting
from app.services.pricing import OptionInput, PriceBreakdown, PricingInput, calculate_price
from app.services.prompt import PromptSpec

# Fallbacks used when the settings row is missing — a fresh database or a test
# fixture that seeds only the catalogue. They match the seeded values.
DEFAULT_DELIVERY_FEE = "350"
DEFAULT_FREE_DELIVERY_THRESHOLD = "15000"


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


@dataclass
class PricedRequest:
    """Everything a caller needs after pricing a design: the resolved catalogue
    rows (so the order can snapshot them) and the breakdown itself."""

    cloth_type: ClothType
    material: Material
    color: MaterialColor | None
    options: list[DesignOption]
    breakdown: PriceBreakdown


def get_setting(db: Session, key: str, default: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return str(row.value) if row else default


def price_request(
    db: Session,
    cloth_type_id: int,
    material_id: int,
    material_color_id: int | None,
    design_option_ids: list[int],
    measurements: dict[str, float],
) -> PricedRequest:
    """Resolve a design against the catalogue and price it.

    THE single path from a customer's selections to a number. /api/quote and
    POST /api/orders both call this and nothing else.

    They used to hold byte-identical copies of this logic, each with its own
    copy of the settings lookup. That meant the price a customer was *quoted*
    and the price they were *charged* were produced by two independent code
    paths: editing one without the other would show one figure in the wizard
    and commit a different one to the order, with nothing comparing them. The
    duplication was the bug — not any particular divergence, which simply
    hadn't happened yet.
    """
    cloth_type = get_cloth_type_or_404(db, cloth_type_id)
    if not cloth_type:
        raise HTTPException(status_code=404, detail="Cloth type not found")

    material = get_material_or_404(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    color = next((c for c in material.colors if c.id == material_color_id), None)
    options = get_design_options(db, design_option_ids)

    # Fabric scales with the one measurement flagged as driving it — chest for a
    # shirt, waist for trousers — so which field that is comes from the
    # catalogue rather than being hardcoded per garment.
    primary_field = next((f for f in cloth_type.measurement_fields if f.affects_fabric), None)
    primary_body_cm = None
    if primary_field and primary_field.field_key in measurements:
        primary_body_cm = Decimal(str(measurements[primary_field.field_key]))

    pricing_input = build_pricing_input(
        cloth_type,
        material,
        color,
        options,
        primary_body_cm,
        Decimal(get_setting(db, "delivery_fee", DEFAULT_DELIVERY_FEE)),
        Decimal(get_setting(db, "free_delivery_threshold", DEFAULT_FREE_DELIVERY_THRESHOLD)),
    )
    return PricedRequest(cloth_type, material, color, options, calculate_price(pricing_input))


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
