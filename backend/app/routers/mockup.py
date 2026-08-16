from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import catalog as catalog_service
from app.services import mockup as mockup_service
from app.services.prompt import build_prompt

router = APIRouter(prefix="/api/mockup", tags=["ai"])


class MockupRequest(BaseModel):
    cloth_type_id: int
    material_id: int
    material_color_id: int | None = None
    design_option_ids: list[int] = Field(default_factory=list)
    custom_description: str = ""
    use_cache: bool = True


class MockupResponse(BaseModel):
    image_url: str
    prompt: str
    negative_prompt: str
    model_id: str
    latency_ms: int
    cached: bool
    is_fallback: bool
    disclaimer: str


# Shown alongside every generated image. The proposal commits to labelling AI
# output as a computer-generated preview, and it is also simply honest.
DISCLAIMER = (
    "This is an AI-generated preview, not a photograph of your finished garment. "
    "The final stitched item may differ."
)


@router.post("", response_model=MockupResponse)
def create_mockup(payload: MockupRequest, db: Session = Depends(get_db)):
    cloth_type = catalog_service.get_cloth_type_or_404(db, payload.cloth_type_id)
    if not cloth_type:
        raise HTTPException(status_code=404, detail="Cloth type not found")

    material = catalog_service.get_material_or_404(db, payload.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    color = next((c for c in material.colors if c.id == payload.material_color_id), None)
    options = catalog_service.get_design_options(db, payload.design_option_ids)

    spec = catalog_service.build_prompt_spec(cloth_type, material, color, options, payload.custom_description)
    built = build_prompt(spec)

    result = mockup_service.generate_mockup(
        db,
        prompt=built.positive,
        negative_prompt=built.negative,
        cloth_type=cloth_type.name,
        colour=color.name if color else "",
        use_cache=payload.use_cache,
    )

    return MockupResponse(
        image_url=result.image_url,
        prompt=built.positive,
        negative_prompt=built.negative,
        model_id=result.model_id,
        latency_ms=result.latency_ms,
        cached=result.cached,
        is_fallback=result.is_fallback,
        disclaimer=DISCLAIMER,
    )


@router.get("/status")
def mockup_status():
    """Which image provider is actually configured. Check this before a demo —
    a missing API key should be visible here, not discovered live."""
    return mockup_service.provider_status()
