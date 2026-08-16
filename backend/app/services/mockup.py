"""AI garment mockup generation.

Provider chain, tried in order:

  1. Cloudflare Workers AI  (10,000 free neurons/day, Apache-2.0 FLUX.1-schnell)
  2. Hugging Face Inference (fallback if the CF daily quota is exhausted)
  3. Deterministic local placeholder (always succeeds)

Step 3 is not a cop-out — it is the reason a live demo cannot fail. Free
serverless image APIs cold-start, rate-limit and occasionally 503, and none of
that should take down a viva. Every generation records which provider served it
(`mockup_model`), so a fallback is always visible in the data rather than
silently passed off as a real generation.

Results are cached on a hash of (prompt, negative prompt, model) so repeat
requests for the same design are instant and cost nothing.
"""

import base64
import time
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import MockupGeneration
from app.services import storage

FALLBACK_MODEL_ID = "fallback-placeholder"


@dataclass(frozen=True)
class MockupResult:
    image_url: str
    model_id: str
    latency_ms: int
    cached: bool
    is_fallback: bool


def _cache_key(prompt: str, negative: str, model_id: str) -> str:
    return storage.content_hash(f"{model_id}||{prompt}||{negative}".encode())


def _find_cached(db: Session, key: str) -> MockupGeneration | None:
    return (
        db.query(MockupGeneration)
        .filter(MockupGeneration.image_url.isnot(None), MockupGeneration.prompt == key)
        .order_by(MockupGeneration.created_at.desc())
        .first()
    )


# FLUX.1-schnell on Workers AI accepts exactly these properties and rejects the
# request outright if it sees anything else — `{"code": 5006, "message":
# "Additional or unevaluated properties ... not allowed"}`. Notably it does NOT
# accept `negative_prompt` (unlike the Hugging Face route below), and the steps
# parameter is `steps`, not `num_steps`.
CLOUDFLARE_ALLOWED_KEYS = {"prompt", "steps", "seed"}
CLOUDFLARE_MAX_PROMPT_CHARS = 2048
CLOUDFLARE_DEFAULT_STEPS = 4  # schnell's default; max is 8


def build_cloudflare_payload(prompt: str, steps: int = CLOUDFLARE_DEFAULT_STEPS) -> dict:
    """Build the request body, restricted to properties the API accepts.

    Kept separate from the HTTP call so it can be unit-tested — a stray key here
    fails the whole request and silently degrades every mockup to the fallback.
    """
    payload = {
        "prompt": prompt[:CLOUDFLARE_MAX_PROMPT_CHARS],
        "steps": max(1, min(int(steps), 8)),
    }
    assert set(payload) <= CLOUDFLARE_ALLOWED_KEYS, "unsupported Workers AI property"
    return payload


def _generate_cloudflare(prompt: str, negative: str) -> bytes | None:
    """Cloudflare Workers AI. Returns raw image bytes, or None if unavailable.

    `negative` is accepted for interface symmetry with the Hugging Face path but
    deliberately unused: FLUX.1-schnell on Workers AI has no negative-prompt
    support, and sending one is a hard 400.
    """
    if not (settings.cf_account_id and settings.cf_api_token):
        return None

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.cf_account_id}/ai/run/{settings.cf_image_model}"
    )
    payload = build_cloudflare_payload(prompt)

    try:
        with httpx.Client(timeout=settings.mockup_timeout_seconds) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {settings.cf_api_token}"},
                json=payload,
            )
        if response.status_code != 200:
            print(f"Cloudflare Workers AI returned {response.status_code}: {response.text[:200]}")
            return None

        # flux-1-schnell returns JSON with a base64 image; some CF models return
        # raw bytes. Handle both rather than assuming one.
        if response.headers.get("content-type", "").startswith("application/json"):
            body = response.json()
            encoded = (body.get("result") or {}).get("image")
            if not encoded:
                print(f"Unexpected Cloudflare response shape: {str(body)[:200]}")
                return None
            return base64.b64decode(encoded)
        return response.content
    except Exception as exc:  # noqa: BLE001
        print(f"Cloudflare Workers AI failed: {exc}")
        return None


def _generate_huggingface(prompt: str, negative: str) -> bytes | None:
    """Hugging Face Inference fallback. Returns raw image bytes, or None."""
    if not settings.hf_token:
        return None

    url = f"https://api-inference.huggingface.co/models/{settings.hf_image_model}"
    payload: dict = {"inputs": prompt}
    if negative:
        payload["parameters"] = {"negative_prompt": negative}

    try:
        with httpx.Client(timeout=settings.mockup_timeout_seconds) as client:
            response = client.post(
                url, headers={"Authorization": f"Bearer {settings.hf_token}"}, json=payload
            )
            # 503 means the model is cold-loading; one retry is worth it.
            if response.status_code == 503:
                time.sleep(min(20, settings.mockup_timeout_seconds))
                response = client.post(
                    url, headers={"Authorization": f"Bearer {settings.hf_token}"}, json=payload
                )
        if response.status_code != 200:
            print(f"HF Inference returned {response.status_code}: {response.text[:200]}")
            return None
        return response.content
    except Exception as exc:  # noqa: BLE001
        print(f"HF Inference failed: {exc}")
        return None


