# Short Video from Try-On Still — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add offline bake-off for LTX / Hunyuan / AnimateDiff image→video from a try-on still, then wire one Preview button to `DEFAULT_VIDEO_PIPELINE`.

**Architecture:** New `VideoGenerationService` (separate from the 962-line `comfyui.py`) builds per-pipeline ComfyUI graphs, reuses upload/submit/poll helpers, saves MP4 under `backend/output/`. Bake-off CLI runs all three pipelines sequentially. Mobile Preview calls `POST /api/comfyui/generate-video` with no pipeline picker.

**Tech Stack:** Python 3.12, FastAPI, httpx, Pillow, ComfyUI 0.27 (Pinokio), Expo SDK 57, `expo-av`, pytest

**Spec:** `docs/superpowers/specs/2026-07-19-hairstyle-short-video-design.md`

## Global Constraints

- Source frame = **try-on still** only (not raw selfie)
- Clip length ≈ **2–3 seconds** (~24 frames @ 8–12 fps)
- App entry = **Preview only**; no in-app pipeline picker
- Ship strategy = Approach **A** (bake-off → pick default)
- Default setting key = `DEFAULT_VIDEO_PIPELINE` / `default_video_pipeline`, initial value `ltx`
- Video jobs **sequential** only (`Semaphore(1)`); never run LTX+Hunyuan+AnimateDiff concurrently on M3 18GB
- Reuse existing weights on Samsung Pinokio drive; do not re-download LTX 5.9G / Hunyuan 12G
- Sync HTTP MVP; client timeout **900_000 ms** (15 min) for video
- Points: same as one still generate when `skip_points_check` is false
- No `as any` / `@ts-ignore` on mobile; no empty catch blocks
- Commits only when the user explicitly asks (skip commit steps unless told)

---

## File Structure

```text
backend/
├── app/
│   ├── config.py                          # MODIFY — default_video_pipeline, video timeout
│   ├── models/schemas.py                  # MODIFY — GenerateVideoRequest/Response
│   ├── routers/comfyui_generation.py      # MODIFY — POST /generate-video, serve mp4
│   └── services/
│       ├── comfyui.py                     # UNCHANGED (still pipelines)
│       └── video_generation.py            # NEW — VideoGenerationService
├── scripts/
│   ├── discover_video_nodes.py            # NEW — dump LTX/Hunyuan/AD node names
│   └── video_bakeoff.py                   # NEW — sequential 3-pipeline bake-off
├── data/
│   └── video_node_catalog.json            # NEW — frozen class_types from discovery
├── static/workflows/
│   ├── ltx_i2v_hairstyle.json             # NEW — manual ComfyUI twin (after discovery)
│   ├── hunyuan_i2v_hairstyle.json         # NEW
│   └── animatediff_i2v_hairstyle.json     # NEW
├── tests/
│   └── test_video_generation.py           # NEW
├── .env.example                           # MODIFY
Makefile                                   # MODIFY — video-bakeoff, discover-video-nodes
mobile/
├── package.json                           # MODIFY — expo-av
├── app/preview.tsx                        # MODIFY — generate video button + player
├── services/generation.ts                 # MODIFY — generateVideo()
└── types.ts                               # MODIFY — VideoGenerateResult
docs/
├── oc_short_video.md                      # NEW — bake-off + node notes
└── superpowers/specs/2026-07-19-hairstyle-short-video-design.md  # already written
```

Also update (after bake-off winner chosen):
`~/.agents/skills/comfyui-model-locator/references/apps/hairflow.json`

---

### Task 1: Discover ComfyUI video nodes + freeze catalog

**Files:**
- Create: `backend/scripts/discover_video_nodes.py`
- Create: `backend/data/video_node_catalog.json`
- Create: `docs/oc_short_video.md` (section “Node discovery”)
- Modify: `Makefile` (target `discover-video-nodes`)

**Interfaces:**
- Consumes: live ComfyUI `GET {COMFYUI_URL}/object_info`
- Produces: `video_node_catalog.json` with keys `ltx`, `hunyuan`, `animatediff`, each listing required `class_type` names found (or `"missing": [...]`)

- [ ] **Step 1: Write the discovery script**

Create `backend/scripts/discover_video_nodes.py`:

