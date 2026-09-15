# 根据 API 文档完善后端 P0 接口：实施计划

## 目标

按 `docs/api.md` 的 P0 契约补齐 FastAPI 后端接口、PostgreSQL 持久化、统一错误与幂等语义、任务事件回放 SSE，并用真实 PostgreSQL 验证迁移、租户隔离和接口行为。

本次验收边界是“接口与持久化可用”：

- 实现 `POST/GET /api/v1/tasks`、任务快照、取消、重试、报告、证据和 SSE 共 8 条 P0 业务路由。
- 创建任务时在一个数据库事务内写入 task、task_items、初始事件、outbox 和幂等记录。
- 完成统一成功信封、错误信封、请求 ID、游标分页、UTC 时间、租户范围和 `Idempotency-Key` 行为。
- 完成 Alembic 初始迁移、Compose 迁移服务、容器和示例环境变量接入。
- 同步更新 API 文档的实现状态和 README 的启动、迁移、限制说明。

本次不虚构 Celery Worker、LangGraph、评论采集或报告生成能力的接入状态。真实创建出的任务在没有 Worker 时保持 `QUEUED`；报告和证据接口只在数据库中确实存在对应数据时返回成功。

## 当前事实及依据

- `docs/api.md` 已冻结 P0 REST + SSE 契约草案：8 条 P0 路由、成功/错误信封、共享 DTO、状态枚举、分页、幂等、租户隔离、报告/证据字段及 SSE 回放语义均已写明；第 2.3 节把 SSE 错写为“见第 6 节”，实际 SSE 在第 7 节。
- `docs/api.md` 当前把任务接口标为“P0 拟议-未实现”；唯一已实现业务接口是 `GET /api/v1/health`，其 DB/Redis 字段仍是固定 `false`。
- `backend/src/insightx/main.py` 只创建 FastAPI 应用、CORS 和 `/api/v1` 聚合路由；`backend/src/insightx/api/router.py` 只注册 health router；不存在任务、错误处理、鉴权、数据库会话、模型、迁移或 SSE 代码。
- `backend/pyproject.toml` 已声明 FastAPI、SQLAlchemy 2、psycopg 3、Alembic、Pydantic Settings、Redis 等相关依赖，无需新增运行时依赖。
- `backend/tests/conftest.py` 只有异步测试 client；`test_health.py` 重复定义了一个 client fixture。当前测试不连接真实 PostgreSQL。
- `infra/compose.yaml` 有 PostgreSQL、Redis、API、Web，但 API 未注入 `DATABASE_URL`/`REDIS_URL`，也没有迁移执行步骤；`infra/backend.Dockerfile` 未复制 Alembic 配置和迁移目录。
- `.env.example` 当前只有 Mongo 和 crawler 变量；本地未跟踪环境文件由配置自动读取，计划不读取或写入其真实值。
- `docs/architecture.md` 明确 PostgreSQL 是任务、报告、证据和事件的事实源；数据库访问采用 SQLAlchemy 2 + psycopg 3 同步会话，普通 DB 路由使用 `def`，SSE 的短查询交给线程池且不长期占用会话；测试应在真实 PostgreSQL 上验证，不用 SQLite 替代。
- 当前没有生产登录/会话/CSRF 实现，也没有 Worker、dispatcher 或 LangGraph 图。为避免伪造认证，本次用服务端配置 `DEV_TENANT_ID` 提供开发租户；`AUTH_MODE=required` 时业务接口统一 fail closed 返回 `401 UNAUTHORIZED`，不引入可冒充正式身份的临时客户端 header。

## 预计变更文件

### 后端配置、数据库与 DTO

