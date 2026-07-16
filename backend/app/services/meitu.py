import base64
import json
import logging

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

MTLAB_BASE = "https://openapi.mtlab.meitu.com/v1"


class MeituService:
    """Client for Meitu mtlab API (openapi.mtlab.meitu.com).

    Auth is passed as query parameters (?api_key=&api_secret=).
    Requests use the standard media_info_list format.
    """

    def __init__(self):
        self.api_key = settings.meitu_api_key
        self.api_secret = settings.meitu_api_secret

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auth_params(self) -> dict[str, str]:
        return {"api_key": self.api_key, "api_secret": self.api_secret}

    def _build_body(self, b64_image: str, extra_params: dict | None = None) -> dict:
        return {
            "parameter": {"rsp_media_type": "jpg", **(extra_params or {})},
            "media_info_list": [
                {
                    "media_data": b64_image,
                    "media_profiles": {"media_data_type": "jpg"},
                }
            ],
        }

    async def _post(
        self, endpoint: str, body: dict, timeout: float = 30.0
    ) -> dict:
        """POST to an mtlab endpoint and return the JSON response."""
        url = f"{MTLAB_BASE}/{endpoint}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url, params=self._auth_params(), json=body
            )
            try:
                data = resp.json()
            except Exception:
                logger.error(
                    "Meitu API %s: non-JSON response %s: %s",
                    endpoint,
                    resp.status_code,
                    resp.text[:500],
                )
                raise MeituAPIError(
                    f"Non-JSON response ({resp.status_code})"
                )

            if not data:
                raise MeituAPIError("Empty response from API")

            # mtlab errors come as {"ErrorCode": NNN, "ErrorMsg": "..."}
            err_code = data.get("ErrorCode")
            if err_code is not None and err_code != 0:
                err_msg = data.get("ErrorMsg", "Unknown error")
                logger.warning(
                    "Meitu API %s error [%s]: %s", endpoint, err_code, err_msg
                )
                raise MeituAPIError(f"[{err_code}] {err_msg}")

            # mtlab "code" field also signals errors for some endpoints
            code = data.get("code")
            if code is not None and code != 0:
                err_msg = data.get("message", "Unknown error")
                logger.warning(
                    "Meitu API %s code error [%s]: %s", endpoint, code, err_msg
                )
                raise MeituAPIError(f"[{code}] {err_msg}")

            return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def detect_hair(self, photo_base64: str) -> dict:
        """Classify hair attributes using hairclassifier endpoint.

        Returns decoded analysis result or raises MeituAPIError
        (including 'detect no face').
        """
        body = self._build_body(photo_base64)
        data = await self._post("hairclassifier", body, timeout=15.0)
        # data format: {"media_info_list": [{"media_data": "base64json"}]}
        media_list = data.get("media_info_list") or []
        if not media_list:
            raise MeituAPIError("No media in response")
        raw = media_list[0].get("media_data", "")
        if not raw:
            raise MeituAPIError("Empty media_data in hairclassifier response")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise MeituAPIError(
                f"hairclassifier returned non-JSON media_data: {raw[:200]}"
            )

    async def segment_hair(self, photo_base64: str) -> bytes:
        """Segment hair from portrait using hair_segment endpoint.

        Returns the hair mask as PNG bytes.
        """
        body = self._build_body(photo_base64, {"outputType": 1})
        data = await self._post("hair_segment", body, timeout=60.0)
        media_list = data.get("media_info_list") or []
        if not media_list:
            raise MeituAPIError("No media in hair_segment response")
        raw = media_list[0].get("media_data", "")
        if not raw:
            raise MeituAPIError("Empty media_data in hair_segment response")
        return base64.b64decode(raw)

    async def generate_hairstyle(
        self, photo_base64: str, style_id: str, mask_base64: str | None = None
    ) -> bytes:
        """Apply a hairstyle to the portrait using mtlab portrait_edit.

        Args:
            photo_base64: Base64-encoded JPEG of the person's photo.
            style_id: Hairstyle style ID (from templates.json style_id field).
            mask_base64: Optional base64-encoded PNG hair mask from
                         segment_hair(). The Meitu API requires the hair
                         mask to be pre-computed and passed as a second
                         media item.

        Returns:
            Bytes of the resulting JPEG image.

        Raises:
            MeituAPIError: If the API returns an error (including
                GATEWAY_AUTHORIZED_ERROR when user hasn't purchased this
                capability).
        """
        media_info_list = [
            {
                "media_data": photo_base64,
                "media_profiles": {"media_data_type": "jpg"},
            }
        ]
        if mask_base64:
            media_info_list.append(
                {
                    "media_data": mask_base64,
                    "media_profiles": {"media_data_type": "png"},
                }
            )
        body = {
            "parameter": {
                "rsp_media_type": "jpg",
                "style_id": style_id,
            },
            "media_info_list": media_info_list,
        }
        data = await self._post("portrait_edit", body, timeout=120.0)
        media_list = data.get("media_info_list") or []
        if not media_list:
            raise MeituAPIError("No media in portrait_edit response")
        raw = media_list[0].get("media_data", "")
        if not raw:
            raise MeituAPIError("Empty media_data in portrait_edit response")
        return base64.b64decode(raw)

    async def regenerate_hairstyle(
        self,
        photo_base64: str,
        style_id: str,
        params: dict,
        mask_base64: str | None = None,
    ) -> bytes:
        """Re-generate with additional parameters.

        Same API as generate but passes extra styling hints
        (length, curl, colour, bang).
        """
        media_info_list = [
            {
                "media_data": photo_base64,
                "media_profiles": {"media_data_type": "jpg"},
            }
        ]
        if mask_base64:
            media_info_list.append(
                {
                    "media_data": mask_base64,
                    "media_profiles": {"media_data_type": "png"},
                }
            )
        extra = {
            "rsp_media_type": "jpg",
            "style_id": style_id,
        }
        if params.get("length") is not None:
            extra["hair_length"] = params["length"]
        if params.get("curl") is not None:
            extra["curl_level"] = params["curl"]
        if params.get("color"):
            extra["hair_color"] = params["color"]
        if params.get("bang_style"):
            extra["bang_style"] = params["bang_style"]

        body = {
            "parameter": extra,
            "media_info_list": media_info_list,
        }
        data = await self._post("portrait_edit", body, timeout=120.0)
        media_list = data.get("media_info_list") or []
        if not media_list:
            raise MeituAPIError("No media in portrait_edit response")
        raw = media_list[0].get("media_data", "")
        if not raw:
            raise MeituAPIError("Empty media_data in portrait_edit response")
        return base64.b64decode(raw)


class MeituAPIError(Exception):
    """Raised when the Meitu API returns an error response."""


meitu_service = MeituService()
