from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field


class MeasurementFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_key: str
    label: str
    letter: str | None
    unit: str
    min_value: Decimal
    max_value: Decimal
    is_required: bool
    affects_fabric: bool
    instructions: str | None
    sort_order: int


class DesignOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    stitching_premium: Decimal
    fabric_multiplier: Decimal


class DesignOptionGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    selection_type: str
    is_required: bool
    options: list[DesignOptionOut]


class MaterialColorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hex_code: str
    surcharge: Decimal
    # Stock is per colourway: a tailor runs out of burgundy silk, not of silk.
    stock_metres: Decimal
    low_stock_threshold: Decimal

    @computed_field
    @property
    def is_low_stock(self) -> bool:
        return self.stock_metres <= self.low_stock_threshold


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    cost_per_metre: Decimal
    stock_metres: Decimal
    low_stock_threshold: Decimal
    swatch_css: str | None
    colors: list[MaterialColorOut]

    @computed_field
    @property
    def is_low_stock(self) -> bool:
        """True when the material as a whole is short, or any single colourway
        is. A material with 100 m spread over six colours can still be unable to
        fulfil an order for the one colour a customer wants."""
        if self.colors:
            return any(c.is_low_stock for c in self.colors)
        return self.stock_metres <= self.low_stock_threshold

    @computed_field
    @property
    def total_stock_metres(self) -> Decimal:
        """Sum across colourways, which is where the cloth actually is."""
        return sum((c.stock_metres for c in self.colors), Decimal("0")) if self.colors else self.stock_metres


class AdminMaterialOut(MaterialOut):
    """Admin view of a fabric.

    Adds the active flag and the prompt term. Neither belongs on the customer
    surface: the public catalogue already filters inactive rows out, and
    ai_prompt_term is internal vocabulary fed to the image model rather than
    anything a shopper should see attached to a product.
    """

    is_active: bool
    ai_prompt_term: str
    care_notes: str | None = None


class AdminDesignOptionOut(DesignOptionOut):
    """Adds the fields the customer surface deliberately hides: the active flag
    and the prompt term the image model actually receives."""

    is_active: bool
    ai_prompt_term: str
    sort_order: int


class AdminDesignOptionGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    selection_type: str
    is_required: bool
    is_active: bool
    sort_order: int
    # NULL means the group applies to every garment — the customer endpoint
    # merges those in, so the admin needs to see which is which.
    cloth_type_id: int | None
    options: list[AdminDesignOptionOut]


class ClothTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None
    image_url: str | None
    base_price: Decimal
    production_days: int
    measurement_fields: list[MeasurementFieldOut]
    option_groups: list[DesignOptionGroupOut]


class AdminClothTypeOut(ClothTypeOut):
    """Admin view of a cloth type.

    Adds the pricing inputs and the active flag. None of these belong on the
    customer surface: `is_active` is meaningless there because the public
    catalogue endpoint already filters inactive rows out, and the cost
    components would let a client reconstruct — and therefore dispute or
    forge — a quote that the server computes deliberately on its own.
    """

    is_active: bool
    base_stitching_cost: Decimal
    base_fabric_metres: Decimal
    reference_body_cm: Decimal
    ai_prompt_noun: str
    sort_order: int
