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

    # Contact and delivery. Required for every order — a made-to-measure garment
    # is a physical thing that has to arrive somewhere, and the previous schema
    # took payment without ever asking where.
    #
    # Note the absence of card fields. Those go from the browser to Stripe and
    # never reach this API, so there is nothing here to accidentally log or store.
    guest_email: EmailStr | None = None
    guest_name: str | None = None
    customer_name: str | None = Field(default=None, max_length=200)
    customer_phone: str | None = Field(default=None, max_length=40)
    delivery_address: str | None = None
    delivery_city: str | None = Field(default=None, max_length=120)
    delivery_postcode: str | None = Field(default=None, max_length=20)


class OrderStatusUpdate(BaseModel):
    status: str
    note: str | None = None


class OrderCancel(BaseModel):
    """Customer-initiated cancellation.

    guest_email is the second factor for orders placed without an account: the
    order number alone identifies an order but must not be enough to destroy
    one, since it appears on printed paperwork.
    """

    guest_email: EmailStr | None = None
    reason: str | None = None


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


class DeliveryOut(BaseModel):
    """Where an order is going. Admin-only — it is personal data, and the public
    tracking endpoint is reachable with nothing but an order number."""

    customer_name: str | None = None
    customer_phone: str | None = None
    delivery_address: str | None = None
    delivery_city: str | None = None
    delivery_postcode: str | None = None


class AdminOrderOut(OrderOut, DeliveryOut):
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


class ReorderPlan(BaseModel):
    """A past order re-resolved against the current catalogue, ready to load
    into the wizard. Anything discontinued is named in `unavailable` rather than
    silently dropped."""

    cloth_type_id: int | None = None
    cloth_type_slug: str | None = None
    material_id: int | None = None
    material_color_id: int | None = None
    design_option_ids: list[int] = Field(default_factory=list)
    measurements: dict = Field(default_factory=dict)
    unavailable: list[str] = Field(default_factory=list)


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
