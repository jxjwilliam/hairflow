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