```python
#!/usr/bin/env python3
"""Dump ComfyUI node class_types relevant to LTX / Hunyuan / AnimateDiff."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

KEYWORDS = {
    "ltx": ("ltx", "ltxv"),
    "hunyuan": ("hunyuan",),
    "animatediff": ("animatediff", "animate_diff", "ad_"),
    "video_io": ("vhs_", "videocombine", "savevideo", "createvideo"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "video_node_catalog.json",
    )
    args = parser.parse_args()

    try:
        r = httpx.get(f"{args.url.rstrip('/')}/object_info", timeout=60.0)
        r.raise_for_status()
        info = r.json()
    except Exception as e:
        print(f"FAIL: cannot reach ComfyUI object_info: {e}", file=sys.stderr)
        return 1

    names = sorted(info.keys())
    catalog: dict = {"comfyui_url": args.url, "pipelines": {}}
    for pipe, kws in KEYWORDS.items():
        matched = [n for n in names if any(k in n.lower() for k in kws)]
        catalog["pipelines"][pipe] = {
            "matched_class_types": matched,
            "missing": matched == [],
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, indent=2) + "\n")
    print(json.dumps(catalog, indent=2))
    if any(catalog["pipelines"][p]["missing"] for p in ("ltx", "hunyuan", "animatediff")):
        print(
            "\nNOTE: One or more pipelines have zero matched nodes. "
            "Install custom nodes before implementing that builder.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Add Makefile target**

Append to `Makefile` `.PHONY` and add:

```makefile
discover-video-nodes: ## Probe ComfyUI for LTX/Hunyuan/AnimateDiff nodes
	cd $(BACKEND_DIR) && \
	  COMFYUI_URL=$(COMFYUI_URL) $(or $(wildcard .venv/bin/python),python3) \
	  scripts/discover_video_nodes.py
```

(If backend uses `venv` at repo root, adjust interpreter to `/Users/william.jiang/my-tests/my-fun/hairstyle/venv/bin/python` or `backend/.venv/bin/python` — use whichever already runs pytest.)

- [ ] **Step 3: Run discovery (ComfyUI must be up)**

Run:

```bash
curl -s -m 3 http://127.0.0.1:8188/system_stats | head -c 100
make discover-video-nodes
```

Expected: `backend/data/video_node_catalog.json` written; `ltx` and/or `hunyuan` have non-empty `matched_class_types`. If `animatediff` is missing, Task 5 installs it.

- [ ] **Step 4: Document results in `docs/oc_short_video.md`**

Create the file with:
- Path to catalog JSON
- Table of matched class_types for each pipeline
- Install commands if AnimateDiff missing (ComfyUI-Manager → “ComfyUI-AnimateDiff-Evolved” or official AnimateDiff pack)
- Model paths from inventory (already on disk):

| Pipeline | Files |
|----------|-------|
| ltx | `ltx-video-2b-v0.9.5.safetensors`, `t5xxl_fp16.safetensors` |
| hunyuan | `hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors`, `hunyuan_video_vae_bf16.safetensors` |
| animatediff | motion module TBD after install + `realisticVisionV60B1_v60B1VAE.safetensors` |

---

### Task 2: Config, schemas, shared video service skeleton

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/app/models/schemas.py`
- Create: `backend/app/services/video_generation.py`
- Create: `backend/tests/test_video_generation.py` (skeleton tests that fail until builders exist)

**Interfaces:**
- Produces:
  - `Settings.default_video_pipeline: str = "ltx"`
  - `Settings.video_timeout_seconds: float = 900.0`
  - `GenerateVideoRequest(image_id: str | None, image_url: str | None, photo_base64: str | None, pipeline: str | None, seed: int | None, frames: int = 24, fps: int = 8)`
  - `GenerateVideoResponse(video_url: str, video_id: str, pipeline: str, duration_s: float)`
  - `async def VideoGenerationService.generate_video(*, pipeline: str, image: PIL.Image.Image, seed: int, frames: int, fps: int) -> bytes`

- [ ] **Step 1: Write failing tests for request validation + dispatch keys**

Create `backend/tests/test_video_generation.py`:

