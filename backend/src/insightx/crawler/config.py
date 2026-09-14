"""Runtime configuration for the DOM crawler."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_ENV_FILE = "." + "env" + "." + "local"


class CrawlerSettings(BaseSettings):
    """Environment-backed crawler settings."""

    mongodb_uri: str = Field(default="mongodb://127.0.0.1:27017", min_length=1)
    mongodb_database: str = Field(default="insightx", min_length=1)
    mongodb_dom_collection: str = Field(default="dom_snapshots", min_length=1)
    crawler_output_dir: Path = Path("artifacts/dom")
    crawler_timeout_ms: int = Field(default=30_000, ge=1_000, le=300_000)
    crawler_headless: bool = True

    model_config = SettingsConfigDict(
        env_file=_LOCAL_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def with_cli_overrides(
        self,
        *,
        output_dir: Path | None = None,
        headed: bool = False,
    ) -> "CrawlerSettings":
        """Return a validated copy with explicit CLI overrides applied."""

        values = self.model_dump()
        if output_dir is not None:
            values["crawler_output_dir"] = output_dir
        if headed:
            values["crawler_headless"] = False
        return CrawlerSettings.model_validate(values)
