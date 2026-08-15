from sqlalchemy import JSON, Column, DateTime, String, Text, func

from app.db.base import Base


class AppSetting(Base):
    """Admin-editable global configuration — delivery fee, free-delivery
    threshold, AI prompt template, etc. Avoids hardcoding business constants
    that a non-technical admin might reasonably need to change."""

    __tablename__ = "app_settings"

    key = Column(String(60), primary_key=True)
    value = Column(JSON, nullable=False)
    label = Column(String(120))
    description = Column(Text)
    value_type = Column(String(20), nullable=False, default="string")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
