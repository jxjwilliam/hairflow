"""Face detection using mediapipe.

Replaces the stub in face.py with real face detection
for the ComfyUI-based generation pipeline.
"""

import base64
import io
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


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

    async def detect_face(
        self, photo_base64: str, min_confidence: float = 0.5
    ) -> dict:
        """Detect faces in a base64-encoded photo.

        Returns:
            {
                "face_detected": bool,
                "face_count": int,
                "confidence": float | None,  # highest confidence
                "bbox": [x, y, w, h] | None,  # relative coords (0-1)
            }
        """
        try:
            photo_bytes = base64.b64decode(photo_base64)
            image = Image.open(io.BytesIO(photo_bytes))
            image_rgb = image.convert("RGB")

            with self.mp_face_detection.FaceDetection(
                model_selection=1,  # 1 = full-range model
                min_detection_confidence=min_confidence,
            ) as detector:
                # mediapipe expects RGB numpy array
                import numpy as np
                image_np = np.array(image_rgb)
                results = detector.process(image_np)

            if not results.detections:
                return {
                    "face_detected": False,
                    "face_count": 0,
                    "confidence": None,
                    "bbox": None,
                }

            # Get the highest-confidence face
            best = max(
                results.detections,
                key=lambda d: d.score[0] if d.score else 0,
            )
            confidence = float(best.score[0]) if best.score else 0.0

            # Get bounding box (relative coords)
            bbox = None
            if best.location_data and best.location_data.relative_bounding_box:
                rb = best.location_data.relative_bounding_box
                bbox = [rb.xmin, rb.ymin, rb.width, rb.height]

            return {
                "face_detected": True,
                "face_count": len(results.detections),
                "confidence": confidence,
                "bbox": bbox,
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
