from pydantic import BaseModel

from app.schemas.measurement import MeasurementOut
from app.schemas.order import OrderOut, SavedDesignOut


class DashboardUser(BaseModel):
    first_name: str
    last_name: str
    email: str
    created_at: str


class DashboardData(BaseModel):
    user: DashboardUser
    total_orders: int
    active_orders_count: int
    measurements_saved: bool
    measurements: MeasurementOut | None = None
    recent_orders: list[OrderOut] = []
    saved_designs: list[SavedDesignOut] = []
