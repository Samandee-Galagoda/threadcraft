"""Integration for the three models trained on Kaggle and published to the Hub.

Design points that matter for a free-tier deployment:

- **Lazy loading.** Nothing is downloaded at import time. A model is fetched on
  first use and cached in-process. Cold start therefore stays fast, and the app
  boots fine on a host with no HF access at all.
- **Never fatal.** If a model is unconfigured, unreachable, or fails to load,
  the corresponding endpoint reports it as unavailable rather than 500-ing.
  These are assistive features; none of them should be able to take down
  checkout.
- **The classifier is optional even when configured** — it pulls a ~350 MB ViT,
  which is more than a 512 MB free-tier instance can comfortably hold alongside
  the app. `ML_ENABLE_CLASSIFIER` gates it separately for that reason.
"""

import threading
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

# How long a failed load is remembered before another attempt is allowed.
#
# Failures used to be cached for the life of the process. On Render the process
# is long-lived, so a single Hub 503 or a DNS blip during boot silently disabled
# that model until the next redeploy — with /api/ml/status the only evidence it
# had happened. A sliding window lets it heal on its own.
MODEL_RETRY_AFTER_SECONDS = 300

_lock = threading.Lock()
_cache: dict[str, Any] = {}


@dataclass(frozen=True)
class _Failure:
    at: float  # time.monotonic() — wall clock would break if the host clock steps
    message: str
    retryable: bool


_failures: dict[str, _Failure] = {}


@dataclass
class ModelStatus:
    name: str
    repo: str | None
    loaded: bool
    error: str | None
    retryable: bool = True


def _load(name: str, loader) -> Any | None:
    """Load once and cache. Failures are remembered so we don't retry on every
    request, but only for MODEL_RETRY_AFTER_SECONDS — a transient network fault
    must not black out an assistive feature until someone notices and redeploys."""
    if name in _cache:
        return _cache[name]

    failure = _failures.get(name)
    if failure is not None and (
        not failure.retryable or (time.monotonic() - failure.at) < MODEL_RETRY_AFTER_SECONDS
    ):
        return None

    with _lock:
        if name in _cache:
            return _cache[name]
        try:
            _cache[name] = loader()
            _failures.pop(name, None)
            return _cache[name]
        except Exception as exc:  # noqa: BLE001
            # A missing dependency is not transient: no amount of retrying
            # installs transformers. Everything else — network, HTTP, unpickling,
            # a version mismatch — is worth another attempt later, and retries
            # are cheap because the artefact is already in the local HF cache.
            retryable = not isinstance(exc, ImportError)
            message = f"{type(exc).__name__}: {exc}"
            _failures[name] = _Failure(at=time.monotonic(), message=message, retryable=retryable)
            print(f"[ml] failed to load {name}: {message}" + ("" if retryable else " (not retryable)"))
            return None


def reset_cache() -> None:
    """Drop every cached model and remembered failure.

    Exists for the test suite, which previously reached into the two private
    dicts directly — coupling that breaks silently when their shape changes,
    because `.clear()` works on any dict.
    """
    with _lock:
        _cache.clear()
        _failures.clear()


# ── Measurement predictor ────────────────────────────────────────────────


def _load_measurement():
    import joblib
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(settings.measurement_repo, "measurement_predictor.joblib")
    return joblib.load(path)


def measurement_available() -> bool:
    return bool(settings.ml_enabled and settings.measurement_repo)


def suggest_measurements(customer: dict) -> dict | None:
    """Predict the measurements the customer hasn't supplied.

    `customer` uses ThreadCraft field names in cm (plus weight in kg, age in
    years, sex 1=male/0=female).
    """
    if not measurement_available():
        return None
    art = _load("measurement", _load_measurement)
    if art is None:
        return None

    import numpy as np
    import pandas as pd

    targets = art["targets"]
    base = art["base_features"]
    known = [k for k in targets if customer.get(k) is not None]

    row = {f: customer.get(f) for f in set(base) | set(targets)}
    if customer.get("height") and customer.get("weight"):
        row["bmi"] = round(customer["weight"] / (customer["height"] / 100) ** 2, 2)
    frame = pd.DataFrame([{k: (np.nan if v is None else v) for k, v in row.items()}])

    out = {}
    for target in targets:
        if target in known:
            continue
        feats = art["feature_sets"][target]
        X = frame.reindex(columns=feats).copy()
        for col in feats:
            if col not in base and col not in known:
                X[col] = np.nan
        value = float(art["models"][target].predict(X)[0])
        out[target] = {
            "predicted_cm": round(value, 1),
            "confidence_cm": round(art["thresholds"][target] / 2.5, 1),
        }
    return out


