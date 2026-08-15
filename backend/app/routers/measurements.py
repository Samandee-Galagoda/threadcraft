from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserMeasurement
from app.schemas.measurement import MeasurementOut, MeasurementUpdate

router = APIRouter(prefix="/api/measurements", tags=["measurements"])


@router.put("", response_model=MeasurementOut)
def update_measurements(
    meas_in: MeasurementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meas = db.query(UserMeasurement).filter(UserMeasurement.user_id == current_user.id).first()
    if not meas:
        meas = UserMeasurement(user_id=current_user.id)
        db.add(meas)

    for key, value in meas_in.model_dump().items():
        setattr(meas, key, value)

    db.commit()
    db.refresh(meas)
    return meas
