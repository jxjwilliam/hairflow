import asyncio
import base64
import io
import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    RegenerateRequest,
    MultiAngleResponse,
    AngleImage,
)
from app.services.comfyui import comfyui_service, ComfyUIError
from app.services.face import face_service
from app.services.prompt_builder import build_adjusted_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/comfyui", tags=["comfyui-generation"])

COMPYUI_TEMPLATES_PATH = Path(__file__).parent.parent.parent / "data" / "templates_comfyui.json"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _load_comfyui_templates() -> list[dict]:
    """Load ComfyUI-specific templates with prompts."""
    with open(COMPYUI_TEMPLATES_PATH) as f:
        return json.load(f)


def _save_locally(image_bytes: bytes, base_url: str = "http://localhost:8000") -> tuple[str, str]:
    """Save generated image to local output/ directory. Returns (url, image_id)."""
    image_id = uuid.uuid4().hex
    filename = f"{image_id}.png"
    filepath = OUTPUT_DIR / filename
    filepath.write_bytes(image_bytes)
    url = f"{base_url}/api/comfyui/output/{filename}"
    logger.info("Saved locally: %s (%d bytes)", filepath, len(image_bytes))
    return url, image_id


@router.get("/output/{filename}")
async def serve_output(filename: str):
    """Serve generated images from local output/ directory."""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath, media_type="image/png")


@router.post("/generate", response_model=GenerateResponse)
async def comfyui_generate(req: GenerateRequest, request: Request):
    """Generate a hairstyle preview using local ComfyUI + PhotoMaker."""
    # --- Step 1: Validate template ---
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

    # --- Step 3: Optionally crop for better PhotoMaker results ---
    photo_for_generation = req.photo_base64
    cropped = await face_service.crop_face(req.photo_base64, padding=0.3)
    if cropped:
        photo_for_generation = cropped
        logger.info("Face cropped for generation")

    # --- Step 4: ComfyUI generation ---
    try:
        logger.info("Submitting to ComfyUI (style=%s, checkpoint=%s)...", req.style_id, template.get("checkpoint"))
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
        logger.info("ComfyUI generation complete: %d bytes", len(image_bytes))
    except ComfyUIError as e:
        logger.error("ComfyUI generation failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"AI generation failed: {e}",
        )
    except Exception as e:
        logger.exception("ComfyUI generation unexpected error")
        raise HTTPException(status_code=502, detail=f"AI generation error: {e}")

    # --- Step 5: Save result (try OSS, fall back to local) ---
    try:
        from app.services.oss import get_oss_service
        oss = get_oss_service()
        url, image_id = oss.upload_image(image_bytes, content_type="image/png")
        logger.info("Uploaded to OSS: %s", url)
    except Exception as e:
        logger.warning("OSS upload failed (%s), saving locally", e)
        base_url = str(request.base_url).rstrip("/")
        url, image_id = _save_locally(image_bytes, base_url=base_url)

    return GenerateResponse(image_url=url, image_id=image_id)


@router.post("/regenerate", response_model=GenerateResponse)
async def comfyui_regenerate(req: RegenerateRequest, request: Request):
    templates = _load_comfyui_templates()
    template = next((t for t in templates if t["id"] == req.style_id), None)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Hairstyle template '{req.style_id}' not found.",
        )

    adjusted_prompt = build_adjusted_prompt(
        base_prompt=template["positive_prompt"],
        length=req.params.length,
        curl=req.params.curl,
        color=req.params.color,
    )
    logger.info(
        "Regenerate: style=%s length=%.1f curl=%.1f color=%s prompt=%s",
        req.style_id, req.params.length, req.params.curl, req.params.color,
        adjusted_prompt[:100],
    )

    face_result = await face_service.detect_face(req.photo_base64)
    if not face_result["face_detected"]:
        raise HTTPException(status_code=400, detail="No face detected in photo.")

    photo_for_generation = req.photo_base64
    cropped = await face_service.crop_face(req.photo_base64, padding=0.3)
    if cropped:
        photo_for_generation = cropped

    try:
        image_bytes = await comfyui_service.generate_hairstyle(
            photo_base64=photo_for_generation,
            prompt=adjusted_prompt,
            negative_prompt=template.get("negative_prompt", ""),
            checkpoint=template.get("checkpoint", "photon_v1.safetensors"),
            photomaker_model=template.get("photomaker_model", "photomaker-v1.bin"),
            width=template.get("width", 512),
            height=template.get("height", 768),
            steps=req.steps or template.get("steps", 25),
            cfg=req.cfg or template.get("cfg", 6.5),
            denoise=req.denoise or template.get("denoise", 0.85),
        )
    except ComfyUIError as e:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}")

    try:
        from app.services.oss import get_oss_service
        oss = get_oss_service()
        url, image_id = oss.upload_image(image_bytes, content_type="image/png")
    except Exception:
        base_url = str(request.base_url).rstrip("/")
        url, image_id = _save_locally(image_bytes, base_url=base_url)

    return GenerateResponse(image_url=url, image_id=image_id)


ANGLES = ["front", "left", "right", "back"]
ANGLE_PROMPTS = {
    "front": "front view, looking at camera",
    "left": "left side view, head turned slightly left",
    "right": "right side view, head turned slightly right",
    "back": "back view, showing back of head",
}


@router.post("/generate-multi", response_model=MultiAngleResponse)
async def comfyui_generate_multi(req: GenerateRequest, request: Request):
    templates = _load_comfyui_templates()
    template = next((t for t in templates if t["id"] == req.style_id), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{req.style_id}' not found.")

    face_result = await face_service.detect_face(req.photo_base64)
    if not face_result["face_detected"]:
        raise HTTPException(status_code=400, detail="No face detected in photo.")

    photo_for_generation = req.photo_base64
    cropped = await face_service.crop_face(req.photo_base64, padding=0.3)
    if cropped:
        photo_for_generation = cropped

    base_url = str(request.base_url).rstrip("/")
    # Serialize ComfyUI calls to avoid GPU OOM (one SD pipeline at a time)
    _comfyui_sem = asyncio.Semaphore(1)

    async def generate_for_angle(angle: str) -> tuple[str, AngleImage | None]:
        angle_prompt = f"{template['positive_prompt']}, {ANGLE_PROMPTS[angle]}"
        async with _comfyui_sem:
            try:
                image_bytes = await comfyui_service.generate_hairstyle(
                    photo_base64=photo_for_generation,
                    prompt=angle_prompt,
                    negative_prompt=template.get("negative_prompt", ""),
                    checkpoint=template.get("checkpoint", "photon_v1.safetensors"),
                    photomaker_model=template.get("photomaker_model", "photomaker-v1.bin"),
                    width=template.get("width", 512),
                    height=template.get("height", 768),
                    steps=template.get("steps", 25),
                    cfg=template.get("cfg", 6.5),
                    denoise=template.get("denoise", 0.85),
                )
                url, image_id = _save_locally(image_bytes, base_url=base_url)
            except ComfyUIError as e:
                logger.error("Angle %s failed: %s", angle, e)
                return angle, None
        return angle, AngleImage(url=url, id=image_id)

    tasks = [generate_for_angle(angle) for angle in ANGLES]
    results = await asyncio.gather(*tasks)
    images = {angle: img for angle, img in results if img is not None}

    if not images:
        raise HTTPException(status_code=502, detail="所有角度生成均失败")

    return MultiAngleResponse(
        images=images,
        template_name=template.get("name", ""),
    )