```python
import pytest
from app.models.schemas import GenerateVideoRequest
from app.services.video_generation import VideoGenerationService, VIDEO_PIPELINES


def test_generate_video_request_requires_one_source():
    with pytest.raises(Exception):
        GenerateVideoRequest()  # all sources None — use model_validator


def test_video_pipelines_include_three():
    assert set(VIDEO_PIPELINES) == {"ltx", "hunyuan", "animatediff"}


def test_build_ltx_workflow_has_load_image_and_save():
    svc = VideoGenerationService(base_url="http://127.0.0.1:8188")
    wf = svc.build_workflow("ltx", image_filename="still.png", seed=42, frames=24, fps=8)
    types = {n["class_type"] for n in wf.values() if isinstance(n, dict) and "class_type" in n}
    assert any("LoadImage" == t or t.startswith("LoadImage") for t in types)
    assert any("Save" in t or "Video" in t or "VHS" in t for t in types)
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd backend && PYTHONPATH=. pytest tests/test_video_generation.py -v
```

Expected: import / attribute errors (module missing).

- [ ] **Step 3: Extend settings**

In `backend/app/config.py` add fields:

```python
default_video_pipeline: str = "ltx"  # ltx | hunyuan | animatediff
video_timeout_seconds: float = 900.0
```

In `backend/.env.example` add:

```bash
# Short video (image→video). Flip after bake-off.
DEFAULT_VIDEO_PIPELINE=ltx
# VIDEO_TIMEOUT_SECONDS=900
```

- [ ] **Step 4: Add Pydantic schemas**

Append to `backend/app/models/schemas.py`:

```python
from pydantic import model_validator


class GenerateVideoRequest(BaseModel):
    """Animate an existing try-on still. Provide exactly one image source."""

    image_id: Optional[str] = None
    image_url: Optional[str] = None
    photo_base64: Optional[str] = None  # still PNG/JPEG as base64 (not selfie)
    pipeline: Optional[str] = None  # default from settings
    seed: Optional[int] = None
    frames: int = 24
    fps: int = 8

    @model_validator(mode="after")
    def one_source(self) -> "GenerateVideoRequest":
        sources = [self.image_id, self.image_url, self.photo_base64]
        if sum(1 for s in sources if s) != 1:
            raise ValueError("Provide exactly one of image_id, image_url, photo_base64")
        if self.frames < 8 or self.frames > 48:
            raise ValueError("frames must be 8–48 for ~1–6s clips")
        if self.fps < 6 or self.fps > 24:
            raise ValueError("fps must be 6–24")
        return self


class GenerateVideoResponse(BaseModel):
    video_url: str
    video_id: str
    pipeline: str
    duration_s: float
```

- [ ] **Step 5: Create service skeleton**

Create `backend/app/services/video_generation.py` that:
- Defines `VIDEO_PIPELINES = ("ltx", "hunyuan", "animatediff")`
- Class `VideoGenerationService` with `base_url` from settings
- Reuses upload via composing/calling the same httpx patterns as `ComfyUIService._upload_image` (copy the small helpers or import `comfyui_service` and call its private methods — **prefer copy of upload/submit/wait/download into this module** to avoid tight coupling; keep under ~80 lines of HTTP helpers)
- `build_workflow(pipeline, ...)` raises `NotImplementedError` for each pipeline until Tasks 3–5
- `generate_video(...)` uploads image → build → submit → poll → download bytes
- Poll must accept **video** outputs: history nodes may expose `gifs` / `videos` / `images` depending on SaveVideo vs VHS_VideoCombine — implement:

```python
def _first_media_filename(outputs: dict) -> str | None:
    for node_output in outputs.values():
        for key in ("videos", "gifs", "images"):
            items = node_output.get(key) or []
            if items:
                return items[0]["filename"]
    return None
```

- Module-level `video_generation_service = VideoGenerationService()`

- [ ] **Step 6: Re-run tests**

`test_video_pipelines_include_three` and request validator should PASS.  
`test_build_ltx_workflow_*` still FAIL until Task 3.

---

### Task 3: LTX image→video workflow builder

**Files:**
- Modify: `backend/app/services/video_generation.py`
- Create: `backend/static/workflows/ltx_i2v_hairstyle.json`
- Modify: `backend/tests/test_video_generation.py`
- Modify: `docs/oc_short_video.md`

