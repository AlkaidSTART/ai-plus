"""Environment-backed application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_ENV_FILE = "." + "env" + "." + "local"


class Settings(BaseSettings):
    """Runtime settings for the API service."""

    database_url: str = Field(
        default="postgresql+psycopg://insightx:insightx-dev@127.0.0.1:5432/insightx",
        min_length=1,
    )
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", min_length=1)
    auth_mode: Literal["dev", "required"] = "dev"
    dev_tenant_id: str = Field(default="dev-tenant", min_length=1)

    model_config = SettingsConfigDict(
        env_file=_LOCAL_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""

    return Settings()
