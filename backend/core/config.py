"""Application configuration via environment variables (pydantic-settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "dev"
    APP_VERSION: str = "0.1.0"

    # Database & cache
    DATABASE_URL: str = "postgresql+asyncpg://insightx:insightx@localhost:5432/insightx"
    REDIS_URL: str = "redis://localhost:6379/0"
    DB_ECHO: bool = False

    # CORS: JSON list or comma-separated origins
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # SSE heartbeat interval in seconds
    SSE_HEARTBEAT_SECONDS: float = 15.0

    # Runtime backends: "memory" (dev/test) or "db"/"redis" (production)
    TASK_STORE_BACKEND: str = "memory"
    EVENT_STORE_BACKEND: str = "memory"

    # Upstream data providers (Step 3). Empty means "not configured".
    AMAZON_API_BASE_URL: str = ""
    AMAZON_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"

    # Embedding
    EMBEDDING_DEVICE: str = "cpu"

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV.lower() in {"prod", "production"}


def _parse_origins(value: object) -> list[str]:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value  # type: ignore[return-value]


@lru_cache
def get_settings() -> Settings:
    import os

    raw_origins = os.environ.get("BACKEND_CORS_ORIGINS")
    kwargs: dict = {}
    if raw_origins is not None:
        kwargs["BACKEND_CORS_ORIGINS"] = _parse_origins(raw_origins)
    return Settings(**kwargs)