**Interfaces:**
- Consumes: `video_node_catalog.json` matched LTX class_types
- Produces: `build_workflow("ltx", ...)` returning API-format prompt dict

- [ ] **Step 1: Choose node graph from catalog**

Open `backend/data/video_node_catalog.json`. Prefer native ComfyUI LTX img2vid nodes (names containing `LTXV`). If missing, install the official Comfy-Org LTX support / custom node, re-run `make discover-video-nodes`, then continue.

Document the exact chosen `class_type` list in `docs/oc_short_video.md` under “LTX graph”.

- [ ] **Step 2: Extend failing test with required filenames**

```python
def test_ltx_workflow_references_known_weights():
    svc = VideoGenerationService(base_url="http://127.0.0.1:8188")
    wf = svc.build_workflow("ltx", image_filename="still.png", seed=1, frames=24, fps=8)
    blob = json.dumps(wf)
    assert "ltx-video-2b-v0.9.5.safetensors" in blob
    assert "t5xxl_fp16.safetensors" in blob or "t5xxl" in blob.lower()
```

- [ ] **Step 3: Implement `_build_ltx_workflow`**

Implement against **discovered** class_types. Required behaviors:
- `LoadImage` with `image_filename` (still uploaded to ComfyUI input)
- Downscale still to max side ~512–768 before encode if a scale node exists (avoid OOM)
- Length from `frames` / `fps`
- Positive prompt fixed English:  
  `"subtle natural hair movement, soft head turn, cinematic portrait, keep face identity, keep hairstyle"`
- Negative: `"morphing face, identity change, flicker, watermark, text"`
- Checkpoint / diffusion model filename: `ltx-video-2b-v0.9.5.safetensors`  
  (mapped under Pinokio `diffusion_models/` — if ComfyUI expects it under checkpoints, use whatever `/object_info` enum lists; discovery run or a one-line probe of loader inputs)
- Text encoder: `t5xxl_fp16.safetensors`
- Terminal node must write a video file ComfyUI history can return

If the live graph cannot be known ahead of time, the implementer must paste the working API-format JSON exported from ComfyUI “Save (API Format)” into `backend/static/workflows/ltx_i2v_hairstyle.json` and load/parameterize it in Python (string-replace seed/filename/frames). **Prefer parameterized JSON load over hand-invented nodes.**

Example loader pattern:

```python
def _load_workflow_template(name: str) -> dict:
    path = Path(__file__).resolve().parent.parent.parent / "static" / "workflows" / name
    return json.loads(path.read_text())


def _build_ltx_workflow(self, image_filename: str, seed: int, frames: int, fps: int) -> dict:
    wf = _load_workflow_template("ltx_i2v_hairstyle.json")
    # walk nodes; set LoadImage image=image_filename; set seed; set frame count fields
    ...
    return wf
```

- [ ] **Step 4: Unit tests PASS without live ComfyUI**

```bash
cd backend && PYTHONPATH=. pytest tests/test_video_generation.py::test_ltx_workflow_references_known_weights tests/test_video_generation.py::test_build_ltx_workflow_has_load_image_and_save -v
```

Expected: PASS

- [ ] **Step 5: Optional live smoke (manual)**

```bash
# After API exists (Task 6), or call service from a tiny script
```

Defer full live run to Task 7 bake-off if API not ready.

---

### Task 4: Hunyuan image→video workflow builder

**Files:**
- Modify: `backend/app/services/video_generation.py`
- Create: `backend/static/workflows/hunyuan_i2v_hairstyle.json`
- Modify: `backend/tests/test_video_generation.py`
- Modify: `docs/oc_short_video.md`

**Interfaces:**
- Consumes: `comfyui-hunyuanvideowrapper` nodes from catalog
- Produces: `build_workflow("hunyuan", ...)`

- [ ] **Step 1: Write failing test**

```python
def test_hunyuan_workflow_references_weights():
    svc = VideoGenerationService(base_url="http://127.0.0.1:8188")
    wf = svc.build_workflow("hunyuan", image_filename="still.png", seed=2, frames=24, fps=8)
    blob = json.dumps(wf)
    assert "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors" in blob
    assert "hunyuan_video_vae_bf16.safetensors" in blob
```

