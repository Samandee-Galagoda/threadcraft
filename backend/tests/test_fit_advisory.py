"""Fit-risk advisory: feature building and verdict interpretation.

Everything here is pure — no model, no network — so it runs in CI where the
autouse `isolate_from_developer_env` fixture forces `ml_enabled=False` and no
artefact can be loaded.

Two tests carry most of the weight:

  * test_probabilities_are_mapped_by_name_not_position — scikit-learn sorts
    string labels, and getting this wrong produces a confident wrong answer
    rather than a crash.
  * test_a_marginal_lead_is_reported_as_uncertain — the anti-overclaim rule.
"""

import pytest

from app.services import fit

# ── clipping, mirroring the cleaning notebook ────────────────────────────────


@pytest.mark.parametrize(
    ("value", "bounds", "expected"),
    [
        (170, fit.HEIGHT_CM_RANGE, 170.0),
        (120, fit.HEIGHT_CM_RANGE, 120.0),  # inclusive lower bound
        (210, fit.HEIGHT_CM_RANGE, 210.0),  # inclusive upper bound
        (119, fit.HEIGHT_CM_RANGE, None),
        (211, fit.HEIGHT_CM_RANGE, None),
        (0, fit.HEIGHT_CM_RANGE, None),
        (None, fit.HEIGHT_CM_RANGE, None),
        ("nonsense", fit.HEIGHT_CM_RANGE, None),
        (29, fit.WEIGHT_KG_RANGE, None),
        (201, fit.WEIGHT_KG_RANGE, None),
        (9, fit.AGE_RANGE, None),
        (101, fit.AGE_RANGE, None),
    ],
)
def test_values_outside_the_training_range_become_missing(value, bounds, expected):
    """The cleaning notebook clipped these to NaN before training, so passing one
    through at inference would feed the model a region it never saw."""
    assert fit.clip_to_none(value, bounds) == expected


@pytest.mark.parametrize(
    ("cup", "expected"),
    [
        ("d", 4),
        ("D", 4),
        (" dd ", 5),
        ("aa", 0),
        ("ddd/e", 6),
        ("j", 11),
        ("z", None),
        ("", None),
        (None, None),
    ],
)
def test_cup_letters_map_to_the_training_ordinal(cup, expected):
    """The scale is verbatim from 01_data_cleaning.ipynb, which self-asserts
    parse_bust('34d') == (34, 4)."""
    assert fit.cup_to_ordinal(cup) == expected


# ── feature building ─────────────────────────────────────────────────────────


def test_bmi_is_derived_from_height_and_weight():
    built = fit.build_fit_features({"height": 170, "weight": 68, "usual_size": 8})
    assert built.features["bmi"] == pytest.approx(23.53, abs=0.01)


def test_bmi_is_clipped_independently_of_height_and_weight():
    """A plausible height and a plausible weight can still combine into a BMI the
    model never saw, so BMI is range-checked on its own."""
    built = fit.build_fit_features({"height": 130, "weight": 190})
    assert built.features["height_cm"] == 130.0
    assert built.features["weight_kg"] == 190.0
    assert built.features["bmi"] is None  # ~112, far outside (12, 60)


def test_missing_height_does_not_crash_bmi():
    built = fit.build_fit_features({"weight": 68})
    assert built.features["bmi"] is None


def test_every_model_feature_is_always_present_even_when_unknown():
    """A silently absent key still becomes NaN downstream, but with no record of
    why. A renamed feature must fail loudly here rather than degrade quietly."""
    built = fit.build_fit_features({})
    assert set(built.features) == set(fit.FIT_FEATURES)


def test_unknown_inputs_are_reported_rather_than_silently_defaulted():
    built = fit.build_fit_features({"height": 170, "weight": 68, "usual_size": 8})
    assert "bust_band" in built.missing
    assert "bust_cup" in built.missing
    assert "body_type" in built.missing
    assert "height_cm" in built.used
    assert "size" in built.used


def test_bra_size_reaches_the_model_when_supplied():
    """These are two of the model's seven numeric features and were previously
    unreachable from the API, so every prediction ran without them."""
    built = fit.build_fit_features({"bra_band": 34, "bra_cup": "D"})
    assert built.features["bust_band"] == 34.0
    assert built.features["bust_cup"] == 4.0


@pytest.mark.parametrize(
    ("slug", "expected"),
    [("dress", "dress"), ("skirt", "skirt"), ("trousers", "pants"), ("tshirt", "top"), ("shirt", "shirt")],
)
def test_mapped_garments_reach_the_training_vocabulary(slug, expected):
    assert fit.build_fit_features({"cloth_type_slug": slug}).features["category"] == expected


