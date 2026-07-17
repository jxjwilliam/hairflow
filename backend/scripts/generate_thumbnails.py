#!/usr/bin/env python3
"""Generate catalog thumbnail portraits via local ComfyUI txt2img API.

Usage:
  cd backend
  python scripts/generate_thumbnails.py
  python scripts/generate_thumbnails.py --id m1 --force --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import uuid
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_COMFYUI = BACKEND_ROOT / "data" / "templates_comfyui.json"
TEMPLATES_LEGACY = BACKEND_ROOT / "data" / "templates.json"
THUMB_DIR = BACKEND_ROOT / "static" / "thumbnails"
DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"
POLL_INTERVAL = 2.0
TIMEOUT = 300.0


def thumbnail_rel_path(template_id: str) -> str:
    return f"/static/thumbnails/{template_id}.png"


def build_txt2img_workflow(
    *,
    prompt: str,
    negative_prompt: str,
    checkpoint: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    seed: int,
) -> dict:
    """Build the same graph as workflows/txt2img_hairstyle_catalog.json."""
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
            "inputs": {
                "text": negative_prompt
                or "ugly, deformed, bad anatomy, blurry, low quality, text, watermark",
                "clip": ["1", 1],
            },
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
            "inputs": {
                "filename_prefix": "catalog_thumb",
                "images": ["6", 0],
            },
            "class_type": "SaveImage",
        },
    }


def update_template_thumbnails(path: Path, updates: dict[str, str]) -> None:
    """Atomically update thumbnail fields for the given template ids."""
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data:
        tid = item.get("id")
        if tid in updates:
            item["thumbnail"] = updates[tid]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_templates() -> list[dict]:
    return json.loads(TEMPLATES_COMFYUI.read_text(encoding="utf-8"))


def check_comfyui(base_url: str) -> None:
    url = f"{base_url.rstrip('/')}/system_stats"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"ComfyUI is unreachable at {base_url}. "
            f"Start Pinokio ComfyUI first. Underlying error: {exc}"
        ) from exc


def submit_workflow(base_url: str, workflow: dict) -> str:
    payload = {"prompt": workflow, "client_id": str(uuid.uuid4())}
    resp = httpx.post(f"{base_url.rstrip('/')}/prompt", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "prompt_id" not in data:
        raise RuntimeError(f"ComfyUI submit failed: {data}")
    return data["prompt_id"]


def wait_for_image(base_url: str, prompt_id: str, timeout: float = TIMEOUT) -> str:
    url = f"{base_url.rstrip('/')}/history/{prompt_id}"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            for node_output in outputs.values():
                images = node_output.get("images") or []
                if images:
                    return images[0]["filename"]
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"ComfyUI timed out after {timeout}s (prompt_id={prompt_id})")


def download_image(base_url: str, filename: str) -> bytes:
    resp = httpx.get(
        f"{base_url.rstrip('/')}/view",
        params={"filename": filename, "subfolder": "", "type": "output"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content


def generate_one(
    template: dict,
    *,
    base_url: str,
    seed: int,
    force: bool,
    dry_run: bool,
) -> Path | None:
    """Generate or skip one thumbnail. Returns output path if PNG should exist."""
    tid = template["id"]
    out_path = THUMB_DIR / f"{tid}.png"

    if out_path.exists() and not force and not dry_run:
        print(f"[skip] {tid} exists ({out_path})")
        return out_path

    prompt = template["positive_prompt"]
    negative = template.get("negative_prompt", "")
    checkpoint = template.get("checkpoint", "photon_v1.safetensors")
    width = int(template.get("width", 512))
    height = int(template.get("height", 768))
    steps = int(template.get("steps", 25))
    cfg = float(template.get("cfg", 6.5))

    print(f"[gen] {tid} seed={seed} steps={steps} cfg={cfg}")
    print(f"      prompt={prompt[:100]}...")

    if dry_run:
        return out_path

    workflow = build_txt2img_workflow(
        prompt=prompt,
        negative_prompt=negative,
        checkpoint=checkpoint,
        width=width,
        height=height,
        steps=steps,
        cfg=cfg,
        seed=seed,
    )
    prompt_id = submit_workflow(base_url, workflow)
    filename = wait_for_image(base_url, prompt_id)
    png = download_image(base_url, filename)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(png)
    print(f"[ok]  {tid} -> {out_path} ({len(png)} bytes)")
    return out_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate ComfyUI catalog thumbnails")
    p.add_argument("--id", help="Generate only this template id")
    p.add_argument("--seed", type=int, default=None, help="Fixed seed for all selected templates")
    p.add_argument("--comfyui-url", default=DEFAULT_COMFYUI_URL)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--fail-fast", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    templates = load_templates()
    if args.id:
        templates = [t for t in templates if t["id"] == args.id]
        if not templates:
            print(f"Unknown template id: {args.id}", file=sys.stderr)
            return 2

    if not args.dry_run:
        check_comfyui(args.comfyui_url)

    updates: dict[str, str] = {}
    failures: list[str] = []

    for t in templates:
        seed = args.seed if args.seed is not None else random.randint(0, 2**31 - 1)
        try:
            out_path = generate_one(
                t,
                base_url=args.comfyui_url,
                seed=seed,
                force=args.force,
                dry_run=args.dry_run,
            )
            if not args.dry_run and out_path is not None and out_path.exists():
                updates[t["id"]] = thumbnail_rel_path(t["id"])
        except Exception as exc:  # noqa: BLE001
            failures.append(t["id"])
            print(f"[fail] {t['id']}: {exc}", file=sys.stderr)
            if args.fail_fast:
                break

    if updates and not args.dry_run:
        update_template_thumbnails(TEMPLATES_COMFYUI, updates)
        update_template_thumbnails(TEMPLATES_LEGACY, updates)
        print(f"Updated thumbnail paths for: {', '.join(sorted(updates))}")

    if failures:
        print(f"Failed templates: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
