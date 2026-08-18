from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClothType(Base):
    """An admin-configurable garment category — the thing that must be addable
    without code changes per the proposal's functional requirements."""

    __tablename__ = "cloth_types"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(60), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))

    base_price = Column(Numeric(10, 2), nullable=False)
    base_stitching_cost = Column(Numeric(10, 2), nullable=False, default=0)
    base_fabric_metres = Column(Numeric(6, 2), nullable=False)
    reference_body_cm = Column(Numeric(6, 2), nullable=False, default=90)
    ai_prompt_noun = Column(String(200), nullable=False)

    production_days = Column(Integer, nullable=False, default=7)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    measurement_fields = relationship(
        "MeasurementField",
        back_populates="cloth_type",
        cascade="all, delete-orphan",
        order_by="MeasurementField.sort_order",
    )
    option_groups = relationship(
        "DesignOptionGroup", back_populates="cloth_type", cascade="all, delete-orphan"
    )


class MeasurementField(Base):
    """Per-garment measurement input spec — replaces the hardcoded 8-column
    Measurement table and the frontend's MEASUREMENT_DATA literal."""

    __tablename__ = "measurement_fields"
    __table_args__ = (UniqueConstraint("cloth_type_id", "field_key"),)

    id = Column(Integer, primary_key=True, index=True)
    cloth_type_id = Column(Integer, ForeignKey("cloth_types.id", ondelete="CASCADE"), nullable=False)

    field_key = Column(String(50), nullable=False)
    label = Column(String(100), nullable=False)
    letter = Column(String(2))  # the A/B/C badge already styled by .td-letter
    unit = Column(String(10), nullable=False, default="cm")
    min_value = Column(Numeric(6, 2), nullable=False)
    max_value = Column(Numeric(6, 2), nullable=False)
    is_required = Column(Boolean, nullable=False, default=True)
    affects_fabric = Column(Boolean, nullable=False, default=False)  # feeds the pricing size factor
    instructions = Column(Text)
    sort_order = Column(Integer, nullable=False, default=0)

    cloth_type = relationship("ClothType", back_populates="measurement_fields")


class DesignOptionGroup(Base):
    """Fit / Neckline / Sleeve / Pattern — the Step 2 tag categories."""

    __tablename__ = "design_option_groups"
    __table_args__ = (UniqueConstraint("cloth_type_id", "code"),)

    id = Column(Integer, primary_key=True, index=True)
    cloth_type_id = Column(Integer, ForeignKey("cloth_types.id", ondelete="CASCADE"), nullable=True)

    code = Column(String(40), nullable=False)
    label = Column(String(100), nullable=False)
    selection_type = Column(String(10), nullable=False, default="single")  # single | multi
    is_required = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    cloth_type = relationship("ClothType", back_populates="option_groups")
    options = relationship(
        "DesignOption",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="DesignOption.sort_order",
    )


class DesignOption(Base):
    """The tags themselves — e.g. 'Puffed sleeve'. ai_prompt_term decouples the
    UI label from the diffusion prompt vocabulary; stitching_premium and
    fabric_multiplier make pricing configuration-driven, not code-driven."""

    __tablename__ = "design_options"
    __table_args__ = (UniqueConstraint("group_id", "code"),)

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("design_option_groups.id", ondelete="CASCADE"), nullable=False)

    code = Column(String(60), nullable=False)
    label = Column(String(100), nullable=False)
    ai_prompt_term = Column(String(200), nullable=False)
    stitching_premium = Column(Numeric(10, 2), nullable=False, default=0)
    fabric_multiplier = Column(Numeric(4, 3), nullable=False, default=1.000)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    group = relationship("DesignOptionGroup", back_populates="options")


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(60), unique=True, nullable=False)
    name = Column(String(100), nullable=False)

    cost_per_metre = Column(Numeric(10, 2), nullable=False)
    stock_metres = Column(Numeric(10, 2), nullable=False, default=0)
    low_stock_threshold = Column(Numeric(10, 2), nullable=False, default=20)

    swatch_css = Column(String(200))  # preserves the existing gradient swatches
    ai_prompt_term = Column(String(200), nullable=False)
    care_notes = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    colors = relationship("MaterialColor", back_populates="material", cascade="all, delete-orphan")


class MaterialColor(Base):
    __tablename__ = "material_colors"
    __table_args__ = (UniqueConstraint("material_id", "name"),)

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(60), nullable=False)
    hex_code = Column(String(7), nullable=False)
    ai_prompt_term = Column(String(120), nullable=False)
    surcharge = Column(Numeric(10, 2), nullable=False, default=0)
    # Stock is tracked per colourway, not per material: a tailor runs out of
    # burgundy silk, not of "silk". Material.stock_metres is only used for a
    # material that has no colours at all.
    stock_metres = Column(Numeric(10, 2), nullable=False, default=0)
    low_stock_threshold = Column(Numeric(10, 2), nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)

    material = relationship("Material", back_populates="colors")
