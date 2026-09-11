# 阶段 04：Worker 与事件闭环

## 目标与前置条件

用明确标识的固定测试夹具验证“持久任务 → 领取执行 → 状态事件 → 断线恢复 → 终态”，替换空轮询，但不把测试夹具作为真实采集或 AI 报告。

依赖 [阶段 03](../03-任务持久化与接口/plan.md)。先读 `worker/runner.py`、`worker/nodes.py`、`docs/技术方案.md` §5.3、`docs/api.md` §6–7。新增 LangGraph/checkpointer 依赖前读取其锁定版本的官方文档与兼容示例，确认最小持久执行方式。

## 文件范围

已有：`backend/app/worker/runner.py`、`worker/nodes.py`、`worker/__main__.py`、`api/routes/events.py`、`api/routes/tasks.py`、`api/schemas.py`、`db/models.py`、`pyproject.toml`、`uv.lock`。

拟新增：`backend/app/worker/graph.py`、最小事件写入/读取服务、节点产物或执行记录的必要增量迁移、`backend/tests/test_worker.py`、`test_events.py`、`test_recovery.py`、明确标注的固定夹具。只添加被真实使用的文件，不先建通用队列框架。

## 实施步骤

- [ ] 固定开发/测试夹具注入边界：仅测试依赖覆盖或明确开发入口可启用，生产拒绝夹具执行。测试终态与合成报告不能进入真实统计。
- [ ] 用数据库原子领取实现租约 owner/until/version，版本单调递增；续租、状态和产物写入均检查当前租约版本，领取的并发正确性不能仅靠单 worker 假设。
- [ ] 为节点状态、耗时、输出版本和恢复位置提供必要持久字段/执行记录，幂等键覆盖 item/attempt/node/output_version；保证取消后不能提交新的节点产物。
- [ ] 集成实际七节点执行图与持久 checkpoint，线程范围限定 item/attempt。checkpoint 不替代业务表；检查点落后时复用已提交产物而非重复写报告。
- [ ] 使用固定夹具模拟节点成功、合法零样本、永久错误与瞬时错误；生产真实节点尚未实现时明确失败，不返回假成功。
- [ ] 外部调用封装明确超时、取消检查和重试分类；按已确认口径有限退避，401/非法输入不重试。不能承诺外部计费调用恰好一次。
- [ ] 将状态变化与相应业务事件放入同一数据库事务；任务内并发分配 seq 使用锁定计数或其他经过验证的方法，不能裸用 max(seq)+1。
- [ ] 实现部分失败、全失败、合法零样本、全部取消、活动任务取消等终态聚合；保留已完成分项，不新增未经契约定义的 PARTIAL/VETOED 任务状态。
- [ ] 发布边界与 cancel 标记串行校验，确保先取消后不能新发成功报告；关闭 SSE 只取消订阅。
- [ ] GET events 返回真实 text/event-stream，使用 DB 作为补发与增量共同来源；支持命名事件、单调 id、注释心跳、禁缓存/缓冲与连接清理。
- [ ] 实现 Last-Event-ID 优先于 after、默认 0、非法/超前游标 422、过期游标 stream.reset、终态已消费 stream.end。保留期未确认时不擅自删事件；reset 可用隔离测试场景验证。
- [ ] 将阶段 03 的租户范围检查应用到整个流生命周期。正式会话过期检查由阶段 08 接入，但现在不能允许流通过自报租户绕过隔离。

## 验证与验收

```bash
cd backend
uv run pytest -q tests/test_worker.py tests/test_events.py tests/test_recovery.py
uv run pytest -q
```

- [ ] 使用隔离数据库和独立 worker 进程跑夹具纵切，重启 API 后状态仍可读取。
- [ ] worker 中断、租约过期、重新领取、旧 worker 迟到提交均有竞态测试；旧版本写入必须拒绝。
- [ ] 检查点/业务提交不同步时恢复不产生重复产物或报告。
- [ ] 模拟多分项同时发事件，seq 唯一递增且无丢失已提交状态；SSE 断线补发与终态关闭可验证。
- [ ] 覆盖取消/发布两种提交先后、部分成功/全失败/零样本，人工 retry 保留原任务。
- [ ] Redis 不可用仍能发现任务及补发事件。测试有超时边界，不能无限等待 SSE。

## 非目标与停止条件

不接真实来源、模型、图片或财务，不新增 Celery，不把 fixture 数据计入业务成果。checkpoint 版本兼容、产物幂等或租约所有权无法保证时，不推进真实调用阶段。

## 交接

向阶段 05–07 提供可信执行上下文、节点输入输出/失败约定、幂等产物与事件机制；阶段 07 必须用真实数据重跑七节点闭环，不能直接沿用夹具验收结论。
