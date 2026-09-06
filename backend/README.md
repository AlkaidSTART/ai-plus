# InsightX Backend

InsightX 后端：FastAPI + LangGraph，前后端分离，仅通过 REST + SSE 通信。

## 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL（需 `pgvector` 扩展）+ Redis（生产路径；本地未启动时应用可运行，`/health` 会如实报告 `degraded`）

## 启动

```bash
cp .env.example .env   # 按需修改
uv sync
uv run uvicorn main:app --reload --port 8000
```

- API 文档：http://localhost:8000/docs
- OpenAPI：http://localhost:8000/openapi.json
- 健康检查：http://localhost:8000/api/v1/health

## 测试

```bash
uv run pytest -q
```

测试完全离线，不依赖 PostgreSQL / Redis / 外部 AI 服务。

## 真实服务（可选）

- 真实 Embedding（bge-m3）：`uv sync --extra embedding`（下载模型，约 2GB）
- 正式数据源 / LLM：在 `.env` 配置 `AMAZON_API_BASE_URL`、`ANTHROPIC_API_KEY`
- `PROVIDER_MODE=real` 时启用正式 Service/Provider；`TASK_STORE_BACKEND=db`、
  `EVENT_STORE_BACKEND=redis` 时任务与事件走 PostgreSQL / Redis 生产路径

## Docker

```bash
docker compose up --build   # 仓库根目录：PostgreSQL(pgvector) + Redis + backend
curl http://localhost:8000/api/v1/health
```

## 目录结构

```text
backend/
├── main.py            # FastAPI 入口，唯一挂载 /api/v1 前缀的位置
├── api/               # 路由、统一响应 Envelope、错误码、依赖
├── core/              # 配置（pydantic-settings）、Redis client
├── db/                # async engine / session / Base / models / repositories
├── runtime/           # Task / Event 存储与运行时
├── services/          # 业务服务层
├── agents/            # LangGraph 状态机
└── tests/             # pytest（离线）
```
