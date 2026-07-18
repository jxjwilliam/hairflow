"""Face shape classification using MediaPipe Face Mesh (468 landmarks).

Extends the face detection pipeline to classify face shape into one of
six categories: oval, round, square, heart, diamond, long.

Key landmarks used:
  - 10:  forehead (front hairline center)
  - 338: right temple
  - 109: left temple
  - 152: chin tip
  - 172: left cheekbone (outermost)
  - 397: right cheekbone (outermost)
  - 58:  left jaw angle
  - 288: right jaw angle
"""

import base64
import io
import logging
import math

from PIL import Image, ImageOps

from app.services.face import MAX_DETECTION_DIM

logger = logging.getLogger(__name__)

# Face shape categories
FACE_SHAPES = ["oval", "round", "square", "heart", "diamond", "long"]

# ---- landmark indices for face shape analysis ----
FOREHEAD_TOP = 10
LEFT_TEMPLE = 109
RIGHT_TEMPLE = 338
CHIN_TIP = 152
LEFT_CHEEK = 172
RIGHT_CHEEK = 397
LEFT_JAW = 58
RIGHT_JAW = 288


def _distance(p1, p2) -> float:
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def _landmark_to_dict(landmark):
    return {"x": landmark.x, "y": landmark.y, "z": getattr(landmark, "z", 0.0)}


class FaceShapeService:
    """Classify face shape from a portrait photo using MediaPipe Face Mesh."""

    def __init__(self):
        self._mp_face_mesh = None

    @property
    def mp_face_mesh(self):
        if self._mp_face_mesh is None:
            import mediapipe as mp
            self._mp_face_mesh = mp.solutions.face_mesh
        return self._mp_face_mesh

    def _prepare_image(self, photo_bytes: bytes) -> Image.Image:
        """Decode, fix EXIF, convert to RGB, resize to max detection dim."""
        image = Image.open(io.BytesIO(photo_bytes))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        w, h = image.size
        if max(w, h) > MAX_DETECTION_DIM:
            ratio = MAX_DETECTION_DIM / max(w, h)
            image = image.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        return image

    def classify(self, photo_base64: str) -> dict:
        """Classify face shape from a base64-encoded portrait photo.

        Returns:
            {
                "face_detected": bool,
                "face_shape": str | None,        # oval|round|square|heart|diamond|long
                "confidence": float | None,       # how confident the classification is
                "landmarks": dict | None,         # normalized key measurements
            }
        """
        try:
            photo_bytes = base64.b64decode(photo_base64)
            image = self._prepare_image(photo_bytes)
            import numpy as np
            image_np = np.array(image)

            with self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                min_detection_confidence=0.3,
            ) as face_mesh:
                results = face_mesh.process(image_np)

            if not results or not results.multi_face_landmarks:
                logger.warning("No face mesh found for shape classification")
                return {
                    "face_detected": False,
                    "face_shape": None,
                    "confidence": None,
                    "landmarks": None,
                }

            landmarks = results.multi_face_landmarks[0].landmark

            # ---- extract key measurements ----
            fh = _distance(landmarks[FOREHEAD_TOP], landmarks[CHIN_TIP])  # face height
            fw = _distance(landmarks[LEFT_CHEEK], landmarks[RIGHT_CHEEK])  # cheekbone width
            fw = max(fw, 1e-6)  # prevent div by zero
            jw = _distance(landmarks[LEFT_JAW], landmarks[RIGHT_JAW])  # jaw width
            hw = _distance(landmarks[LEFT_TEMPLE], landmarks[RIGHT_TEMPLE])  # forehead width

            # ---- ratios ----
            aspect = fh / fw  # height / width
            jaw_to_cheek = jw / fw
            forehead_to_cheek = hw / fw
            forehead_to_jaw = hw / max(jw, 1e-6)

            # jaw angularity: how wide the jaw is relative to the total face
            # square = high jaw_to_cheek, round = lower but wide
            # also check if jaw is angular (strong jaw muscles)

            # ---- classification logic ----
            shape = "oval"
            confidence = 0.6
            reasons = []

            if aspect > 1.5:
                # Significantly taller than wide
                if forehead_to_jaw > 1.2:
                    shape = "heart"
                    confidence = 0.65
                    reasons.append(f"high aspect ratio {aspect:.2f} + wide forehead")
                else:
                    shape = "long"
                    confidence = 0.7
                    reasons.append(f"high aspect ratio {aspect:.2f}")
            elif aspect < 1.25:
                # Nearly as wide as tall
                if jaw_to_cheek > 0.88:
                    shape = "square"
                    confidence = 0.7
                    reasons.append(f"low aspect {aspect:.2f} + wide jaw {jaw_to_cheek:.2f}")
                else:
                    shape = "round"
                    confidence = 0.7
                    reasons.append(f"low aspect {aspect:.2f} + narrow jaw {jaw_to_cheek:.2f}")
            else:
                # Moderate aspect ratio (1.25 - 1.5) — check width distribution
                if forehead_to_jaw > 1.25 and forehead_to_cheek > 0.85:
                    # Wider forehead, narrower jaw
                    shape = "heart"
                    confidence = 0.65
                    reasons.append(f"wide forehead {forehead_to_jaw:.2f}x jaw")
                elif forehead_to_cheek < 0.78 and jaw_to_cheek < 0.82:
                    # Narrow both forehead and jaw — widest at cheekbones
                    shape = "diamond"
                    confidence = 0.7
                    reasons.append(f"narrow ends (f={forehead_to_cheek:.2f}, j={jaw_to_cheek:.2f})")
                elif jaw_to_cheek > 0.85:
                    # Broad jaw — square
                    shape = "square"
                    confidence = 0.6
                    reasons.append(f"moderate aspect + wide jaw {jaw_to_cheek:.2f}")
                else:
                    shape = "oval"
                    confidence = 0.6
                    reasons.append(f"balanced ratios (aspect={aspect:.2f})")

            normalized = {
                "face_height": round(fh, 4),
                "face_width": round(fw, 4),
                "jaw_width": round(jw, 4),
                "forehead_width": round(hw, 4),
                "aspect_ratio": round(aspect, 3),
                "jaw_to_cheek_ratio": round(jaw_to_cheek, 3),
                "forehead_to_cheek_ratio": round(forehead_to_cheek, 3),
                "forehead_to_jaw_ratio": round(forehead_to_jaw, 3),
            }
            logger.info(
                "Face shape classified: %s (%.2f) | ratios: aspect=%.2f jaw/cheek=%.2f | %s",
                shape, confidence, aspect, jaw_to_cheek, "; ".join(reasons),
            )

            return {
                "face_detected": True,
                "face_shape": shape,
                "confidence": confidence,
                "landmarks": normalized,
            }

        except Exception as e:
            logger.error("Face shape classification error: %s", e)
            return {
                "face_detected": True,  # optimistic — let generation proceed
                "face_shape": None,
                "confidence": None,
                "landmarks": None,
                "error": str(e),
            }


face_shape_service = FaceShapeService()
