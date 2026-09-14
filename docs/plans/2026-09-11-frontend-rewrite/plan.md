# 删除旧前端 + 重建 Vue 3 前端（InsightX）

## 审核状态

已批准（含范围变更），执行中。

- 2026-09-11：本计划 v1（仅「删除 + 产出设计文档」）已提交用户审核并等待批准。
- 2026-09-11：用户回复原文 —— 「好，现在删掉frontend文件夹的所有内容，并重新初始化vue3项目，按照frontend的文档开始开发」。
  该指令同时构成两部分信息：(a) 对上一条计划的批准（「好」+ 明确动作指令）；(b) 对本计划范围的实质性扩大 —— 从「只删 + 写设计文档」扩大到「删 + 写设计文档 + 重新初始化 Vue 3 脚手架 + 按该文档实现前端」。
- 本次修订即按 (b) 扩围重写本文件。用户指令本身即为扩围后的授权，故本轮不再追加一次「扩围后计划」的二次确认；此判断记录在 `result.md` 的「计划偏差」一节，供复核。
- 未获批或未授权的事项：commit、push、部署、改后端行为、改历史计划记录。以上本轮均不做。

## 目标

1. 删除 `frontend/` 的全部内容：34 个受版本控制的文件 + ignored 的 `node_modules/`、`dist/`。
2. 在不参考旧前端任何文件的前提下，从零产出新前端设计文档 `docs/前端设计.md`（后续实现与联调的唯一依据）。
3. 依该设计文档重新初始化 Vue 3 + Vite + TypeScript 项目（bun 管理依赖）并实现 P0 前端：任务列表 / 新建任务 / 任务详情（快照 + SSE 实时事件）/ 取消 / 重试 / 错误与告警如实呈现。
4. 让仓库文档与「前端已重建」的事实一致（README.md、AGENTS.md、docs/plans/README.md 最小修订）。

## 口径说明：「不参考任何现有文件」如何界定

- 新前端**不参考**：`frontend/**` 的任何代码、样式、组件、命名、目录结构，以及旧前端计划与结果（`docs/plans/2026-09-10-frontend-ux-workbench/**`、`plan/**`）。
- 新前端**必须依据**：用户需求 + 后端真实接口能力。依据理由：AGENTS.md「No fabrication」与「actual code is the source of truth」——接口契约若凭空设计就无法落地。
- 行为准则：只把后端**已实现**的能力画成可用；未实现的一律显式标注，不做假数据、不画假图表。

## 当前事实（含依据）

### 删除面与影响面

- `frontend/` 共 34 个受控文件（命令依据：`git ls-files frontend | wc -l` = 34）；本地另有 ignored 的 `frontend/node_modules`、`frontend/dist`。
- 代码级引用旧前端的只有后端 CORS 默认白名单 `http://localhost:5173`（`backend/app/config.py:30`、`docker-compose.yml:44`、`backend/tests/test_config.py:15,20,23,29`）。新前端沿用 5173，**后端零改动**。
- 文档层面删除后会失真或断链的位置（本轮只做最小修订，历史引用不动）：
  - `README.md:7,11-13,19,21,26-34,46`
  - `AGENTS.md:10,13,16`
  - `docs/技术方案.md`（多个 `../frontend/...` 死链）、`docs/api.md`、`docs/PRD.md`（本轮不改，记入 result.md 遗留）

### 新前端必须面对的后端真实能力（代码为准）

- 接口前缀 `/api/v1`（`backend/app/main.py:49-51`），另有 `/health`（`main.py:45-47`）。
- `POST /insight/task` 202，**必须带 `Idempotency-Key` 头**（`backend/app/api/routes/tasks.py:49-57`）；body `{project_id, asins[1–10,去重,^[A-Z0-9]{10}$], platform, marketplace, window?}`（`tasks.py:30-39,56-57`；`backend/app/api/schemas.py:53-58`）；响应 `{task_id,status,phase,reused,window,items[{item_id,asin,status}],links{self,events}}`（`schemas.py:110-128`）。
- `GET /insight/tasks?project_id&status&cursor&limit(≤100)` → `{items:[{task_id,project_id,created_at,status,asins,item_counts,warnings_count}],next_cursor}`（`tasks.py:87-118`；`schemas.py:184-196`；`backend/app/services/tasks.py:519-572`）。
- `GET /insight/task/{task_id}` 一致性快照（`tasks.py:121-133`；`services/tasks.py:428-516`；`schemas.py:170-181`）：`task_id/project_id/phase/status/created_at/completed_at/cancel_requested_at/last_event_id(string)/item_counts{total,queued,running,completed,failed,canceled}/items[]/warnings[{code,message,item_id}]`。
  - item：`item_id/asin/status/attempt/current_node/nodes[]/progress{completed_nodes,total_nodes,processed_reviews,total_reviews}/report_id/error`（`schemas.py:152-161`）。
  - node：`key/status/duration_ms/started_at/completed_at/output_summary/skip_reason`（`schemas.py:135-142`）。
  - 关键实现细节：`nodes[]` **只包含已有执行记录的节点**（`services/tasks.py:399-425,473-475`），未开始的节点不会出现；`progress.total_nodes` 固定 7（`services/tasks.py:29,496`）；`processed_reviews` 恒为 0、`total_reviews` 恒为 null（`services/tasks.py:497-498`）。