- [ ] **Step 2: Export / author API workflow**

Use ComfyUI UI with `comfyui-hunyuanvideowrapper` I2V template: load still, set ~24 frames, low resolution (480p) for Mac. Save API format → `backend/static/workflows/hunyuan_i2v_hairstyle.json`. Parameterize in `_build_hunyuan_workflow` like LTX.

- [ ] **Step 3: Implement builder + run unit test**

```bash
cd backend && PYTHONPATH=. pytest tests/test_video_generation.py::test_hunyuan_workflow_references_weights -v
```

Expected: PASS

---

### Task 5: Install AnimateDiff + workflow builder

**Files:**
- Modify: ComfyUI `custom_nodes/` (outside repo — document in `docs/oc_short_video.md`)
- Create: `backend/static/workflows/animatediff_i2v_hairstyle.json`
- Modify: `backend/app/services/video_generation.py`
- Modify: `backend/tests/test_video_generation.py`
- Modify: `backend/data/video_node_catalog.json` (re-run discovery)

**Interfaces:**
- Produces: `build_workflow("animatediff", ...)`

- [ ] **Step 1: Install AnimateDiff in Pinokio ComfyUI**

Via ComfyUI-Manager (or git clone into `custom_nodes/`):
- `ComfyUI-AnimateDiff-Evolved` (or current maintained AnimateDiff pack)
- Download SD1.5 motion module e.g. `v3_sd15_mm.ckpt` / `.safetensors` into the path the node expects (usually `custom_nodes/.../models/` or `models/animatediff_models/`)
- Restart ComfyUI
- Re-run `make discover-video-nodes` — `animatediff.missing` must be false

Document exact motion module filename in `docs/oc_short_video.md`.

- [ ] **Step 2: Failing test**

```python
def test_animatediff_workflow_uses_realistic_vision():
    svc = VideoGenerationService(base_url="http://127.0.0.1:8188")
    wf = svc.build_workflow("animatediff", image_filename="still.png", seed=3, frames=24, fps=8)
    blob = json.dumps(wf)
    assert "realisticVisionV60B1_v60B1VAE.safetensors" in blob
```

- [ ] **Step 3: Author img2vid AnimateDiff API workflow**

Still → VAE encode → AnimateDiff sampler (~20–24 frames) → decode → video combine. Keep 512×768 or 512×512. Save API JSON; parameterize in `_build_animatediff_workflow`.

- [ ] **Step 4: Unit test PASS**

```bash
cd backend && PYTHONPATH=. pytest tests/test_video_generation.py::test_animatediff_workflow_uses_realistic_vision -v
```

---

### Task 6: FastAPI `POST /api/comfyui/generate-video` + MP4 serve

**Files:**
- Modify: `backend/app/routers/comfyui_generation.py`
- Modify: `backend/tests/test_video_generation.py` (API tests with httpx ASGI + mocks)

**Interfaces:**
- Consumes: `GenerateVideoRequest`, `video_generation_service.generate_video`
- Produces: `GenerateVideoResponse`; `GET /api/comfyui/output/{filename}` serves `video/mp4` when suffix is `.mp4`

- [ ] **Step 1: Write failing API test with mocked service**

```python
import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_generate_video_endpoint_returns_mp4_url(tmp_path, monkeypatch):
    from app.routers import comfyui_generation as mod

    monkeypatch.setattr(mod, "OUTPUT_DIR", tmp_path)
    still = tmp_path / "abc123.png"
    still.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    fake_mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32

    with patch(
        "app.routers.comfyui_generation.video_generation_service.generate_video",
        new_callable=AsyncMock,
        return_value=fake_mp4,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/comfyui/generate-video",
                json={"image_id": "abc123", "pipeline": "ltx", "frames": 24, "fps": 8},
            )
    assert res.status_code == 200
    data = res.json()
    assert data["pipeline"] == "ltx"
    assert data["video_url"].endswith(".mp4")
    assert data["duration_s"] == pytest.approx(24 / 8)
```

- [ ] **Step 2: Run test — FAIL (404 route)**

```bash
cd backend && PYTHONPATH=. pytest tests/test_video_generation.py::test_generate_video_endpoint_returns_mp4_url -v
```

- [ ] **Step 3: Implement endpoint**

