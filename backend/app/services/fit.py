"""Pure logic for the fit-risk advisory.

No model, no Session, no I/O — the same testability contract as
`services/pricing.py` and `build_cloudflare_payload` in `services/mockup.py`.
Everything here can be exercised with scikit-learn not even installed, which is
what the CI suite does (`tests/conftest.py` forces `ml_enabled=False`).

**Why this exists at all.** The fit recommender was originally exposed as a size
*picker*: sweep every candidate size, return the top three by P(fit). Measured
against the deployed model, that inverts. Holding height at 170 cm and sweeping
weight 45 -> 105 kg, the top "recommended" size goes 27, 0, 15, 17, 7, 7, 7.
Two causes, both structural:

  * `size` is the raw RentTheRunway numeric size, and the mapping to a
    made-to-measure specification that the model card defers to "the
    application layer" was never written.
  * `bust_band` and `bust_cup` are two of the model's seven numeric features
    and had no field on the request schema, so every production prediction ran
    with them missing.

The small/fit/large axis, however, does carry signal — macro F1 0.4051 against
a 0.2830 majority-class baseline — and it is the use the model card actually
names: "a fit-risk advisory ... flagging that a given size is likely to run
small or large for this body". So we ask the model that question instead, about
one size the customer already owns, rather than sweeping sizes it cannot rank.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

# ── Training-time bounds ─────────────────────────────────────────────────────
# Copied verbatim from ml/fit-recommender/01_data_cleaning.ipynb. A value outside
# these was clipped to NaN before training, so passing one at inference feeds the
# model a region it has never seen. Mirroring the clipping is more honest than
# rejecting the customer.
HEIGHT_CM_RANGE = (120.0, 210.0)
WEIGHT_KG_RANGE = (30.0, 200.0)
AGE_RANGE = (10.0, 100.0)
BMI_RANGE = (12.0, 60.0)

# Verbatim from the same notebook. Changing this without retraining silently
# shifts every bust_cup value the model receives.
CUP_ORDER = ("aa", "a", "b", "c", "d", "dd", "ddd/e", "f", "g", "h", "i", "j")

# The exact feature set the artefact was fit on, in the notebook's order.
NUMERIC_FEATURES = ("height_cm", "weight_kg", "bmi", "bust_band", "bust_cup", "age", "size")
CATEGORICAL_FEATURES = ("body_type", "category", "rented_for")
FIT_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# ThreadCraft garment slug -> the RentTheRunway `category` vocabulary.
# Deliberately partial: the Sri Lankan garments have no analogue in US rental
# data. An unmapped garment resolves to None, which becomes the model's
# "__missing__" bucket — a value it *did* see during training — rather than an
# unknown string, which would land in the encoder's unseen -1 bucket.
CATEGORY_BY_SLUG = {
    "dress": "dress",
    "skirt": "skirt",
    "trousers": "pants",
    "tshirt": "top",
    "shirt": "shirt",
}

# The garments we knowingly cannot advise on, for a caveat rather than silence.
UNMAPPED_GARMENT_CAVEAT = (
    "{name} isn't represented in the training data (US clothing rental), so this is an extrapolation."
)
BASE_CAVEAT = "Trained on US women's clothing-rental data, mostly dresses and gowns."

# ── Verdict thresholds ───────────────────────────────────────────────────────
# A weak model has to clear a bar before it is allowed to say anything definite.
# Balanced accuracy is 0.3960 against a 0.3333 chance floor, so a two-point lead
# over P(fits) is noise, not a finding.
RISK_FLOOR = 0.30  # the risk class must be plausible in absolute terms
RISK_MARGIN = 0.10  # ...and must beat P(fits) by a real margin
FITS_FLOOR = 0.55  # calling "it fits" needs a clear majority, not a plurality

NOTE = (
    "Advisory only. Trained on US women's clothing-rental data (mostly dresses and gowns), "
    "it calls small/fit/large correctly about 4 times in 10 where chance is 3 in 10. Treat it "
    "as a prompt to re-check your measurements, never as a size decision."
)


@dataclass(frozen=True)
class FitRisk:
    verdict: str
    probabilities: dict[str, float]
    headline: str
    detail: str
    confidence: str
    caveats: tuple[str, ...] = ()
    inputs_used: tuple[str, ...] = ()
    inputs_missing: tuple[str, ...] = ()
    usual_size: float | None = None


@dataclass
class FeatureBuild:
    features: dict[str, Any] = field(default_factory=dict)
    used: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)


def clip_to_none(value: float | None, bounds: tuple[float, float]) -> float | None:
    """Mirror `clip_to_nan` from the cleaning notebook: out-of-range becomes
    missing rather than being passed through as a plausible-looking outlier."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    low, high = bounds
    return number if low <= number <= high else None


def cup_to_ordinal(cup: str | None) -> int | None:
    """'D' -> 4, matching the ordinal scale the model was trained on.
    Unrecognised input is missing, not an error — a bra size is optional."""
    if not cup:
        return None
    normalised = str(cup).strip().lower()
    return CUP_ORDER.index(normalised) if normalised in CUP_ORDER else None


