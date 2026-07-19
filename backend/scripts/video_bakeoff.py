#!/usr/bin/env python3
"""Sequential video bake-off: one still → LTX / Hunyuan / AnimateDiff MP4s."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.video_generation import VIDEO_PIPELINES, video_generation_service

OUTPUT = ROOT / "output" / "bakeoff"


async def run_one(
    still: Path, pipelines: list[str], frames: int, fps: int, seed: int
) -> list[dict[str, str | float]]:
    """Run requested video pipelines sequentially for one input still."""
    image = Image.open(still).convert("RGB")
    out_dir = OUTPUT / still.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str | float]] = []

    for pipeline in pipelines:
        started_at = time.monotonic()
        status = "ok"
        error = ""
        destination = out_dir / f"{pipeline}.mp4"
        try:
            data = await video_generation_service.generate_video(
                pipeline=pipeline,
                image=image,
                seed=seed,
                frames=frames,
                fps=fps,
            )
            destination.write_bytes(data)
        except Exception as exc:
            status = "fail"
            error = str(exc)[:500]

        elapsed = round(time.monotonic() - started_at, 1)
        row: dict[str, str | float] = {
            "still": still.name,
            "pipeline": pipeline,
            "status": status,
            "elapsed_s": elapsed,
            "path": str(destination) if status == "ok" else "",
            "error": error,
        }
        rows.append(row)
        print(f"[{status}] {still.name} / {pipeline}  {elapsed:.1f}s  {error}")

    return rows


async def main_async(args: argparse.Namespace) -> int:
    stills = [Path(path) for path in args.stills]
    for still in stills:
        if not still.exists():
            print(f"missing still: {still}")
            return 1

    pipelines = list(VIDEO_PIPELINES) if args.pipeline == "all" else [args.pipeline]
    rows: list[dict[str, str | float]] = []
    for still in stills:
        rows.extend(await run_one(still, pipelines, args.frames, args.fps, args.seed))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = OUTPUT / "report.md"
    lines = [
        "# Video bake-off report",
        "",
        "| still | pipeline | status | elapsed_s | path | error |",
        "|-------|----------|--------|-----------|------|-------|",
    ]
    for row in rows:
        error = str(row["error"]).replace("|", "\\|").replace("\n", " ")[:80]
        lines.append(
            f"| {row['still']} | {row['pipeline']} | {row['status']} | "
            f"{row['elapsed_s']} | `{row['path']}` | {error} |"
        )
    report.write_text("\n".join(lines) + "\n")
    print(f"Wrote {report}")
    return 0 if all(row["status"] == "ok" for row in rows) else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stills", nargs="+", help="Try-on still PNG paths")
    parser.add_argument(
        "--pipeline",
        default="all",
        choices=["all", *VIDEO_PIPELINES],
        help="Pipeline to evaluate (default: all)",
    )
    parser.add_argument("--frames", type=int, default=24)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