In `comfyui_generation.py`:

1. Import `GenerateVideoRequest`, `GenerateVideoResponse`, `video_generation_service`
2. Add helpers:

```python
def _resolve_still_bytes(req: GenerateVideoRequest) -> bytes:
    if req.image_id:
        path = OUTPUT_DIR / f"{req.image_id}.png"
        if not path.exists():
            # also try raw filename
            path = OUTPUT_DIR / req.image_id
        if not path.exists():
            raise HTTPException(400, detail=f"Still not found for image_id={req.image_id}")
        return path.read_bytes()
    if req.image_url:
        name = req.image_url.rstrip("/").split("/")[-1]
        path = OUTPUT_DIR / name
        if path.exists():
            return path.read_bytes()
        raise HTTPException(400, detail="image_url must point to a local /api/comfyui/output/ file")
    # photo_base64
    import base64
    raw = req.photo_base64.split(",", 1)[-1]
    return base64.b64decode(raw)


def _save_video_locally(video_bytes: bytes, base_url: str) -> tuple[str, str]:
    video_id = uuid.uuid4().hex
    filename = f"{video_id}.mp4"
    (OUTPUT_DIR / filename).write_bytes(video_bytes)
    return f"{base_url}/api/comfyui/output/{filename}", video_id
```

3. Endpoint:

```python
@router.post("/generate-video", response_model=GenerateVideoResponse)
async def comfyui_generate_video(
    req: GenerateVideoRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user),
):
    pipeline = (req.pipeline or settings.default_video_pipeline).lower()
    if pipeline not in ("ltx", "hunyuan", "animatediff"):
        raise HTTPException(400, detail=f"Unknown pipeline: {pipeline}")

    if not settings.skip_points_check and user is not None:
        quota_ok = await membership_service.check_generation_quota(user)
        if not quota_ok:
            raise HTTPException(403, detail="已达每日生成上限，升级会员可增加次数")

    still_bytes = _resolve_still_bytes(req)
    from PIL import Image
    import io
    image = Image.open(io.BytesIO(still_bytes)).convert("RGB")

    seed = req.seed if req.seed is not None else int(uuid.uuid4().hex[:8], 16)
    try:
        video_bytes = await video_generation_service.generate_video(
            pipeline=pipeline,
            image=image,
            seed=seed,
            frames=req.frames,
            fps=req.fps,
        )
    except ComfyUIError as e:
        raise HTTPException(502, detail=str(e)) from e

    base_url = str(request.base_url).rstrip("/")
    video_url, video_id = _save_video_locally(video_bytes, base_url)
    duration_s = req.frames / float(req.fps)

    # optional: deduct points when not skip — mirror generate() if that path deducts
    return GenerateVideoResponse(
        video_url=video_url,
        video_id=video_id,
        pipeline=pipeline,
        duration_s=duration_s,
    )
```

4. Fix `serve_output` media type:

```python
@router.get("/output/{filename}")
async def serve_output(filename: str):
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, detail="File not found")
    media = "video/mp4" if filename.lower().endswith(".mp4") else "image/png"
    return FileResponse(filepath, media_type=media)
```

- [ ] **Step 4: Run API test — PASS**

```bash
cd backend && PYTHONPATH=. pytest tests/test_video_generation.py -v
```

Expected: all unit/API tests PASS.

---

### Task 7: Bake-off CLI + Makefile

**Files:**
- Create: `backend/scripts/video_bakeoff.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: still PNG path(s); calls `video_generation_service.generate_video` for each pipeline sequentially
- Produces: `backend/output/bakeoff/<stem>/{ltx,hunyuan,animatediff}.mp4` + `report.md`

- [ ] **Step 1: Implement `video_bakeoff.py`**

```python
#!/usr/bin/env python3
"""Sequential video bake-off: one still → ltx / hunyuan / animatediff MP4s."""
from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from PIL import Image

# Ensure backend imports work
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.video_generation import VIDEO_PIPELINES, video_generation_service

OUTPUT = ROOT / "output" / "bakeoff"