- 新增 `backend/src/insightx/config.py`：用 `pydantic-settings` 定义 `DATABASE_URL`、`REDIS_URL`、`AUTH_MODE`（`dev|required`，默认 `dev`）、`DEV_TENANT_ID`（默认 `dev-tenant`）及缓存 settings 工厂；本地配置自动读取未跟踪环境文件，示例只写非敏感占位值。
- 新增 `backend/src/insightx/database.py`：定义 `Base`、同步 engine/session factory 构造和请求会话依赖所需的基础类型；创建 engine 时不主动连接数据库。
- 新增 `backend/src/insightx/models.py`：定义以下 PostgreSQL 表和约束：
  - `tasks(task_id, tenant_id, parent_task_id, platform, marketplace, window_preset, status, cancel_requested_at, created_at, updated_at, finished_at)`。
  - `task_items(item_id, task_id, tenant_id, asin, status, current_node, attempt, data_quality, sample_metrics, error, created_at, updated_at)`。
  - `task_events(event_id bigint identity, task_id, task_item_id, event_type, payload, created_at)`；`event_id` 按数据库序列单调递增并序列化为字符串。
  - `reports(report_id, tenant_id, task_id, item_id, data_quality, sample_metrics, generated_at, financial_state, pain_points, proposals, warnings, model_metadata)`。
  - `evidence(evidence_id, tenant_id, task_id, item_id, source_type, source_ref, excerpt, source_url, published_at, metadata, provenance, created_at)`。
  - `evidence_claim_refs(evidence_id, claim_id, claim_type)`，用于 `claim_id` 过滤并防止把其他 item 的证据混入。
  - `idempotency_records(record_id, tenant_id, scope, key, request_hash, response_status, resource_id, created_at)`，唯一键为 `(tenant_id, scope, key)`。
  - `outbox_messages(message_id, tenant_id, topic, aggregate_id, payload, status, available_at, attempts, created_at, published_at)`。
  - 所有业务表使用 `tenant_id` 和任务/item 外键约束、必要的查询索引及级联子表删除；时间列使用 `DateTime(timezone=True)`，结构化 DTO 使用 JSONB。
- 新增 `backend/src/insightx/schemas.py`：实现文档中的全部 P0 DTO 与枚举，包括统一 `Page[T]`、`TaskCreateRequest`、`TaskCreatedResponse`、`TaskListItem`、`TaskSnapshot`、`TaskItemSnapshot`、`SampleMetrics`、`NodeProgress`、`Report`、证据和 SSE 事件 DTO。请求模型 `extra="forbid"`；ASIN 先大写、去重，再做 `^[A-Z0-9]{10}$` 和 1–10 项校验；P0 固定 `platform="amazon"`、`marketplace="US"`、`financial_state="NOT_EVALUATED"`；所有 datetime 序列化为 UTC `...Z`。
- 新增 `backend/src/insightx/errors.py`：定义 `ApiError`、错误码常量、`{error:{code,message,details,retryable,request_id}}` 处理器、FastAPI `RequestValidationError` 到 `422 VALIDATION_ERROR` 的转换，以及未处理异常的通用 `500 INTERNAL_ERROR`；不把数据库或异常堆栈泄露给客户端。无匹配路由仍保留 Starlette 原生 404。
- 新增 `backend/src/insightx/dependencies.py`：从 `request.app.state.session_factory` 创建/关闭同步 Session；实现开发租户依赖和 `AUTH_MODE=required` 的 fail-closed 逻辑；所有业务查询都必须显式附加当前租户条件。

### 业务服务与路由

- 新增 `backend/src/insightx/services/__init__.py` 和 `backend/src/insightx/services/tasks.py`：集中实现任务创建、列表/快照、取消、重试、报告读取、证据分页和 SSE 事件查询。ID 使用 `tsk_`、`itm_`、`rpt_`、`ev_` 前缀加 `uuid4().hex`；查询统一使用 `tenant_id`，跨租户或跨任务统一返回 `404 TASK_NOT_FOUND`/`404 ITEM_NOT_FOUND`，不泄露资源是否存在。
- 新增 `backend/src/insightx/api/v1/tasks.py`：实现以下精确契约：
  - `POST /api/v1/tasks`：要求 `Idempotency-Key`；返回值 `202` 与 `TaskCreatedResponse`。同一 key + 相同规范化请求返回原任务且 `reused=true`；同一 key + 不同请求返回 `409 IDEMPOTENCY_CONFLICT`。task、items、初始任务/item 事件、outbox 和幂等记录在同一事务提交。
  - `GET /api/v1/tasks`：支持 `status`、`cursor`、`limit`；`limit` 默认 20、最大 100，按 `created_at DESC, task_id DESC` 稳定排序，返回 `Page[TaskListItem]` 和不透明游标。
  - `GET /api/v1/tasks/{task_id}`：返回含真实 item 状态和 `progress={total_items,finished_items}` 的 `TaskSnapshot`。
  - `POST /api/v1/tasks/{task_id}/cancel`：首次接受写入 `cancel_requested_at` 并返回 `202 TaskSnapshot`；重复取消或终态任务不产生第二次动作，返回 `200 TaskSnapshot`。无 Worker 时不会伪造执行边界或把未终态任务自动改成已完成。
  - `POST /api/v1/tasks/{task_id}/retry`：要求 `Idempotency-Key`；空 item 列表返回 `422 VALIDATION_ERROR`，重复、未知、跨任务、非 `FAILED` 或源任务非终态返回 `409 ITEM_NOT_RETRYABLE`；成功创建一个保留 `parent_task_id` 的新任务并返回 `202 TaskCreatedResponse`。
  - `GET /api/v1/tasks/{task_id}/items/{item_id}/report`：报告不存在返回 `409 REPORT_NOT_READY` 且 `retryable=true`；存在时返回完整 `Report`，保留合法 `NO_DATA` 报告。
  - `GET /api/v1/tasks/{task_id}/items/{item_id}/evidence`：支持 `claim_id`、`source_type`、`cursor`、`limit`，返回 `Page[Evidence]`；无证据返回真实空页，不构造占位证据。
  - `GET /api/v1/tasks/{task_id}/events`：返回 `text/event-stream`。首帧为 `retry: 3000`；事件使用 `id/event/data`，三个事件类型仅限 `task.status_changed`、`task_item.status_changed`、`task_item.node_progress`；每 0.5 秒短查询增量事件，每 15 秒发送注释心跳；`Last-Event-ID` 优先于 `after`；非法或超出当前可用范围的游标返回 `422 INVALID_EVENT_CURSOR`；任务到达 `COMPLETED/FAILED/CANCELED` 后先追平事件再关闭流。SSE 循环每次使用独立的短 Session 在线程池中查询，不把请求级 Session 持有到连接结束。
