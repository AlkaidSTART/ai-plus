# 前后端接口接通与整套服务运行：实施计划

## 目标

在现有前端、FastAPI 任务 API、PostgreSQL/Redis Compose 基座之间完成可运行的最小端到端闭环：

1. 前端继续通过同域 `/api` 真实调用任务创建和任务列表 REST 接口。
2. 前端接入后端已实现的 SSE 端点，能解析 `task.status_changed`、`task_item.status_changed`、`task_item.node_progress` 三类命名事件，并在终端状态关闭连接。
3. Compose 为 API 注入 PostgreSQL/Redis 配置，并在 API 启动前执行 Alembic 迁移，使 Web → Nginx → API → PostgreSQL 的任务创建、列表和 SSE 回放真实可用。
4. 在宿主机 `18080` 端口启动完整 Compose，验证首页、健康检查、创建任务、查询任务和 SSE 回放。

这里的“整套服务”指当前仓库实际已有的 Web/API/PostgreSQL/Redis 传输与持久化栈。仓库尚未实现 Celery Worker、outbox dispatcher、LangGraph 执行链、评论采集和报告生成，因此不会把任务停留在 `QUEUED` 描述为业务全链路完成。

## 当前事实及依据

- `frontend/src/features/dashboard/NewTaskDialog.vue` 已调用 `useCreateTask()`，`DashboardPage.vue` 已调用 `useTaskList()`；REST 使用相对 `/api`，开发时由 `frontend/vite.config.ts` 代理到 `http://localhost:8000`，Compose 中由 `infra/nginx.conf` 同域转发到 `api:8000`。
- `frontend/src/api/client.ts` 已定义创建、列表、详情和取消接口，任务创建与列表页面已接入真实请求，不是 mock。
- `frontend/src/composables/useTaskEvents.ts` 仍是占位实现：只监听 EventSource 默认 `message`，而 `backend/src/insightx/api/v1/tasks.py` 发送命名事件；前端 `events.types.ts` 使用 camelCase，后端 `services/tasks.py` 发送 snake_case 信封。
- `DashboardPage.vue` 当前固定传入 `<SseTimeline :nodes="[]" />`，没有任何组件调用 `useTaskEvents().connect()`。
- 后端已提供 8 条任务 API 路由，其中 SSE 支持 `after` 查询参数和 `Last-Event-ID`，创建任务时持久化任务、任务项、状态事件和 outbox 消息。
- `infra/compose.yaml` 的 API 未设置 `DATABASE_URL`、`REDIS_URL`，会使用容器内 `127.0.0.1:5432` 和 `127.0.0.1:6379`；Compose 也没有 migration 服务。
- `infra/backend.Dockerfile` 只复制 `backend/src`，没有复制 `backend/alembic.ini` 和 `backend/migrations/`。
- 当前主机 `8080` 已被其它 Docker 监听；本次使用 `APP_PORT=18080`，避免改动或停止现有服务。
- 工作区已有未提交改动；本任务只修改与本计划列明的文件，不 reset、checkout、commit、push 或触碰生产数据。

## 预计变更文件

前端：

- `frontend/src/api/events.types.ts`：把 SSE 信封与 payload 对齐后端 snake_case DTO，并补齐错误、数据质量和节点字段。
- `frontend/src/composables/useTaskEvents.ts`：使用三个命名事件监听；支持初始 `after` 游标、按事件 ID 去重、终态关闭；保留 EventSource 自动重连语义。
- `frontend/src/features/dashboard/DashboardPage.vue`：订阅最近任务的 SSE；把 `task_item.node_progress` 映射到 `SseTimeline`；状态变化时刷新任务列表查询。

部署：

- `infra/backend.Dockerfile`：把 Alembic 配置和迁移目录复制到镜像。
- `infra/compose.yaml`：为 API 注入数据库、Redis、开发认证和租户配置；新增一次性 `migrate` 服务执行 `alembic upgrade head`；API 在迁移成功后启动。
- `infra/start.sh`：失败日志提示中加入 `migrate`，保持启动脚本与实际服务一致。
- `.env.example`：增加后端数据库、Redis、认证模式和开发租户的非敏感示例变量。

文档：

