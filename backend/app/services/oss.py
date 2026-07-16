import io
import uuid
from functools import lru_cache
import oss2
from app.config import settings


class OSSService:
    def __init__(self):
        if not settings.oss_endpoint or not settings.oss_bucket:
            raise RuntimeError(
                "OSS not configured. Set OSS_ENDPOINT, OSS_BUCKET, "
                "OSS_ACCESS_KEY, and OSS_SECRET_KEY in .env"
            )
        auth = oss2.Auth(settings.oss_access_key, settings.oss_secret_key)
        self.bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)

    def upload_image(self, data: bytes, content_type: str = "image/png") -> tuple[str, str]:
        image_id = f"gen/{uuid.uuid4().hex}.png"
        self.bucket.put_object(
            image_id,
            io.BytesIO(data),
            headers={"Content-Type": content_type},
        )
        url = f"https://{settings.oss_bucket}.{settings.oss_endpoint}/{image_id}"
        return url, image_id


@lru_cache(maxsize=None)
def get_oss_service() -> OSSService:
    return OSSService()
