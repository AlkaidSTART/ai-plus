# 阶段 01：基础配置与迁移 — 实施结果

## 完成状态

已完成（代码与离线验证部分；真实库验收因环境缺失而阻塞，见遗留事项）。

## 对应计划

[plan.md](plan.md)。用户在计划展示后明确回复“开始实施 01”，按该计划 12 项
checklist 执行，无范围外改动。

## 实际变更

修改 9 个文件：

- `backend/app/config.py`：新增 `sync_db_url()`（asyncpg → psycopg3 结构化转换，
  保留全部连接参数）。
- `backend/alembic/env.py`：改用 `sync_db_url()`，不再做字符串替换。
- `backend/alembic/versions/0001_p0_core.py`：改写为显式冻结 DDL
  （18 表，含 9 个唯一约束与 3 个索引），revision 不变。
- `backend/app/db/models.py`：声明 9 个 `UniqueConstraint` 与 3 个 `Index`；
  连接表租户链以文档 + 可达性测试覆盖，未做加列式组合外键（最小结构，见偏差）。
- `backend/pyproject.toml`：删除无效的 `asyncio_mode = "strict"`。
- `docker-compose.yml`：新增 `migrate`（`alembic upgrade head`）与 `worker` 服务；
  删除 4 个无代码消费变量；CORS 改名并改为 JSON 列表格式；`backend` 改为等待
  迁移完成，去掉对 redis 的硬依赖。
- `README.md`：后端启动入口改为 `app.main:app`，删除失效文档链接，
  注明业务接口 501 现状。
- `docs/api.md` / `docs/技术方案.md`：各改 1 行，把“仓库没有 backend”更新为
  “已有单包骨架、业务路由 501 占位”。

新增 3 个文件：`backend/app/db/seed_dev.py`（uuid5 确定性预置 ID，生产拒绝）、
`backend/tests/test_config.py`（8 项）、`backend/tests/test_migrations.py`（5 项）。

## 验证结果

以下均为当时实际运行的命令与输出：

- `uv sync --frozen`（uv 0.12.12）：成功复现，仅安装 `insightx-backend` 本体。
- `pytest -q`：**15 passed，2 warnings**（实施前 2 passed / 3 warnings；
  `asyncio_mode` 未知配置警告已消除；剩余 2 个为第三方弃用警告，未盲目加 httpx2）。
- 新旧离线 SQL 渲染 diff（`alembic upgrade base:head --sql`）：
  **纯新增**——9 个 UNIQUE 约束 + 3 个 CREATE INDEX，表/列/类型/顺序零差异；
  全部改动完成后重渲染一致。
- 引擎探针（未连接）：`sync_db_url` 输出驱动为 `psycopg`；
  旧转换路径在本机复现 `ModuleNotFoundError: No module named 'psycopg2'`。
- 入口模块导入（`app.main`、`app.worker`、`seed_dev`）与 Compose YAML 解析通过。
- 83 文件基线比对：仅上述预期文件变更（另见遗留事项的并发改动）。

## 计划偏差

1. 连接表租户链：未采用加列式组合外键，改用 FK 可达性测试 + 文档
   （`test_every_table_reaches_tenants`），理由是阶段 01 求最小结构，
   应用层隔离由阶段 03/08 测试覆盖。
2. Compose 去掉 `backend` 对 redis 的硬依赖（代码无任何 redis 调用），
   redis 服务保留供未来可选使用。
3. `AsyncSession` 工厂经核查无需改动；`backend/README.md` 已正确，无需改动。

## 遗留事项与未执行检查

- **真实库验收阻塞**：环境无 postgres/docker，以下未执行——隔离库
  `alembic upgrade head/current`、约束违反拒绝测试、重复 upgrade 无副作用、
  downgrade/upgrade 重建。有库后执行：
  `DATABASE_URL=postgresql+asyncpg://…@隔离库/insightx uv run alembic upgrade head`
  再 `uv run pytest -q`；破坏性操作仅限可销毁测试库。
- 冻结前提假设：判定 0001 从未应用（证据：无运行数据库、无 CI、无版本表引用；
  改前已备份）。若外部存在已应用该迁移的库，须先确认兼容策略。
- 当时工作区另有非本任务改动，未触碰：`frontend/src/mock/data.ts`
 （709 新增/248 删除）、新增 `.mimosa/` 目录。
- PostgreSQL/Redis 版本升级、Celery、PRD 业务口径、HNSW 索引均未动，
  分属后续阶段或待确认事项。