- `POST /insight/task/{task_id}/cancel`：202；若任务已终态则返回 200 且不改状态（`tasks.py:136-154`）。响应 `{task_id,status,cancel_requested_at}`（`schemas.py:199-201`）。
- `POST /insight/task/{task_id}/retry` 202，需 `Idempotency-Key` + `{item_ids}`；仅终态任务的 FAILED 分项可重试，否则 409 `ITEM_NOT_RETRYABLE`（`tasks.py:157-192`）。
- SSE `GET /insight/task/{task_id}/events?after=`（`backend/app/api/routes/events.py:30-57`）：`Last-Event-ID` 头优先于 `after`（`events.py:46-50`）；首行 `retry: 3000`（`events.py:81`；`services/events.py:16`）；15s 无事件发注释心跳（`events.py:25-27,104-106`）；单连接 120s 上限后自然断开（`events.py:25,107-108`）→ 客户端必须自行重连；终态且追平 max_seq 后发 `event: stream.end`，data 为 `{last_event_id,status}`（`events.py:98-103`；`services/events.py:71-74`）；非法游标 422 `INVALID_EVENT_CURSOR`（`events.py:45-52`）。
- 事件帧：`id:` 行 = seq（`services/events.py:20-34`），data 为 `{schema_version,task_id,seq,item_id,attempt,occurred_at,payload}`（`services/events.py:52-68`）。
- **实际会发出的事件名**：`node.updated`（payload `{node,status,duration_ms,skip_reason}`，`backend/app/worker/graph.py:164-189`）、`item.updated`（payload `{status}` / `{status,error}`，`graph.py:367-375,417-425,468-476`）、`task.completed|task.failed|task.canceled`（payload `{status,item_counts}`，`graph.py:511-522`）、`warning`（快照聚合 `TaskEvent.type=="warning"`，`services/tasks.py:456-459,505-514`）。**未实现**：`task.updated`、`stream.reset`（`docs/api.md` 中的定义为草案）。
- 错误信封统一 `{error:{code,message,details,retryable,request_id}}`（`backend/app/api/errors.py:10-42`）；FastAPI 请求校验失败也走该信封（`backend/app/main.py:25-35`）。
- 尚不可用，前端必须如实呈现：报告/证据接口 501（`backend/app/api/routes/reports.py:11-20`）；worker 节点执行 `NotImplementedError`（`backend/app/worker/nodes.py:16`）→ 真实提交的任务会走失败路径；无真实身份，dev 用服务端预置 tenant、prod 直接 401（`backend/app/api/deps.py:10-14`）→ 前端不做登录页/令牌存储。
- 开发预置身份（`backend/app/config.py:8-10,33-34`）：tenant `0318c9fa-aeca-505c-bd6b-8db54d33d57f`、project `1fce1ed8-c9f6-5b1c-9e95-7649b30e3904`（本计划用 `python3 -c uuid.uuid5(...)` 复算一致）；需 `python -m app.db.seed_dev` 播种（`backend/app/db/seed_dev.py:13-31`）。
- ASIN 规范化：大写 + 去重 + 排序（`services/tasks.py:68-69`）；缺省时间窗 = 站点当前日向前 6 个日历月（`services/tasks.py:80-93`）。

### 新前端设计要点（`docs/前端设计.md` 的骨架）

1. 设计原则与边界：诚实渲染优先；快照是最终状态来源；最小闭环，不做无关抽象。
2. 技术选型：Vue 3 + Vite + TypeScript + bun + `vue-router`；不引入 UI 组件库 / i18n 库 / 图表库 / Pinia。
3. 信息架构（3 条路由）：`/` 任务列表、`/tasks/new` 新建任务、`/tasks/:taskId` 任务详情。
4. 数据访问层：`api/client.ts`（错误信封解析 + request_id 展示）、`api/tasks.ts`（6 个接口）、`api/sse.ts`（受控 EventSource）、手写类型对齐快照。
5. SSE 客户端行为、6. 状态与视图模型、7. 操作与幂等、8. 组件清单、9. 视觉与文案、10. 开发与联调（Vite `server.proxy` 将 `/api` 代理到 `http://localhost:8000`，浏览器视角同源，SSE 直通，CORS 不动）、11. 不造假清单、12. 分阶段与验收。
   详细内容以 `docs/前端设计.md` 为准（实现必须与之一致）。

## 变更范围

删除：

- `frontend/` 整个目录（受控 34 文件 + ignored `node_modules/`、`dist/`）

