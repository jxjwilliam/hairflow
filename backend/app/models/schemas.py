from pydantic import BaseModel
from typing import Optional


class TemplateOut(BaseModel):
    id: str
    name: str
    category: str
    tags: list[str]
    style_id: str
    thumbnail: str
    description: str


class GenerateRequest(BaseModel):
    photo_base64: str
    style_id: str


class RegenerateRequest(BaseModel):
    image_id: str
    length: Optional[float] = None
    curl: Optional[float] = None
    color: Optional[str] = None
    bang_style: Optional[str] = None


class GenerateResponse(BaseModel):
    image_url: str
    image_id: str