def build_fit_features(request: dict) -> FeatureBuild:
    """ThreadCraft request fields -> the feature dict the fit model expects.

    Every key in FIT_FEATURES is always present, set to None when unknown. A
    silently absent key would still become NaN downstream, but with no record of
    *why* — and the whole point of `inputs_missing` is to make the model's blind
    spots visible instead of quietly averaging over them.
    """
    build = FeatureBuild()

    height = clip_to_none(request.get("height"), HEIGHT_CM_RANGE)
    weight = clip_to_none(request.get("weight"), WEIGHT_KG_RANGE)
    age = clip_to_none(request.get("age"), AGE_RANGE)

    # BMI is derived then clipped independently, exactly as the notebook does —
    # a plausible height and weight can still yield an out-of-range BMI.
    bmi = None
    if height and weight:
        bmi = clip_to_none(weight / (height / 100) ** 2, BMI_RANGE)

    band = request.get("bra_band")
    cup = cup_to_ordinal(request.get("bra_cup"))

    slug = request.get("cloth_type_slug")
    category = CATEGORY_BY_SLUG.get(slug) if slug else None
    if slug and category is None:
        build.caveats.append(UNMAPPED_GARMENT_CAVEAT.format(name=slug.replace("-", " ").title()))

    build.features = {
        "height_cm": height,
        "weight_kg": weight,
        "bmi": bmi,
        "bust_band": float(band) if band else None,
        "bust_cup": float(cup) if cup is not None else None,
        "age": age,
        "size": request.get("usual_size"),
        "body_type": request.get("body_type"),
        "category": category,
        "rented_for": request.get("occasion") or "everyday",
    }

    for name, value in build.features.items():
        (build.used if value is not None else build.missing).append(name)

    if height is None or weight is None:
        build.caveats.append("Add your height and weight above for a more reliable read.")

    return build


def probabilities_by_name(classes: Sequence[str], row: Sequence[float]) -> dict[str, float]:
    """Map one predict_proba row onto {runs_small, fits, runs_large} BY NAME.

    scikit-learn sorts string class labels, so `classes_` is
    ['fit', 'large', 'small'] — NOT the ['small', 'fit', 'large'] display order
    used in the training notebook's confusion matrix. Indexing positionally here
    transposes two of the three probabilities and yields a confident, plausible,
    completely wrong answer.
    """
    by_label = {str(label): float(value) for label, value in zip(classes, row, strict=False)}
    return {
        "runs_small": round(by_label.get("small", 0.0), 4),
        "fits": round(by_label.get("fit", 0.0), 4),
        "runs_large": round(by_label.get("large", 0.0), 4),
    }


def _format_size(size: float) -> str:
    """8.0 reads as 8."""
    return f"{float(size):g}"


def interpret_fit_risk(
    probabilities: dict[str, float],
    *,
    usual_size: float | None,
    caveats: Sequence[str] = (),
) -> FitRisk:
    """Three probabilities -> a verdict and a sentence a customer can act on.

    `uncertain` is a first-class outcome, not a failure mode. With balanced
    accuracy at 0.396 it will fire often, and it should: an advisory that has a
    confident opinion every single time, drawn from a model that is right four
    times in ten, is the overclaim this whole design exists to avoid.
    """
    if usual_size is None:
        return FitRisk(
            verdict="no_size_given",
            probabilities=probabilities,
            headline=(
                "Tell us the size you usually buy and we'll flag whether it tends to run small or large."
            ),
            detail="",
            confidence="low",
            caveats=tuple(caveats),
        )

    size = _format_size(usual_size)
    fits = probabilities.get("fits", 0.0)
    small = probabilities.get("runs_small", 0.0)
    large = probabilities.get("runs_large", 0.0)

    risk = max(small, large)
    runs_small = small >= large

    # Why a margin against P(fits) rather than a lift over the class prior: the
    # model was trained with sqrt-balanced sample weights, so its probabilities
    # are already partly de-biased by an amount the artefact doesn't record.
    # Dividing by the raw 74% prior would double-correct. The margin needs no
    # prior at all and encodes the question we actually care about — has the
    # model moved off "it's fine"?
    if risk >= RISK_FLOOR and risk - fits >= RISK_MARGIN:
        direction = "small" if runs_small else "large"
        opposite = "a little more ease" if runs_small else "it looser than you want"
        return FitRisk(
            verdict=f"runs_{direction}",
            probabilities=probabilities,
            headline=f"A size {size} tends to run {direction} on measurements like yours.",
            detail=(
                "Worth double-checking your chest and waist below — a bespoke garment can be cut with "
                + opposite
                + "."
                if runs_small
                else "Worth double-checking your chest and waist below, so we don't cut " + opposite + "."
            ),
            confidence="moderate",
            caveats=tuple(caveats),
            usual_size=usual_size,
        )

    if fits >= FITS_FLOOR and fits - risk >= RISK_MARGIN:
        return FitRisk(
            verdict="likely_fits",
            probabilities=probabilities,
            headline=f"A size {size} is a sensible reference point for your measurements.",
            detail="Your actual measurements below are still what we cut to.",
            confidence="moderate",
            caveats=tuple(caveats),
            usual_size=usual_size,
        )

    return FitRisk(
        verdict="uncertain",
        probabilities=probabilities,
        headline="We can't call this one either way.",
        detail=(
            f"The model doesn't see a clear signal for a size {size} on your measurements. "
            "Your own measurements below are what matter."
        ),
        confidence="low",
        caveats=tuple(caveats),
        usual_size=usual_size,
    )