def validate_measurements(customer: dict) -> list[dict] | None:
    """Flag supplied measurements that contradict the rest of the profile."""
    if not measurement_available():
        return None
    art = _load("measurement", _load_measurement)
    if art is None:
        return None

    import numpy as np
    import pandas as pd

    targets = art["targets"]
    base = art["base_features"]
    supplied = [k for k in targets if customer.get(k) is not None]

    row = {f: customer.get(f) for f in set(base) | set(targets)}
    if customer.get("height") and customer.get("weight"):
        row["bmi"] = round(customer["weight"] / (customer["height"] / 100) ** 2, 2)
    frame = pd.DataFrame([{k: (np.nan if v is None else v) for k, v in row.items()}])

    warnings = []
    for field in supplied:
        others = [k for k in supplied if k != field]
        feats = art["feature_sets"][field]
        X = frame.reindex(columns=feats).copy()
        for col in feats:
            if col not in base and col not in others:
                X[col] = np.nan
        expected = float(art["models"][field].predict(X)[0])
        deviation = abs(customer[field] - expected)
        if deviation > art["thresholds"][field]:
            warnings.append(
                {
                    "field": field,
                    "entered_cm": customer[field],
                    "expected_cm": round(expected, 1),
                    "deviation_cm": round(deviation, 1),
                    "message": (
                        f"Your {field.replace('_', ' ')} of {customer[field]} cm looks "
                        f"inconsistent with your other measurements (we'd expect around "
                        f"{expected:.0f} cm). Please double-check it."
                    ),
                }
            )
    return warnings


# ── Garment classifier ───────────────────────────────────────────────────


def _load_classifier():
    from transformers import pipeline

    return pipeline("image-classification", model=settings.classifier_repo, device=-1)


def classifier_available() -> bool:
    # Gated separately: the ViT is ~350 MB, which is a lot for a 512 MB free
    # instance to hold alongside the app.
    return bool(settings.ml_enabled and settings.classifier_repo and settings.ml_enable_classifier)


def classify_garment(image_bytes: bytes, top_k: int = 3) -> list[dict] | None:
    if not classifier_available():
        return None
    clf = _load("classifier", _load_classifier)
    if clf is None:
        return None

    import io

    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return [{"label": p["label"], "score": round(float(p["score"]), 4)} for p in clf(image)[:top_k]]


# ── Status ───────────────────────────────────────────────────────────────


def _status_for(name: str, display_name: str, repo: str | None) -> ModelStatus:
    failure = _failures.get(name)
    return ModelStatus(
        name=display_name,
        repo=repo,
        loaded=name in _cache,
        error=failure.message if failure else None,
        # Lets an operator tell "this will recover by itself" from "this needs a
        # redeploy", which is otherwise indistinguishable from an error string.
        retryable=failure.retryable if failure else True,
    )


def status() -> list[ModelStatus]:
    return [
        _status_for("measurement", "measurement_predictor", settings.measurement_repo),
        _status_for(
            "classifier",
            "garment_classifier",
            settings.classifier_repo if settings.ml_enable_classifier else None,
        ),
    ]


def warm_up() -> dict:
    """Force-load every configured model. Call this before a demo so the first
    real request isn't paying the download cost."""
    results = {}
    if measurement_available():
        results["measurement_predictor"] = _load("measurement", _load_measurement) is not None
    if classifier_available():
        results["garment_classifier"] = _load("classifier", _load_classifier) is not None
    return results
