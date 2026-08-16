from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/")
@router.get("/health")
def health():
    """Liveness check, plus the one setting that cannot be diagnosed any other way.

    A CORS misconfiguration is uniquely opaque: the API answers every request
    correctly, `/health` is 200, and the only symptom is the browser refusing
    the response. The admin UI can't help either, because it is itself blocked.
    Reporting the effective origin list here makes it a single curl to confirm,
    instead of guessing which of several plausible URLs was pasted into a
    hosting dashboard.

    Nothing here is sensitive — the allowed origin is echoed to any browser in
    the Access-Control-Allow-Origin header already.
    """
    return {
        "status": "ok",
        "message": "ThreadCraft API is running.",
        "cors": {
            "allowed_origins": settings.cors_origins,
            "origin_regex": settings.cors_origin_regex,
        },
    }
