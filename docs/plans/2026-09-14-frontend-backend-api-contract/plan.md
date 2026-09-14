# 前后端接口清单与契约草案：实施计划

## 目标

新增 `docs/api.md`，形成一份可供前后端评审的接口清单与契约草案，清晰回答：

- 当前仓库真实已经实现哪些 HTTP 接口；
- P0 任务闭环需要哪些 REST 与 SSE 接口、DTO、状态和错误语义；
- P1/P2 能力目前有哪些接口边界，哪些路径和字段尚未冻结；
- 哪些内容来自当前代码、正式目标文档，哪些只是历史设计或本次文档拟议，不能被误当成已实现契约。

本任务只新增文档，不实现接口、不修改前后端代码、不生成 `contracts/openapi.json` 或事件 schema。

## 当前事实及依据

- 当前后端仅实现 `GET /api/v1/health`，返回 HTTP 200 和 `{code,message,data}`；当前固定为 `status="degraded"`、`db=false`、`redis=false`。依据：`backend/src/insightx/main.py`、`backend/src/insightx/api/router.py`、`backend/src/insightx/api/v1/health.py`、`backend/tests/test_health.py`。
- 当前后端没有任务、报告、证据、SSE、鉴权、租户、数据库模型或业务错误模型；`contracts/openapi.json`、`contracts/task-events.schema.json` 也不存在。
- 目标架构要求前后端只通过 HTTP REST + SSE 通信，后端 Pydantic DTO 是唯一契约源，再导出 OpenAPI 与事件 schema 生成前端客户端。依据：`PRD.md` 第 6 节、`docs/architecture.md` 第 5 节。
- 目标流程明确拟用 `POST /api/v1/tasks` 创建任务，提交 1–10 个 ASIN、站点、时间窗与幂等键，成功返回 `202 + task_id`；任务通过 Celery/LangGraph 异步执行。依据：`PRD.md:231-330`、`docs/architecture.md:139-170`。
- 当前前端没有可用 API client、mock 或查询层；新建任务按钮保持禁用。现有 SSE composable 使用草案路径 `GET /api/v1/tasks/{taskId}/events`，草案事件类型为 `task.status_changed`、`task_item.status_changed`、`task_item.node_progress`。依据：`frontend/src/composables/useTaskEvents.ts`、`frontend/src/api/events.types.ts`、`frontend/src/features/dashboard/NewTaskDialog.vue`。
- `docs/前端设计.md` 中的 `/api/v1/insight/...` 是已删除历史后端的接口快照，不是当前实现或目标契约；本次文档只可在“历史资料”说明中提及，不能与 `/api/v1/tasks...` 混用。
- 尚未由正式代码或 DTO 确定的事项包括：JSON 字段命名、成功/错误信封、幂等键的具体 header 名、认证方式、是否保留客户端 `project_id`、节点状态是否用 `SUCCESS` 或 `COMPLETED`、重试是否创建新任务、报告/证据接口的最终粒度。本计划给出拟议默认值并逐项标记为待后端契约确认。

## 预计变更文件

- 新增 `docs/plans/2026-09-14-frontend-backend-api-contract/plan.md`：本实施计划。
- 新增 `docs/api.md`：唯一交付文档，只描述接口与契约，不承载实施方案或验收流水。
- 实施并验证后新增 `docs/plans/2026-09-14-frontend-backend-api-contract/result.md`。
- 不修改 `PRD.md`、`README.md`、`docs/architecture.md`、`docs/前端设计.md`、前后端源码、测试、依赖或生成契约。

## 实施步骤与分工

本任务不启用写型子代理；交付物是单一文档，术语、状态表和接口表需要保持一致，并行写入会制造冲突。主代理负责编写和自检。

### 1. 建立文档状态、权威顺序与成熟度图例

在 `docs/api.md` 开头写明：

- 文档性质：接口盘点 + 可供评审的契约草案，不是已生成 OpenAPI，也不替代后端 DTO；
- 冲突处理顺序：实际代码与测试 > PRD/architecture 的正式目标 > 本草案；后端 DTO 生成后，以导出的 OpenAPI/事件 schema 为最终契约；
- 时间基线：`2026-09-14`；
- 成熟度图例：`已实现`、`P0 拟议-未实现`、`P1 未来-未实现`、`P2 探索-未实现`、`历史资料-不可依赖`；
- 明确只有 `GET /api/v1/health` 能标记为“已实现”。

### 2. 固化通用 HTTP 约定与待确认项

文档统一记录以下约定，并用“拟议/待确认”标记尚无正式 DTO 依据的内容：

