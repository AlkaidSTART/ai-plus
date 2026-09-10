"""应用配置：全部来自环境变量，默认值仅面向本地开发。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str = "postgresql+asyncpg://insightx:insightx@localhost:5432/insightx"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173"]
    # P0 单企业开发闭环的预置项目 ID；真实身份/项目接入后由服务端会话取代。
    preset_project_id: str = "project_home"


settings = Settings()
