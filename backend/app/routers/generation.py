import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerateRequest, GenerateResponse, RegenerateRequest
from app.services.meitu import meitu_service
from app.services.oss import get_oss_service
from app.services.face import face_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    face_result = await face_service.detect_and_segment(req.photo_base64)
    if not face_result.get("face_detected"):
        raise HTTPException(status_code=400, detail="No face detected in photo")

    try:
        image_bytes = await meitu_service.generate_hairstyle(req.photo_base64, req.style_id)
    except Exception as e:
        logger.error(f"Meitu API call failed: {e}")
        raise HTTPException(status_code=502, detail="AI generation failed")

    oss = get_oss_service()
    url, image_id = oss.upload_image(image_bytes)

    return GenerateResponse(image_url=url, image_id=image_id)


@router.post("/regenerate", response_model=GenerateResponse)
async def regenerate(req: RegenerateRequest):
    raise HTTPException(status_code=501, detail="Regenerate not yet implemented in MVP")
