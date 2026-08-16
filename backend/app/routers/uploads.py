import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.order import OrderReferenceImage
from app.services import storage

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


class ReferenceImageOut(BaseModel):
    id: int
    url: str
    draft_id: str
    sort_order: int


@router.post("/reference", response_model=ReferenceImageOut, status_code=status.HTTP_201_CREATED)
async def upload_reference_image(
    draft_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a design reference image at wizard Step 2.

    Images are uploaded against a client-generated `draft_id` before any order
    exists; order creation later claims them by that id.
    """
    try:
        uuid.UUID(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="draft_id must be a UUID") from exc

    existing = db.query(OrderReferenceImage).filter(OrderReferenceImage.draft_id == draft_id).count()
    if existing >= settings.max_reference_images:
        raise HTTPException(
            status_code=400,
            detail=f"A maximum of {settings.max_reference_images} reference images is allowed",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit",
        )

    # Trust the bytes, not the declared content-type — the header is client
    # supplied and trivially spoofed.
    sniffed = storage.sniff_image_type(data)
    if sniffed not in storage.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG or WEBP image")

    url = storage.save_bytes(data, prefix=f"references/{draft_id}", content_type=sniffed)

    record = OrderReferenceImage(
        draft_id=draft_id,
        url=url,
        storage_path=url,
        content_type=sniffed,
        size_bytes=len(data),
        sort_order=existing,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ReferenceImageOut(
        id=record.id, url=record.url, draft_id=record.draft_id, sort_order=record.sort_order
    )


@router.get("/reference/{draft_id}", response_model=list[ReferenceImageOut])
def list_reference_images(draft_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(OrderReferenceImage)
        .filter(OrderReferenceImage.draft_id == draft_id)
        .order_by(OrderReferenceImage.sort_order)
        .all()
    )
    return [ReferenceImageOut(id=r.id, url=r.url, draft_id=r.draft_id, sort_order=r.sort_order) for r in rows]


@router.delete("/reference/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference_image(image_id: int, db: Session = Depends(get_db)):
    record = db.query(OrderReferenceImage).filter(OrderReferenceImage.id == image_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Reference image not found")
    if record.order_id is not None:
        raise HTTPException(status_code=400, detail="Cannot delete an image already attached to an order")
    db.delete(record)
    db.commit()
