from pydantic import BaseModel, model_validator
from typing import Optional


class TemplateOut(BaseModel):
    id: str
    name: str
    category: str
    tags: list[str]
    face_shapes: list[str] = []
    style_id: str
    thumbnail: str
    description: str


class GenerateRequest(BaseModel):
    photo_base64: str
    style_id: str
    # Generation options
    pipeline: str = "photomaker"   # photomaker | sd15 | flux | flux_klein
    method: str = "photomaker"     # photomaker | txt2img | img2img
    checkpoint: str = ""
    denoise: float = 0.85
    steps: int = 15
    cfg: float = 6.5


class GenerateResponse(BaseModel):
    image_url: str
    image_id: str


class RegenerateParams(BaseModel):
    length: float = 0.5
    curl: float = 0.0
    color: str = "black"


class RegenerateRequest(BaseModel):
    photo_base64: str
    style_id: str
    params: RegenerateParams = RegenerateParams()  # noqa: RUF012; immutable fields only
    steps: Optional[int] = None
    cfg: Optional[float] = None
    denoise: Optional[float] = None
    checkpoint: str = ""


class AngleImage(BaseModel):
    url: str
    id: str


class MultiAngleResponse(BaseModel):
    images: dict[str, AngleImage]
    template_name: str = ""


class GenerateVideoRequest(BaseModel):
    """Animate an existing try-on still; exactly one image source is required."""

    image_id: Optional[str] = None
    image_url: Optional[str] = None
    photo_base64: Optional[str] = None
    pipeline: Optional[str] = None
    seed: Optional[int] = None
    frames: int = 24
    fps: int = 8

    @model_validator(mode="after")
    def one_source(self) -> "GenerateVideoRequest":
        sources = [self.image_id, self.image_url, self.photo_base64]
        if sum(1 for source in sources if source) != 1:
            raise ValueError("Provide exactly one of image_id, image_url, photo_base64")
        if not 8 <= self.frames <= 48:
            raise ValueError("frames must be 8–48 for ~1–6s clips")
        if not 6 <= self.fps <= 24:
            raise ValueError("fps must be 6–24")
        return self


class GenerateVideoResponse(BaseModel):
    video_url: str
    video_id: str
    pipeline: str
    duration_s: float

