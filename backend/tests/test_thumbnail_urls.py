import struct
import zlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.routers.templates import absolute_thumbnail_url


def test_absolute_thumbnail_url_rewrites_relative_path():
    assert (
        absolute_thumbnail_url("/static/thumbnails/m1.png", "http://localhost:8000/")
        == "http://localhost:8000/static/thumbnails/m1.png"
    )


def test_absolute_thumbnail_url_keeps_external_url():
    url = "https://placehold.co/200x260/EEE/333?text=Short"
    assert absolute_thumbnail_url(url, "http://localhost:8000/") == url


def test_list_templates_returns_absolute_thumbnail(monkeypatch, tmp_path):
    templates = [
        {
            "id": "m1",
            "name": "清爽短发",
            "category": "men",
            "tags": ["短发"],
            "description": "干净利落的短发造型",
            "thumbnail": "/static/thumbnails/m1.png",
        }
    ]
    path = tmp_path / "templates.json"
    path.write_text(__import__("json").dumps(templates), encoding="utf-8")

    monkeypatch.setattr("app.routers.templates.TEMPLATES_PATH", path)

    client = TestClient(app)
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["thumbnail"].startswith("http://testserver/static/thumbnails/m1.png")


def test_static_thumbnail_is_served():
    static_root = Path(__file__).resolve().parents[1] / "static" / "thumbnails"
    static_root.mkdir(parents=True, exist_ok=True)
    png_path = static_root / "_test_pixel.png"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"\x00" + b"\x00\x00\x00"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    png_path.write_bytes(png)

    client = TestClient(app)
    resp = client.get("/static/thumbnails/_test_pixel.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")
    png_path.unlink(missing_ok=True)
