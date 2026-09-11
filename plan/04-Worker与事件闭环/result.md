# 阶段 04：Worker 与事件闭环 — 实施结果

## 完成状态

已完成（执行基座、事件服务、真实 SSE、夹具驱动与离线验证；
DB 写入测试与 LangGraph 绑定按计划门禁阻塞，见遗留事项）。

## 对应计划

[plan.md](plan.md)。用户指令“依次执行 plan 中剩下的计划”即执行依据，
按 checklist 逐项落实，未经确认的依赖项止于阻塞线。

## 实际变更

新增 7 个文件：

- `backend/app/worker/graph.py`（约 430 行）：租约守卫（版本比对，不符返回
  STOLEN）、取消协作（当前节点 CANCELED、后续 SKIPPED）、瞬时/永久错误分类、
  有限退避（2/4/8s，可注入空 sleep）、幂等节点行
  （item/attempt/node/output_version 唯一，恢复复用 COMPLETED 行且不补发事件）、
  终态聚合（COMPLETED/FAILED/CANCELED，不新增 PARTIAL）、发布前取消复检。
- `backend/app/worker/runner.py`（重写）：`FOR UPDATE SKIP LOCKED` 认领、
  租约 owner/version/until、单分项独立会话执行、逐任务终态聚合；
  Redis 无客户端，纯 DB 轮询（Redis 不可用不影响）。
- `backend/app/services/events.py`（新建）：父行锁定分配 seq（禁裸 max+1）、
  增量读取、SSE 格式化/游标解析/控制事件构造纯函数。
- `backend/app/api/routes/events.py`（重写）：真实 `text/event-stream`，
  Last-Event-ID 优先于 after，非法/超前游标 422，终态消费完发送 stream.end，
  注释心跳、禁缓存/缓冲、120s 连接上限，租户校验在建流时执行。
- `backend/alembic/versions/0003_04_item_nodes.py`（新建）：`item_nodes` 表与索引，
  不碰历史迁移。
- `backend/tests/test_worker.py`、`test_events.py`、`test_recovery.py`；
  3 份 `worker_fixture_*.json`（显式 `fixture: true`，覆盖成功/零样本/永久失败）。

修改 4 个文件：`models.py`（`ItemNode`）、`services/tasks.py`
（快照读真实节点行与进度、创建事件补全 occurred_at/item_id/attempt 字段）、
`tests/test_migrations.py`（表数 18→19）、`tests/test_health.py`
（SSE 占位断言改为离线可验的 UUID 校验断言）。

## 验证结果

以下均为当时实际运行的命令与输出：

- `pytest -q`：**57 passed + 24 skipped**（之前 47 passed + 14 skipped）。
  24 个跳过 = 22 个无隔离库 + 2 个无凭证，零失败。
  离线可跑部分覆盖：终态聚合、错误分类、退避表、夹具三文件校验、
  SSE 格式化/游标解析、OpenAPI 路径。
- `alembic upgrade base:head --sql` 离线渲染：0003 仅新增 `item_nodes` 表与索引，
  历史迁移输出不变；元数据共 19 表。
- 边界核对：本任务仅上述文件变更；此前任务遗留与并行前端改动未触碰。

## 计划偏差与关键决策

1. **未安装 LangGraph**：网络虽通，但按计划“先读锁定版本文档”与停止条件，
   checkpointer 持久化无库可验，盲目集成等于猜 API。
   本阶段交付无框架依赖的执行基座（领取/续租/重试/取消/恢复/终态聚合语义完整），
   LangGraph 图绑定列为遗留事项，其规则不得违背本文件语义。
2. **夹具 publish 不写 Report 行**（断言保证 reports 表为空）：
   04 验证状态机与事件，不生产可被查询到的假报告；任务 COMPLETED 在此阶段
   仅表示分项终态，07 会叠加“已发布报告”口径。
3. 终态重复发送靠聚合前复检（已终结直接返回）；未加终态部分唯一索引，
   跨进程竞态残余风险已记录，P0 单 worker 下不可达。
4. 保留期未确认 → 不删事件 → reset 路径无触发条件（代码未伪造 reset）；
   超前游标按契约返回 422。
5. `current_node` 在节点结果落盘时更新（完成时刻，非开始时刻），快照如实展示。

## 遗留事项与未执行检查

- **DB 写入测试阻塞**：有隔离 pg16 + pgvector 后执行
  `TEST_DATABASE_URL=postgresql+asyncpg://… uv run pytest -q
  tests/test_worker.py tests/test_events.py tests/test_recovery.py`，
  覆盖租约窃取、恢复续跑、取消竞态、SSE 补发与终态关闭；
  另需独立 worker 进程纵切与 API 重启后可读验证。
- LangGraph 绑定：安装锁定版本 → 通读官方持久化文档 → pg checkpointer
  验证 → 不得改变本文件的租约/取消/幂等/终态语义。
- SSE 长连接心跳时序、120s 上限调优留待联调实测。
- 向 05–07 交接：执行上下文、节点输入输出约定、幂等产物与事件机制；
  07 必须用真实数据重跑七节点闭环，不得沿用夹具结论。