@pytest.mark.parametrize("slug", ["kurta", "saree-blouse", "salwar-kameez"])
def test_unmapped_garments_become_missing_with_a_caveat(slug):
    """These have no analogue in US rental data. Resolving to None puts them in
    the model's '__missing__' bucket, which it saw during training — unlike an
    unknown string, which lands in the encoder's unseen bucket."""
    built = fit.build_fit_features({"cloth_type_slug": slug})
    assert built.features["category"] is None
    assert any("extrapolation" in c for c in built.caveats)


def test_occasion_defaults_to_everyday():
    assert fit.build_fit_features({}).features["rented_for"] == "everyday"


# ── the class-ordering trap ──────────────────────────────────────────────────


def test_probabilities_are_mapped_by_name_not_position():
    """scikit-learn sorts string labels, so classes_ is ['fit','large','small'] —
    NOT the ['small','fit','large'] display order in the training notebook.
    Positional indexing transposes two of three probabilities and produces a
    confident, plausible, wrong answer."""
    result = fit.probabilities_by_name(["fit", "large", "small"], [0.1, 0.2, 0.7])
    assert result == {"runs_small": 0.7, "fits": 0.1, "runs_large": 0.2}


def test_probability_mapping_survives_a_different_class_order():
    result = fit.probabilities_by_name(["small", "fit", "large"], [0.7, 0.1, 0.2])
    assert result == {"runs_small": 0.7, "fits": 0.1, "runs_large": 0.2}


# ── verdicts ─────────────────────────────────────────────────────────────────


def _probs(small, fits, large):
    return {"runs_small": small, "fits": fits, "runs_large": large}


def test_no_size_given_is_its_own_verdict():
    result = fit.interpret_fit_risk(_probs(0.3, 0.4, 0.3), usual_size=None)
    assert result.verdict == "no_size_given"


def test_a_dominant_small_probability_reads_as_runs_small():
    result = fit.interpret_fit_risk(_probs(0.55, 0.30, 0.15), usual_size=8)
    assert result.verdict == "runs_small"
    assert "size 8" in result.headline
    assert result.confidence == "moderate"


def test_a_dominant_large_probability_reads_as_runs_large():
    result = fit.interpret_fit_risk(_probs(0.10, 0.30, 0.60), usual_size=12)
    assert result.verdict == "runs_large"


def test_a_marginal_lead_is_reported_as_uncertain():
    """The anti-overclaim rule. A two-point lead is noise against balanced
    accuracy of 0.396, and must not be dressed up as a finding."""
    result = fit.interpret_fit_risk(_probs(0.36, 0.34, 0.30), usual_size=8)
    assert result.verdict == "uncertain"
    assert result.confidence == "low"


def test_a_plurality_below_the_fits_floor_is_uncertain():
    """P(fits) winning is not the same as P(fits) being convincing — the training
    distribution is ~74% 'fit', so a plurality is close to the default state."""
    result = fit.interpret_fit_risk(_probs(0.40, 0.45, 0.15), usual_size=8)
    assert result.verdict == "uncertain"


def test_a_convincing_fit_reads_as_likely_fits():
    result = fit.interpret_fit_risk(_probs(0.15, 0.75, 0.10), usual_size=8)
    assert result.verdict == "likely_fits"


@pytest.mark.parametrize(
    "probs",
    [
        _probs(1.0, 0.0, 0.0),
        _probs(0.0, 1.0, 0.0),
        _probs(0.0, 0.0, 1.0),
        _probs(0.33, 0.34, 0.33),
        _probs(0.55, 0.30, 0.15),
        _probs(0.15, 0.75, 0.10),
    ],
)
def test_confidence_is_never_high(probs):
    """'high' is not a member of the confidence type at all — the type system
    enforcing the honesty constraint, so an overclaim cannot be shipped by
    accident even from a probability of 1.0."""
    assert fit.interpret_fit_risk(probs, usual_size=8).confidence in {"low", "moderate"}


def test_the_headline_renders_the_size_without_a_decimal():
    result = fit.interpret_fit_risk(_probs(0.55, 0.30, 0.15), usual_size=8.0)
    assert "size 8 " in result.headline
    assert "8.0" not in result.headline


def test_caveats_are_carried_through_to_every_verdict():
    caveats = ("Trained on rental data.",)
    for probs in [_probs(0.55, 0.3, 0.15), _probs(0.15, 0.75, 0.1), _probs(0.34, 0.33, 0.33)]:
        assert fit.interpret_fit_risk(probs, usual_size=8, caveats=caveats).caveats == caveats


def test_nothing_in_this_module_recommends_a_size():
    """Encodes the product decision in the suite so the discredited size sweep
    cannot be quietly reintroduced. See the module docstring for the evidence."""
    assert not hasattr(fit, "recommend_size")
    assert "recommended_size" not in {f.name for f in fit.FitRisk.__dataclass_fields__.values()}
