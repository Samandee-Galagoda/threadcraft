import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class QuoteRequest(BaseModel):
    cloth_type_id: int
    material_id: int
    material_color_id: int | None = None
    design_option_ids: list[int] = Field(default_factory=list)
    measurements: dict[str, float] = Field(default_factory=dict)


class LineItemOut(BaseModel):
    label: str
    amount: Decimal
    category: str


class QuoteResponse(BaseModel):
    lines: list[LineItemOut]
    fabric_metres: Decimal
    base: Decimal
    stitching: Decimal
    material: Decimal
    delivery: Decimal
    total: Decimal
    currency: str = "LKR"


class OrderCreate(BaseModel):
    cloth_type_id: int
    material_id: int
    material_color_id: int | None = None
    design_option_ids: list[int] = Field(default_factory=list)
    measurements: dict[str, float] = Field(default_factory=dict)
    custom_description: str = ""
    draft_id: str | None = None  # claims any reference images uploaded under this draft
    mockup_url: str | None = None
    mockup_prompt: str | None = None
    mockup_model: str | None = None

    # Only used for guest checkout — ignored if the caller is authenticated
    guest_email: EmailStr | None = None
    guest_name: str | None = None


class OrderStatusUpdate(BaseModel):
    status: str
    note: str | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_number: str
    cloth_type_name: str
    material_name: str
    color_name: str | None
    design_options_snapshot: list
    measurements_snapshot: dict
    fabric_metres_used: Decimal
    price_total: Decimal
    price_breakdown: list
    currency: str
    mockup_url: str | None
    status: str
    payment_status: str
    created_at: datetime.datetime


class AdminOrderOut(OrderOut):
    """Admin view of an order.

    Exposes the numeric primary key, which OrderOut deliberately omits: the
    customer-facing surface identifies orders by `order_number` only, since a
    sequential id is guessable and would let anyone enumerate other people's
    orders through the public tracking endpoint. Admin routes are already
    behind require_admin, and the status-update endpoint is keyed by id, so
    without this the admin UI has no way to act on a listed order.
    """

    id: int
    guest_email: str | None = None
    guest_name: str | None = None
    custom_description: str | None = None
    updated_at: datetime.datetime | None = None


class SavedDesignCreate(BaseModel):
    name: str
    cloth_type_id: int | None = None
    payload: dict = Field(default_factory=dict)
    estimated_total: Decimal | None = None
    mockup_url: str | None = None


class SavedDesignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cloth_type_id: int | None
    payload: dict
    estimated_total: Decimal | None
    mockup_url: str | None
    created_at: datetime.datetime
