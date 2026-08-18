from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="customer")  # customer | admin
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    measurements = relationship(
        "UserMeasurement", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    orders = relationship("Order", back_populates="user")
    saved_designs = relationship("SavedDesign", back_populates="user", cascade="all, delete-orphan")


class UserMeasurement(Base):
    __tablename__ = "user_measurements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Keyed by the catalogue's own `field_key`, so a measurement field an admin
    # adds through the catalogue screen is storable the moment it exists. Fixed
    # columns could never keep up: the seeded catalogue alone uses eighteen keys.
    values = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="measurements")
