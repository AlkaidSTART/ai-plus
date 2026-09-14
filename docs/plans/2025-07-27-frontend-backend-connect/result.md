# 前后端对接：实施结果

## 完成状态
已完成

## 实际变更

### 后端（3 文件）
1. **`backend/src/insightx/main.py`** — 添加 `get_settings`/`build_database`/`install_exception_handlers` 导入，`create_app()` 中初始化 settings、engine、session_factory 到 `app.state`，注册异常处理器
2. **`backend/src/insightx/api/v1/tasks.py`** — 新建，5 个路由端点：
   - `POST /api/v1/tasks` — 创建任务（需 Idempotency-Key header）
   - `GET /api/v1/tasks` — 分页任务列表（cursor/limit/status）
   - `GET /api/v1/tasks/{task_id}` — 任务快照
   - `POST /api/v1/tasks/{task_id}/cancel` — 取消任务
   - `GET /api/v1/tasks/{task_id}/events` — SSE 事件流
3. **`backend/src/insightx/api/router.py`** — 注册 tasks_router

### 前端（4 文件）
1. **`frontend/src/api/client.ts`** — 新建，薄 fetch wrapper + 4 个端点函数（createTask/listTasks/getTask/cancelTask）+ 类型定义
2. **`frontend/src/composables/useTasks.ts`** — 新建，useTaskList + useCreateTask composables
3. **`frontend/src/features/dashboard/NewTaskDialog.vue`** — 接入 useCreateTask，按钮改为条件 disabled + isPending 状态，成功/失败 toast
4. **`frontend/src/features/dashboard/DashboardPage.vue`** — 接入 useTaskList，最近任务区域改为 loading/空态/列表三态渲染

## 实施记录

1. Step 1 (main.py): 直接添加 3 行导入 + 4 行初始化 + 1 行异常处理器注册
2. Step 2 (tasks.py): 新建文件，所有端点使用 SuccessEnvelope 包裹（SSE 除外），SSE 使用 StreamingResponse + asyncio.sleep 轮询
3. Step 3 (router.py): 一行导入 + 一行 include
4. Step 4 (client.ts): 初始实现有 TS constructor parameter properties，被 `erasableSyntaxOnly` 禁止，改为显式字段赋值
5. Step 5 (useTasks.ts): 初始导入了未使用的 `Ref`/`computed`，移除
6. Step 6 (NewTaskDialog): 接入 mutate + toast
7. Step 7 (DashboardPage): 添加 Loader2 图标 + 条件渲染

## 验证命令与真实结果

1. **后端 app 导入 + state 验证**:
   ```
   uv run python -c "from insightx.main import app; ..."
   → settings: Settings, session_factory: sessionmaker, engine: Engine
   ```

2. **后端 OpenAPI 路由验证**:
   ```
   uv run python -c "from insightx.main import app; spec = app.openapi(); ..."
   → ['get'] /api/v1/health
   → ['post', 'get'] /api/v1/tasks
   → ['get'] /api/v1/tasks/{task_id}
   → ['post'] /api/v1/tasks/{task_id}/cancel
   → ['get'] /api/v1/tasks/{task_id}/events
   ```

3. **前端 build**:
   ```
   bun run build → ✓ 3410 modules transformed. ✓ built in 486ms
   ```
   无 TS 错误。

## 计划偏差
- `IdempotencyKey` 和 `LimitQuery` 作为 Annotated 类型需要用作类型注解而非默认值，实施中修正。属批准范围内的细节调整。
- `ApiError` class 改为显式字段赋值以适配 `erasableSyntaxOnly` tsconfig 选项。

## 遗留问题与未执行检查
- **端到端测试未执行**：需要 PostgreSQL 运行。启动后端 `uv run uvicorn insightx.main:app` 后，若 DB 不可用，创建任务会返回 500（DB 连接失败），列表接口同理。这是预期行为。
- retry/report/evidence 端点未做前端对接（计划中明确为非目标）
- `GET /api/v1/tasks/{task_id}/events` SSE 的 `Last-Event-ID` header 支持未实现（当前用 query param `cursor`，前端 composable `useTaskEvents.ts` 使用 EventSource 原生 `lastEventId`）。需要后续对齐，但 composable 已有 `connect()` 可用。
