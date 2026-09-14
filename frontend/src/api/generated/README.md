# api/generated — 契约生成占位

本目录由 **Hey API** 从后端导出的 `contracts/openapi.json` 生成 TypeScript 客户端（Fetch）。

- 生成文件**不手改**，随契约变更重生成并随代码评审；CI 重生成检查漂移。
- 后端 DTO 是契约的单一来源；当前后端尚未实现，本目录暂空。
- 正式接口路径以 `contracts/openapi.json` 为准（任务创建拟为 `POST /api/v1/tasks`）。
- SSE 不经过本客户端：`src/composables/useTaskEvents.ts` 按 `contracts/task-events.schema.json` 单独接入。

参考：架构文档 `docs/architecture.md` 第 5 节。
