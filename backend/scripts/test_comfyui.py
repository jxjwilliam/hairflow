#!/usr/bin/env python3
"""Quick smoke test for ComfyUI hairstyle generation pipeline.

Usage:
  python3 backend/scripts/test_comfyui.py [--photo PHOTO_PATH] [--style w1]

Requires:
  - ComfyUI running at http://127.0.0.1:8188
  - photomaker-v2.bin downloaded
  - SDXL checkpoint available
"""

import argparse
import asyncio
import base64
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--photo", default=None, help="Path to test photo (optional)")
    parser.add_argument("--style", default="w1", help="Template ID")
    parser.add_argument("--comfyui", default="http://127.0.0.1:8188", help="ComfyUI URL")
    args = parser.parse_args()

    # --- Step 0: Check ComfyUI ---
    print("=" * 60)
    print("1. Checking ComfyUI connectivity...")
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{args.comfyui}/system_stats")
        if resp.status_code != 200:
            print(f"   ERROR: ComfyUI not reachable (HTTP {resp.status_code})")
            print(f"   Is ComfyUI running at {args.comfyui}?")
            return
        data = resp.json()
        print(f"   OK - ComfyUI v{data['system']['comfyui_version']} on {data['system']['os']}")

    # --- Step 1: Check models ---
    print("\n2. Checking available models...")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{args.comfyui}/object_info")
        obj = resp.json()

        ckpt_node = obj.get("CheckpointLoaderSimple", {})
        ckpt_list = ckpt_node.get("input", {}).get("required", {}).get("ckpt_name", [[], {}])[0]
        print(f"   Checkpoints ({len(ckpt_list)}): {ckpt_list[:5]}...")

        pm_node = obj.get("PhotoMakerLoader", {})
        pm_list = pm_node.get("input", {}).get("required", {}).get("photomaker_model_name", [[], {}])[0]
        if isinstance(pm_list, str):
            pm_list = []
        print(f"   PhotoMaker models ({len(pm_list)}): {pm_list}")

    if not ckpt_list:
        print("\n   *** No checkpoints found! Restart ComfyUI in Pinokio. ***")
        return
    if not pm_list:
        print("\n   *** WARNING: PhotoMaker model not listed in object_info. ***")
        print("   Will try submitting anyway — ComfyUI may find it at runtime.")

    # --- Step 2: Load test photo ---
    print("\n3. Loading test photo...")
    if args.photo:
        photo_path = Path(args.photo)
    else:
        # Use a simple solid-color test image
        from PIL import Image
        img = Image.new("RGB", (512, 512), color=(128, 128, 128))
        photo_path = Path("/tmp/test_photo.png")
        img.save(photo_path)
        print("   Using generated test image (gray square)")

    with open(photo_path, "rb") as f:
        photo_base64 = base64.b64encode(f.read()).decode()
    print(f"   Loaded: {photo_path} ({len(photo_base64)} chars base64)")

    # --- Step 3: Test face detection ---
    print("\n4. Testing face detection (mediapipe)...")
    from app.services.face import face_service
    result = await face_service.detect_face(photo_base64)
    print(f"   face_detected={result['face_detected']}, confidence={result.get('confidence')}")
    if not result["face_detected"]:
        print("   WARNING: No face detected in test photo. That's OK for a test square.")
        print("   With a real portrait, this should return True.")

    # --- Step 4: Submit workflow ---
    print(f"\n5. Submitting ComfyUI workflow (style={args.style})...")
    from app.services.comfyui import comfyui_service, ComfyUIError
    from app.routers.comfyui_generation import _load_comfyui_templates

    templates = _load_comfyui_templates()
    template = next((t for t in templates if t["id"] == args.style), None)
    if not template:
        print(f"   ERROR: Template '{args.style}' not found")
        return
    print(f"   Template: {template['name']}")
    print(f"   Prompt: {template['positive_prompt'][:80]}...")

    try:
        print("   Generating (may take 30-120s on MPS)...")
        image_bytes = await comfyui_service.generate_hairstyle(
            photo_base64=photo_base64,
            prompt=template["positive_prompt"],
            negative_prompt=template.get("negative_prompt", ""),
            checkpoint=template.get("checkpoint", "juggernautXL_ragnarokBy.safetensors"),
            photomaker_model=template.get("photomaker_model", "photomaker-v2.bin"),
            width=template.get("width", 768),
            height=template.get("height", 1024),
            steps=template.get("steps", 20),
            cfg=template.get("cfg", 6.5),
            denoise=template.get("denoise", 0.85),
            timeout=300,
        )
        print(f"   SUCCESS - Generated {len(image_bytes)} bytes")

        # Save result
        out_path = Path("/tmp/hairstyle_test_result.png")
        out_path.write_bytes(image_bytes)
        print(f"   Saved to: {out_path}")

    except ComfyUIError as e:
        print(f"   FAILED: {e}")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("Test complete.")


if __name__ == "__main__":
    asyncio.run(main())
