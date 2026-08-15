import datetime

from pydantic import BaseModel, ConfigDict


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
    model_config = ConfigDict(from_attributes=True)

    bust: float
    waist: float
    hip: float
    shoulder: float
    sleeve: float
    total_length: float
    chest: float
    inseam: float
    updated_at: datetime.datetime
