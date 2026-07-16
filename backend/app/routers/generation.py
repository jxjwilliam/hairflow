import base64
import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import GenerateRequest, GenerateResponse, RegenerateRequest
from app.services.meitu import meitu_service, MeituAPIError
from app.services.oss import get_oss_service
from app.routers.templates import _load_templates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    """Detect face, apply hairstyle, upload result to OSS."""
    # --- Step 0: look up template to get the actual Meitu style_id ---
    templates = _load_templates()
    template = next((t for t in templates if t["id"] == req.style_id), None)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Hairstyle template '{req.style_id}' not found",
        )
    meitu_style_id: str = template["style_id"]

    # --- Step 1: verify a face is present via hairclassifier ---
    try:
        await meitu_service.detect_hair(req.photo_base64)
    except MeituAPIError as e:
        msg = str(e)
        if "detect no face" in msg.lower() or "20003" in msg:
            raise HTTPException(status_code=400, detail="No face detected in photo")
        logger.warning("Hair detection pre-check failed: %s", msg)
        # non-fatal — still try generation
    except Exception as e:
        logger.warning("Hair detection pre-check error (non-fatal): %s", e)

    # --- Step 2: hair segmentation (required before portrait_edit) ---
    mask_base64: str | None = None
    try:
        mask_bytes = await meitu_service.segment_hair(req.photo_base64)
        mask_base64 = base64.b64encode(mask_bytes).decode()
        logger.info("Hair segmentation succeeded, mask size=%d bytes", len(mask_bytes))
    except MeituAPIError as e:
        logger.warning("Hair segmentation failed (non-fatal): %s", e)
    except Exception as e:
        logger.warning("Hair segmentation unexpected error (non-fatal): %s", e)

    # --- Step 3: generate hairstyle (with mask if available) ---
    try:
        image_bytes = await meitu_service.generate_hairstyle(
            req.photo_base64, meitu_style_id, mask_base64
        )
    except MeituAPIError as e:
        err_str = str(e)
        logger.error("Meitu generation failed: %s", err_str)
        if "90002" in err_str or "AUTHORIZED" in err_str:
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI generation requires a paid subscription for this "
                    "hairstyle API. Please contact Meitu platform support "
                    "to purchase access."
                ),
            )
        raise HTTPException(status_code=502, detail=f"AI generation failed: {err_str}")
    except Exception as e:
        logger.error("Meitu generation unexpected error: %s", e)
        raise HTTPException(status_code=502, detail="AI generation failed")

    # --- Step 4: upload to OSS ---
    try:
        oss = get_oss_service()
        url, image_id = oss.upload_image(image_bytes)
    except Exception as e:
        logger.error("OSS upload failed: %s", e)
        raise HTTPException(status_code=502, detail="Image storage failed")

    return GenerateResponse(image_url=url, image_id=image_id)


@router.post("/regenerate", response_model=GenerateResponse)
async def regenerate(req: RegenerateRequest):
    """Re-generate hairstyle with adjusted parameters. (MVP stub)"""
    raise HTTPException(
        status_code=501,
        detail="Regenerate is not yet implemented. Parameter sliders coming in P1.",
    )
