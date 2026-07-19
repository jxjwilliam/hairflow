from pydantic import BaseModel
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


class AngleImage(BaseModel):
    url: str
    id: str


class MultiAngleResponse(BaseModel):
    images: dict[str, AngleImage]
    template_name: str = ""

