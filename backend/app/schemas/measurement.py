import datetime

from pydantic import BaseModel, ConfigDict, Field


class MeasurementUpdate(BaseModel):
    """A whole measurement profile, keyed by the catalogue's `field_key`.

    Deliberately open rather than a fixed set of named fields: the catalogue is
    config-driven, so an admin can add a measurement field at any time and it
    has to be storable immediately.
    """

    values: dict[str, float] = Field(default_factory=dict)


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    values: dict[str, float] = Field(default_factory=dict)
    updated_at: datetime.datetime | None = None
