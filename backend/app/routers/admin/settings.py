from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.settings import AppSetting

router = APIRouter(
    prefix="/api/admin/settings",
    tags=["admin:settings"],
    dependencies=[Depends(require_admin)],
)

# Settings the pricing engine reads. Editing these changes quotes immediately,
# so they're validated rather than accepted blindly — a delivery fee of "abc"
# would otherwise only surface as a 500 on the next customer quote.
NUMERIC_SETTINGS = {
    "delivery_fee",
    "free_delivery_threshold",
    "size_factor_k",
    "size_factor_min",
    "size_factor_max",
}


class SettingOut(BaseModel):
    key: str
    value: str
    label: str | None
    description: str | None
    value_type: str


class SettingUpdate(BaseModel):
    value: str


def _serialise(setting: AppSetting) -> SettingOut:
    return SettingOut(
        key=setting.key,
        value=str(setting.value),
        label=setting.label,
        description=setting.description,
        # Derived from NUMERIC_SETTINGS rather than read from the stored
        # value_type column. That column is free text and can disagree with the
        # set that actually drives validation here — in which case the admin UI
        # would offer a text input for a value the API then rejects as
        # non-numeric. One authority, no drift, and no migration needed to
        # correct rows that were seeded before this set existed.
        value_type="number" if setting.key in NUMERIC_SETTINGS else setting.value_type,
    )


@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db)):
    rows = db.query(AppSetting).order_by(AppSetting.key).all()
    return [_serialise(r) for r in rows]


@router.put("/{key}", response_model=SettingOut)
def update_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db)):
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"No setting named '{key}'")

    if key in NUMERIC_SETTINGS:
        try:
            number = float(payload.value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"'{key}' must be a number") from exc
        if number < 0:
            raise HTTPException(status_code=400, detail=f"'{key}' cannot be negative")
        # The size factor clamps bound how far fabric usage can scale with body
        # size. Inverting them would make every quote collapse to the minimum.
        if key == "size_factor_min" and number > 1:
            raise HTTPException(status_code=400, detail="size_factor_min must be <= 1")
        if key == "size_factor_max" and number < 1:
            raise HTTPException(status_code=400, detail="size_factor_max must be >= 1")

    setting.value = payload.value
    db.commit()
    db.refresh(setting)
    return _serialise(setting)
