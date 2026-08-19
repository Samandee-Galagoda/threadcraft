import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base

# Valid order statuses, in fulfilment order. Kept as plain strings (not a native
# DB enum) so tests can run against SQLite without a Postgres-only type.
ORDER_STATUSES = ["received", "fabric_cut", "stitching", "qc", "dispatched", "cancelled"]


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), unique=True, index=True, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    guest_email = Column(String(255), nullable=True)
    guest_name = Column(String(200), nullable=True)

    # Delivery details, captured at checkout. Applies to signed-in customers as
    # well as guests: the name and address on the parcel are not necessarily the
    # ones on the account.
    #
    # There is deliberately no card column here, and there should never be one.
    # Card details go to Stripe from the browser and never reach this server.
    customer_name = Column(String(200), nullable=True)
    customer_phone = Column(String(40), nullable=True)
    delivery_address = Column(Text, nullable=True)
    delivery_city = Column(String(120), nullable=True)
    delivery_postcode = Column(String(20), nullable=True)

    # Catalogue references (nullable — a cloth type could be deactivated after ordering)
    cloth_type_id = Column(Integer, ForeignKey("cloth_types.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    material_color_id = Column(Integer, ForeignKey("material_colors.id", ondelete="SET NULL"), nullable=True)

    # Snapshots — immutable at order time, independent of later catalogue edits
    cloth_type_name = Column(String(100), nullable=False)
    material_name = Column(String(100), nullable=False)
    color_name = Column(String(60))
    color_hex = Column(String(7))
    design_options_snapshot = Column(JSON, nullable=False, default=list)
    measurements_snapshot = Column(JSON, nullable=False, default=dict)
    custom_description = Column(Text)

    # Pricing — server-computed, never trusted from the client
    fabric_metres_used = Column(Numeric(6, 2), nullable=False)
    price_base = Column(Numeric(10, 2), nullable=False)
    price_stitching = Column(Numeric(10, 2), nullable=False)
    price_material = Column(Numeric(10, 2), nullable=False)
    price_delivery = Column(Numeric(10, 2), nullable=False)
    price_total = Column(Numeric(10, 2), nullable=False)
    price_breakdown = Column(JSON, nullable=False, default=list)
    currency = Column(String(3), nullable=False, default="LKR")

    # AI mockup
    mockup_url = Column(String(500))
    mockup_prompt = Column(Text)
    mockup_model = Column(String(120))
    mockup_generated_at = Column(DateTime(timezone=True))

    # Fulfilment + payment
    status = Column(String(30), nullable=False, default="received")
    payment_status = Column(String(20), nullable=False, default="pending")  # pending|paid|failed|refunded
    stripe_session_id = Column(String(255))
    stripe_payment_intent_id = Column(String(255))
    paid_at = Column(DateTime(timezone=True))
    dispatched_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )
    reference_images = relationship(
        "OrderReferenceImage", back_populates="order", cascade="all, delete-orphan"
    )


class OrderStatusHistory(Base):
    """Powers both the fulfilment workflow and average-fulfilment-time analytics."""

    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="status_history")


class OrderReferenceImage(Base):
    """Reference images uploaded at wizard Step 2, before an order necessarily
    exists — claimed by draft_id once the order is created."""

    __tablename__ = "order_reference_images"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True)
    draft_id = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()), index=True)

    url = Column(String(500), nullable=False)
    storage_path = Column(String(500), nullable=False)
    content_type = Column(String(60))
    size_bytes = Column(Integer)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="reference_images")


class SavedDesign(Base):
    __tablename__ = "saved_designs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(120), nullable=False)
    cloth_type_id = Column(Integer, ForeignKey("cloth_types.id", ondelete="SET NULL"), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    estimated_total = Column(Numeric(10, 2))
    mockup_url = Column(String(500))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="saved_designs")


class MockupGeneration(Base):
    """Every AI generation attempt is logged here — this table is what auto-
    accumulates the 30-output evaluation set the testing report requires."""

    __tablename__ = "mockup_generations"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text)
    model_id = Column(String(150), nullable=False)
    image_url = Column(String(500))
    latency_ms = Column(Integer)
    success = Column(String(10), nullable=False, default="true")  # "true" | "false" | "fallback"
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
