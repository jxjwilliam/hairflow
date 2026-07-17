import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.generate_thumbnails import (
    _extract_history_error,
    build_txt2img_workflow,
    download_image,
    thumbnail_rel_path,
    update_template_thumbnails,
    wait_for_image,
)


def test_thumbnail_rel_path():
    assert thumbnail_rel_path("m1") == "/static/thumbnails/m1.png"


def test_build_txt2img_workflow_shape():
    wf = build_txt2img_workflow(
        prompt="photograph of a man with short neat haircut",
        negative_prompt="long hair",
        checkpoint="photon_v1.safetensors",
        width=512,
        height=768,
        steps=25,
        cfg=6.5,
        seed=42,
    )
    assert wf["1"]["class_type"] == "CheckpointLoaderSimple"
    assert wf["2"]["class_type"] == "CLIPTextEncode"
    assert wf["3"]["class_type"] == "CLIPTextEncode"
    assert wf["4"]["class_type"] == "EmptyLatentImage"
    assert wf["5"]["class_type"] == "KSampler"
    assert wf["5"]["inputs"]["denoise"] == 1.0
    assert wf["5"]["inputs"]["seed"] == 42
    dumped = json.dumps(wf)
    assert "PhotoMaker" not in dumped
    assert "LoadImage" not in dumped


def test_update_template_thumbnails_atomic(tmp_path: Path):
    path = tmp_path / "templates.json"
    path.write_text(
        json.dumps(
            [
                {"id": "m1", "thumbnail": "https://placehold.co/x"},
                {"id": "m2", "thumbnail": "https://placehold.co/y"},
            ]
        ),
        encoding="utf-8",
    )
    update_template_thumbnails(path, {"m1": "/static/thumbnails/m1.png"})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["thumbnail"] == "/static/thumbnails/m1.png"
    assert data[1]["thumbnail"] == "https://placehold.co/y"


def test_extract_history_error_from_status():
    entry = {
        "status": {
            "status_str": "error",
            "completed": True,
            "messages": [
                [
                    "execution_error",
                    {
                        "node_id": "5",
                        "exception_message": "CUDA out of memory",
                    },
                ]
            ],
        },
        "outputs": {},
    }
    assert _extract_history_error(entry, "abc-123") == "node 5: CUDA out of memory"


def test_extract_history_error_completed_without_images():
    entry = {
        "status": {"status_str": "success", "completed": True, "messages": []},
        "outputs": {"7": {"images": []}},
    }
    assert _extract_history_error(entry, "abc-123") == "workflow completed without output images"


def test_wait_for_image_raises_on_history_error():
    prompt_id = "fail-id"
    history = {
        prompt_id: {
            "status": {
                "status_str": "error",
                "completed": True,
                "messages": [
                    ["execution_error", {"exception_message": "checkpoint not found"}]
                ],
            },
            "outputs": {},
        }
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = history

    with patch("scripts.generate_thumbnails.httpx.get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="prompt_id=fail-id"):
            wait_for_image("http://127.0.0.1:8188", prompt_id, timeout=1.0)


def test_wait_for_image_returns_image_entry_with_subfolder():
    prompt_id = "ok-id"
    history = {
        prompt_id: {
            "status": {"status_str": "success", "completed": True, "messages": []},
            "outputs": {
                "7": {
                    "images": [
                        {
                            "filename": "catalog_thumb_00001_.png",
                            "subfolder": "2026-07-17",
                            "type": "output",
                        }
                    ]
                }
            },
        }
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = history

    with patch("scripts.generate_thumbnails.httpx.get", return_value=mock_resp):
        image = wait_for_image("http://127.0.0.1:8188", prompt_id, timeout=1.0)

    assert image["filename"] == "catalog_thumb_00001_.png"
    assert image["subfolder"] == "2026-07-17"
    assert image["type"] == "output"


def test_download_image_passes_subfolder_and_type():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b"png-bytes"

    with patch("scripts.generate_thumbnails.httpx.get", return_value=mock_resp) as mock_get:
        data = download_image(
            "http://127.0.0.1:8188",
            "catalog_thumb_00001_.png",
            subfolder="2026-07-17",
            image_type="output",
        )

    assert data == b"png-bytes"
    mock_get.assert_called_once_with(
        "http://127.0.0.1:8188/view",
        params={
            "filename": "catalog_thumb_00001_.png",
            "subfolder": "2026-07-17",
            "type": "output",
        },
        timeout=30,
    )