def _placeholder_svg(cloth_type: str, colour: str) -> bytes:
    """Deterministic, dependency-free placeholder. Clearly labelled as a
    placeholder so it can never be mistaken for a real generation."""
    safe_type = (cloth_type or "Garment").replace("&", "&amp;").replace("<", "&lt;")
    safe_colour = (colour or "").replace("&", "&amp;").replace("<", "&lt;")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="640" viewBox="0 0 512 640">
  <rect width="512" height="640" fill="#F5EFE6"/>
  <rect x="24" y="24" width="464" height="592" fill="none" stroke="#E8D5C0" stroke-width="1"/>
  <path d="M176 150 L136 190 L136 250 L176 250 L176 470 L336 470 L336 250 L376 250 L376 190 L336 150
           L296 178 L256 150 L216 178 Z"
        fill="#E8D5C0" stroke="#8B6B4A" stroke-width="2" stroke-linejoin="round"/>
  <text x="256" y="530" text-anchor="middle" font-family="Georgia,serif" font-size="26" fill="#2C1F14">{safe_type}</text>
  <text x="256" y="558" text-anchor="middle" font-family="Helvetica,sans-serif" font-size="13" fill="#8B6B4A" letter-spacing="2">{safe_colour}</text>
  <text x="256" y="596" text-anchor="middle" font-family="Helvetica,sans-serif" font-size="11" fill="#C4A882" letter-spacing="1.5">PREVIEW UNAVAILABLE — PLACEHOLDER</text>
</svg>"""
    return svg.encode("utf-8")


def generate_mockup(
    db: Session,
    *,
    prompt: str,
    negative_prompt: str = "",
    cloth_type: str = "Garment",
    colour: str = "",
    order_id: int | None = None,
    use_cache: bool = True,
) -> MockupResult:
    """Generate (or retrieve a cached) garment mockup. Never raises."""
    key = _cache_key(prompt, negative_prompt, settings.cf_image_model)

    if use_cache:
        cached = _find_cached(db, key)
        if cached:
            return MockupResult(
                image_url=cached.image_url,
                model_id=cached.model_id,
                latency_ms=0,
                cached=True,
                is_fallback=cached.model_id == FALLBACK_MODEL_ID,
            )

    started = time.perf_counter()
    image_bytes = _generate_cloudflare(prompt, negative_prompt)
    model_id = settings.cf_image_model
    error_message = None

    if image_bytes is None:
        image_bytes = _generate_huggingface(prompt, negative_prompt)
        model_id = settings.hf_image_model if image_bytes else model_id

    is_fallback = image_bytes is None
    if is_fallback:
        image_bytes = _placeholder_svg(cloth_type, colour)
        model_id = FALLBACK_MODEL_ID
        error_message = "No image provider available; served deterministic placeholder."

    content_type = "image/svg+xml" if is_fallback else "image/png"
    image_url = storage.save_bytes(image_bytes, prefix="mockups", content_type=content_type)
    latency_ms = int((time.perf_counter() - started) * 1000)

    # Logged for every attempt — this table is what accumulates the evaluation
    # set the testing report needs, without a separate data-gathering exercise.
    db.add(
        MockupGeneration(
            order_id=order_id,
            prompt=key,  # the cache key; the readable prompt is on the order
            negative_prompt=negative_prompt,
            model_id=model_id,
            image_url=image_url,
            latency_ms=latency_ms,
            success="fallback" if is_fallback else "true",
            error_message=error_message,
        )
    )
    db.commit()

    return MockupResult(
        image_url=image_url,
        model_id=model_id,
        latency_ms=latency_ms,
        cached=False,
        is_fallback=is_fallback,
    )


def provider_status() -> dict:
    """What the app would actually use right now — surfaced at /api/mockup/status
    so a misconfiguration is visible before the demo, not during it."""
    return {
        "cloudflare_configured": bool(settings.cf_account_id and settings.cf_api_token),
        "huggingface_configured": bool(settings.hf_token),
        "cloudflare_model": settings.cf_image_model,
        "huggingface_model": settings.hf_image_model,
        "storage_backend": storage.storage_backend(),
        "will_use_fallback": not ((settings.cf_account_id and settings.cf_api_token) or settings.hf_token),
    }
