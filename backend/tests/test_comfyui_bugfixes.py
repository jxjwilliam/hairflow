"""Regression tests for 2026-07-17 bug report:

1. face.crop_face crashed on RGBA PNG uploads ("cannot write mode RGBA as JPEG")
2. ComfyUI /prompt 400 validation errors were swallowed (opaque 502 to the app)
3. flux_klein pipeline pointed at FLUX.1 VAE (ae.safetensors) instead of flux2-vae
"""

import asyncio
import base64
import io
import json
from unittest.mock import patch

import httpx
import pytest
from PIL import Image

from app.services.comfyui import ComfyUIService, ComfyUIError
from app.services.face import FaceService


def _png_base64(mode: str = "RGBA", size: tuple[int, int] = (200, 200)) -> str:
    color = (255, 0, 0, 128) if mode == "RGBA" else (255, 0, 0)
    img = Image.new(mode, size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------------
# 1. crop_face must convert RGBA -> RGB before saving JPEG
# ---------------------------------------------------------------------

def test_crop_face_handles_rgba_png():
    svc = FaceService()
    fake_detection = {
        "face_detected": True,
        "face_count": 1,
        "confidence": 0.9,
        "bbox": [0.25, 0.25, 0.5, 0.5],
    }
    with patch.object(svc, "detect_face", return_value=fake_detection):
        cropped = asyncio.run(svc.crop_face(_png_base64("RGBA"), padding=0.1))

    assert cropped is not None, "crop_face returned None for RGBA PNG upload"
    img = Image.open(io.BytesIO(base64.b64decode(cropped)))
    assert img.format == "JPEG"
    assert img.mode == "RGB"


# ---------------------------------------------------------------------
# 2. _submit_workflow must surface ComfyUI's validation error body
# ---------------------------------------------------------------------

_FAKE_400_BODY = {
    "error": {
        "type": "prompt_outputs_failed_validation",
        "message": "Prompt outputs failed validation",
        "details": "",
        "extra_info": {},
    },
    "node_errors": {
        "4": {
            "errors": [
                {
                    "type": "value_not_in_list",
                    "message": "Value not in list",
                    "details": "vae_name: 'ae.safetensors' not in ['flux2-vae.safetensors']",
                    "extra_info": {"input_name": "vae_name", "received_value": "ae.safetensors"},
                }
            ],
            "dependent_outputs": ["9"],
            "class_type": "VAELoader",
        }
    },
}


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Client error '{self.status_code}'", request=None, response=None
            )


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None):
        return _FakeResponse(400, _FAKE_400_BODY)


def test_submit_workflow_surfaces_comfyui_validation_error(monkeypatch):
    monkeypatch.setattr("app.services.comfyui.httpx.AsyncClient", _FakeClient)
    svc = ComfyUIService()

    with pytest.raises(ComfyUIError) as exc_info:
        asyncio.run(svc._submit_workflow({"1": {"class_type": "X", "inputs": {}}}))

    msg = str(exc_info.value)
    assert "vae_name" in msg, f"validation detail missing from error: {msg}"
    assert "ae.safetensors" in msg, f"received value missing from error: {msg}"


# ---------------------------------------------------------------------
# 3. flux_klein must use the FLUX.2 VAE, not the FLUX.1 ae.safetensors
# ---------------------------------------------------------------------

def _capture_workflow(monkeypatch, svc: ComfyUIService) -> dict:
    captured: dict = {}

    async def fake_upload(self, image, prefix="input"):
        return "test.png"

    async def fake_submit(self, workflow):
        captured["workflow"] = workflow
        return "pid"

    async def fake_wait(self, prompt_id, timeout=300.0):
        return "out.png"

    async def fake_download(self, filename):
        return b"\x89PNG"

    monkeypatch.setattr(ComfyUIService, "_upload_image", fake_upload)
    monkeypatch.setattr(ComfyUIService, "_submit_workflow", fake_submit)
    monkeypatch.setattr(ComfyUIService, "_wait_for_result", fake_wait)
    monkeypatch.setattr(ComfyUIService, "_download_result", fake_download)
    return captured


def _vae_name_of(workflow: dict) -> str:
    for node in workflow.values():
        if node["class_type"] == "VAELoader":
            return node["inputs"]["vae_name"]
    raise AssertionError("no VAELoader node in workflow")