async def run_one(still: Path, pipelines: list[str], frames: int, fps: int, seed: int) -> list[dict]:
    image = Image.open(still).convert("RGB")
    out_dir = OUTPUT / still.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for pipe in pipelines:
        t0 = time.monotonic()
        status = "ok"
        err = ""
        dest = out_dir / f"{pipe}.mp4"
        try:
            data = await video_generation_service.generate_video(
                pipeline=pipe, image=image, seed=seed, frames=frames, fps=fps
            )
            dest.write_bytes(data)
        except Exception as e:
            status = "fail"
            err = str(e)[:500]
        elapsed = time.monotonic() - t0
        rows.append(
            {
                "still": still.name,
                "pipeline": pipe,
                "status": status,
                "elapsed_s": round(elapsed, 1),
                "path": str(dest) if status == "ok" else "",
                "error": err,
            }
        )
        print(f"[{status}] {still.name} / {pipe}  {elapsed:.1f}s  {err}")
    return rows


async def main_async(args: argparse.Namespace) -> int:
    stills = [Path(p) for p in args.stills]
    for s in stills:
        if not s.exists():
            print(f"missing still: {s}")
            return 1
    pipelines = list(VIDEO_PIPELINES) if args.pipeline == "all" else [args.pipeline]
    all_rows: list[dict] = []
    for still in stills:
        all_rows.extend(
            await run_one(still, pipelines, args.frames, args.fps, args.seed)
        )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = OUTPUT / "report.md"
    lines = [
        "# Video bake-off report",
        "",
        "| still | pipeline | status | elapsed_s | path | error |",
        "|-------|----------|--------|-----------|------|-------|",
    ]
    for r in all_rows:
        lines.append(
            f"| {r['still']} | {r['pipeline']} | {r['status']} | {r['elapsed_s']} | `{r['path']}` | {r['error'][:80]} |"
        )
    report.write_text("\n".join(lines) + "\n")
    print(f"Wrote {report}")
    return 0 if all(r["status"] == "ok" for r in all_rows) else 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("stills", nargs="+", help="Try-on still PNG paths")
    p.add_argument("--pipeline", default="all", choices=["all", "ltx", "hunyuan", "animatediff"])
    p.add_argument("--frames", type=int, default=24)
    p.add_argument("--fps", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Makefile target**

```makefile
video-bakeoff: ## Sequential LTX/Hunyuan/AnimateDiff bake-off. Usage: make video-bakeoff STILL=backend/output/x.png
	@test -n "$(STILL)" || (echo "Set STILL=path/to/still.png"; exit 1)
	cd $(BACKEND_DIR) && PYTHONPATH=. python scripts/video_bakeoff.py $(STILL)
```

- [ ] **Step 3: Run bake-off on 1–2 real stills (ComfyUI up, overnight OK)**

```bash
make video-bakeoff STILL=backend/output/<existing-uuid>.png
open backend/output/bakeoff/report.md
# visually compare the three MP4s
```

- [ ] **Step 4: Set winner in `.env`**

```bash
DEFAULT_VIDEO_PIPELINE=ltx   # or hunyuan / animatediff
```

Restart backend. No mobile rebuild required.

---

### Task 8: Mobile Preview button + player

**Files:**
- Modify: `mobile/package.json` (add `expo-av` matching SDK 57)
- Modify: `mobile/types.ts`
- Modify: `mobile/services/generation.ts`
- Modify: `mobile/app/preview.tsx`

**Interfaces:**
- Produces: `generateVideo({ imageId, imageUrl }) → VideoGenerateResult`
- UI: button enabled when `resultUrl` set; plays `videoUrl`

- [ ] **Step 1: Install expo-av**

```bash
cd mobile && npx expo install expo-av
```

- [ ] **Step 2: Types + API client**

In `mobile/types.ts`:

```typescript
export interface VideoGenerateResult {
  video_url: string;
  video_id: string;
  pipeline: string;
  duration_s: number;
}
```

In `mobile/services/generation.ts`:

```typescript
const VIDEO_TIMEOUT = 900_000;

export async function generateVideo(params: {
  imageId?: string;
  imageUrl?: string;
  photoBase64?: string;
}): Promise<VideoGenerateResult> {
  const body: Record<string, string> = {};
  if (params.imageId) body.image_id = params.imageId;
  else if (params.imageUrl) body.image_url = params.imageUrl;
  else if (params.photoBase64) body.photo_base64 = params.photoBase64;
  else throw new Error('generateVideo requires imageId, imageUrl, or photoBase64');

  const res = await api.post('/api/comfyui/generate-video', body, {
    timeout: VIDEO_TIMEOUT,
  });
  return res.data;
}
```

Track `image_id` from generate response: today `GenerateResult` only has `image_url` / `image_id` — confirm `types.ts` already has `image_id`. If Preview only stores URL, pass `imageUrl: resultUrl` (backend resolves local filename).

- [ ] **Step 3: Preview UI**

In `preview.tsx`:
- State: `videoUrl: string | null`, reuse loading overlay
- Mutation calling `generateVideo({ imageUrl: resultUrl! })`
- Button label `生成短视频` below ActionButtons; `disabled={!resultUrl || videoMutation.isPending}`
- On success set `videoUrl`
- Render player:

```tsx
import { Video, ResizeMode } from 'expo-av';

// when videoUrl:
<Video
  source={{ uri: videoUrl }}
  useNativeControls
  resizeMode={ResizeMode.CONTAIN}
  style={{ width: '100%', height: 360, backgroundColor: '#000' }}
/>
```

- Loading text: `正在生成短视频（本机可能需要数分钟）…`
- onError: `alert('短视频生成失败，请确认 ComfyUI 已启动且视频模型可用')`

- [ ] **Step 4: Manual check on web**

```bash
cd mobile && npx expo start --web
```

Generate a still, tap 生成短视频, confirm MP4 plays (or download works on web if autoplay blocked).

---

### Task 9: Docs + model-locator manifest

**Files:**
- Modify: `README.md` (API table + roadmap bullet)
- Modify: `AGENTS.md` (endpoint + DEFAULT_VIDEO_PIPELINE)
- Modify: `docs/oc_short_video.md` (final bake-off winner)
- Modify: `~/.agents/skills/comfyui-model-locator/references/apps/hairflow.json`

- [ ] **Step 1: Add video keys to hairflow.json**

```json
{
  "photomaker": ["photon_v1.safetensors", "photomaker-v1.bin"],
  "sd15": ["realisticVisionV60B1_v60B1VAE.safetensors"],
  "flux": ["flux1-schnell-Q8_0.gguf", "ae.safetensors", "clip_l.safetensors", "t5xxl_fp16.safetensors"],
  "flux_klein": ["flux-2-klein-4b-Q8_0.gguf", "qwen_3_4b.safetensors", "flux2-vae.safetensors"],
  "video_ltx": ["ltx-video-2b-v0.9.5.safetensors", "t5xxl_fp16.safetensors"],
  "video_hunyuan": ["hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors", "hunyuan_video_vae_bf16.safetensors"],
  "video_animatediff": ["realisticVisionV60B1_v60B1VAE.safetensors"]
}
```

(Add motion module filename to `video_animatediff` once known from Task 5.)

- [ ] **Step 2: README / AGENTS one-liner each for `POST /api/comfyui/generate-video` and bake-off**

- [ ] **Step 3: Run full unit suite**

```bash
cd backend && PYTHONPATH=. pytest tests/ -v
```

Expected: existing tests still green; video tests green.

---

## Parallelization note (multi-agents)

Safe to parallelize **after Task 1–2 complete**:
- Agent A → Task 3 (LTX)
- Agent B → Task 4 (Hunyuan)
- Agent C → Task 5 (AnimateDiff install + builder)

Then serialize Task 6 → 7 → 8 → 9.

Do **not** parallelize live ComfyUI generation.

---

## Plan self-review

| Spec requirement | Task |
|------------------|------|
| Animate try-on still, 2–3s | Tasks 3–5 (`frames`/`fps`), Task 8 |
| Three backends + sequential bake-off | Tasks 3–5, 7 |
| Approach A / DEFAULT_VIDEO_PIPELINE | Tasks 2, 7.4, 8 |
| Preview-only button | Task 8 |
| MP4 save + serve | Task 6 |
| Points / quota when not skip | Task 6 |
| Model locator update | Task 9 |
| No concurrent Mac multi-model | Global constraint + bake-off loop |

No TBD placeholders left; workflow JSON content is intentionally discovery-driven (Task 1) then frozen into `static/workflows/*.json`.
