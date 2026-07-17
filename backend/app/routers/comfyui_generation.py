"""ComfyUI-based hairstyle generation router.

New endpoint: POST /api/comfyui/generate
Replaces the Meitu API pipeline with local ComfyUI + PhotoMaker.

The original POST /api/generate (Meitu-based) is preserved unchanged.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.schemas import GenerateRequest, GenerateResponse
from app.services.comfyui import comfyui_service, ComfyUIError
from app.services.face import face_service
from app.services.oss import get_oss_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/comfyui", tags=["comfyui-generation"])

COMPYUI_TEMPLATES_PATH = Path(__file__).parent.parent.parent / "data" / "templates_comfyui.json"


def _load_comfyui_templates() -> list[dict]:
    """Load ComfyUI-specific templates with prompts."""
    with open(COMPYUI_TEMPLATES_PATH) as f:
        return json.load(f)


@router.post("/generate", response_model=GenerateResponse)
async def comfyui_generate(req: GenerateRequest):
    """Generate a hairstyle preview using local ComfyUI + PhotoMaker.

    Flow:
      1. Detect face via mediapipe (validate photo)
      2. Look up template prompt
      3. Submit PhotoMaker workflow to ComfyUI
      4. Poll for result, download image
      5. Upload to OSS, return URL
    """
    # --- Step 1: Validate template exists ---
    templates = _load_comfyui_templates()
    template = next((t for t in templates if t["id"] == req.style_id), None)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Hairstyle template '{req.style_id}' not found. "
                    f"Available: {[t['id'] for t in templates]}",
        )

    # --- Step 2: Face detection ---
    face_result = await face_service.detect_face(req.photo_base64)
    if not face_result["face_detected"]:
        raise HTTPException(
            status_code=400,
            detail="No face detected in photo. Please upload a clear front-facing portrait.",
        )
    logger.info(
        "Face detected: confidence=%.2f, bbox=%s",
        face_result.get("confidence", 0),
        face_result.get("bbox"),
    )

    # --- Step 3: Optionally crop face for better PhotoMaker results ---
    photo_for_generation = req.photo_base64
    cropped = await face_service.crop_face(req.photo_base64, padding=0.3)
    if cropped:
        photo_for_generation = cropped
        logger.info("Face cropped for generation")

    # --- Step 4: Submit to ComfyUI ---
    try:
        image_bytes = await comfyui_service.generate_hairstyle(
            photo_base64=photo_for_generation,
            prompt=template["positive_prompt"],
            negative_prompt=template.get("negative_prompt", ""),
            checkpoint=template.get("checkpoint", "photon_v1.safetensors"),
            photomaker_model=template.get("photomaker_model", "photomaker-v1.bin"),
            width=template.get("width", 512),
            height=template.get("height", 768),
            steps=template.get("steps", 25),
            cfg=template.get("cfg", 6.5),
            denoise=template.get("denoise", 0.85),
        )
    except ComfyUIError as e:
        logger.error("ComfyUI generation failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"AI generation failed: {e}. Is ComfyUI running at "
                   f"{comfyui_service.base_url}?",
        )
    except Exception as e:
        logger.error("ComfyUI generation unexpected error: %s", e)
        raise HTTPException(status_code=502, detail="AI generation failed")

    # --- Step 5: Upload to OSS ---
    try:
        oss = get_oss_service()
        url, image_id = oss.upload_image(image_bytes, content_type="image/png")
    except Exception as e:
        logger.error("OSS upload failed: %s", e)
        raise HTTPException(status_code=502, detail="Image storage failed")

    return GenerateResponse(image_url=url, image_id=image_id)
