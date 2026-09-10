# InsightX backend（单包双入口）

同一 `app` 包产出两个进程：FastAPI API 与独立 worker（DB 轮询领任务，P0 不引入 Celery）。

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000   # API，/health 自检
uv run python -m app.worker                        # worker（节点步骤 2 前空轮询）
uv run pytest                                      # 测试
uv run alembic upgrade head                        # P0 建表（需 PostgreSQL + pgvector）
```

环境变量见 `app/config.py`（`.env` 可覆盖）：`DATABASE_URL`、`REDIS_URL`、
`CORS_ORIGINS`。P1（vision/financial）与 P2（evolution）
在对应阶段新增模块与迁移，本期只有 `app/services/placeholders.py` 占位。