- 修改 `backend/src/insightx/api/router.py`：注册任务 router，保留 health router。
- 修改 `backend/src/insightx/main.py`：让 `create_app(settings=None, session_factory=None)` 支持注入测试配置和 session factory；将 settings、engine、session factory 放入 `app.state`；注册请求 ID 中间件、异常处理器和任务路由。模块级 `app` 保持 `insightx.main:app` 启动方式不变。

### 迁移、容器与文档

- 新增 `backend/alembic.ini`、`backend/migrations/env.py`、`backend/migrations/script.py.mako`、`backend/migrations/versions/20260914_task_api_base.py`：建立并验证上述 8 张表的初始迁移，支持 `upgrade head` 和 `downgrade base`。迁移不写演示数据，不调用网络或模型。
- 修改 `infra/backend.Dockerfile`：复制 `alembic.ini` 和 `migrations/` 到镜像，使运行容器可以执行迁移。
- 修改 `infra/compose.yaml`：为 migrate/api 注入 PostgreSQL、Redis、认证模式和开发租户环境变量；新增一次性 `migrate` 服务执行 `alembic upgrade head`；让 `api` 等待 `migrate` 成功和 Redis 健康后再启动；不新增 Worker 或 dispatcher 服务。
- 修改 `.env.example`：只增加非敏感占位变量 `DATABASE_URL`、`REDIS_URL`、`AUTH_MODE`、`DEV_TENANT_ID`、`TEST_DATABASE_URL`；不加入真实密钥或环境专属值。
- 修改 `backend/README.md`：增加数据库迁移和 P0 API 启动说明、测试数据库要求、环境变量清单、接口实现范围，并明确没有 Worker 时任务只停留在 `QUEUED`、报告/证据数据不会被虚构生成。
- 修改 `docs/api.md`：修正第 2.3 节把 SSE 指向第 6 节的错误引用；把 P0 决策从“待确认”更新为本次 DTO 已确认的实现、把接口总览和当前结论准确标记为“API 已实现但执行/数据生产未接入”；不把 Worker、真实分析结果或报告生成标记为已完成。

## 实施步骤与分工

1. 由主实施者先完成 `config.py`、`database.py`、`models.py`、Alembic 初始迁移，并在真实 PostgreSQL 测试库上执行迁移和反向下翻，确认表、索引、约束和 JSONB 类型有效。
2. 在同一串行路径实现 `schemas.py`、`errors.py`、`dependencies.py`，先用契约测试固定 DTO 校验、信封、UTC 时间、分页和开发租户行为。
3. 实现 `services/tasks.py` 与 `api/v1/tasks.py`：先完成创建、列表、快照、取消、重试和幂等事务，再接入报告、证据和 SSE；所有查询都从 `request.app.state.session_factory` 获取短会话。
4. 调整 `main.py` 和 `api/router.py`，补齐请求 ID、全局异常处理和 OpenAPI 路由；保持 health 端点和无路由 404 的现有非业务行为不被意外改写。
5. 增加 REST 与 SSE 集成测试，测试 fixture 只在 `TEST_DATABASE_URL` 指向数据库名以 `_test` 结尾时执行破坏性建表/清表操作；未配置测试数据库时允许离线测试跳过新集成用例，但最终验证必须显式运行真实 PostgreSQL 测试。
6. 最后更新 Dockerfile、Compose、示例环境文件和两份文档；主实施者完成迁移、静态检查、OpenAPI 和完整测试后，再由独立只读 Reviewer 依据本计划和 `docs/api.md` 检查字段、状态码、租户隔离、SSE 边界与未实现能力声明。Reviewer 不修改文件。

