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
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

_lock = threading.Lock()
_cache: dict[str, Any] = {}
_failures: dict[str, str] = {}


@dataclass
class ModelStatus:
    name: str
    repo: str | None
    loaded: bool
    error: str | None


def _load(name: str, loader) -> Any | None:
    """Load once, cache, and remember failures so we don't retry on every request."""
    if name in _cache:
        return _cache[name]
    if name in _failures:
        return None
    with _lock:
        if name in _cache:
            return _cache[name]
        try:
            _cache[name] = loader()
            return _cache[name]
        except Exception as exc:  # noqa: BLE001
            _failures[name] = f"{type(exc).__name__}: {exc}"
            print(f"[ml] failed to load {name}: {_failures[name]}")
            return None


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


# ── Size / fit recommender ───────────────────────────────────────────────


def _load_fit():
    import joblib
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(settings.fit_repo, "fit_recommender.joblib")
    return joblib.load(path)


def fit_available() -> bool:
    return bool(settings.ml_enabled and settings.fit_repo)


def recommend_size(customer: dict, top_k: int = 3) -> list[dict] | None:
    """Sweep candidate sizes, return those ranked by P(fit)."""
    if not fit_available():
        return None
    art = _load("fit", _load_fit)
    if art is None:
        return None

    import numpy as np
    import pandas as pd

    feats = art["features"]
    sizes = art["candidate_sizes"]

    rows = []
    for size in sizes:
        row = {f: customer.get(f) for f in feats}
        row["size"] = size
        rows.append(row)
    frame = pd.DataFrame([{k: (np.nan if v is None else v) for k, v in r.items()} for r in rows])

    for col in art["categorical_features"]:
        frame[col] = frame[col].fillna(art["missing_token"]).astype(str)

    X = frame[art["numeric_features"]].astype(float).copy()
    encoded = art["encoder"].transform(frame[art["categorical_features"]])
    for i, col in enumerate(art["categorical_features"]):
        X[col] = encoded[:, i] + 1

    proba = art["model"].predict_proba(X[feats])
    classes = list(art["model"].classes_)
    fit_index = classes.index("fit")

    ranked = sorted(
        (
            {
                "size": float(size),
                "p_fit": round(float(proba[i][fit_index]), 4),
                **{f"p_{c}": round(float(proba[i][j]), 4) for j, c in enumerate(classes)},
            }
            for i, size in enumerate(sizes)
        ),
        key=lambda r: r["p_fit"],
        reverse=True,
    )
    return ranked[:top_k]


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


def status() -> list[ModelStatus]:
    return [
        ModelStatus(
            name="measurement_predictor",
            repo=settings.measurement_repo,
            loaded="measurement" in _cache,
            error=_failures.get("measurement"),
        ),
        ModelStatus(
            name="fit_recommender",
            repo=settings.fit_repo,
            loaded="fit" in _cache,
            error=_failures.get("fit"),
        ),
        ModelStatus(
            name="garment_classifier",
            repo=settings.classifier_repo if settings.ml_enable_classifier else None,
            loaded="classifier" in _cache,
            error=_failures.get("classifier"),
        ),
    ]


def warm_up() -> dict:
    """Force-load every configured model. Call this before a demo so the first
    real request isn't paying the download cost."""
    results = {}
    if measurement_available():
        results["measurement_predictor"] = _load("measurement", _load_measurement) is not None
    if fit_available():
        results["fit_recommender"] = _load("fit", _load_fit) is not None
    if classifier_available():
        results["garment_classifier"] = _load("classifier", _load_classifier) is not None
    return results
