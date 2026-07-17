"""Face detection using mediapipe.

Replaces the stub in face.py with real face detection
for the ComfyUI-based generation pipeline.
"""

import base64
import io
import logging
from typing import Optional

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Max dimension for face detection — mediapipe works best with moderate sizes
MAX_DETECTION_DIM = 1024


class FaceService:
    """Face detection and preprocessing for hairstyle generation.

    Uses mediapipe for face detection. Lightweight, runs locally,
    no API costs.
    """

    def __init__(self):
        self._mp_face_detection = None

    @property
    def mp_face_detection(self):
        """Lazy-load mediapipe to avoid import cost when not used."""
        if self._mp_face_detection is None:
            try:
                import mediapipe as mp
                self._mp_face_detection = mp.solutions.face_detection
            except ImportError:
                raise RuntimeError(
                    "mediapipe is required for face detection. "
                    "Install with: pip install mediapipe"
                )
        return self._mp_face_detection

    def _prepare_image(self, photo_bytes: bytes) -> "Image.Image":
        """Decode and preprocess image for face detection."""
        image = Image.open(io.BytesIO(photo_bytes))
        # Fix EXIF rotation (selfies from phones often have orientation metadata)
        image = ImageOps.exif_transpose(image)
        # Convert to RGB
        image = image.convert("RGB")
        # Resize if too large
        w, h = image.size
        if max(w, h) > MAX_DETECTION_DIM:
            ratio = MAX_DETECTION_DIM / max(w, h)
            image = image.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            logger.info("Resized image %dx%d → %dx%d for detection", w, h, *image.size)
        return image

    async def detect_face(
        self, photo_base64: str, min_confidence: float = 0.3
    ) -> dict:
        """Detect faces in a base64-encoded photo.

        Tries short-range model first (selfies, <2m), falls back to
        full-range model (group photos, >2m).

        Returns:
            {
                "face_detected": bool,
                "face_count": int,
                "confidence": float | None,
                "bbox": [x, y, w, h] | None,  # relative coords (0-1)
            }
        """
        try:
            photo_bytes = base64.b64decode(photo_base64)
            image = self._prepare_image(photo_bytes)

            import numpy as np
            image_np = np.array(image)

            # Try short-range model first (model_selection=0, for selfies <2m)
            for model_sel, label in [(0, "short-range"), (1, "full-range")]:
                with self.mp_face_detection.FaceDetection(
                    model_selection=model_sel,
                    min_detection_confidence=min_confidence,
                ) as detector:
                    results = detector.process(image_np)

                if results.detections:
                    best = max(results.detections, key=lambda d: d.score[0] if d.score else 0)
                    confidence = float(best.score[0]) if best.score else 0.0
                    bbox = None
                    if best.location_data and best.location_data.relative_bounding_box:
                        rb = best.location_data.relative_bounding_box
                        bbox = [rb.xmin, rb.ymin, rb.width, rb.height]
                    logger.info(
                        "Face detected with %s model: confidence=%.2f, bbox=%s",
                        label, confidence, bbox,
                    )
                    return {
                        "face_detected": True,
                        "face_count": len(results.detections),
                        "confidence": confidence,
                        "bbox": bbox,
                    }
                logger.debug("No face with %s model at confidence %.2f", label, min_confidence)

            # Neither model found a face
            logger.warning(
                "No face detected in photo (%dx%d). Ensure it's a clear front-facing portrait.",
                image.width, image.height,
            )
            return {
                "face_detected": False,
                "face_count": 0,
                "confidence": None,
                "bbox": None,
            }

        except Exception as e:
            logger.error("Face detection error: %s", e)
            # Non-fatal: return True so generation still proceeds
            return {
                "face_detected": True,
                "face_count": -1,
                "confidence": None,
                "bbox": None,
                "error": str(e),
            }

    async def crop_face(
        self, photo_base64: str, padding: float = 0.3
    ) -> Optional[str]:
        """Crop photo to face region for better PhotoMaker input.

        Returns base64-encoded cropped image, or None if no face.
        """
        result = await self.detect_face(photo_base64)
        if not result["face_detected"] or not result["bbox"]:
            return None

        try:
            photo_bytes = base64.b64decode(photo_base64)
            image = Image.open(io.BytesIO(photo_bytes))
            image = ImageOps.exif_transpose(image)
            w, h = image.size
            x, y, bw, bh = result["bbox"]

            # Convert relative to absolute, add padding
            x1 = max(0, int((x - padding * bw) * w))
            y1 = max(0, int((y - padding * bh) * h))
            x2 = min(w, int((x + bw + padding * bw) * w))
            y2 = min(h, int((y + bh + padding * bh) * h))

            cropped = image.crop((x1, y1, x2, y2))
            buf = io.BytesIO()
            cropped.save(buf, format="JPEG", quality=95)
            return base64.b64encode(buf.getvalue()).decode()

        except Exception as e:
            logger.warning("Face crop failed: %s", e)
            return None


face_service = FaceService()
