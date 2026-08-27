from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    bot_token: str = Field(default="replace_me", alias="BOT_TOKEN")
    admin_ids: Annotated[List[int], NoDecode] = Field(default_factory=list, alias="ADMIN_IDS")
    webhook_secret: str = Field(default="change_me", alias="WEBHOOK_SECRET")

    database_url: str = Field(
        default="postgresql+asyncpg://musicsave:musicsave@localhost:5432/musicsave",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    audd_api_token: str = Field(default="", alias="AUDD_API_TOKEN")
    youtube_api_key: str = Field(default="", alias="YOUTUBE_API_KEY")

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    rate_limit_per_minute: int = Field(default=30, alias="RATE_LIMIT_PER_MINUTE")
    max_media_size_mb: int = Field(default=20, alias="MAX_MEDIA_SIZE_MB")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: object) -> List[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        return [int(x.strip()) for x in str(value).split(",") if x.strip()]

    @property
    def max_media_size_bytes(self) -> int:
        return self.max_media_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
