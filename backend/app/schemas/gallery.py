import datetime

from pydantic import BaseModel


class GalleryItem(BaseModel):
    """One AI preview, stripped of everything that could identify who ordered it."""

    image_url: str
    cloth_type: str | None = None
    material: str | None = None
    colour: str | None = None
    created_at: datetime.datetime | None = None
