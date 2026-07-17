import json
from pathlib import Path

from scripts.generate_thumbnails import (
    build_txt2img_workflow,
    thumbnail_rel_path,
    update_template_thumbnails,
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
