import base64
import io
import logging
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


class ComfyUIService:
    """Client for ComfyUI HTTP REST API.

    ComfyUI exposes:
      - POST /prompt          Submit a workflow
      - GET  /history/{id}    Poll for results
      - GET  /view?filename=  Download generated image
      - POST /upload/image    Upload an image to ComfyUI's input dir

    Workflow JSON: a dict of node_id → {class_type, inputs}.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_hairstyle(
        self,
        photo_base64: str,
        prompt: str,
        negative_prompt: str = "",
        checkpoint: str = "photon_v1.safetensors",
        photomaker_model: str = "photomaker-v1.bin",
        width: int = 512,
        height: int = 768,
        steps: int = 25,
        cfg: float = 6.5,
        seed: int | None = None,
        denoise: float = 0.85,
        timeout: float = 300.0,
    ) -> bytes:
        """Run a PhotoMaker hairstyle generation workflow.

        Args:
            photo_base64: Base64-encoded user photo (JPEG/PNG).
            prompt: Positive prompt describing the desired hairstyle.
            negative_prompt: Things to avoid.
            checkpoint: SD checkpoint name (must be in ComfyUI models).
            photomaker_model: PhotoMaker model filename.
            width, height: Output image size.
            steps, cfg, seed, denoise: KSampler parameters.

        Returns:
            Bytes of the generated image (PNG).

        Raises:
            ComfyUIError: If ComfyUI returns an error or times out.
        """
        # 1. Decode base64, save to temp file
        photo_bytes = base64.b64decode(photo_base64)
        photo = Image.open(io.BytesIO(photo_bytes))

        # 2. Upload to ComfyUI
        filename = await self._upload_image(photo, prefix="hairstyle_input")

        # 3. Build PhotoMaker workflow
        import random
        effective_seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        workflow = self._build_photomaker_workflow(
            image_filename=filename,
            checkpoint=checkpoint,
            photomaker_model=photomaker_model,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            seed=effective_seed,
            denoise=denoise,
        )

        # 4. Submit workflow
        prompt_id = await self._submit_workflow(workflow)

        # 5. Poll for result
        result_filename = await self._wait_for_result(prompt_id, timeout=timeout)

        # 6. Download result
        image_bytes = await self._download_result(result_filename)

        logger.info(
            "ComfyUI generation complete: prompt_id=%s, filename=%s, size=%d",
            prompt_id,
            result_filename,
            len(image_bytes),
        )
        return image_bytes

    # ------------------------------------------------------------------
    # Workflow builder
    # ------------------------------------------------------------------

    def _build_photomaker_workflow(
        self,
        image_filename: str,
        checkpoint: str,
        photomaker_model: str,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg: float,
        seed: int,
        denoise: float,
    ) -> dict:
        """Build a PhotoMaker hairstyle generation workflow JSON.

        Node layout:
          1: LoadImage           → IMAGE (user photo)
          2: CheckpointLoader    → MODEL, CLIP, VAE
          3: PhotoMakerLoader    → PHOTOMAKER
          4: PhotoMakerEncode    → CONDITIONING (identity + style prompt)
          5: CLIPTextEncode      → CONDITIONING (negative prompt)
          6: EmptyLatentImage    → LATENT
          7: KSampler            → LATENT
          8: VAEDecode           → IMAGE
          9: SaveImage           → (saves to output/)
        """
        # Ensure trigger word is present for PhotoMaker
        if "img" not in prompt:
            prompt = f"{prompt}, img"

        return {
            "1": {
                "inputs": {"image": image_filename},
                "class_type": "LoadImage",
            },
            "2": {
                "inputs": {"ckpt_name": checkpoint},
                "class_type": "CheckpointLoaderSimple",
            },
            "3": {
                "inputs": {"photomaker_model_name": photomaker_model},
                "class_type": "PhotoMakerLoader",
            },
            "4": {
                "inputs": {
                    "photomaker": ["3", 0],
                    "image": ["1", 0],
                    "clip": ["2", 1],
                    "text": prompt,
                },
                "class_type": "PhotoMakerEncode",
            },
            "5": {
                "inputs": {
                    "text": negative_prompt or "ugly, deformed, bad anatomy, blurry, low quality, disfigured, extra fingers, mutated hands",
                    "clip": ["2", 1],
                },
                "class_type": "CLIPTextEncode",
            },
            "6": {
                "inputs": {"width": width, "height": height, "batch_size": 1},
                "class_type": "EmptyLatentImage",
            },
            "7": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": denoise,
                    "model": ["2", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["6", 0],
                },
                "class_type": "KSampler",
            },
            "8": {
                "inputs": {"samples": ["7", 0], "vae": ["2", 2]},
                "class_type": "VAEDecode",
            },
            "9": {
                "inputs": {
                    "filename_prefix": "hairstyle_result",
                    "images": ["8", 0],
                },
                "class_type": "SaveImage",
            },
        }

    # ------------------------------------------------------------------
    # Low-level ComfyUI HTTP helpers
    # ------------------------------------------------------------------

    async def _upload_image(self, image: Image.Image, prefix: str = "input") -> str:
        """Upload a PIL Image to ComfyUI's input directory.

        Returns the filename (without path) to use in LoadImage nodes.
        """
        filename = f"{prefix}_{uuid.uuid4().hex[:12]}.png"
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)

        url = f"{self.base_url}/upload/image"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                files={"image": (filename, buf, "image/png")},
                data={"overwrite": "true"},
            )
            resp.raise_for_status()
            result = resp.json()
            # Response: {"name": "input_abc123.png", "subfolder": "", "type": "input"}
            uploaded_name = result.get("name", filename)
            logger.info("Uploaded image to ComfyUI: %s", uploaded_name)
            return uploaded_name

    async def _submit_workflow(self, workflow: dict) -> str:
        """Submit a workflow to ComfyUI, return prompt_id."""
        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}

        url = f"{self.base_url}/prompt"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        if "prompt_id" not in data:
            error_msg = data.get("error", "Unknown ComfyUI error")
            raise ComfyUIError(f"Failed to submit workflow: {error_msg}")

        prompt_id = data["prompt_id"]
        logger.info("ComfyUI workflow submitted: prompt_id=%s", prompt_id)
        return prompt_id

    async def _wait_for_result(
        self,
        prompt_id: str,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
    ) -> str:
        """Poll ComfyUI /history/{prompt_id} until the workflow completes.

        Returns the filename of the first output image.
        """
        url = f"{self.base_url}/history/{prompt_id}"
        deadline = time.monotonic() + timeout

        async with httpx.AsyncClient(timeout=10) as client:
            while time.monotonic() < deadline:
                resp = await client.get(url)
                resp.raise_for_status()
                history = resp.json()

                if prompt_id in history:
                    entry = history[prompt_id]
                    outputs = entry.get("outputs", {})
                    # Find the SaveImage node output
                    for node_id, node_output in outputs.items():
                        images = node_output.get("images", [])
                        if images:
                            filename = images[0]["filename"]
                            logger.info(
                                "ComfyUI result ready: prompt_id=%s, filename=%s",
                                prompt_id,
                                filename,
                            )
                            return filename

                await _async_sleep(poll_interval)

        raise ComfyUIError(
            f"ComfyUI generation timed out after {timeout}s (prompt_id={prompt_id})"
        )

    async def _download_result(self, filename: str) -> bytes:
        """Download a generated image from ComfyUI's output."""
        url = f"{self.base_url}/view"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                url,
                params={
                    "filename": filename,
                    "subfolder": "",
                    "type": "output",
                },
            )
            resp.raise_for_status()
            return resp.content


class ComfyUIError(Exception):
    """Raised when ComfyUI API returns an error or times out."""


async def _async_sleep(seconds: float):
    """Async sleep helper."""
    import asyncio
    await asyncio.sleep(seconds)


comfyui_service = ComfyUIService(base_url=settings.comfyui_url)
