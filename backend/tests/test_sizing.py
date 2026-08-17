"""UK size-band lookup.

The replacement for the withdrawn fit recommender. Pure and deterministic, so
these run with no model and no network.

The headline test is test_the_chart_is_monotonic_in_every_measurement: the
previous model was withdrawn precisely because it inverted, and the whole
argument for this design is that a monotonic chart composed with a monotonic
predictor cannot. That has to be asserted, not assumed.
"""

import pytest

from app.services import sizing

WOMEN, MEN = 0, 1


def test_the_chart_is_monotonic_in_every_measurement():
    """Bands must ascend in chest, waist and hip together. A chart that doubled
    back would reintroduce exactly the failure this replaced."""
    for bands in (sizing.WOMENS_BANDS, sizing.MENS_BANDS):
        for slot in (1, 2, 3):
            lows = [band[slot][0] for band in bands]
            assert lows == sorted(lows), f"slot {slot} is not ascending"


def test_the_chart_has_no_gaps_or_overlaps():
    """Adjacent bands must meet exactly: a gap silently drops a customer to the
    clamp, and an overlap makes the band assignment order-dependent."""
    for bands in (sizing.WOMENS_BANDS, sizing.MENS_BANDS):
        for slot in (1, 2, 3):
            for lower, upper in zip(bands, bands[1:], strict=False):
                assert lower[slot][1] == upper[slot][0], f"gap/overlap at slot {slot}"


@pytest.mark.parametrize(
    ("chest", "expected"),
    [(76, "UK 6"), (81.9, "UK 6"), (82, "UK 8"), (90, "UK 12"), (94.9, "UK 12"), (95, "UK 14")],
)
def test_band_boundaries_are_half_open(chest, expected):
    """Lower bound inclusive, upper exclusive — so a measurement on a boundary
    lands in exactly one band."""
    assert sizing.band_for("chest", chest, WOMEN) == expected


def test_a_body_below_the_smallest_band_is_clamped_not_dropped():
    """A very slight customer should still get a reference point rather than
    silence."""
    assert sizing.band_for("chest", 60, WOMEN) == "UK 6"


def test_a_body_above_the_largest_band_is_clamped():
    assert sizing.band_for("chest", 200, WOMEN) == "UK 24"


def test_men_and_women_use_different_charts():
    assert sizing.band_for("chest", 96, WOMEN) == "UK 14"
    assert sizing.band_for("chest", 96, MEN) == "M"


def test_consistent_measurements_give_one_band():
    estimate = sizing.estimate_size({"chest": 91, "waist": 73, "hip": 99}, sex=WOMEN)
    assert estimate.size == "UK 12"
    assert estimate.spans_multiple_bands is False


def test_the_largest_band_wins_when_measurements_disagree():
    """Standard tailoring practice: cloth can be taken in but not let out, so
    the conservative direction is up."""
    estimate = sizing.estimate_size({"chest": 91, "waist": 73, "hip": 110}, sex=WOMEN)
    assert estimate.size == "UK 16"  # hip band, the largest of the three
    assert estimate.spans_multiple_bands is True
    assert "UK 12 to UK 16" in estimate.note


def test_a_disagreement_is_explained_rather_than_hidden():
    estimate = sizing.estimate_size({"chest": 84, "waist": 96, "hip": 99}, sex=WOMEN)
    assert estimate.spans_multiple_bands is True
    # The customer is told why, because a single number here would misrepresent
    # how well any off-the-rack size actually fits them.
    assert "normal" in estimate.note


def test_a_partial_profile_still_produces_an_estimate():
    estimate = sizing.estimate_size({"chest": 91}, sex=WOMEN)
    assert estimate.size == "UK 12"
    assert set(estimate.per_measurement) == {"chest"}


def test_no_measurements_produces_nothing():
    assert sizing.estimate_size({}, sex=WOMEN) is None
    assert sizing.estimate_size({"shoulder": 40}, sex=WOMEN) is None


def test_every_band_is_reachable_from_some_body():
    """Guards against a band that no measurement can ever select — which would
    make part of the chart dead weight."""
    for bands, sex in ((sizing.WOMENS_BANDS, WOMEN), (sizing.MENS_BANDS, MEN)):
        reachable = set()
        for chest in range(60, 200):
            reachable.add(sizing.band_for("chest", chest, sex))
        assert reachable == {b[0] for b in bands}


# ── endpoint ─────────────────────────────────────────────────────────────────


def test_size_estimate_requires_height_and_weight(client):
    assert client.post("/api/ml/size-estimate", json={"age": 30}).status_code == 400


def test_size_estimate_reports_unavailable_without_the_predictor(client):
    """The chart is deterministic, but the measurements feeding it are not — with
    no model and nothing measured there is nothing to look up."""
    body = client.post("/api/ml/size-estimate", json={"height": 165, "weight": 62}).json()
    assert body["available"] is False


def test_measured_values_are_used_instead_of_predictions(client):
    """A customer who has actually measured themselves must not have those
    numbers overridden by a model, and must be able to see which is which."""
    body = client.post(
        "/api/ml/size-estimate",
        json={"height": 165, "weight": 62, "chest": 91, "waist": 73, "hip": 99, "sex": 0},
    ).json()
    assert body["available"] is True
    assert body["size"] == "UK 12"
    assert {v["source"] for v in body["basis"].values()} == {"measured"}
    assert body["basis"]["chest"]["value_cm"] == 91.0