- `README.md`、`backend/README.md`、`infra/README.md`：修正“业务 API/SSE/迁移完全未实现”的过时描述，同时明确 Worker 与业务执行链仍未接入。
- `docs/api.md`：把已存在的任务 REST/SSE 从“拟议-未实现”更新为“HTTP/SSE 传输已实现，执行器未接入”，并说明任务会保持 `QUEUED`。

验证后新增：

- `docs/plans/2026-09-15-frontend-backend-e2e-run/result.md`：记录实际变更、命令、真实结果、偏差与遗留问题。

## 实施步骤与分工

1. 按后端真实 DTO 修改前端 SSE 类型，保持字段名、可空性和状态枚举一致。
2. 重写 `useTaskEvents` 的连接与监听逻辑：首次连接可带 `after`；三个命名事件经同一解析函数处理；依据信封 `id` 与 SSE `lastEventId` 去重；任务终态主动关闭。
3. 在 Dashboard 选择列表首条（最近）任务，创建 `TaskEvent` 订阅；维护按任务项和节点 ID 唯一的时间线状态；状态事件触发任务列表重新拉取。
4. 修改后端镜像和 Compose：复制 Alembic 文件，新增 `migrate` 一次性服务，注入 `DATABASE_URL`、`REDIS_URL`、`AUTH_MODE=dev`、`DEV_TENANT_ID=dev-tenant`，并让 API 仅在迁移服务成功退出后启动。
5. 同步启动脚本与文档，明确 REST/SSE 和迁移已接通，但 Worker/outbox/LangGraph/报告生产仍未实现。
6. 执行静态检查：前端构建、后端 pytest/ruff/mypy、Compose 配置解析、`git diff --check`。
7. 使用 `APP_PORT=18080 ./infra/start.sh` 真实构建并启动服务；通过 `curl` 验证 Web、健康接口、任务创建、任务列表和 SSE 事件帧。
8. 独立 Reviewer 子代理只读审查变更，重点核对前后端字段、SSE 命名事件、Compose 依赖顺序和文档真实性；主代理复核实测结果。
9. 验证完成后写独立 `result.md`，不把结果回写本计划。

## 验证与验收

- `cd frontend && bun run build`：TypeScript 与 Vite 构建通过。
- `cd backend && .venv/bin/pytest -q`：现有测试全部通过。
- `cd backend && .venv/bin/ruff check . && .venv/bin/mypy src`：静态检查通过。
- `docker compose -f infra/compose.yaml config`：Compose 配置可解析，且 API/migrate 环境与 depends_on 符合计划。
- `APP_PORT=18080 ./infra/start.sh`：`db`、`redis`、`api`、`web` 健康，`migrate` 成功退出。
- `curl -fsS http://127.0.0.1:18080/`：返回前端 HTML。
- `curl -fsS http://127.0.0.1:18080/api/v1/health`：返回 HTTP 200；允许业务状态仍为 `degraded`，因为真实探针不在本任务范围。
- 使用固定 `Idempotency-Key` 以合法 10 位 ASIN 调用 `POST /api/v1/tasks`：返回 202 和 `QUEUED` 任务。
- `GET /api/v1/tasks`：返回刚才创建的任务。
- `curl -N` 订阅 `GET /api/v1/tasks/{task_id}/events`：能看到 `retry: 3000` 及 `task.status_changed`/`task_item.status_changed` 命名事件；因无 Worker，流会继续等待，不能用“任务完成”作为验收条件。

验收条件：前端构建通过；Compose 迁移成功；容器中的任务创建和列表使用 PostgreSQL 成功；SSE 返回真实持久事件；文档不声称 Worker 或完整 AI 分析链已实现。

## 风险与非目标

- 首次构建可能需要访问镜像仓库和包仓库；若网络受限，将按权限流程请求网络/ Docker 访问。
- PostgreSQL、Redis 和 Docker 卷可能已有旧状态；迁移使用 Alembic 当前 head，不执行 `down -v`，不删除数据。
- `8080` 已被占用，本次固定使用 `18080`；不停止现有容器。
- SSE 没有 Worker 写入后续事件，因此任务会保持 `QUEUED`，订阅在回放创建事件后持续等待；这是当前实现的真实边界。
- 非目标：实现 Celery Worker、outbox dispatcher、LangGraph 图、评论采集、报告生成、真实 health 探针、认证系统、完整浏览器 E2E 测试框架和生产部署。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-15
- 批准信息：用户于 2026-09-15 回复“计划好了直接运行。”，明确授权计划完成后直接实施和运行。
