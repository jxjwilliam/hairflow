#!/usr/bin/env python3
"""Comprehensive test: run every pipeline+method combo and report pass/fail.

Usage:
    python scripts/test_all_pipelines.py [--photo PATH] [--timeout SEC]

Skips tests that would obviously fail (e.g. photomaker without photo).
"""

import argparse
import base64
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
COMFYUI_URL = "http://127.0.0.1:8188"

def check_comfyui() -> bool:
    try:
        resp = urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
        data = json.loads(resp.read())
        ver = data.get("system", {}).get("comfyui_version", "?")
        print(f"  ComfyUI v{ver} — OK")
        return True
    except Exception as e:
        print(f"  ComfyUI unreachable: {e}")
        return False

def check_queue_clear() -> bool:
    try:
        resp = urllib.request.urlopen(f"{COMFYUI_URL}/queue", timeout=5)
        d = json.loads(resp.read())
        return len(d.get("queue_running", [])) == 0 and len(d.get("queue_pending", [])) == 0
    except Exception:
        return False

def run_test(label: str, pipeline: str, method: str, photo_b64: str | None,
             style_id: str, timeout: int, steps: int = 15) -> tuple[bool, float, str]:
    """Run one pipeline test against the backend API."""
    body = {
        "style_id": style_id,
        "pipeline": pipeline,
        "method": method,
        "steps": steps,
        "photo_base64": photo_b64 or "",
    }
    if pipeline == "photomaker":
        body["cfg"] = 6.5
        body["denoise"] = 0.85
    elif pipeline == "sd15":
        body["cfg"] = 6.5
        body["denoise"] = 0.85
    else:  # flux / flux_klein
        body["cfg"] = 1.0
        body["denoise"] = 1.0  # txt2img only; flux_klein img2img ignores denoise

    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BACKEND_URL}/api/comfyui/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    start = time.monotonic()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        elapsed = time.monotonic() - start
        resp_body = json.loads(resp.read())
        url = resp_body.get("image_url", "?")
        return True, elapsed, url
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - start
        detail = e.read().decode()[:200]
        return False, elapsed, f"HTTP {e.code}: {detail}"
    except urllib.error.URLError as e:
        elapsed = time.monotonic() - start
        return False, elapsed, f"URLError: {e.reason}"
    except Exception as e:
        elapsed = time.monotonic() - start
        return False, elapsed, f"{type(e).__name__}: {e}"


def wait_for_queue(timeout: int = 30) -> bool:
    """Wait until ComfyUI queue is clear."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = urllib.request.urlopen(f"{COMFYUI_URL}/queue", timeout=5)
            d = json.loads(resp.read())
            running = len(d.get("queue_running", []))
            pending = len(d.get("queue_pending", []))
            if running == 0 and pending == 0:
                return True
            print(f"  ⏳ queue: {running} running, {pending} pending — waiting...")
            time.sleep(5)
        except Exception:
            time.sleep(2)
    return False


def main():
    parser = argparse.ArgumentParser(description="Test all ComfyUI pipeline+method combos")
    parser.add_argument("--photo", default=str(Path(__file__).parent.parent.parent / "data" / "doubao-1-9x16.png"),
                        help="Photo file for img2img tests")
    parser.add_argument("--timeout", type=int, default=600, help="Per-test timeout (s)")
    args = parser.parse_args()

    # Load photo
    photo_path = Path(args.photo)
    if not photo_path.exists():
        print(f"❌ Photo not found: {photo_path}")
        sys.exit(1)
    photo_b64 = base64.b64encode(photo_path.read_bytes()).decode()
    print(f"📷 Photo: {photo_path.name} ({len(photo_b64)//1024}KB base64)")
    print()

    # Health checks
    print("🔍 Health checks:")
    if not check_comfyui():
        sys.exit(1)
    try:
        resp = urllib.request.urlopen(f"{BACKEND_URL}/", timeout=5)
        print(f"  Backend — OK ({resp.status})")
    except Exception as e:
        print(f"  Backend unreachable: {e}")
        sys.exit(1)

    if not wait_for_queue():
        print("❌ Queue not clear, aborting")
        sys.exit(1)
    print()

    # Define all test cases
    # NOTE: FLUX.1 Schnell deliberately omitted — its 12GB GGUF model cannot
    # run on CPU (RAM exhausted). FLUX.2 Klein txt2img is also omitted — it
    # tries to load 8GB qwen_3_4b via DualCLIPLoaderGGUF and OOMs.
    # Only CPU-feasible combos are listed here.
    # (label, pipeline, method, needs_photo, style_id, steps)
    TEST_CASES = [
        # --- PhotoMaker ---
        ("PhotoMaker v1 + 保持人脸",  "photomaker", "photomaker", True,  "w1", 15),

        # --- SD 1.5 (Realistic Vision) ---
        ("SD1.5 + 文本生成",          "sd15",       "txt2img",    False, "w1", 15),
        ("SD1.5 + 图生图",            "sd15",       "img2img",    True,  "w1", 15),

        # --- FLUX.2 Klein 4B (img2img only — txt2img loads 8GB CLIP, OOM on CPU) ---
        ("FLUX.2 Klein + 图生图(编辑)", "flux_klein", "img2img",    True,  "w1", 4),
    ]

    results = []

    for label, pipeline, method, needs_photo, style_id, steps in TEST_CASES:
        print(f"{'='*60}")
        print(f"🧪 {label}")
        print(f"   pipeline={pipeline}, method={method}, style={style_id}, steps={steps}")

        # photo_base64 always required by the API schema (face detection), empty for txt2img
        photo = photo_b64 if needs_photo else ""

        ok, elapsed, detail = run_test(
            label, pipeline, method, photo, style_id,
            timeout=args.timeout, steps=steps,
        )

        status_icon = "✅" if ok else "❌"
        print(f"   {status_icon} ({elapsed:.0f}s): {detail[:120]}")

        # Wait for queue to clear before next test
        wait_for_queue(timeout=60)

        results.append((pipeline, method, ok, elapsed))
        print()

    # --- Summary ---
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for pipeline, method, ok, elapsed in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {pipeline}/{method:15s}  {elapsed:6.0f}s")

    # Identify failures
    failures = [(p, m) for p, m, ok, _ in results if not ok]
    successes = [(p, m) for p, m, ok, _ in results if ok]

    print()
    print(f"✅ Passed: {len(successes)}/{len(results)}")
    if failures:
        print(f"❌ Failed: {len(failures)}/{len(results)}")
        for p, m in failures:
            print(f"   - {p}/{m}")
        print()
        print("💡 Recommendation: remove failing pipeline(s) from options screen")
    else:
        print("🎉 All pipelines work!")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
