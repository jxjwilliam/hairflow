import asyncio
import base64
import io
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.models.schemas import GenerateVideoRequest
from app.services.video_generation import VIDEO_PIPELINES, VideoGenerationService


def test_generate_video_request_requires_exactly_one_source():
    with pytest.raises(ValueError, match="exactly one"):
        GenerateVideoRequest()

    with pytest.raises(ValueError, match="exactly one"):
        GenerateVideoRequest(image_id="still", image_url="http://example/still.png")


def test_video_pipelines_include_three():
    assert set(VIDEO_PIPELINES) == {"ltx", "hunyuan", "animatediff"}


def test_build_ltx_workflow_has_load_image_and_save():
    svc = VideoGenerationService(base_url="http://127.0.0.1:8188")
    workflow = svc.build_workflow("ltx", image_filename="still.png", seed=42, frames=24, fps=8)
    types = {
        node["class_type"]
        for node in workflow.values()
        if isinstance(node, dict) and "class_type" in node
    }
    assert any(node_type == "LoadImage" or node_type.startswith("LoadImage") for node_type in types)
    assert any("Save" in node_type or "Video" in node_type or "VHS" in node_type for node_type in types)


def test_ltx_workflow_references_known_weights():
    svc = VideoGenerationService(base_url="http://127.0.0.1:8188")
    workflow = svc.build_workflow("ltx", image_filename="still.png", seed=1, frames=24, fps=8)
    blob = json.dumps(workflow)
    assert "ltx-video-2b-v0.9.5.safetensors" in blob
    assert "t5xxl_fp16.safetensors" in blob or "t5xxl" in blob.lower()
    assert "CheckpointLoaderSimple" in blob
    assert "LTXVPreprocess" in blob
    assert '"type": "ltxv"' in blob or '"type":"ltxv"' in blob
    # Official order: ImgToVideo → Conditioning (not Conditioning before ImgToVideo)
    assert workflow["8"]["class_type"] == "LTXVImgToVideo"
    assert workflow["9"]["class_type"] == "LTXVConditioning"
    assert workflow["9"]["inputs"]["positive"] == ["8", 0]
    assert workflow["12"]["inputs"]["latent_image"] == ["8", 2]
    assert workflow["1"]["inputs"]["image"] == "still.png"
    assert "__IMAGE_FILENAME__" not in blob
    assert "missing_input" not in blob


def test_hunyuan_workflow_references_weights():
    svc = VideoGenerationService(base_url="http://127.0.0.1:8188")
    workflow = svc.build_workflow("hunyuan", image_filename="still.png", seed=2, frames=24, fps=8)
    blob = json.dumps(workflow)
    assert "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors" in blob
    assert "hunyuan_video_vae_bf16.safetensors" in blob
    # Official Hunyuan *Video* I2V path (not DiT / mt5xl)
    assert "TextEncodeHunyuanVideo_ImageToVideo" in blob
    assert "CLIPTextEncodeHunyuanDiT" not in blob
    assert '"type": "hunyuan_video"' in blob or '"type":"hunyuan_video"' in blob
    assert "llava_llama3_fp8_scaled.safetensors" in blob
    assert "llava_llama3_vision.safetensors" in blob


def test_animatediff_workflow_requires_install_but_references_realistic_vision():
    svc = VideoGenerationService(base_url="http://127.0.0.1:8188")
    workflow = svc.build_workflow("animatediff", image_filename="still.png", seed=3, frames=24, fps=8)
    assert "realisticVisionV60B1_v60B1VAE.safetensors" in json.dumps(workflow)


def test_first_media_filename_supports_video_outputs():
    assert VideoGenerationService._first_media_filename(
        {"save": {"videos": [{"filename": "clip.mp4"}]}}
    ) == "clip.mp4"


def test_generate_video_endpoint_returns_mp4_url(tmp_path, monkeypatch):
    asyncio.run(_generate_video_endpoint_returns_mp4_url(tmp_path, monkeypatch))


async def _generate_video_endpoint_returns_mp4_url(tmp_path, monkeypatch):
    from app.main import app
    from app.routers import comfyui_generation as module

    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path)
    image = Image.new("RGB", (16, 16), color="white")
    still = io.BytesIO()
    image.save(still, format="PNG")
    (tmp_path / "abc123.png").write_bytes(still.getvalue())
    fake_mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32

    with patch(
        "app.routers.comfyui_generation.video_generation_service.generate_video",
        new_callable=AsyncMock,
        return_value=fake_mp4,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/comfyui/generate-video",
                json={"image_id": "abc123", "pipeline": "ltx", "frames": 24, "fps": 8},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["pipeline"] == "ltx"
    assert data["video_url"].endswith(".mp4")
    assert data["duration_s"] == pytest.approx(24 / 8)


def test_generate_video_endpoint_accepts_base64_still(tmp_path, monkeypatch):
    asyncio.run(_generate_video_endpoint_accepts_base64_still(tmp_path, monkeypatch))


async def _generate_video_endpoint_accepts_base64_still(tmp_path, monkeypatch):
    from app.main import app
    from app.routers import comfyui_generation as module

    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path)
    image = Image.new("RGB", (16, 16), color="white")
    still = io.BytesIO()
    image.save(still, format="PNG")
    source = base64.b64encode(still.getvalue()).decode()

    with patch(
        "app.routers.comfyui_generation.video_generation_service.generate_video",
        new_callable=AsyncMock,
        return_value=b"\x00\x00\x00\x18ftypmp42",
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/comfyui/generate-video",
                json={"photo_base64": source, "pipeline": "ltx"},
            )

    assert response.status_code == 200
