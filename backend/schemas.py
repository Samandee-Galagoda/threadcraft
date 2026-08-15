from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
import datetime
from decimal import Decimal

# Authentication Schemas
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict

# Measurement Schemas
class MeasurementUpdate(BaseModel):
    bust: float
    waist: float
    hip: float
    shoulder: float
    sleeve: float
    total_length: float
    chest: float
    inseam: float

class MeasurementOut(BaseModel):
    bust: float
    waist: float
    hip: float
    shoulder: float
    sleeve: float
    total_length: float
    chest: float
    inseam: float
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# Order Schemas
class OrderCreate(BaseModel):
    clothType: str
    fit: str
    material: str
    price: Optional[float] = 0.0
    measurements: Optional[Dict[str, float]] = None

class OrderOut(BaseModel):
    order_number: str
    cloth_type: str
    material: str
    fit: str
    price: Decimal
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Saved Design Schemas
class SavedDesignCreate(BaseModel):
    name: str
    material: Optional[str] = None
    color: Optional[str] = None
    details: Optional[str] = None

class SavedDesignOut(BaseModel):
    id: int
    name: str
    material: Optional[str] = None
    color: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Dashboard Schema (Combined response)
class DashboardData(BaseModel):
    user: Dict
    total_orders: int
    active_orders_count: int
    measurements_saved: bool
    measurements: Optional[MeasurementOut] = None
    recent_orders: List[OrderOut] = []
    saved_designs: List[SavedDesignOut] = []
