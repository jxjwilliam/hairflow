import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.models.schemas import TemplateOut

router = APIRouter(prefix="/api/templates", tags=["templates"])

TEMPLATES_PATH = Path(__file__).parent.parent.parent / "data" / "templates.json"


def _load_templates() -> list[dict]:
    with open(TEMPLATES_PATH) as f:
        return json.load(f)


@router.get("", response_model=list[TemplateOut])
async def list_templates(category: str | None = None):
    templates = _load_templates()
    if category:
        templates = [t for t in templates if t["category"] == category]
    return templates


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: str):
    templates = _load_templates()
    for t in templates:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")
