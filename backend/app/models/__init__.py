"""Re-exports so Alembic autogenerate and `Base.metadata.create_all` see every table."""

from app.db.base import Base
from app.models.catalog import (
    ClothType,
    DesignOption,
    DesignOptionGroup,
    Material,
    MaterialColor,
    MeasurementField,
)
from app.models.order import (
    MockupGeneration,
    Order,
    OrderReferenceImage,
    OrderStatusHistory,
    SavedDesign,
)
from app.models.settings import AppSetting
from app.models.user import User, UserMeasurement

__all__ = [
    "Base",
    "User",
    "UserMeasurement",
    "ClothType",
    "MeasurementField",
    "DesignOptionGroup",
    "DesignOption",
    "Material",
    "MaterialColor",
    "Order",
    "OrderStatusHistory",
    "OrderReferenceImage",
    "SavedDesign",
    "MockupGeneration",
    "AppSetting",
]