本任务的主要写入路径彼此依赖，数据库模型必须先于服务和路由冻结；因此不把相互依赖的领域代码拆成并行写入。只有最后的只读评审适合独立子代理。

## 验证与验收

1. `cd backend && uv run ruff check .`：退出码 0。
2. `cd backend && uv run mypy src`：退出码 0。
3. `cd backend && TEST_DATABASE_URL=<真实 PostgreSQL 测试库> uv run alembic upgrade head`：迁移成功；核对 `tasks`、`task_items`、`task_events`、`reports`、`evidence`、`evidence_claim_refs`、`idempotency_records`、`outbox_messages` 及关键唯一索引存在；再执行 `downgrade base` 和 `upgrade head`，确认可逆。
4. `cd backend && TEST_DATABASE_URL=<真实 PostgreSQL 测试库> uv run pytest -q`：现有爬虫/health 测试及新增 REST、SSE 测试全部通过，不跳过需要真实 PostgreSQL 的用例。
5. `cd backend && uv run pytest -q tests/test_tasks_api.py tests/test_task_events.py`：聚焦套件通过，覆盖创建规范化、空/超量/非法 ASIN、固定平台与站点、时间窗、幂等复用/冲突、分页与稳定次级排序、租户隔离、取消重复、重试边界、报告未就绪、证据空页/过滤、SSE 回放、`Last-Event-ID` 优先级、非法游标和终态关闭。
6. `cd backend && uv run python -c "from insightx.main import create_app; print(sorted(create_app().openapi()['paths']))"`：输出包含 8 条 P0 路径和 `/api/v1/health`，且不出现重复 `/api/v1` 前缀。
7. `cd backend && uv run alembic upgrade head --sql`：离线生成 SQL 成功，用于确认容器迁移不依赖预先启动 API。
8. `git diff --check -- .env.example backend docs/api.md docs/plans/2026-09-14-backend-api-implementation infra`：无空白错误。
9. 人工核对响应：时间以 `Z` 结束、JSON 字段为 `snake_case`、成功/错误信封严格符合文档、跨租户资源统一 404、SSE 不使用 JSON 信封且不伪造业务事件。

验收条件：真实 PostgreSQL 上迁移和测试通过；P0 路由的 OpenAPI 与 DTO 契约一致；创建、查询、幂等、取消、重试、报告、证据和 SSE 的 P0 行为有自动化证据；文档明确区分“API 已实现”和“执行器/数据生产未接入”。

## 风险与非目标

- 最大风险是本仓库没有 Worker、dispatcher、评论采集、报告或证据生产链路。本次只实现文档定义的接口事实源和传输层；新任务会真实处于 `QUEUED`，没有失败 item 时无法自然产生可重试数据，不能把接口测试中的种子数据当生产能力。
- `AUTH_MODE=dev` 只适用于本机开发，将固定服务端 `DEV_TENANT_ID` 作为租户；`AUTH_MODE=required` 当前 fail closed，不是生产登录实现。正式会话、Cookie、CSRF 和成员关系校验仍待单独任务。
- SSE 保留时间、最大回放量和反向代理空闲超时尚未冻结；本次不删除历史事件，游标是事件主键字符串。若未来设置保留边界，需要迁移并重新验证 `INVALID_EVENT_CURSOR` 语义。
- Alembic 初始迁移会创建空表，不迁移历史数据；当前仓库没有可迁移的业务任务数据。
- 非目标：不改 `/health` 的 DB/Redis 探针语义，不新增依赖，不实现 Celery/Redis 派发、LangGraph、真实报告生成、前端客户端、P1/P2 API、登录授权、图片证据、限流或生产部署。
- 不执行 commit、push、PR、发布或生产数据库变更；仅在获批后运行本计划的实现、真实测试数据库迁移和必要验证。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-14
- 批准信息：用户于 2026-09-14 回复“开始”，批准本计划全部范围。
