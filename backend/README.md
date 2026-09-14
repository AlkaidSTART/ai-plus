# InsightX Backend

InsightX 后端：FastAPI + LangGraph 目标架构，前后端分离，仅通过 REST + SSE 通信。

## 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL（需 `pgvector` 扩展）+ Redis（生产路径；本地未启动时应用可运行，`/health` 会如实报告 `degraded`）
- MongoDB（单 URL DOM 爬虫保存原始快照）
- Playwright Chromium（单 URL DOM 爬虫的真实浏览器运行时）

## 启动

```bash
uv sync
uv run uvicorn insightx.main:app --reload --port 8000
```

- API 文档：http://localhost:8000/docs
- OpenAPI：http://localhost:8000/openapi.json
- 健康检查：http://localhost:8000/api/v1/health

## 单 URL DOM 爬虫

安装 Chromium 后运行 CLI：

```bash
uv run playwright install chromium
uv run python -m insightx.crawler --url https://example.com
```

CLI 会使用 Playwright Chromium 访问目标页面，把渲染后的可见 DOM 递归序列化为 JSON 文件，并将同一快照与采集元数据写入 MongoDB。JSON 默认输出到 `artifacts/dom/`，MongoDB 默认集合为 `dom_snapshots`；`_id` 与返回的 `snapshot_id` 相同。

可用参数：

- `--url`：必填，仅接受绝对 `http://` 或 `https://` URL。
- `--output-dir`：覆盖 JSON 输出目录。
- `--headed`：以有界面模式运行 Chromium；默认无头。
- `--tenant-id`、`--task-id`、`--task-item-id`：写入可选的关联标识。

环境变量模板见根目录示例环境文件；本地覆盖文件由配置自动读取。可用变量为 `MONGODB_URI`、`MONGODB_DATABASE`、`MONGODB_DOM_COLLECTION`、`CRAWLER_OUTPUT_DIR`、`CRAWLER_TIMEOUT_MS`、`CRAWLER_HEADLESS`。

## 测试

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

离线测试不依赖真实 MongoDB、PostgreSQL、Redis、Chromium 或外部 AI 服务；爬虫测试使用 fake Playwright/Mongo 契约。真实浏览器和 MongoDB 端到端检查需要单独安装 Chromium 并启动 MongoDB。

## 当前目录结构

```text
backend/
├── pyproject.toml       # 依赖、构建与工具配置
├── uv.lock              # uv 锁定依赖
├── src/insightx/
│   ├── main.py          # FastAPI 应用工厂与模块级 app
│   ├── api/
│   │   ├── router.py    # 聚合路由
│   │   └── v1/
│   │       └── health.py
│   └── crawler/         # Playwright DOM 抓取、JSON 与 MongoDB 持久化
│       ├── config.py
│       ├── dom.py
│       ├── fetch.py
│       ├── service.py
│       └── storage.py
└── tests/               # pytest（离线契约测试）
```

MongoDB 爬虫持久化已接入，但 PostgreSQL 仍是任务、评论、报告、证据和事件的业务事实源。PostgreSQL 连接、Alembic 迁移、Celery Worker、outbox 派发器和 LangGraph 图尚未接入；`/health` 在真实探针实施前保持 `degraded`。
