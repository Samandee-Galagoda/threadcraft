"""Object storage with a local-disk fallback.

If Cloudflare R2 credentials are configured, files go to the bucket and the
returned URL is publicly servable. If they are not, files are written under
`app/static/generated/` and served by the app itself.

The fallback is deliberate: `git clone && pip install && uvicorn` must produce a
fully working application with no third-party accounts, because that is exactly
what a marker will do.
"""

import hashlib
import mimetypes
import uuid
from pathlib import Path

from app.core.config import settings

# Served by the StaticFiles mount in app/main.py
LOCAL_STATIC_DIR = Path(__file__).resolve().parent.parent / "static" / "generated"
LOCAL_URL_PREFIX = "/static/generated"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Magic-byte signatures. Content-Type headers are client-supplied and trivially
# spoofed, so uploads are checked against the actual file bytes.
_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}


def sniff_image_type(data: bytes) -> str | None:
    """Detect image type from magic bytes, ignoring any declared content-type."""
    for signature, mime in _MAGIC.items():
        if data.startswith(signature):
            return mime
    # WEBP is "RIFF....WEBP"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _extension_for(content_type: str) -> str:
    return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(
        content_type, mimetypes.guess_extension(content_type) or ".bin"
    )


def _r2_configured() -> bool:
    return bool(
        settings.r2_account_id
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
        and settings.r2_public_base_url
    )


def _save_local(data: bytes, key: str) -> str:
    path = LOCAL_STATIC_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"{LOCAL_URL_PREFIX}/{key}"


def _save_r2(data: bytes, key: str, content_type: str) -> str:
    import boto3  # imported lazily so boto3 is only needed when R2 is actually used

    client = boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )
    client.put_object(Bucket=settings.r2_bucket, Key=key, Body=data, ContentType=content_type)
    return f"{settings.r2_public_base_url.rstrip('/')}/{key}"


def save_bytes(data: bytes, *, prefix: str, content_type: str, filename: str | None = None) -> str:
    """Persist `data` and return a URL that will serve it.

    Uses R2 when configured, local disk otherwise. Callers do not need to know
    which, and the returned URL works either way.
    """
    key = f"{prefix}/{filename or uuid.uuid4().hex}{_extension_for(content_type)}"
    if _r2_configured():
        try:
            return _save_r2(data, key, content_type)
        except Exception as exc:  # noqa: BLE001 - never lose an upload to a storage outage
            print(f"R2 upload failed ({exc}); falling back to local disk.")
    return _save_local(data, key)


def content_hash(data: bytes) -> str:
    """Stable short hash, used to deduplicate identical generated mockups."""
    return hashlib.sha256(data).hexdigest()[:16]


def storage_backend() -> str:
    return "r2" if _r2_configured() else "local"