def test_flux_klein_img2img_uses_flux2_vae(monkeypatch):
    svc = ComfyUIService()
    captured = _capture_workflow(monkeypatch, svc)
    asyncio.run(
        svc.generate(
            pipeline="flux_klein",
            method="img2img",
            prompt="test",
            photo_base64=_png_base64("RGB", (64, 64)),
        )
    )
    assert _vae_name_of(captured["workflow"]) == "flux2-vae.safetensors"


def test_flux_schnell_img2img_keeps_ae_vae(monkeypatch):
    svc = ComfyUIService()
    captured = _capture_workflow(monkeypatch, svc)
    asyncio.run(
        svc.generate(
            pipeline="flux",
            method="img2img",
            prompt="test",
            photo_base64=_png_base64("RGB", (64, 64)),
        )
    )
    assert _vae_name_of(captured["workflow"]) == "ae.safetensors"


# ---------------------------------------------------------------------
# 4. Template SD1.5 checkpoint must not leak into flux pipelines as UNET
# ---------------------------------------------------------------------

def _unet_name_of(workflow: dict) -> str:
    for node in workflow.values():
        if node["class_type"] == "UnetLoaderGGUF":
            return node["inputs"]["unet_name"]
    raise AssertionError("no UnetLoaderGGUF node in workflow")


def test_flux_klein_ignores_sd15_checkpoint_override(monkeypatch):
    """Router passes template['checkpoint'] (photon_v1.safetensors, SD1.5) —
    flux pipelines must fall back to their GGUF default instead of 400ing."""
    svc = ComfyUIService()
    captured = _capture_workflow(monkeypatch, svc)
    asyncio.run(
        svc.generate(
            pipeline="flux_klein",
            method="img2img",
            prompt="test",
            photo_base64=_png_base64("RGB", (64, 64)),
            checkpoint="photon_v1.safetensors",
        )
    )
    assert _unet_name_of(captured["workflow"]) == "flux-2-klein-4b-Q8_0.gguf"


def test_flux_klein_accepts_gguf_checkpoint_override(monkeypatch):
    svc = ComfyUIService()
    captured = _capture_workflow(monkeypatch, svc)
    asyncio.run(
        svc.generate(
            pipeline="flux_klein",
            method="img2img",
            prompt="test",
            photo_base64=_png_base64("RGB", (64, 64)),
            checkpoint="flux1-dev-F16.gguf",
        )
    )
    assert _unet_name_of(captured["workflow"]) == "flux1-dev-F16.gguf"


# ---------------------------------------------------------------------
# 5. flux_klein img2img must use the native edit workflow (ReferenceLatent)
#    so the selfie identity is preserved instead of resampled away
# ---------------------------------------------------------------------

def test_flux_klein_img2img_uses_native_edit_layout(monkeypatch):
    svc = ComfyUIService()
    captured = _capture_workflow(monkeypatch, svc)
    asyncio.run(
        svc.generate(
            pipeline="flux_klein",
            method="img2img",
            prompt="short neat haircut",
            photo_base64=_png_base64("RGB", (64, 64)),
            steps=4,
        )
    )
    wf = captured["workflow"]
    class_types = [n["class_type"] for n in wf.values()]

    clip_loaders = [n for n in wf.values() if n["class_type"] == "CLIPLoader"]
    assert len(clip_loaders) == 1
    assert clip_loaders[0]["inputs"]["type"] == "flux2"
    assert clip_loaders[0]["inputs"]["clip_name"] == "qwen_3_4b.safetensors"

    assert "DualCLIPLoaderGGUF" not in class_types
    assert "KSampler" not in class_types

    vae_encode_ids = [nid for nid, n in wf.items() if n["class_type"] == "VAEEncode"]
    assert len(vae_encode_ids) == 1
    ref_nodes = [n for n in wf.values() if n["class_type"] == "ReferenceLatent"]
    assert len(ref_nodes) == 2
    for rn in ref_nodes:
        assert rn["inputs"]["latent"] == [vae_encode_ids[0], 0]

    guider = next(n for n in wf.values() if n["class_type"] == "CFGGuider")
    assert guider["inputs"]["cfg"] == 1.0

    sampler = next(n for n in wf.values() if n["class_type"] == "KSamplerSelect")
    assert sampler["inputs"]["sampler_name"] == "euler"

    scheduler = next(n for n in wf.values() if n["class_type"] == "Flux2Scheduler")
    assert scheduler["inputs"]["steps"] == 4

    encode = next(n for n in wf.values() if n["class_type"] == "CLIPTextEncode")
    assert encode["inputs"]["text"].startswith(
        "Give the person in the image this hairstyle:"
    )
    assert "short neat haircut" in encode["inputs"]["text"]
