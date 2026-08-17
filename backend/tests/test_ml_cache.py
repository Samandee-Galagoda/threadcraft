"""Model load caching and failure retry.

Failures used to be cached for the life of the process. On a long-lived Render
instance that meant a single Hugging Face 503 — or a DNS blip during boot —
silently disabled measurement suggestions until somebody noticed and redeployed,
with /api/ml/status the only place it showed up. These tests pin the retry
window that fixes it, and the one case that must NOT retry.
"""

import pytest

from app.services import ml as ml_service


@pytest.fixture(autouse=True)
def clean_cache():
    ml_service.reset_cache()
    yield
    ml_service.reset_cache()


class Clock:
    """Controllable stand-in for time.monotonic, so the retry window can be
    crossed without the test sleeping for five minutes."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_a_successful_load_is_cached_and_the_loader_runs_once():
    calls = []

    def loader():
        calls.append(1)
        return "artefact"

    assert ml_service._load("thing", loader) == "artefact"
    assert ml_service._load("thing", loader) == "artefact"
    assert len(calls) == 1


def test_a_transient_failure_is_retried_after_the_window(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(ml_service.time, "monotonic", clock)

    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("Hub returned 503")
        return "artefact"

    assert ml_service._load("thing", flaky) is None
    assert len(calls) == 1

    # Inside the window the loader must not be called again — that is the whole
    # point of remembering the failure.
    clock.advance(ml_service.MODEL_RETRY_AFTER_SECONDS - 1)
    assert ml_service._load("thing", flaky) is None
    assert len(calls) == 1

    clock.advance(2)
    assert ml_service._load("thing", flaky) == "artefact"
    assert len(calls) == 2


def test_a_recovered_load_clears_the_recorded_failure(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(ml_service.time, "monotonic", clock)

    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("transient")
        return "artefact"

    ml_service._load("measurement", flaky)
    clock.advance(ml_service.MODEL_RETRY_AFTER_SECONDS + 1)
    ml_service._load("measurement", flaky)

    entry = next(s for s in ml_service.status() if s.name == "measurement_predictor")
    assert entry.loaded is True
    assert entry.error is None


def test_a_missing_dependency_is_never_retried(monkeypatch):
    """No amount of waiting installs transformers. Retrying an ImportError would
    re-run the import on every request forever for no possible benefit."""
    clock = Clock()
    monkeypatch.setattr(ml_service.time, "monotonic", clock)

    calls = []

    def missing_dep():
        calls.append(1)
        raise ImportError("No module named 'transformers'")

    assert ml_service._load("classifier", missing_dep) is None
    clock.advance(ml_service.MODEL_RETRY_AFTER_SECONDS * 10)
    assert ml_service._load("classifier", missing_dep) is None
    assert len(calls) == 1


def test_status_distinguishes_recoverable_from_permanent_failure():
    ml_service._load("measurement", lambda: (_ for _ in ()).throw(RuntimeError("network")))
    ml_service._load("classifier", lambda: (_ for _ in ()).throw(ImportError("no transformers")))

    by_name = {s.name: s for s in ml_service.status()}
    assert by_name["measurement_predictor"].retryable is True
    assert "network" in by_name["measurement_predictor"].error
    assert by_name["garment_classifier"].retryable is False


def test_reset_cache_clears_models_and_failures():
    ml_service._load("thing", lambda: "artefact")
    ml_service._load("measurement", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    ml_service.reset_cache()

    assert ml_service._cache == {}
    assert ml_service._failures == {}
