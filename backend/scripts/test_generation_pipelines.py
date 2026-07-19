#!/usr/bin/env python3
"""Test ComfyUI generation pipelines via the backend API.

Tests 4 pipeline/method combinations:
  1. sd15  + txt2img  (no photo needed by ComfyUI, but endpoint requires it)
  2. flux  + txt2img
  3. sd15  + img2img
  4. flux_klein + img2img

Usage:
  python scripts/test_generation_pipelines.py

Requires:
  - Backend running at http://localhost:8000
  - ComfyUI running at http://127.0.0.1:8188 (or as configured in backend .env)
"""

import asyncio
import base64
import json
import random
import sys
import time
from pathlib import Path

import httpx

BACKEND_URL = "http://localhost:8000"
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent  # hairstyle/
DATA_DIR = PROJECT_DIR / "data"  # hairstyle/data/ (test photos)
TEMPLATES_FILE = PROJECT_DIR / "backend" / "data" / "templates_comfyui.json"  # backend/data/ (templates)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "pipeline_test"

# Test scenarios: (pipeline, method, description)
TESTS = [
    ("sd15",        "txt2img",  "SD1.5 txt2img"),
    ("flux",        "txt2img",  "FLUX.1 Schnell txt2img"),
    ("sd15",        "img2img",  "SD1.5 img2img"),
    ("flux_klein",  "img2img",  "FLUX.2 Klein img2img (native edit)"),
]


def pick_random_photo() -> tuple[str, str]:
    """Return (base64_data, filename) of a random test photo."""
    photos = sorted(DATA_DIR.glob("*.png")) + sorted(DATA_DIR.glob("*.jpg")) + sorted(DATA_DIR.glob("*.jpeg"))
    if not photos:
        print("❌ No test photos found in data/")
        sys.exit(1)
    photo_path = random.choice(photos)
    print(f"  📷 Photo: {photo_path.name}")
    data = base64.b64encode(photo_path.read_bytes()).decode()
    return data, photo_path.stem


def pick_random_templates(count: int = 4) -> list[dict]:
    """Pick random templates from templates_comfyui.json."""
    templates = json.loads(TEMPLATES_FILE.read_text())
    # Pick random templates (allow repeats if we have more tests than templates)
    picks = random.choices(templates, k=count)
    for t in picks:
        print(f"  💇 Template: {t['id']} — {t['name']}")
    return picks


async def test_one(
    client: httpx.AsyncClient,
    pipeline: str,
    method: str,
    desc: str,
    photo_base64: str,
    template: dict,
    index: int,
) -> dict:
    """Run one generation test."""
    url = f"{BACKEND_URL}/api/comfyui/generate"
    payload = {
        "photo_base64": photo_base64,
        "style_id": template["id"],
        "pipeline": pipeline,
        "method": method,
        "steps": 15,  # reduced for CPU perf; was 25
        "cfg": template.get("cfg", 6.5),
        "denoise": template.get("denoise", 0.85),
    }

    # Strip photo for txt2img (ComfyUI doesn't use it, but endpoint still requires it)
    # Actually the endpoint requires photo_base64 so we keep it for all.

    label = f"[{index+1}/4] {desc}"
    print(f"\n  🧪 {label}")
    print(f"     URL: POST {url}")
    print(f"     Payload: pipeline={pipeline}, method={method}, style={template['id']}")

    start = time.monotonic()
    try:
        resp = await client.post(url, json=payload, timeout=600.0)
        elapsed = time.monotonic() - start
        print(f"     Status: {resp.status_code} ({elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            print(f"     ✅ SUCCESS: {data.get('image_url', '?')}")
            return {"status": "ok", "elapsed": elapsed, "desc": desc, "url": data.get("image_url")}
        else:
            body = resp.text[:500]
            print(f"     ❌ FAILED: {body}")
            return {"status": "fail", "elapsed": elapsed, "desc": desc, "error": body}
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"     ❌ EXCEPTION ({elapsed:.1f}s): {e}")
        return {"status": "error", "elapsed": elapsed, "desc": desc, "error": str(e)}


async def main():
    print("=" * 60)
    print("🧪 ComfyUI Pipeline Test")
    print("=" * 60)

    # Check backend health
    print("\n🔍 Checking backend health...")
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{BACKEND_URL}/")
            r.raise_for_status()
            print(f"  ✅ Backend OK ({BACKEND_URL})")
    except Exception as e:
        print(f"  ❌ Backend unreachable: {e}")
        sys.exit(1)

    # Check ComfyUI
    print("\n🔍 Checking ComfyUI...")
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8188/system_stats")
            r.raise_for_status()
            print(f"  ✅ ComfyUI OK (http://127.0.0.1:8188)")
    except Exception as e:
        print(f"  ❌ ComfyUI unreachable: {e}")
        sys.exit(1)

    # Prepare test data
    print("\n📦 Preparing test data...")
    photo_base64, photo_name = pick_random_photo()
    templates = pick_random_templates(len(TESTS))

    print(f"\n📁 Output dir: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Run tests
    print("\n" + "=" * 60)
    print("🚀 Running 4 generation tests...")
    print("=" * 60)
    print("  (Note: first run loads models into GPU — may take 30-60s)")

    results = []
    async with httpx.AsyncClient(timeout=600.0) as client:
        for i, (pipeline, method, desc) in enumerate(TESTS):
            result = await test_one(
                client, pipeline, method, desc,
                photo_base64, templates[i], i,
            )
            results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("📊 Results Summary")
    print("=" * 60)
    ok = [r for r in results if r["status"] == "ok"]
    fail = [r for r in results if r["status"] != "ok"]
    print(f"\n  ✅ Passed: {len(ok)}/{len(results)}")
    print(f"  ❌ Failed: {len(fail)}/{len(results)}")
    print()

    for r in results:
        icon = "✅" if r["status"] == "ok" else "❌"
        elapsed = r.get("elapsed", 0)
        print(f"  {icon}  {r['desc']}  ({elapsed:.1f}s)")
        if r["status"] == "ok":
            print(f"       URL: {r.get('url', '?')}")
        else:
            err = r.get("error", r.get("detail", "?"))
            print(f"       Error: {err[:200]}")
        print()

    # Cold-start diagnosis
    if results and len(results) >= 2:
        first = results[0]
        rest = [r for r in results[1:] if r["status"] == "ok"]
        if first["status"] != "ok" and len(rest) == len(results) - 1:
            print("  ⚠️  Pattern detected: first test failed, all subsequent passed.")
            print("     This confirms a COLD-START issue — model loading on first request")
            print("     causes timeout or failure. Suggestion:")
            print("     - Add a warm-up endpoint that runs a minimal txt2img on server start")
            print("     - Increase timeout on the client side for the first request")
        elif first["status"] == "ok":
            print("  ✅ No cold-start issue detected (first request passed)")

    # Save results
    report = {
        "photo": photo_name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "results": results,
    }
    report_path = OUTPUT_DIR / "test_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n📄 Report saved: {report_path}")

    return 0 if len(fail) == 0 else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