新增：

- `frontend/`（新脚手架与实现：Vue 3 + Vite + TS + vue-router，bun 管理）
- `docs/前端设计.md`
- `docs/plans/2026-09-11-frontend-rewrite/result.md`（实施结束后生成）

修改：

- `README.md`：技术架构树（9–15 行）、技术栈表前端行（19 行）、快速开始前端小节（26–34 行）—— 按新前端事实重写
- `AGENTS.md`：Project Facts 中 `frontend/` 条目（10 行）、前端命令（13 行）、`04-技术方案.md` 失效文件名（16 行）
- `docs/plans/README.md`：任务索引表新增本任务一行

明确不动：`backend/**`、`docs/api.md`、`docs/技术方案.md`、`docs/PRD.md`、`plan/**`、`docs/plans/2026-09-10-frontend-ux-workbench/**`（含工作区已存在的未提交改动 ` D docs/plans/2026-09-10-frontend-ux-workbench/result.md`，保持原样）。

## 实施步骤

1. ✅ 新建任务目录与 `plan.md`。
2. 修订本文件，记录用户批准与扩围指令（本步）。
3. 撰写 `docs/前端设计.md`（12 节，后端能力断言附 `文件:行号`）。
4. 删除 `frontend/`：`rm -rf frontend`（一次性覆盖受控文件与 ignored 目录）。
5. 重新初始化脚手架：`bun create vue@latest frontend`（TS + Router；JSX/Pinia/Vitest/E2E/ESLint 一律否）。网络受限时需要用户级授权；失败则记录并停在该步。
6. 按设计文档实现：
   - F0 脚手架 + 路由 + API/SSE 客户端 + 设计令牌（CSS 变量）
   - F1 任务列表（cursor 分页、状态/进度）+ 新建任务（ASIN 校验、幂等键、409 提示）
   - F2 任务详情（快照 + SSE 实时事件、节点/分项进度、告警）
   - F3 取消 / 重试 / 错误与 request_id 展示
7. 修订 `README.md`、`AGENTS.md`、`docs/plans/README.md`。
8. 执行「验证与验收」，随后生成 `result.md`。

## 验证与验收

1. 删除与重建：`frontend/package.json`、`frontend/src/main.ts` 为新文件（`git status` 显示旧前端文件删除、新前端文件未跟踪）；`test -d frontend/node_modules` 为真（依赖已装）。
2. 类型与构建：`cd frontend && bun run build`（内含 `vue-tsc` 类型检查）**真实通过**，输出 dist 产物。
3. 结构自检：`frontend/src` 下不出现旧前端的任何文件名/组件名（`AgentWorkflowTab`、`DualColumnProposalsTab`、`FinancialVetoTab`、`VocClusterTab`、`i18n/locales`、`mock/data.ts` 等）；不引入 UI 组件库/图表库/i18n 库/Pinia。
4. 契约自检：前端调用的每个接口路径、方法、请求头、字段名与「当前事实」小节的 `backend/...:行号` 依据一致；`git grep` 校验无编造的接口路径（如 `/api/v1/insight/report`、`task.updated`、`stream.reset`）。
5. 文档自检：`docs/前端设计.md` 每条后端能力断言均可回溯到具体 `backend/...:行号`。
6. 不运行后端测试（本轮无后端改动）；如尝试 dev 联调需先播种数据库并起后端，未见成效则如实记为「未执行」。
7. 验收条件：`frontend/` 为按设计文档实现的新工程且 `bun run build` 通过；`docs/前端设计.md` 成文；README/AGENTS 不再指向旧前端结构；无 commit / push。

## 风险与非目标

风险：

- 删除不可逆（只能靠 git 历史取回）；旧品牌素材 `frontend/src/assets/Product_logo.webp` 随目录删除，用户未要求保留。
- 新前端代码量较大（约 30 个文件），本轮一次交付 F0–F3；若构建或类型检查不通过，按「失败不得伪装完成」如实记录（可在获批范围内修到通过）。
- 后端 worker 未实现：真实任务会走失败路径，UI 只能呈现失败/告警，无法演示完成态（这是后端事实，不是前端缺陷）。
- 网络受限可能导致脚手架初始化失败；需用户级授权，被拒则停在第 5 步并如实记录。

非目标（本轮不做）：

- 不改后端行为、接口、CORS（新前端沿用 5173 与 `/api` 代理）。
- 不做登录页 / 令牌存储（后端 P0 无真实身份）；不做报告页、证据页（后端 501）。
- 不做营销首页、图表可视化、多语言、暗色主题切换。
- 不改 `docs/api.md`（草案与实现不一致）、`docs/技术方案.md`、`docs/PRD.md` 中的历史前端引用（记入 result.md 遗留）。
- 不改历史记录：`plan/**`、`docs/plans/2026-09-10-frontend-ux-workbench/**`。
- 不 commit、不 push、不部署。
