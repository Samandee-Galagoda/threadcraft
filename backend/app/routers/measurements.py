from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserMeasurement
from app.schemas.measurement import MeasurementOut, MeasurementUpdate

router = APIRouter(prefix="/api/measurements", tags=["measurements"])


@router.get("", response_model=MeasurementOut)
def get_measurements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The signed-in customer's saved measurements.

    An empty map rather than a 404 when nothing is saved: "you have not measured
    yourself yet" is a normal state for the profile screen, not an error.
    """
    meas = db.query(UserMeasurement).filter(UserMeasurement.user_id == current_user.id).first()
    if not meas:
        return MeasurementOut(values={}, updated_at=None)
    return meas


@router.put("", response_model=MeasurementOut)
def update_measurements(
    meas_in: MeasurementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Replace the saved profile.

    Blank entries are dropped rather than stored as 0: a measurement the
    customer has not taken is missing, and recording it as zero would both look
    measured and skew the ML validator that compares fields against each other.
    """
    meas = db.query(UserMeasurement).filter(UserMeasurement.user_id == current_user.id).first()
    if not meas:
        meas = UserMeasurement(user_id=current_user.id)
        db.add(meas)

    meas.values = {key: float(value) for key, value in meas_in.values.items() if value}

    db.commit()
    db.refresh(meas)
    return meas
