# 前后端对接：实施计划

## 目标
前端能通过 Vite proxy 调用后端 REST API（任务创建、任务列表、任务详情、取消），Dashboard 页面展示任务列表，NewTaskDialog 能提交任务。SSE 事件流对接（已有 composable 框架，连通即可）。

## 当前事实及依据

### 后端
- `main.py`：只创建 FastAPI app + CORS，**没有**初始化 DB engine/session、没有 `app.state.settings`/`session_factory`、没有注册异常处理器（`install_exception_handlers`）。
- `api/v1/` 只有 `health.py`，**没有 tasks 路由**。
- `services/tasks.py` 已完整实现：`create_task`、`list_tasks`、`get_task_snapshot`、`cancel_task`、`retry_task`、`get_report`、`list_evidence`、`prepare_event_stream`、`fetch_task_events`、`task_is_terminal`。
- `dependencies.py` 有 `get_tenant_id`、`get_session`（在 database.py）、`IdempotencyKey`、`LimitQuery`。
- `schemas.py` 有 `SuccessEnvelope`、`Page`、所有 request/response model。

### 前端
- Vite proxy 已配好 `/api` → `localhost:8000`。
- TanStack Query 已安装。
- `api/generated/` 为空（等 openapi 生成）。
- `useTaskEvents.ts` SSE composable 已实现（结构占位，connect 可用）。
- `NewTaskDialog.vue` 提交按钮 disabled。
- `DashboardPage.vue` 全部空态。
- 没有任何 API 客户端函数。

## 预计变更文件

### 后端（3 个文件）
1. **`backend/src/insightx/main.py`** — 添加 DB/settings 初始化 + 异常处理器注册
2. **`backend/src/insightx/api/v1/tasks.py`** — 新建，tasks REST 路由（create/list/get/cancel + SSE）
3. **`backend/src/insightx/api/router.py`** — 注册 tasks router

### 前端（4 个文件）
1. **`frontend/src/api/client.ts`** — 新建，薄 fetch wrapper + 各端点函数
2. **`frontend/src/composables/useTasks.ts`** — 新建，TanStack Query composables（useTaskList、useCreateTask、useTaskSnapshot、useCancelTask）
3. **`frontend/src/features/dashboard/NewTaskDialog.vue`** — 接入 useCreateTask，解除 disabled
4. **`frontend/src/features/dashboard/DashboardPage.vue`** — 接入 useTaskList，展示任务列表

## 实施步骤与分工

直接执行，无需子代理（单人 7 个文件的连贯修改）。

### Step 1: 后端 main.py 补全初始化
- 导入 `build_database`、`get_settings`、`install_exception_handlers`
- `create_app()` 中初始化 `settings`、`engine`、`session_factory`，挂到 `app.state`
- 注册异常处理器

### Step 2: 后端新建 tasks 路由
`api/v1/tasks.py`，路由：
- `POST /tasks` — 创建任务（需 Idempotency-Key header）
- `GET /tasks` — 分页列表（cursor + limit + status filter）
- `GET /tasks/{task_id}` — 任务快照
- `POST /tasks/{task_id}/cancel` — 取消
- `GET /tasks/{task_id}/events` — SSE 事件流

所有端点使用 `SuccessEnvelope` 包裹（SSE 除外）。依赖 `get_session`、`get_tenant_id`。

### Step 3: 后端 router.py 注册 tasks
导入并 include tasks router。

### Step 4: 前端 API 客户端
`api/client.ts`：薄 fetch wrapper，处理 JSON 响应 + error envelope。各端点函数导出。

### Step 5: 前端 TanStack Query composables
`composables/useTasks.ts`：`useTaskList`、`useCreateTask`、`useTaskSnapshot`、`useCancelTask`。

### Step 6: 前端 NewTaskDialog 接入
- 导入 `useCreateTask`
- 生成 Idempotency-Key（crypto.randomUUID）
- 提交按钮解除 disabled，绑定 mutate
- 成功后关闭 dialog + invalidate 任务列表

### Step 7: 前端 DashboardPage 接入
- 导入 `useTaskList`
- "最近任务" Card 展示任务列表（替换 EmptyState 为条件渲染）
- 加载中/空态/有数据三态

## 验证与验收
1. `cd backend && uv run python -c "from insightx.main import app; print('ok')"` — 确认 app 能导入
2. 启动后端 `uv run uvicorn insightx.main:app`，curl 测试：
   - `curl localhost:8000/api/v1/health` → 200
   - `curl localhost:8000/docs` → OpenAPI UI 可访问
3. 前端 `cd frontend && bun run build` — 无 TS 编译错误
4. 手动验证：启动前后端，在浏览器创建任务（需要 DB 可用才能真正创建；无 DB 时确认请求到达后端并返回合理错误）

**不可执行的检查**：完整端到端测试需要 PostgreSQL 数据库运行。当前计划不要求数据库可用，仅确认代码编译和路由注册正确。

## 风险与非目标
- **风险**：无 DB 时 create_task 会失败 — 这是预期行为，不影响代码正确性
- **非目标**：不做 retry、report、evidence 前端对接（当前无对应 UI 页面）
- **非目标**：不生成 openapi client（Hey API），手写薄客户端即可
- **非目标**：不修改 SSE composable（已可用）
- **非目标**：不添加新依赖

## 审核状态
- 状态：待审核
- 创建日期：2025-07-27
- 批准信息：未批准
