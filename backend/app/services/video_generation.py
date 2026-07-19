"""ComfyUI image-to-video client and pipeline workflow builders."""

import asyncio
import io
import json
import logging
import time
import uuid
from pathlib import Path

import httpx
from PIL import Image

from app.config import settings
from app.services.comfyui import ComfyUIError

logger = logging.getLogger(__name__)

VIDEO_PIPELINES = ("ltx", "hunyuan", "animatediff")
_COMFYUI_VIDEO_SEMAPHORE = asyncio.Semaphore(1)
_WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / "static" / "workflows"


def _load_workflow_template(name: str) -> dict:
    return json.loads((_WORKFLOWS_DIR / name).read_text())


class VideoGenerationService:
    """Generate a short MP4 from a still image through one ComfyUI prompt."""

    def __init__(self, base_url: str = settings.comfyui_url):
        self.base_url = base_url.rstrip("/")

    async def generate_video(
        self,
        *,
        pipeline: str,
        image: Image.Image,
        seed: int,
        frames: int,
        fps: int,
    ) -> bytes:
        """Upload one still, submit a video workflow, and return its MP4 bytes."""
        async with _COMFYUI_VIDEO_SEMAPHORE:
            filename = await self._upload_image(image, prefix="hairflow_video_input")
            workflow = self.build_workflow(
                pipeline,
                image_filename=filename,
                seed=seed,
                frames=frames,
                fps=fps,
            )
            prompt_id = await self._submit_workflow(workflow)
            result_filename = await self._wait_for_result(
                prompt_id, timeout=settings.video_timeout_seconds
            )
            return await self._download_result(result_filename)

    def build_workflow(
        self, pipeline: str, *, image_filename: str, seed: int, frames: int, fps: int
    ) -> dict:
        """Return an API-format ComfyUI graph for the requested video pipeline."""
        pipeline = pipeline.lower()
        if pipeline == "ltx":
            return self._build_ltx_workflow(image_filename, seed, frames, fps)
        if pipeline == "hunyuan":
            return self._build_hunyuan_workflow(image_filename, seed, frames, fps)
        if pipeline == "animatediff":
            return self._build_animatediff_workflow(image_filename, seed, frames, fps)
        raise ComfyUIError(f"Unknown video pipeline: {pipeline}")

    @staticmethod
    def _parameterize(
        workflow: dict, *, image_filename: str, seed: int, frames: int, fps: int
    ) -> dict:
        """Replace explicit placeholders in a copied API workflow template."""
        replacement = {
            "__IMAGE_FILENAME__": image_filename,
            "__SEED__": seed,
            "__FPS__": float(fps),
            # Video nodes count the supplied first still, hence requested frames + 1.
            "__FRAME_COUNT_WITH_INITIAL__": frames + 1,
        }
        for node in workflow.values():
            for key, value in node.get("inputs", {}).items():
                if isinstance(value, str) and value in replacement:
                    node["inputs"][key] = replacement[value]
        return workflow

    def _build_ltx_workflow(
        self, image_filename: str, seed: int, frames: int, fps: int
    ) -> dict:
        return self._parameterize(
            _load_workflow_template("ltx_i2v_hairstyle.json"),
            image_filename=image_filename,
            seed=seed,
            frames=frames,
            fps=fps,
        )

    def _build_hunyuan_workflow(
        self, image_filename: str, seed: int, frames: int, fps: int
    ) -> dict:
        return self._parameterize(
            _load_workflow_template("hunyuan_i2v_hairstyle.json"),
            image_filename=image_filename,
            seed=seed,
            frames=frames,
            fps=fps,
        )

    def _build_animatediff_workflow(
        self, image_filename: str, seed: int, frames: int, fps: int
    ) -> dict:
        return self._parameterize(
            _load_workflow_template("animatediff_i2v_hairstyle.json"),
            image_filename=image_filename,
            seed=seed,
            frames=frames,
            fps=fps,
        )

    async def _upload_image(self, image: Image.Image, prefix: str) -> str:
        filename = f"{prefix}_{uuid.uuid4().hex[:12]}.png"
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/upload/image",
                files={"image": (filename, buffer, "image/png")},
                data={"overwrite": "true"},
            )
            response.raise_for_status()
        return response.json().get("name", filename)

    async def _submit_workflow(self, workflow: dict) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": str(uuid.uuid4())},
            )
        if response.status_code != 200:
            detail = response.text[:1000]
            try:
                errors = response.json().get("node_errors", {})
                detail = "; ".join(
                    error.get("details", error.get("message", ""))
                    for node in errors.values()
                    for error in node.get("errors", [])
                ) or detail
            except (ValueError, AttributeError):
                pass
            raise ComfyUIError(f"ComfyUI rejected video workflow (HTTP {response.status_code}): {detail}")
        prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            raise ComfyUIError("ComfyUI did not return a prompt_id for video workflow")
        return prompt_id

    @staticmethod
    def _first_media_filename(outputs: dict) -> str | None:
        for node_output in outputs.values():
            for key in ("videos", "gifs", "images"):
                items = node_output.get(key) or []
                if items:
                    return items[0].get("filename")
        return None

    async def _wait_for_result(self, prompt_id: str, *, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        async with httpx.AsyncClient(timeout=10) as client:
            while time.monotonic() < deadline:
                response = await client.get(f"{self.base_url}/history/{prompt_id}")
                response.raise_for_status()
                entry = response.json().get(prompt_id, {})
                filename = self._first_media_filename(entry.get("outputs", {}))
                if filename:
                    return filename
                await asyncio.sleep(2)
        raise ComfyUIError(f"ComfyUI video generation timed out after {timeout}s (prompt_id={prompt_id})")

    async def _download_result(self, filename: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{self.base_url}/view",
                params={"filename": filename, "subfolder": "", "type": "output"},
            )
            response.raise_for_status()
            return response.content


video_generation_service = VideoGenerationService()
