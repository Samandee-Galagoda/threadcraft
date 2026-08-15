from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    measurements = relationship("Measurement", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    saved_designs = relationship("SavedDesign", back_populates="user", cascade="all, delete-orphan")

class Measurement(Base):
    __tablename__ = "measurements"

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
    
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="measurements")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    cloth_type = Column(String(100), nullable=False)
    material = Column(String(100), nullable=False)
    fit = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), default="Received") # Received, Stitching, Dispatched, etc.
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")

class SavedDesign(Base):
    __tablename__ = "saved_designs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(100), nullable=False)
    material = Column(String(100), nullable=True)
    color = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="saved_designs")
