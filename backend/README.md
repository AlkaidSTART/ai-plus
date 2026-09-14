# InsightX Backend

InsightX 后端：FastAPI + LangGraph，前后端分离，仅通过 REST + SSE 通信。

## 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL（需 `pgvector` 扩展）+ Redis（生产路径；本地未启动时应用可运行，`/health` 会如实报告 `degraded`）

## 启动

```bash
uv sync
uv run uvicorn insightx.main:app --reload --port 8000
```

- API 文档：http://localhost:8000/docs
- OpenAPI：http://localhost:8000/openapi.json
- 健康检查：http://localhost:8000/api/v1/health

## 测试

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

测试完全离线，不依赖 PostgreSQL / Redis / 外部 AI 服务。

## 当前目录结构

```text
backend/
├── pyproject.toml       # 依赖、构建与工具配置
├── uv.lock              # uv 锁定依赖
├── src/insightx/
│   ├── main.py          # FastAPI 应用工厂与模块级 app
│   └── api/
│       ├── router.py    # 聚合路由
│       └── v1/
│           └── health.py
└── tests/               # pytest（离线）
```

数据库连接、Alembic 迁移、Celery Worker、outbox 派发器和 LangGraph 图尚未接入；`/health` 在真实探针实施前保持 `degraded`。
