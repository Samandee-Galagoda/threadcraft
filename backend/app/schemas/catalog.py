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
        return self.stock_metres <= self.low_stock_threshold


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
