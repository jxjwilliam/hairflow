import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import TemplateOut

router = APIRouter(prefix="/api/templates", tags=["templates"])

TEMPLATES_PATH = Path(__file__).parent.parent.parent / "data" / "templates_comfyui.json"
LEGACY_TEMPLATES_PATH = Path(__file__).parent.parent.parent / "data" / "templates.json"


def absolute_thumbnail_url(thumbnail: str, base_url: str) -> str:
    """Turn relative /static/... paths into absolute URLs; leave external URLs alone."""
    if thumbnail.startswith("/"):
        return f"{base_url.rstrip('/')}{thumbnail}"
    return thumbnail


def _load_legacy_style_ids() -> dict[str, str]:
    if not LEGACY_TEMPLATES_PATH.exists():
        return {}
    with open(LEGACY_TEMPLATES_PATH) as f:
        legacy = json.load(f)
    return {
        t["id"]: t["style_id"]
        for t in legacy
        if "id" in t and "style_id" in t
    }


def _load_templates() -> list[dict]:
    with open(TEMPLATES_PATH) as f:
        templates = json.load(f)
    legacy_style_ids = _load_legacy_style_ids()
    for t in templates:
        if "style_id" not in t:
            t["style_id"] = legacy_style_ids.get(t["id"], t["id"])
    return templates


def _with_absolute_thumbnails(templates: list[dict], request: Request) -> list[dict]:
    base = str(request.base_url)
    out: list[dict] = []
    for t in templates:
        item = dict(t)
        item["thumbnail"] = absolute_thumbnail_url(item["thumbnail"], base)
        out.append(item)
    return out


@router.get("", response_model=list[TemplateOut])
async def list_templates(request: Request, category: str | None = None):
    templates = _load_templates()
    if category:
        templates = [t for t in templates if t["category"] == category]
    return _with_absolute_thumbnails(templates, request)


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: str, request: Request):
    templates = _load_templates()
    for t in templates:
        if t["id"] == template_id:
            return _with_absolute_thumbnails([t], request)[0]
    raise HTTPException(status_code=404, detail="Template not found")
