from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.order import SavedDesign
from app.models.user import User
from app.schemas.order import SavedDesignCreate, SavedDesignOut

router = APIRouter(prefix="/api/designs", tags=["designs"])


@router.post("", response_model=SavedDesignOut)
def save_design(
    design_in: SavedDesignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    design = SavedDesign(user_id=current_user.id, **design_in.model_dump())
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


@router.get("", response_model=list[SavedDesignOut])
def list_saved_designs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(SavedDesign)
        .filter(SavedDesign.user_id == current_user.id)
        .order_by(SavedDesign.created_at.desc())
        .all()
    )


@router.delete("/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_design(
    design_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Discard a saved design.

    A hard delete, unlike everything in the catalogue: a saved design is the
    customer's own scratch work, referenced by no order and carrying no
    history worth preserving. Soft-deleting it would mean their dashboard
    quietly kept rows they had asked to be rid of.

    Scoped by user_id in the same query as the id, so another customer's design
    is a 404 rather than a 403 — a 403 would confirm the row exists.
    """
    design = (
        db.query(SavedDesign)
        .filter(SavedDesign.id == design_id, SavedDesign.user_id == current_user.id)
        .first()
    )
    if not design:
        raise HTTPException(status_code=404, detail="Saved design not found")
    db.delete(design)
    db.commit()
