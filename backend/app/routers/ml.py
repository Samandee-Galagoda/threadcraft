"""Endpoints backed by the three models trained on Kaggle and published to the Hub.

Every endpoint here is **assistive**: if a model is unavailable the response says
so and the caller carries on. None of this is allowed to block the ordering flow.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.catalog import ClothType
from app.services import ml as ml_service
from app.services import storage

router = APIRouter(prefix="/api/ml", tags=["ml"])


class CustomerProfile(BaseModel):
    """Body profile in ThreadCraft units: cm, kg, years. sex 1=male, 0=female."""

    height: float | None = None
    weight: float | None = None
    age: float | None = None
    sex: int | None = None
    chest: float | None = None
    waist: float | None = None
    hip: float | None = None
    shoulder: float | None = None
    sleeve: float | None = None
    collar: float | None = None
    inseam: float | None = None
    outseam: float | None = None
    thigh: float | None = None
    calf: float | None = None
    cuff: float | None = None
    ankle: float | None = None
    total_length: float | None = None


class SuggestResponse(BaseModel):
    available: bool
    suggestions: dict = Field(default_factory=dict)
    note: str


class ValidateResponse(BaseModel):
    available: bool
    warnings: list[dict] = Field(default_factory=list)
    note: str


SUGGEST_NOTE = (
    "Predicted from anthropometric data (ANSUR II). These are editable starting "
    "points, not a replacement for measuring — body proportions vary between "
    "populations."
)


@router.post("/measurements/suggest", response_model=SuggestResponse)
def suggest_measurements(profile: CustomerProfile):
    """Predict the measurements a customer hasn't taken, to pre-fill Step 4."""
    payload = profile.model_dump(exclude_none=True)
    if not payload.get("height") or not payload.get("weight"):
        raise HTTPException(status_code=400, detail="height and weight are required to predict measurements")

    result = ml_service.suggest_measurements(payload)
    if result is None:
        return SuggestResponse(
            available=False, note="Measurement predictor is not configured on this deployment."
        )
    return SuggestResponse(available=True, suggestions=result, note=SUGGEST_NOTE)


@router.post("/measurements/validate", response_model=ValidateResponse)
def validate_measurements(profile: CustomerProfile):
    """Flag entered measurements that contradict the rest of the profile."""
    payload = profile.model_dump(exclude_none=True)
    result = ml_service.validate_measurements(payload)
    if result is None:
        return ValidateResponse(
            available=False, note="Measurement validator is not configured on this deployment."
        )
    note = (
        "No inconsistencies detected."
        if not result
        else f"{len(result)} measurement(s) look inconsistent — please re-check."
    )
    return ValidateResponse(available=True, warnings=result, note=note)


class SizeRequest(CustomerProfile):
    category: str = "dress"
    rented_for: str = "everyday"
    body_type: str | None = None


class SizeResponse(BaseModel):
    available: bool
    recommendations: list[dict] = Field(default_factory=list)
    note: str


@router.post("/recommend-size", response_model=SizeResponse)
def recommend_size(payload: SizeRequest):
    """Suggest a starting size by sweeping candidates for the highest P(fit)."""
    customer = payload.model_dump(exclude_none=True)
    if customer.get("height") and customer.get("weight"):
        customer["bmi"] = round(customer["weight"] / (customer["height"] / 100) ** 2, 2)
    # The fit model was trained with these column names.
    customer["height_cm"] = customer.get("height")
    customer["weight_kg"] = customer.get("weight")

    result = ml_service.recommend_size(customer)
    if result is None:
        return SizeResponse(available=False, note="Size recommender is not configured on this deployment.")
    return SizeResponse(
        available=True,
        recommendations=result,
        note=(
            "Advisory only. Trained on rental data dominated by dresses and gowns, "
            "so treat this as a starting point rather than an authoritative size."
        ),
    )


class ClassifyResponse(BaseModel):
    available: bool
    predictions: list[dict] = Field(default_factory=list)
    matched_cloth_type_id: int | None = None
    note: str


@router.post("/classify-garment", response_model=ClassifyResponse)
async def classify_garment(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Identify the garment in an uploaded reference photo, and map it onto a
    ThreadCraft cloth type when the label corresponds to one."""
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="File too large")
    if storage.sniff_image_type(data) not in storage.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG or WEBP image")

    predictions = ml_service.classify_garment(data)
    if predictions is None:
        return ClassifyResponse(
            available=False,
            note="Garment classifier is not enabled on this deployment (ML_ENABLE_CLASSIFIER).",
        )

    # Best-effort mapping of the top label onto a configured cloth type.
    matched_id = None
    if predictions:
        top = predictions[0]["label"].lower().rstrip("s")
        for cloth_type in db.query(ClothType).filter(ClothType.is_active.is_(True)).all():
            if top in cloth_type.name.lower() or cloth_type.name.lower().rstrip("s") in top:
                matched_id = cloth_type.id
                break

    return ClassifyResponse(
        available=True,
        predictions=predictions,
        matched_cloth_type_id=matched_id,
        note="Suggested from your reference image — you can change it.",
    )


@router.get("/status")
def ml_status():
    """Which models are configured and loaded. Check before a demo."""
    return {
        "ml_enabled": settings.ml_enabled,
        "models": [
            {"name": s.name, "repo": s.repo, "loaded": s.loaded, "error": s.error}
            for s in ml_service.status()
        ],
    }


@router.post("/warm-up")
def warm_up():
    """Force-load configured models so the first real request doesn't pay the
    download cost. Worth hitting 15 minutes before a demo."""
    return {"loaded": ml_service.warm_up()}
