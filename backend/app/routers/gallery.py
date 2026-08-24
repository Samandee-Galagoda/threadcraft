"""Public gallery of AI previews that customers have actually ordered.

Two things make this more than a `SELECT ... LIMIT 12`.

**Nothing identifying leaves here.** An order row carries a name, a phone
number and a delivery address; a gallery entry carries the picture and the
garment, fabric and colour it was made in. The customer's own description is
withheld too — they wrote it for the tailor, not for the shop window.

**A row is not a picture.** Mockups saved by the local storage backend live on
the instance's disk, and Render's free tier gives each deploy a fresh one, so
the database happily lists images that no longer exist anywhere. Serving those
would fill the page with broken thumbnails, which reads as a broken site rather
than an empty one. Local paths are therefore checked against the filesystem
before being offered, and only R2-backed absolute URLs are trusted blind.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.order import Order
from app.schemas.gallery import GalleryItem
from app.services import storage

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


@router.get("", response_model=list[GalleryItem])
def list_gallery(
    limit: int = Query(default=12, ge=1, le=48),
    db: Session = Depends(get_db),
):
    """Recent customer designs, newest first."""
    # Over-fetched because the existence check below discards rows, and a page
    # asking for 12 should still get 12 when some images have expired.
    candidates = (
        db.query(Order)
        .filter(Order.mockup_url.isnot(None), Order.mockup_url != "")
        .order_by(Order.id.desc())
        .limit(limit * 4)
        .all()
    )

    items: list[GalleryItem] = []
    seen: set[str] = set()
    for order in candidates:
        url = order.mockup_url
        # The same cached generation can back several orders — showing it twice
        # makes a small gallery look smaller.
        if url in seen or not storage.media_exists(url):
            continue
        seen.add(url)
        items.append(
            GalleryItem(
                image_url=url,
                cloth_type=order.cloth_type_name,
                material=order.material_name,
                colour=order.color_name,
                created_at=order.created_at,
            )
        )
        if len(items) >= limit:
            break

    return items
