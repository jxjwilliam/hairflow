import base64
import io
import logging
import random
import time
import uuid

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
        import random as random_module
        effective_seed = seed if seed is not None else random_module.randint(0, 2**31 - 1)
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
    # Pipeline dispatch
    # ------------------------------------------------------------------

    async def generate(
        self,
        pipeline: str,
        method: str,
        prompt: str,
        negative_prompt: str = "",
        photo_base64: str | None = None,
        checkpoint: str = "",
        width: int = 512,
        height: int = 768,
        steps: int = 25,
        cfg: float = 6.5,
        denoise: float = 0.85,
        seed: int | None = None,
        timeout: float = 300.0,
    ) -> bytes:
        """Run any pipeline: photomaker, sd15, flux, flux_klein with txt2img or img2img.

        Args:
            pipeline: Model family - photomaker | sd15 | flux | flux_klein
            method: Generation method - photomaker | txt2img | img2img
            prompt: Positive prompt.
            negative_prompt: Negative prompt (ignored by flux pipelines).
            photo_base64: Required for photomaker/img2img, optional for txt2img.
            checkpoint: Override auto-detected checkpoint filename.
            width, height: Output dimensions.
            steps, cfg, denoise: Generation parameters.
            seed: Explicit seed (random if None).
            timeout: Max wait for ComfyUI completion.
        """
        effective_seed = seed if seed is not None else random.randint(0, 2**31 - 1)

        if pipeline == "photomaker":
            if not photo_base64:
                raise ComfyUIError("photo_base64 required for photomaker pipeline")
            photo_bytes = base64.b64decode(photo_base64)
            photo = Image.open(io.BytesIO(photo_bytes))
            filename = await self._upload_image(photo, prefix="photomaker_input")
            template_cp = checkpoint or "photon_v1.safetensors"
            # Use photomaker-v2.bin? No — MVP only supports v1.
            workflow = self._build_photomaker_workflow(
                image_filename=filename,
                checkpoint=template_cp,
                photomaker_model="photomaker-v1.bin",
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                seed=effective_seed,
                denoise=denoise,
            )
        elif pipeline == "sd15":
            if method == "txt2img":
                workflow = self._build_sd15_txt2img_workflow(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    checkpoint=checkpoint or "realisticVisionV60B1_v60B1VAE.safetensors",
                    width=width,
                    height=height,
                    steps=steps,
                    cfg=cfg,
                    seed=effective_seed,
                )
            else:  # img2img
                if not photo_base64:
                    raise ComfyUIError("photo_base64 required for img2img mode")
                photo_bytes = base64.b64decode(photo_base64)
                photo = Image.open(io.BytesIO(photo_bytes))
                filename = await self._upload_image(photo, prefix="sd15_input")
                workflow = self._build_sd15_img2img_workflow(
                    image_filename=filename,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    checkpoint=checkpoint or "realisticVisionV60B1_v60B1VAE.safetensors",
                    width=width,
                    height=height,
                    steps=steps,
                    cfg=cfg,
                    seed=effective_seed,
                    denoise=denoise,
                )
        elif pipeline in ("flux", "flux_klein"):
            if method == "txt2img":
                workflow = self._build_flux_txt2img_workflow(
                    prompt=prompt,
                    unet_name=checkpoint or self._flux_unet_for(pipeline),
                    clip_name1="clip_l.safetensors",
                    clip_name2=self._flux_clip_for(pipeline),
                    vae_name="ae.safetensors",
                    width=width,
                    height=height,
                    steps=steps,
                    seed=effective_seed,
                )
            else:  # img2img
                if not photo_base64:
                    raise ComfyUIError("photo_base64 required for img2img mode")
                photo_bytes = base64.b64decode(photo_base64)
                photo = Image.open(io.BytesIO(photo_bytes))
                filename = await self._upload_image(photo, prefix="flux_input")
                workflow = self._build_flux_img2img_workflow(
                    image_filename=filename,
                    prompt=prompt,
                    unet_name=checkpoint or self._flux_unet_for(pipeline),
                    clip_name1="clip_l.safetensors",
                    clip_name2=self._flux_clip_for(pipeline),
                    vae_name="ae.safetensors",
                    steps=steps,
                    seed=effective_seed,
                    denoise=denoise,
                )
        else:
            raise ComfyUIError(f"Unknown pipeline: {pipeline}")

        prompt_id = await self._submit_workflow(workflow)
        result_filename = await self._wait_for_result(prompt_id, timeout=timeout)
        image_bytes = await self._download_result(result_filename)

        logger.info(
            "ComfyUI generation complete: pipeline=%s method=%s prompt_id=%s filename=%s size=%d",
            pipeline, method, prompt_id, result_filename, len(image_bytes),
        )
        return image_bytes

    @staticmethod
    def _flux_unet_for(pipeline: str) -> str:
        """Return the default UNET GGUF filename for the given FLUX pipeline."""
        if pipeline == "flux_klein":
            return "flux-2-klein-4b-Q8_0.gguf"
        return "flux1-schnell-Q8_0.gguf"

    @staticmethod
    def _flux_clip_for(pipeline: str) -> str:
        """Return the second CLIP encoder for the given FLUX pipeline."""
        if pipeline == "flux_klein":
            return "qwen_3_4b.safetensors"
        return "t5xxl_fp16.safetensors"

    # ------------------------------------------------------------------
    # Workflow builders
    # ------------------------------------------------------------------

    def _build_sd15_txt2img_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        checkpoint: str,
        width: int,
        height: int,
        steps: int,
        cfg: float,
        seed: int,
    ) -> dict:
        """Build a standard SD1.5 text-to-image workflow.

        Node layout:
          1: CheckpointLoaderSimple  → MODEL, CLIP, VAE
          2: CLIPTextEncode          → positive conditioning
          3: CLIPTextEncode          → negative conditioning
          4: EmptyLatentImage        → LATENT
          5: KSampler                → LATENT
          6: VAEDecode               → IMAGE
          7: SaveImage
        """
        neg = negative_prompt or "ugly, deformed, bad anatomy, blurry, low quality"
        return {
            "1": {
                "inputs": {"ckpt_name": checkpoint},
                "class_type": "CheckpointLoaderSimple",
            },
            "2": {
                "inputs": {"text": prompt, "clip": ["1", 1]},
                "class_type": "CLIPTextEncode",
            },
            "3": {
                "inputs": {"text": neg, "clip": ["1", 1]},
                "class_type": "CLIPTextEncode",
            },
            "4": {
                "inputs": {"width": width, "height": height, "batch_size": 1},
                "class_type": "EmptyLatentImage",
            },
            "5": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                },
                "class_type": "KSampler",
            },
            "6": {
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
                "class_type": "VAEDecode",
            },
            "7": {
                "inputs": {"filename_prefix": "sd15_result", "images": ["6", 0]},
                "class_type": "SaveImage",
            },
        }

    def _build_sd15_img2img_workflow(
        self,
        image_filename: str,
        prompt: str,
        negative_prompt: str,
        checkpoint: str,
        width: int,
        height: int,
        steps: int,
        cfg: float,
        seed: int,
        denoise: float,
    ) -> dict:
        """Build SD1.5 image-to-image workflow using the user photo as base.

        Node layout:
          1: LoadImage              → IMAGE
          2: CheckpointLoaderSimple → MODEL, CLIP, VAE
          3: CLIPTextEncode         → positive conditioning
          4: CLIPTextEncode         → negative conditioning
          5: VAEEncode              → LATENT (from user photo)
          6: KSampler               → LATENT (with denoise < 1.0)
          7: VAEDecode              → IMAGE
          8: SaveImage
        """
        neg = negative_prompt or "ugly, deformed, bad anatomy, blurry, low quality"
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
                "inputs": {"text": prompt, "clip": ["2", 1]},
                "class_type": "CLIPTextEncode",
            },
            "4": {
                "inputs": {"text": neg, "clip": ["2", 1]},
                "class_type": "CLIPTextEncode",
            },
            "5": {
                "inputs": {"pixels": ["1", 0], "vae": ["2", 2]},
                "class_type": "VAEEncode",
            },
            "6": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": denoise,
                    "model": ["2", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0],
                },
                "class_type": "KSampler",
            },
            "7": {
                "inputs": {"samples": ["6", 0], "vae": ["2", 2]},
                "class_type": "VAEDecode",
            },
            "8": {
                "inputs": {"filename_prefix": "sd15_img2img_result", "images": ["7", 0]},
                "class_type": "SaveImage",
            },
        }

    def _build_flux_txt2img_workflow(
        self,
        prompt: str,
        unet_name: str,
        clip_name1: str,
        clip_name2: str,
        vae_name: str,
        width: int,
        height: int,
        steps: int,
        seed: int,
    ) -> dict:
        """Build FLUX GGUF text-to-image workflow.

        Uses ComfyUI-GGUF nodes (UnetLoaderGGUF + DualCLIPLoaderGGUF).

        Node layout:
          1: UnetLoaderGGUF        → MODEL
          2: DualCLIPLoaderGGUF    → CLIP
          3: VAELoader             → VAE
          4: CLIPTextEncode        → positive conditioning
          5: EmptyLatentImage      → LATENT
          6: KSampler              → LATENT
          7: VAEDecode             → IMAGE
          8: SaveImage
        """
        # FLUX.1 schnell uses fixed cfg=1.0; FLUX.2 Klein uses guidance
        return {
            "1": {
                "inputs": {"unet_name": unet_name},
                "class_type": "UnetLoaderGGUF",
            },
            "2": {
                "inputs": {
                    "clip_name1": clip_name1,
                    "clip_name2": clip_name2,
                    "type": "flux",
                },
                "class_type": "DualCLIPLoaderGGUF",
            },
            "3": {
                "inputs": {"vae_name": vae_name},
                "class_type": "VAELoader",
            },
            "4": {
                "inputs": {"text": prompt, "clip": ["2", 0]},
                "class_type": "CLIPTextEncode",
            },
            "5": {
                "inputs": {"width": width, "height": height, "batch_size": 1},
                "class_type": "EmptyLatentImage",
            },
            "6": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": 1.0,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["4", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0],
                },
                "class_type": "KSampler",
            },
            "7": {
                "inputs": {"samples": ["6", 0], "vae": ["3", 0]},
                "class_type": "VAEDecode",
            },
            "8": {
                "inputs": {"filename_prefix": "flux_result", "images": ["7", 0]},
                "class_type": "SaveImage",
            },
        }

    def _build_flux_img2img_workflow(
        self,
        image_filename: str,
        prompt: str,
        unet_name: str,
        clip_name1: str,
        clip_name2: str,
        vae_name: str,
        steps: int,
        seed: int,
        denoise: float,
    ) -> dict:
        """Build FLUX GGUF image-to-image workflow using the user photo as base.

        Node layout:
          1: LoadImage              → IMAGE
          2: UnetLoaderGGUF         → MODEL
          3: DualCLIPLoaderGGUF     → CLIP
          4: VAELoader              → VAE
          5: CLIPTextEncode         → positive conditioning
          6: VAEEncode              → LATENT (from user photo)
          7: KSampler               → LATENT (with denoise)
          8: VAEDecode              → IMAGE
          9: SaveImage
        """
        return {
            "1": {
                "inputs": {"image": image_filename},
                "class_type": "LoadImage",
            },
            "2": {
                "inputs": {"unet_name": unet_name},
                "class_type": "UnetLoaderGGUF",
            },
            "3": {
                "inputs": {
                    "clip_name1": clip_name1,
                    "clip_name2": clip_name2,
                    "type": "flux",
                },
                "class_type": "DualCLIPLoaderGGUF",
            },
            "4": {
                "inputs": {"vae_name": vae_name},
                "class_type": "VAELoader",
            },
            "5": {
                "inputs": {"text": prompt, "clip": ["3", 0]},
                "class_type": "CLIPTextEncode",
            },
            "6": {
                "inputs": {"pixels": ["1", 0], "vae": ["4", 0]},
                "class_type": "VAEEncode",
            },
            "7": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": 1.0,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": denoise,
                    "model": ["2", 0],
                    "positive": ["5", 0],
                    "negative": ["5", 0],
                    "latent_image": ["6", 0],
                },
                "class_type": "KSampler",
            },
            "8": {
                "inputs": {"samples": ["7", 0], "vae": ["4", 0]},
                "class_type": "VAEDecode",
            },
            "9": {
                "inputs": {"filename_prefix": "flux_img2img_result", "images": ["8", 0]},
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
