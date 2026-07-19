from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    comfyui_url: str = "http://127.0.0.1:8188"

    # Database
    database_url: str = "sqlite+aiosqlite:///./hairstyle.db"

    # JWT Auth
    jwt_secret_key: str = "hairstyle-dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Development flags
    skip_points_check: bool = True
    dev_magic_code: str = "888888"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
