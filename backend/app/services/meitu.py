import base64
import httpx
from app.config import settings


class MeituService:
    def __init__(self):
        self.base_url = "https://api.meitu.com/v1"
        self.api_key = settings.meitu_api_key
        self.api_secret = settings.meitu_api_secret

    async def generate_hairstyle(self, photo_base64: str, style_id: str) -> bytes:
        """Call Meitu hairstyle generation API and return image bytes."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/hairstyle/generate",
                json={
                    "api_key": self.api_key,
                    "api_secret": self.api_secret,
                    "image": photo_base64,
                    "style_id": style_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            result_base64 = data["data"]["result_image"]
            return base64.b64decode(result_base64)

    async def regenerate_hairstyle(
        self, photo_base64: str, style_id: str, params: dict
    ) -> bytes:
        async with httpx.AsyncClient(timeout=60.0) as client:
            body = {
                "api_key": self.api_key,
                "api_secret": self.api_secret,
                "image": photo_base64,
                "style_id": style_id,
            }
            if "length" in params:
                body["hair_length"] = params["length"]
            if "curl" in params:
                body["curl_level"] = params["curl"]
            if "color" in params:
                body["hair_color"] = params["color"]
            if "bang_style" in params:
                body["bang_style"] = params["bang_style"]

            resp = await client.post(f"{self.base_url}/hairstyle/regenerate", json=body)
            resp.raise_for_status()
            data = resp.json()
            return base64.b64decode(data["data"]["result_image"])


meitu_service = MeituService()
