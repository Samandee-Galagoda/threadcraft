"""Guards on the Cloudflare Workers AI request body.

Workers AI rejects the entire request if it sees a property it doesn't
recognise, and the app is built to fall back silently on any provider failure —
so a stray key here degrades every mockup to a placeholder with nothing in the
UI to indicate why. That combination is exactly what these tests exist to stop.

This is a real regression: the first implementation sent `num_steps` and a
`negative_prompt`, both of which FLUX.1-schnell rejects, so every Cloudflare
call 400'd and served the placeholder instead.
"""

import pytest

from app.services.mockup import (
    CLOUDFLARE_ALLOWED_KEYS,
    CLOUDFLARE_MAX_PROMPT_CHARS,
    build_cloudflare_payload,
)


def test_payload_contains_only_supported_properties():
    payload = build_cloudflare_payload("a red dress")
    assert set(payload) <= CLOUDFLARE_ALLOWED_KEYS


def test_uses_steps_not_num_steps():
    """Regression: `num_steps` is the SDXL spelling and is rejected by schnell."""
    payload = build_cloudflare_payload("a red dress")
    assert "steps" in payload
    assert "num_steps" not in payload


def test_never_sends_a_negative_prompt():
    """Regression: schnell has no negative-prompt support; sending one is a 400.
    The negative prompt is still built and stored, and still used on the
    Hugging Face path — it just must not go to Cloudflare."""
    payload = build_cloudflare_payload("a red dress")
    assert "negative_prompt" not in payload


def test_prompt_is_truncated_to_the_documented_maximum():
    payload = build_cloudflare_payload("x" * 5000)
    assert len(payload["prompt"]) == CLOUDFLARE_MAX_PROMPT_CHARS


@pytest.mark.parametrize(
    "requested,expected",
    [(4, 4), (1, 1), (8, 8), (0, 1), (-5, 1), (99, 8)],
)
def test_steps_are_clamped_to_the_supported_range(requested, expected):
    """schnell documents a maximum of 8 steps; out-of-range values are a 400."""
    assert build_cloudflare_payload("a dress", steps=requested)["steps"] == expected


def test_payload_is_json_serialisable():
    import json

    json.dumps(build_cloudflare_payload("a dress"))