- Base path 为 `/api/v1`；开发态由 Vite 将 `/api` 代理到 FastAPI，生产态由同域反向代理暴露 REST 与 SSE。
- 资源 ID 为不透明字符串；时间使用带时区的 ISO 8601 字符串；金额、枚举和可空字段不得用字符串冒充数值或空值。
- P0 目标建议 JSON 字段使用 `snake_case`，与 FastAPI/Pydantic 的默认形态一致；当前前端事件草案使用 camelCase，列为必须由后端 DTO 统一裁决的差异项。
- 鉴权采用“由认证身份在服务端推导租户”的原则；客户端不得提交可覆盖租户的 `tenant_id`。具体认证 header、会话和 CSRF 机制未在目标代码中存在，列为待确认，不虚构实现。
- 创建与重试拟使用 `Idempotency-Key` 请求头；同一逻辑请求重试复用同一 key，内容变化必须更换 key。该位置列为待后端确认。
- 业务成功响应拟统一为 `{code: 0, message: "ok", data: <DTO>}`，与当前健康检查保持同一外形；业务错误拟议为 `{error: {code, message, details, retryable, request_id}}`。同时说明当前仓库尚未实现业务错误信封。
- HTTP 状态码仍表达传输/资源语义：`200` 查询或幂等无变化、`202` 已接受异步工作、`400/422` 输入或游标不合法、`401/403` 身份或权限、`404` 资源不存在、`409` 冲突或不可重试、`429` 限流、`500/503` 服务或依赖失败。
- 列表统一使用 `cursor` + `limit`；P0 默认 `limit=20`、最大 `100`，响应含 `items` 与可空 `next_cursor`。

### 3. 记录当前已实现接口

为 `GET /api/v1/health` 写出：

- 方法与路径；
- 无请求参数；
- 当前真实 200 响应示例；
- `degraded`、`db=false`、`redis=false` 的当前含义；
- 依据文件，避免把未来真实探针能力写成已实现。

### 4. 定义 P0 任务资源与生命周期接口

在 `docs/api.md` 的“P0 拟议接口”章节列出并逐接口定义：

| 接口 | 用途与拟定语义 |
| --- | --- |
| `POST /api/v1/tasks` | 创建 1–10 个 ASIN 的异步诊断任务；需 `Idempotency-Key`；返回 `202`、`task_id` 与初始 item 列表；重复提交返回原任务并标记 `reused=true` |
| `GET /api/v1/tasks` | 按状态分页查询当前租户任务；参数为 `status?`、`cursor?`、`limit?` |
| `GET /api/v1/tasks/{task_id}` | 获取任务一致性快照，包括任务状态、item 状态、节点进度摘要和 `last_event_id` |
| `POST /api/v1/tasks/{task_id}/cancel` | 显式取消任务；已终态时保持幂等；SSE 断开不代表取消 |
| `POST /api/v1/tasks/{task_id}/retry` | 仅终态任务的部分/全部 `FAILED` item 可重试；需新 `Idempotency-Key`；拟返回 `202 + new_task_id + parent_task_id` |
| `GET /api/v1/tasks/{task_id}/events` | 建立 SSE；支持 `after` 查询游标，`Last-Event-ID` 优先 |
| `GET /api/v1/tasks/{task_id}/items/{item_id}/report` | 获取单 ASIN 的报告；无有效评论时返回数据不足报告，不生成痛点或建议 |
| `GET /api/v1/tasks/{task_id}/items/{item_id}/evidence` | 按结论/主张和游标查询可反查的 P0 文本证据 |

明确 `POST /tasks` 的拟议请求字段：

- `asins`：字符串数组，1–10 个，去重，P0 大写 10 位 Amazon ASIN；
- `platform`：P0 固定 `amazon`；
- `marketplace`：P0 固定 `US`；
- `window`：P0 拟议 `{"preset":"1m"|"3m"|"6m"}`，与当前新建任务界面一致；绝对起止日期仅在未来需求明确后增加；
- 不把客户端 `project_id` 纳入 P0 必填字段；项目/租户归属由认证上下文推导。如产品确认多项目选择，再单独修订契约。

同时定义以下共享 DTO 和规则：

- 任务生命周期：`QUEUED | RUNNING | COMPLETED | FAILED | CANCELED`；
- 数据质量：`SUFFICIENT | PARTIAL | NO_DATA`，与执行状态分离；
- 财务状态：P0 固定 `NOT_EVALUATED`，P1 才出现 `PASSED | VETOED`；
- 节点状态拟议：`PENDING | RUNNING | SUCCESS | SKIPPED | FAILED | CANCELED`；`NO_DATA` 属于数据质量，不并入节点状态，当前前端草案的差异列为审核项；
- `TaskSnapshot`、`TaskItemSnapshot`、`NodeProgress`、`Page<T>`、`Report`、`Evidence` 的字段表、可空性和示例；
- 批次完成但部分 item 失败时，批次结果必须保留逐 item 原因，不能把部分失败伪装为全部成功。

