from fastapi import APIRouter, Depends
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
