from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
@router.get("/health")
def health():
    return {"status": "ok", "message": "ThreadCraft API is running."}
