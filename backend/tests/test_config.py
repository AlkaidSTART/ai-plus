"""配置解析与 URL 转换测试（无需数据库）。"""

import asyncio
import uuid

import pytest
from pydantic_settings import SettingsError

from app.config import Settings, sync_db_url
from app.db import seed_dev


def test_cors_origins_default(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert Settings().cors_origins == ["http://localhost:5173"]


def test_cors_origins_json_list(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS", '["http://localhost:5173", "https://app.example"]'
    )
    assert Settings().cors_origins == [
        "http://localhost:5173",
        "https://app.example",
    ]


def test_cors_origins_plain_string_rejected(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    with pytest.raises(SettingsError):
        Settings()


def test_sync_db_url_asyncpg():
    assert (
        sync_db_url("postgresql+asyncpg://u:p@h:5432/db?sslmode=require")
        == "postgresql+psycopg://u:p@h:5432/db?sslmode=require"
    )


def test_sync_db_url_bare_postgresql():
    assert sync_db_url("postgresql://u@h/db") == "postgresql+psycopg://u@h/db"


def test_sync_db_url_psycopg_unchanged():
    url = "postgresql+psycopg://u@h/db"
    assert sync_db_url(url) == url


def test_seed_ids_stable_uuid5():
    assert seed_dev.TENANT_PRESET_ID.version == 5
    assert seed_dev.PROJECT_PRESET_ID.version == 5
    assert seed_dev.TENANT_PRESET_ID == uuid.uuid5(
        uuid.NAMESPACE_URL, "insightx/dev/tenant-preset"
    )
    assert seed_dev.PROJECT_PRESET_ID == uuid.uuid5(
        uuid.NAMESPACE_URL, "insightx/dev/project-home"
    )


def test_seed_refuses_prod(monkeypatch):
    monkeypatch.setattr(seed_dev.settings, "app_env", "prod")
    with pytest.raises(RuntimeError):
        asyncio.run(seed_dev.seed())
