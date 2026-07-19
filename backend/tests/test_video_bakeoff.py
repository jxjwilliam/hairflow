import asyncio
from unittest.mock import AsyncMock

from PIL import Image


def test_run_one_records_success_and_writes_mp4(tmp_path, monkeypatch):
    from scripts import video_bakeoff

    still = tmp_path / "try-on.png"
    Image.new("RGB", (16, 16), color="white").save(still)
    monkeypatch.setattr(video_bakeoff, "OUTPUT", tmp_path / "bakeoff")
    monkeypatch.setattr(
        video_bakeoff.video_generation_service,
        "generate_video",
        AsyncMock(return_value=b"video-bytes"),
    )

    rows = asyncio.run(
        video_bakeoff.run_one(still, ["ltx"], frames=24, fps=8, seed=42)
    )

    assert rows == [
        {
            "still": "try-on.png",
            "pipeline": "ltx",
            "status": "ok",
            "elapsed_s": rows[0]["elapsed_s"],
            "path": str(tmp_path / "bakeoff" / "try-on" / "ltx.mp4"),
            "error": "",
        }
    ]
    assert (tmp_path / "bakeoff" / "try-on" / "ltx.mp4").read_bytes() == b"video-bytes"
