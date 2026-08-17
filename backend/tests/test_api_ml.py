"""ML endpoint tests.

No models are configured in CI, so these verify the **graceful degradation**
contract: every ML endpoint must report unavailability in a normal 200 response
rather than raising, because none of these features may block the ordering flow.
"""

import pytest


def test_ml_status_lists_all_three_models(client):
    resp = client.get("/api/ml/status")
    assert resp.status_code == 200
    names = {m["name"] for m in resp.json()["models"]}
    assert names == {"measurement_predictor", "fit_recommender", "garment_classifier"}


def test_suggest_reports_unavailable_rather_than_failing(client):
    resp = client.post(
        "/api/ml/measurements/suggest",
        json={"height": 170, "weight": 68, "age": 30, "sex": 0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["suggestions"] == {}
    assert body["note"]


def test_suggest_requires_height_and_weight(client):
    resp = client.post("/api/ml/measurements/suggest", json={"age": 30})
    assert resp.status_code == 400


def test_validate_reports_unavailable_rather_than_failing(client):
    resp = client.post(
        "/api/ml/measurements/validate",
        json={"height": 170, "weight": 68, "chest": 92, "waist": 76},
    )
    assert resp.status_code == 200
    assert resp.json()["available"] is False


def test_fit_risk_reports_unavailable_rather_than_failing(client):
    resp = client.post("/api/ml/fit-risk", json={"height": 165, "weight": 61, "usual_size": 8})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["verdict"] is None


def test_the_size_sweep_is_no_longer_reachable(client):
    """POST /recommend-size ranked candidate sizes by P(fit) and inverted: at a
    fixed height, sweeping weight 45 -> 105 kg moved the top size 27, 0, 15, 17,
    7, 7, 7. It was withdrawn rather than left exposed. See
    docs/testing/ml-evaluation.md."""
    resp = client.post("/api/ml/recommend-size", json={"height": 165, "weight": 61})
    assert resp.status_code == 404


def test_fit_risk_without_a_usual_size_is_still_a_200(client, monkeypatch):
    """The panel renders before the customer picks a size, so 'no size yet' is a
    normal state — and it must be answered without loading the artefact."""
    from app.services import ml as ml_service

    monkeypatch.setattr(ml_service, "fit_available", lambda: True)
    monkeypatch.setattr(
        ml_service,
        "assess_fit_risk",
        lambda request: pytest.fail("the model must not be loaded when no size was given"),
    )

    body = client.post("/api/ml/fit-risk", json={"height": 165, "weight": 61}).json()
    assert body["available"] is True
    assert body["verdict"] == "no_size_given"


@pytest.mark.parametrize("size", [-1, 31, 99])
def test_fit_risk_rejects_a_size_outside_the_training_sweep(client, size):
    assert client.post("/api/ml/fit-risk", json={"usual_size": size}).status_code == 422


def test_fit_risk_returns_the_typed_verdict(client, monkeypatch):
    """Exercises the whole router with scikit-learn never touched, by swapping
    the one service function the endpoint calls."""
    from app.services import fit as fit_service
    from app.services import ml as ml_service

    monkeypatch.setattr(ml_service, "fit_available", lambda: True)
    monkeypatch.setattr(
        ml_service,
        "assess_fit_risk",
        lambda request: fit_service.FitRisk(
            verdict="runs_small",
            probabilities={"runs_small": 0.6, "fits": 0.25, "runs_large": 0.15},
            headline="A size 8 tends to run small on measurements like yours.",
            detail="Worth double-checking your chest and waist below.",
            confidence="moderate",
            caveats=("Trained on rental data.",),
            inputs_used=("height_cm",),
            inputs_missing=("bust_band",),
            usual_size=8.0,
        ),
    )

    body = client.post("/api/ml/fit-risk", json={"height": 165, "weight": 61, "usual_size": 8}).json()
    assert body["verdict"] == "runs_small"
    assert body["probabilities"] == {"runs_small": 0.6, "fits": 0.25, "runs_large": 0.15}
    assert body["confidence"] == "moderate"
    assert body["caveats"] == ["Trained on rental data."]
    assert body["inputs_missing"] == ["bust_band"]
    # The contract must never carry a recommended size.
    assert "recommendations" not in body
    assert "recommended_size" not in body


def test_classify_reports_unavailable_rather_than_failing(client):
    from tests.test_api_mockup import _tiny_png

    resp = client.post(
        "/api/ml/classify-garment",
        files={"file": ("ref.png", _tiny_png(), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["available"] is False


def test_classify_still_validates_the_upload_before_checking_the_model(client):
    """Input validation must happen regardless of model availability — otherwise
    enabling the model later would newly expose an unvalidated path."""
    resp = client.post(
        "/api/ml/classify-garment",
        files={"file": ("evil.png", b"not an image", "image/png")},
    )
    assert resp.status_code == 400


def test_warm_up_is_safe_with_nothing_configured(client):
    resp = client.post("/api/ml/warm-up")
    assert resp.status_code == 200
    assert resp.json()["loaded"] == {}


def test_classifier_never_suggests_a_garment_we_do_not_tailor(client, seeded_catalog, monkeypatch):
    """The model has 25 retail classes including Bra, Briefs and Trunk, none of
    which are orderable. On ordinary photographs it returns 'Bra' at 0.5-0.7
    confidence for dresses and kurtas, so an unfiltered suggestion is both wrong
    and embarrassing. No match must mean no suggestion."""
    from app.services import ml as ml_service
    from tests.test_api_mockup import _tiny_png

    monkeypatch.setattr(
        ml_service,
        "classify_garment",
        lambda data, top_k=3: [
            {"label": "Bra", "score": 0.68},
            {"label": "Briefs", "score": 0.2},
        ],
    )

    body = client.post(
        "/api/ml/classify-garment", files={"file": ("ref.png", _tiny_png(), "image/png")}
    ).json()
    assert body["available"] is True
    assert body["predictions"] == []
    assert body["matched_cloth_type_id"] is None
    assert "couldn't match" in body["note"]


def test_classifier_surfaces_a_prediction_that_maps_to_the_catalogue(client, seeded_catalog, monkeypatch):
    """seeded_catalog's cloth type is a T-shirt, so 'Tshirts' must map through
    and carry the id the wizard uses to switch garment type."""
    from app.services import ml as ml_service
    from tests.test_api_mockup import _tiny_png

    monkeypatch.setattr(
        ml_service,
        "classify_garment",
        lambda data, top_k=3: [
            {"label": "Bra", "score": 0.7},
            {"label": "Tshirts", "score": 0.55},
        ],
    )

    body = client.post(
        "/api/ml/classify-garment", files={"file": ("ref.png", _tiny_png(), "image/png")}
    ).json()
    # The unsellable higher-confidence label is dropped, not shown.
    assert [p["label"] for p in body["predictions"]] == ["Tshirts"]
    assert body["matched_cloth_type_id"] == seeded_catalog["cloth_type"].id


def test_a_low_confidence_suggestion_is_withheld(client, seeded_catalog, monkeypatch):
    """On real photographs the surviving sellable labels score 0.04-0.26. Showing
    'that looks like a T-shirt (6% confidence)' is noise presented as advice."""
    from app.services import ml as ml_service
    from tests.test_api_mockup import _tiny_png

    monkeypatch.setattr(
        ml_service, "classify_garment", lambda data, top_k=3: [{"label": "Tshirts", "score": 0.06}]
    )

    body = client.post(
        "/api/ml/classify-garment", files={"file": ("ref.png", _tiny_png(), "image/png")}
    ).json()
    assert body["predictions"] == []
    assert body["matched_cloth_type_id"] is None
