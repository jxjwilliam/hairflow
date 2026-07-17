from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    meitu_api_key: str = ""
    meitu_api_secret: str = ""
    meitu_api_appid: str = ""
    oss_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key: str = ""
    oss_secret_key: str = ""
    ali_cloud_vision_key: str = ""
    comfyui_url: str = "http://127.0.0.1:8188"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