### 5. 定义 SSE 事件契约与连接行为

在 `docs/api.md` 中给出：

- `Content-Type: text/event-stream`，SSE `id` 为任务内可排序、可去重的事件游标；
- 事件 data 信封：`version`、`id`、`type`、`task_id`、可空 `task_item_id`、`time`、`payload`；
- P0 事件表：
  - `task.status_changed`：批次生命周期变化；
  - `task_item.status_changed`：单 ASIN 生命周期变化；
  - `task_item.node_progress`：节点开始、完成、跳过或失败；
- 心跳使用 SSE 注释帧而不是伪造业务事件；
- `Last-Event-ID` 优先于 `after`；支持历史回放、按 ID 去重和游标失效错误；
- 终态事件后前端停止重连并重新拉取快照/报告；页面卸载关闭连接但不取消后端任务；
- 不定义当前代码和 PRD 都未确认的 `stream.reset` 等事件。

### 6. 定义报告与证据读取边界

在文档中将报告与证据保持为只读查询接口：

- 报告按 `task_id + item_id` 获取，包含 ASIN、数据质量、生成时间、财务状态、痛点聚类、双栏建议、警告和模型/版本元数据；
- 痛点与建议通过稳定的 `evidence_refs` 指向证据，不让前端伪造引用；
- P0 证据仅覆盖评论原文、清洗片段和必要元数据；图片证据为 P1；
- `NO_DATA` 时 `pain_points=[]`、`proposals=[]`，响应中提供明确原因，不返回占位建议；
- 分页使用游标，限制每条证据的上下文长度，避免用未定义字段承载任意 JSON。

### 7. 标注 P1/P2 能力边界与历史接口

- P1：财务确定性评估与 `PASSED/VETOED`、图片视觉证据、工程改款任务书导出；
- P2：回测、跨平台扩展、供应链相关能力；
- 对未在 PRD/architecture 中冻结的 P1/P2 路径，只记录能力、前后端数据需求和新增契约前置条件，不编造具体资源路径或 DTO；
- 单列“历史资料”说明 `docs/前端设计.md` 的 `/api/v1/insight/...` 及其 7 类历史事件，明确其对应已删除实现，当前前端不得按该路径接入；
- 单列“待确认决策”表，至少覆盖字段命名、幂等键位置、认证机制、成功/错误信封、节点状态枚举、重试返回模型、报告/证据是否全部进入 P0、绝对时间窗、多项目/租户语义。

### 8. 自检与收口

- 逐条对照源码、测试和正式文档，确认未把目标接口写成已实现；
- 检查接口路径无重复、状态枚举一致、每个请求字段都有响应或错误语义；
- 实施完成后新增 `result.md`，记录实际文档变化、执行的检查、偏差和未决项。

## 验证与验收

批准后执行以下检查，并在 `result.md` 如实记录真实输出：

```bash
rg -n "^#{1,4} |/api/v1|Last-Event-ID|SSE|待确认|已实现|未实现" docs/api.md
rg -n "insight/task|/api/v1/tasks|task\.status_changed|task_item\.status_changed|node_progress" docs/api.md
git diff --check -- docs/api.md docs/plans/2026-09-14-frontend-backend-api-contract/
git status --short
```

验收条件：

- `docs/api.md` 存在且包含状态图例、通用约定、已实现接口、P0 拟议接口、SSE、查询类接口、P1/P2 边界和待确认项；
- 只有 `GET /api/v1/health` 被标记为已实现；
- 所有 P0 任务接口明确标记为拟议/未实现，并统一使用 `/api/v1/tasks...`；
- 历史 `/api/v1/insight/...` 只出现在历史资料上下文；
- 任务、数据质量、财务、节点四类状态不混用；
- 所有无正式依据的选择均显式标记为“拟议”或“待确认”；
- 不修改任何代码、配置、依赖或生成契约。

## 风险与非目标

- `docs/api.md` 是评审草案，不等同于机器可依赖的 OpenAPI；后端 DTO 落地后必须重新生成并校对，不得直接把草案当成最终 schema。
- PRD 对部分字段只给能力边界，没有字段名、枚举或认证细节；文档会记录推荐方案与确认项，不伪造“已经决定”的事实。
- 本任务不修改后端 Pydantic DTO/路由，不修改前端 API client/类型，不新增 mock，不导出 OpenAPI 或事件 schema，不补充鉴权、数据库、Celery 或 LangGraph 实现。
- 本任务不处理工作区已有的 Playwright/MongoDB crawler 改动，也不提交、推送或创建 PR。

## 审核状态

- 状态：待审核
- 创建日期：2026-09-14
- 批准信息：未批准；初始任务请求不代表对本计划的批准，需用户明确确认后才可实施。
