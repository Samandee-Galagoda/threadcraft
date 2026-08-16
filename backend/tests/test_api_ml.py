"""ML endpoint tests.

No models are configured in CI, so these verify the **graceful degradation**
contract: every ML endpoint must report unavailability in a normal 200 response
rather than raising, because none of these features may block the ordering flow.
"""


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


def test_recommend_size_reports_unavailable_rather_than_failing(client):
    resp = client.post(
        "/api/ml/recommend-size",
        json={"height": 165, "weight": 61, "category": "dress"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["recommendations"] == []


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
