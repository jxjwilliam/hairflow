"""Face shape recommendation router.

Accepts a portrait photo, detects face shape via MediaPipe Face Mesh,
and returns matching templates whose face_shapes include the detected shape.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.models.schemas import TemplateOut
from app.routers.templates import _load_templates, _with_absolute_thumbnails
from app.services.face_shape import face_shape_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommend", tags=["face-recommend"])


class RecommendByPhotoRequest(BaseModel):
    photo_base64: str
    category: Optional[str] = None


class RecommendByPhotoResponse(BaseModel):
    face_shape: str
    face_confidence: float
    templates: list[TemplateOut]
    total: int


@router.post("/by-photo", response_model=RecommendByPhotoResponse)
async def recommend_by_photo(req: RecommendByPhotoRequest, request: Request):
    """Detect face shape from photo and return matching templates."""
    result = face_shape_service.classify(req.photo_base64)

    if not result["face_detected"] or not result["face_shape"]:
        # No face detected — return all popular templates as fallback
        logger.warning("No face shape detected, returning all templates as fallback")
        templates = _load_templates()
        if req.category:
            templates = [t for t in templates if t["category"] == req.category]
        # Sort by popularity (ovals are most versatile — kept first)
        templates = _with_absolute_thumbnails(templates, request)
        return RecommendByPhotoResponse(
            face_shape="unknown",
            face_confidence=0.0,
            templates=templates,
            total=len(templates),
        )

    detected_shape = result["face_shape"]
    confidence = result["confidence"] or 0.0

    all_templates = _load_templates()

    # Filter templates whose face_shapes include the detected shape
    matched = []
    for t in all_templates:
        shapes = t.get("face_shapes", [])
        if detected_shape in shapes:
            matched.append(t)

    if req.category:
        matched = [t for t in matched if t["category"] == req.category]

    # If no match, fallback to all templates
    if not matched:
        logger.info("No templates match face shape '%s', returning all as fallback", detected_shape)
        matched = all_templates
        if req.category:
            matched = [t for t in matched if t["category"] == req.category]

    matched = _with_absolute_thumbnails(matched, request)

    logger.info(
        "Recommend by-photo: shape=%s confidence=%.2f matched=%d",
        detected_shape, confidence, len(matched),
    )

    return RecommendByPhotoResponse(
        face_shape=detected_shape,
        face_confidence=confidence,
        templates=matched,
        total=len(matched),
    )
