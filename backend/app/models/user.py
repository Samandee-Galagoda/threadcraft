from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func
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

    bust = Column(Float, default=0.0)
    waist = Column(Float, default=0.0)
    hip = Column(Float, default=0.0)
    shoulder = Column(Float, default=0.0)
    sleeve = Column(Float, default=0.0)
    total_length = Column(Float, default=0.0)
    chest = Column(Float, default=0.0)
    inseam = Column(Float, default=0.0)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="measurements")
