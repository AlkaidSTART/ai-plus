# 阶段 03：任务持久化与接口 — 实施结果

## 完成状态

已完成（代码、迁移与离线验证；DB 写入测试已编写但因无隔离库阻塞，见遗留事项）。

## 对应计划

[plan.md](plan.md)。用户明确回复“plan\03-任务持久化与接口 实施”，
按该计划执行，无范围外改动。

## 实际变更

修改 9 个文件：

- `backend/app/services/tasks.py`（新建，约 470 行）：幂等创建（含并发键冲突
  回查）、一致快照、稳定分页、取消、重试、日期窗/ASIN/游标纯函数、
  站点时区 `America/New_York`（已探明本机可用）。
- `backend/app/api/routes/tasks.py`（重写）：5 个真实端点；
  `_validate_asins` 保留原名与语义（阶段 02 测试继续通过）。
- `backend/app/api/schemas.py`：追加创建/列表/快照/取消/重试的响应模型，
  与 api.md §4 字段对齐；未改 `CreateTaskRequest`（阶段 02 测试依赖其宽松形态）。
- `backend/app/api/deps.py`（重写）：预置租户来自服务端配置，不再读取请求头；
  生产模式直接 401。
- `backend/app/api/errors.py`：错误包加 `details` 参数与请求级 ID
  （ContextVar，中间件写入，缺省 `req_todo`）。
- `backend/app/api/request_id.py`（新建）：请求 ID 中间件。
- `backend/app/main.py`：接中间件；Pydantic 校验失败转 422 统一包；
  401/404 转统一包，其余 HTTP 异常原样抛出。
- `backend/app/db/models.py`：`tasks` 加 `completed_at`、`parent_task_id`（FK）、
  `task_items` 加 `error`（JSON）。
- `backend/alembic/versions/0002_03_task_fields.py`（新建）：上述 3 列 1 外键，
  不碰已冻结的 0001。
- `backend/app/config.py`：预置身份改为确定性 UUID（与 `seed_dev` 同源，
  消除示例字符串与 UUID 列的不兼容）。
- `backend/tests/`：`support.py`（pg 门控/`asyncio.run` 入口/清库）、
  `conftest.py`（`pg_session` 等夹具）、`test_task_contract.py`（纯函数）、
  `test_tasks.py`（服务 + 路由）、`test_task_isolation.py`（隔离）；
  `test_health.py` 的过期 501 断言改为报告/SSE 占位断言（任务接口已实现）。

## 验证结果

以下均为当时实际运行的命令与输出：

- `pytest -q`：**47 passed + 14 skipped**（之前 28 passed + 2 skipped）。
  14 个跳过 = 9 个任务 DB 测试 + 3 个隔离 DB 测试 + 2 个无凭证真实调用，
  跳过原因均为“无隔离 PostgreSQL”或“无凭证”，无失败、无错误。
- `alembic upgrade base:head --sql` 离线渲染：0002 恰为 4 条语句
  （`completed_at`、`parent_task_id`、自引用外键、`task_items.error`），无其他变更。
- OpenAPI 探针（契约测试内）：5 个任务路径方法齐全，报告/SSE 占位路径保留。
- 基线比对：本任务仅上述文件变更；工作区另有非本任务的前端大改
  （多文件 M/D/??，疑似并行重构）与此前任务遗留项，均未触碰。

## 计划偏差

1. 测试未引入 pytest-asyncio：DB 测试用 `asyncio.run()` 包裹，
   无需新依赖，行为等价且在全环境可跑。
2. `limit` 越界采用钳制（1–100）而非 422；畸形 UUID 采用 422
   （契约未定义，已在此记录）。
3. 取消终态返回 200、活动返回 202（路由内按状态区分，符合 api.md §7）。
4. 重试窗口沿用源任务冻结窗口（显式传入，不重新按当日默认），
   保证同一重试语义稳定。

## 遗留事项与未执行检查

- **DB 写入测试阻塞**（环境无 postgres/docker）：有隔离 pg16 + pgvector 后执行
  `TEST_DATABASE_URL=postgresql+asyncpg://… uv run pytest -q`，
  预期 14 个跳过转为执行，覆盖并发同键、跨租户、游标绑定、取消重试全链路。
- 取消的 worker 落实、发布竞态、节点状态与进度数据归阶段 04；
  报告/SSE 实现归阶段 07/04；真实鉴权归阶段 08。
  当前所有分项恒为 QUEUED、节点数组为空、进度为零，不伪装执行。
- `X-Request-ID` 断言位于 pg 门控的路由测试内，本次未执行；
  中间件本身已随每个 TestClient 请求运行。
