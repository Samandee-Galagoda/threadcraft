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
from app.services import sizing, storage

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


class SizeEstimateRequest(CustomerProfile):
    """Height and weight are enough; any measurement the customer has already
    entered is used directly instead of being predicted."""


class SizeEstimateResponse(BaseModel):
    available: bool
    size: str | None = None
    # Per measurement: the value used, its band, and whether it was measured by
    # the customer or predicted. Without that split the customer cannot tell
    # which parts of the answer rest on a model.
    basis: dict[str, dict] = Field(default_factory=dict)
    spans_multiple_bands: bool = False
    detail: str | None = None
    note: str


SIZE_NOTE = (
    "A reference point only — UK retail charts differ by several centimetres between "
    "shops, which is exactly why ready-to-wear fit is unreliable. Your garment is cut "
    "to the measurements below, not to this size."
)


@router.post("/size-estimate", response_model=SizeEstimateResponse)
def size_estimate(payload: SizeEstimateRequest):
    """What size would this customer be off the rack?

    Composes two things with clearly separated responsibilities: the trained
    measurement predictor infers chest/waist/hip from height and weight, and a
    deterministic UK chart turns those into a band.

    This replaces the withdrawn fit recommender. Because both halves are
    monotonic in body size, the composition cannot invert — the failure that
    made the previous model unshippable is structurally impossible here rather
    than merely unobserved. See docs/testing/ml-evaluation.md.
    """
    profile = payload.model_dump(exclude_none=True)
    if not profile.get("height") or not profile.get("weight"):
        raise HTTPException(status_code=400, detail="height and weight are required to estimate a size")

    measured = {k: profile[k] for k in ("chest", "waist", "hip") if profile.get(k) is not None}

    predicted = {}
    if len(measured) < 3:
        suggestions = ml_service.suggest_measurements(profile) or {}
        predicted = {
            k: v for k, v in suggestions.items() if k in ("chest", "waist", "hip") and k not in measured
        }

    values = {**measured, **{k: v["predicted_cm"] for k, v in predicted.items()}}
    if not values:
        return SizeEstimateResponse(
            available=False,
            note="Size estimates need the measurement predictor, which is not configured here.",
        )

    estimate = sizing.estimate_size(values, sex=profile.get("sex"))
    if estimate is None:
        return SizeEstimateResponse(available=False, note="Not enough information to estimate a size.")

    basis = {
        name: {
            "value_cm": round(float(value), 1),
            "band": estimate.per_measurement.get(name),
            "source": "measured" if name in measured else "predicted",
            "confidence_cm": predicted.get(name, {}).get("confidence_cm"),
        }
        for name, value in values.items()
    }

    return SizeEstimateResponse(
        available=True,
        size=estimate.size,
        basis=basis,
        spans_multiple_bands=estimate.spans_multiple_bands,
        detail=estimate.note,
        note=SIZE_NOTE,
    )


# Below this, a suggestion is noise presented as advice.
#
# Chosen from measured behaviour, not taste. On the 60x80 catalogue images the
# model was trained on, correct predictions mostly score 0.5-0.96 while its
# mistakes sit at 0.23-0.49. On ordinary photographs — which is what a customer
# actually uploads — the surviving sellable labels score 0.04-0.26, i.e. noise.
# A floor here means the feature answers confidently on inputs it can handle and
# stays quiet on the ones it cannot, rather than offering "that looks like a
# Kurta (4% confidence)".
MIN_CLASSIFIER_CONFIDENCE = 0.35


def _match_key(value: str) -> str:
    """Normalise a garment name or model label for comparison.

    Lowercases, drops non-alphanumerics and trims a trailing plural, so
    "T-shirt", "tshirt" and "Tshirts" all collapse to the same key.
    """
    stripped = "".join(ch for ch in value.lower() if ch.isalnum())
    return stripped[:-1] if stripped.endswith("s") else stripped


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

    # Only surface predictions that name something ThreadCraft actually tailors.
    #
    # The model has 25 classes from a retail catalogue, including Bra, Briefs,
    # Trunk and Innerwear Vests — none of which are orderable here, so suggesting
    # one is wrong by construction. That is not hypothetical: on ordinary
    # photographs (as opposed to the 60x80 catalogue images it was trained on) it
    # returns "Bra" at 0.5-0.7 confidence for dresses, kurtas and skirts. See
    # docs/testing/ml-evaluation.md section 3.1. Filtering to the sellable
    # catalogue turns a confidently absurd suggestion into no suggestion, which
    # is the honest outcome for an input the model cannot handle.
    cloth_types = db.query(ClothType).filter(ClothType.is_active.is_(True)).all()
    matched_id, sellable = None, []
    for prediction in predictions:
        if prediction.get("score", 0) < MIN_CLASSIFIER_CONFIDENCE:
            continue
        label = _match_key(prediction["label"])
        for cloth_type in cloth_types:
            # Compared against the slug as well as the name: the seeded name is
            # "T-shirt" while the model's label is "Tshirts", and the previous
            # substring test never matched them because of the hyphen.
            candidates = {_match_key(cloth_type.name), _match_key(cloth_type.slug)}
            if any(label and (label in c or c in label) for c in candidates):
                sellable.append(prediction)
                if matched_id is None:
                    matched_id = cloth_type.id
                break

    if not sellable:
        return ClassifyResponse(
            available=True,
            note="We couldn't match that photo to a garment we tailor — please pick the type yourself.",
        )

    return ClassifyResponse(
        available=True,
        predictions=sellable,
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
