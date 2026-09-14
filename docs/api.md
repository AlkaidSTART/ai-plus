# InsightX 前后端接口文档（契约草案）

> 文档日期：2026-09-14
> 文档状态：接口盘点 + P0 契约草案，尚未生成正式 OpenAPI
> 适用范围：Vue 3 前端与 FastAPI 后端之间的 HTTP REST + SSE 接口

## 1. 阅读说明

### 1.1 文档性质

本文档用于统一前后端对接口、DTO、状态、错误和 SSE 行为的理解。它不是已生成的 `contracts/openapi.json`，也不能替代后端 Pydantic DTO；后端契约生成后，应以 `contracts/openapi.json`、`contracts/task-events.schema.json` 和生成的前端客户端为准。

冲突处理顺序：

1. 当前可运行代码、测试和导出契约；
2. `PRD.md` 与 `docs/architecture.md` 的正式目标；
3. 本文档中的拟议方案；
4. `docs/前端设计.md` 中的历史接口快照，仅用于追溯，不得作为当前接入依据。

### 1.2 成熟度图例

| 标记 | 含义 |
| --- | --- |
| 已实现 | 当前仓库存在可运行代码或测试证据 |
| P0 拟议-未实现 | 已进入当前目标范围，但后端 DTO、路由和前端客户端尚未落地 |
| P1 未来-未实现 | 已出现在产品规划中，接口与字段尚未冻结 |
| P2 探索-未实现 | 仅有能力方向，尚不足以定义稳定接口 |
| 历史资料-不可依赖 | 来自已删除实现或旧设计，不能用于当前前后端联调 |

### 1.3 当前结论

截至本文档日期，当前仓库**唯一已实现的业务 HTTP 接口**是：

- `GET /api/v1/health`

`POST /api/v1/tasks` 等任务接口来自 PRD、架构文档和前端草案，目前均为 P0 拟议接口，尚未在后端实现。本文档中标注为“拟议”的字段名、枚举、状态码和 header 均需在后端 DTO 落地时确认。

## 2. 通用 HTTP 约定

### 2.1 Base URL 与开发代理

| 项目 | 约定 |
| --- | --- |
| API 版本前缀 | `/api/v1` |
| 开发环境 | 前端仍使用 `/api/v1/...`；Vite 将 `/api` 代理到 FastAPI |
| 生产环境 | 推荐同域反向代理，同时转发静态资源、REST 和 SSE |
| REST Content-Type | 请求和 JSON 响应使用 `application/json; charset=utf-8` |
| SSE Content-Type | 响应使用 `text/event-stream` |

### 2.2 JSON 字段命名

P0 推荐统一使用 `snake_case`，以匹配 FastAPI/Pydantic 的常见默认输出，并避免前端草案和生成类型之间反复转换。

当前 `frontend/src/api/events.types.ts` 使用 `taskId`、`taskItemId` 等 camelCase 字段，属于未完成草案；在后端事件 DTO 确定前，不得把该草案视为正式 wire format。

### 2.3 成功响应信封

健康检查已实现 `{code, message, data}` 外形。P0 业务接口拟沿用相同外形：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

约定：

- `code`：项目内业务结果码；成功固定为 `0`。
- `message`：面向开发者的结果说明；前端不得依赖其精确文案做分支。
- `data`：资源 DTO、列表或操作结果；无额外内容时使用 `null`。
- HTTP 状态码仍表达真实语义，不能用 HTTP 200 包裹失败。
- SSE 不使用该 JSON 信封，事件格式见第 6 节。

该成功信封目前只有健康检查有实现证据，其他接口仍在待确认列表。

### 2.4 错误响应信封

P0 拟统一为：

```json
{
  "error": {
    "code": "ITEM_NOT_RETRYABLE",
    "message": "Only failed items can be retried.",
    "details": null,
    "retryable": false,
    "request_id": "req_01J..."
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `error.code` | string | 是 | 稳定业务错误码，前端按该字段分支 |
| `error.message` | string | 是 | 错误说明；不应作为稳定判断条件 |
| `error.details` | object/array/null | 是 | 字段级校验信息或错误上下文；结构由错误码定义 |
| `error.retryable` | boolean | 是 | 当前请求是否适合按相同语义重试 |
| `error.request_id` | string | 是 | 用于日志关联和问题排查 |

当前后端尚未实现业务错误信封或统一异常处理器。

### 2.5 认证、租户与授权

目标架构要求 API 从已认证身份核验租户，不能信任客户端自报的授权信息。

- P0 任务、报告、证据和 SSE 接口均要求已认证身份。正式架构方向是服务端会话配合 HttpOnly/Secure/SameSite cookie；浏览器不持久化 bearer token，写操作必须执行 CSRF 防护。
- 客户端不得提交可覆盖服务端租户归属的 `tenant_id`；`tenant_id` 如需作为选择器，也必须由服务端核验成员关系。
- 具体登录/退出接口、会话生命周期、CSRF token 传递 header、Cookie 属性细节，以及无权访问时返回 `403` 还是 `404`，仍待后端契约确认。
- 未认证返回 `401` 是本草案的推荐默认，但当前仓库没有生产鉴权实现，开发期不得把一个临时 header 写成正式契约。

### 2.6 标识、时间与分页

| 项目 | 约定 |
| --- | --- |
| ID | `task_id`、`item_id`、`evidence_id` 等使用不透明字符串，客户端不得解析内部结构 |
| 时间 | 带时区的 ISO 8601 字符串；统一输出 UTC，例如 `2026-09-14T08:30:00Z` |
| 分页参数 | `cursor` 可为空，`limit` 拟定默认 `20`、最大 `100` |
| 分页响应 | 统一使用第 5.2 节 `Page<T>` |
| 排序 | 列表默认按 `created_at` 倒序；后端需补充稳定次级排序，避免翻页重复或遗漏 |

### 2.7 幂等

创建任务和重试任务拟要求 `Idempotency-Key` 请求头。该 header 名尚未由后端 DTO 最终确认。

- 同一逻辑请求因网络错误重试时，必须复用相同 key。
- 请求内容变化时必须生成新 key。
- 相同 key 且请求内容相同，返回原资源并设置 `reused=true`。
- 相同 key 但请求内容不同，返回 `409 IDEMPOTENCY_CONFLICT`。
- 仅依赖前端按钮禁用不能提供幂等保证。

## 3. 已实现接口

### 3.1 获取服务健康状态

| 项目 | 内容 |
| --- | --- |
| 成熟度 | 已实现 |
| 方法 | `GET` |
| 路径 | `/api/v1/health` |
| 鉴权 | 当前实现无鉴权 |
| 请求参数 | 无 |

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "degraded",
    "version": "0.1.0",
    "db": false,
    "redis": false
  }
}
```

当前语义：

- `status="degraded"`：当前健康检查没有实现可用 DB/Redis 探针。
- `db=false`：当前实现固定返回 false，不代表数据库已配置或不可用。
- `redis=false`：当前实现固定返回 false，不代表 Redis 已配置或不可用。

证据：`backend/src/insightx/api/v1/health.py`、`backend/tests/test_health.py`。

## 4. P0 接口总览

| 成熟度 | 方法 | 路径 | 用途 |
| --- | --- | --- | --- |
| 已实现 | GET | `/api/v1/health` | 服务健康检查 |
| P0 拟议-未实现 | POST | `/api/v1/tasks` | 创建异步诊断任务 |
| P0 拟议-未实现 | GET | `/api/v1/tasks` | 分页查询当前身份可见任务 |
| P0 拟议-未实现 | GET | `/api/v1/tasks/{task_id}` | 获取任务一致性快照 |
| P0 拟议-未实现 | POST | `/api/v1/tasks/{task_id}/cancel` | 显式请求取消任务 |
| P0 拟议-未实现 | POST | `/api/v1/tasks/{task_id}/retry` | 重试失败的任务项 |
| P0 拟议-未实现 | GET | `/api/v1/tasks/{task_id}/events` | 订阅任务 SSE 事件与历史回放 |
| P0 拟议-未实现 | GET | `/api/v1/tasks/{task_id}/items/{item_id}/report` | 获取单 ASIN 报告 |
| P0 拟议-未实现 | GET | `/api/v1/tasks/{task_id}/items/{item_id}/evidence` | 查询报告引用的文本证据 |

## 5. P0 共享 DTO 与状态

### 5.1 状态枚举

四类状态不能混用。

#### 任务与任务项生命周期

```text
QUEUED | RUNNING | COMPLETED | FAILED | CANCELED
```

| 状态 | 含义 |
| --- | --- |
| `QUEUED` | 已持久化并等待派发/执行 |
| `RUNNING` | 至少一个有效执行尝试正在处理 |
| `COMPLETED` | 该任务或工作单元已完成；批次内其他 item 仍可能失败 |
| `FAILED` | 执行失败；必须提供原因 |
| `CANCELED` | 显式取消已生效，或在执行边界停止 |

任务批次为 `COMPLETED` 时仍必须保留 item 的失败、取消和数据不足信息，不能用批次状态掩盖部分失败。

#### 报告数据质量

```text
SUFFICIENT | PARTIAL | NO_DATA
```

- `SUFFICIENT`：样本满足当前报告规则。
- `PARTIAL`：只能基于部分有效数据生成结论，必须说明覆盖缺口。
- `NO_DATA`：没有有效评论；不得生成痛点或建议。

#### 财务状态

```text
NOT_EVALUATED | PASSED | VETOED
```

P0 固定为 `NOT_EVALUATED`。`PASSED` 与 `VETOED` 属于 P1，不能由任务完成状态推导。

#### 节点状态

P0 拟议：

```text
PENDING | RUNNING | SUCCESS | SKIPPED | FAILED | CANCELED
```

说明：

- `NO_DATA` 是报告数据质量，不是节点执行状态，推荐不并入节点状态。
- 当前前端 `frontend/src/types/domain.ts` 使用 `SUCCESS` 并额外包含 `NO_DATA`，与本文档推荐存在差异，待后端事件 DTO 最终确认。
- 节点是否存在、节点顺序与名称由后端实际执行记录决定；前端不得自行编造固定七步进度。

### 5.2 `Page<T>`

所有游标分页接口的 `data` 使用同一泛型外形：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `items` | `T[]` | 是 | 当前页数据；无结果时为空数组，不返回 `null` |
| `next_cursor` | string/null | 是 | 下一页游标；没有下一页时为 `null` |

`next_cursor` 是不透明值，客户端不得解析或自行拼接。`T` 由具体接口决定，例如任务列表使用 `TaskListItem`，证据列表使用 `Evidence`。

### 5.3 `TaskCreateRequest`

```json
{
  "asins": ["B0EXAMPLE1", "B0EXAMPLE2"],
  "platform": "amazon",
  "marketplace": "US",
  "window": {
    "preset": "6m"
  }
}
```

| 字段 | 类型 | 必填 | P0 约束 |
| --- | --- | --- | --- |
| `asins` | string[] | 是 | 1–10 个；去重；大写 10 位 `^[A-Z0-9]{10}$` |
| `platform` | string | 是 | P0 固定 `amazon` |
| `marketplace` | string | 是 | P0 固定 `US` |
| `window.preset` | string | 是 | P0 拟议 `1m | 3m | 6m`，分别表示近 1/3/6 个月 |

客户端不提交 `tenant_id`。当前界面没有多项目选择，P0 请求也不把 `project_id` 设为必填；若产品确认多项目语义，需要重新修订契约。

### 5.4 `TaskCreatedResponse`

```json
{
  "task_id": "tsk_01J...",
  "status": "QUEUED",
  "reused": false,
  "parent_task_id": null,
  "created_at": "2026-09-14T08:30:00Z",
  "items": [
    {
      "item_id": "itm_01J...",
      "asin": "B0EXAMPLE1",
      "status": "QUEUED"
    }
  ]
}
```

### 5.5 `TaskListItem`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务 ID |
| `status` | enum | 任务生命周期 |
| `platform` | string | P0 为 `amazon` |
| `marketplace` | string | P0 为 `US` |
| `window` | object | 与创建请求相同的规范化时间窗 |
| `created_at` | string | ISO 8601 UTC |
| `updated_at` | string | ISO 8601 UTC |
| `total_items` | integer | item 总数，1–10 |
| `completed_items` | integer | 完成 item 数 |
| `failed_items` | integer | 失败 item 数 |
| `canceled_items` | integer | 取消 item 数 |
| `last_event_id` | string/null | 可用于恢复 SSE 游标 |

### 5.6 `TaskSnapshot`

`TaskSnapshot` 在 `TaskListItem` 基础上增加：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `parent_task_id` | string/null | 重试产生的新任务指向原任务 |
| `cancel_requested_at` | string/null | 已收到取消请求的时间，不代表已完成取消 |
| `finished_at` | string/null | 终态时间 |
| `items` | `TaskItemSnapshot[]` | 每个 ASIN 的真实状态 |
| `progress` | object | 批次级聚合进度，不代替 item 状态 |

### 5.7 `TaskItemSnapshot`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `item_id` | string | 工作单元 ID |
| `asin` | string | 规范化 ASIN |
| `status` | enum | item 生命周期 |
| `current_node` | string/null | 当前或最后节点 ID |
| `attempt` | integer | 当前有效尝试编号 |
| `data_quality` | enum/null | 报告数据质量；未评估时为空 |
| `sample_metrics` | `SampleMetrics/null` | 采集后统计的实际样本指标；尚未采集时为空 |
| `nodes` | `NodeProgress[]` | 已产生真实执行记录的节点 |
| `error` | object/null | `{code,message,retryable}`；无错误时为空 |
| `report_available` | boolean | 是否已有可读取报告 |

#### `SampleMetrics`

`SampleMetrics` 用于区分采集数量、清洗后有效样本和统计口径，不能把目标样本量当成实际样本量。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `raw_review_count` | integer | 采集到的原始评论数量 |
| `valid_review_count` | integer | 清洗和去重后的有效样本数量 |
| `excluded_review_count` | integer | 因短评、重复、语言/字段缺失等被排除的数量 |
| `average_rating` | number/null | 有效样本平均星级；无有效样本时为空 |
| `negative_review_ratio` | number/null | 有效样本中的差评占比，范围 `[0,1]`；无有效样本时为空 |
| `pain_point_count_with_evidence` | integer | 至少有可回查证据支持的痛点数量 |
| `window` | object | 实际统计时间窗，需包含起止时间与站点时区 |
| `methodology` | string | 样本纳入/排除、星级和差评口径的简明说明 |
| `missing_reasons` | string[] | 字段缺失、覆盖不足或采集失败造成的数据质量说明 |

### 5.8 `NodeProgress`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `node_id` | string | 稳定节点 ID |
| `node_name` | string | 展示名；未知 ID 时前端可原样显示 |
| `status` | enum | 节点状态 |
| `started_at` | string/null | 开始时间 |
| `finished_at` | string/null | 结束时间 |
| `duration_ms` | integer/null | 实际耗时 |
| `skip_reason` | string/null | `SKIPPED` 时必填 |
| `error` | object/null | 失败原因与是否可重试 |

### 5.9 `Report`

```json
{
  "report_id": "rpt_01J...",
  "task_id": "tsk_01J...",
  "item_id": "itm_01J...",
  "asin": "B0EXAMPLE1",
  "data_quality": "SUFFICIENT",
  "sample_metrics": {
    "raw_review_count": 480,
    "valid_review_count": 436,
    "excluded_review_count": 44,
    "average_rating": 3.7,
    "negative_review_ratio": 0.31,
    "pain_point_count_with_evidence": 3,
    "window": {},
    "methodology": "…",
    "missing_reasons": []
  },
  "generated_at": "2026-09-14T08:31:00Z",
  "financial_state": "NOT_EVALUATED",
  "pain_points": [],
  "proposals": [],
  "warnings": [],
  "model_metadata": {}
}
```

`pain_points[]` 拟议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `pain_point_id` | string | 稳定结论 ID |
| `label` | string | 痛点标签 |
| `actual_frequency` | integer | 在有效样本中的实际支持频次 |
| `frequency_methodology` | string | 频次统计口径，例如按评论、清洗片段或聚类归属计数 |
| `severity_score` | integer | PRD 要求的严重度评分，范围 `1–5` |
| `severity_rationale` | string | 严重度评分依据，不得只给分数 |
| `severity_level` | string | UI 徽章等级 `CRITICAL` / `MODERATE` / `MINOR`，不能替代 `severity_score` |
| `summary` | string | 基于证据的摘要 |
| `evidence_refs` | string[] | 支持该结论的可查询证据 ID，不得为空 |
| `typical_evidence_refs` | string[] | 从 `evidence_refs` 中选出的典型原声引用，不得为空 |

`proposals[]` 拟议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `proposal_id` | string | 稳定建议 ID |
| `column` | enum | `PRODUCT_OPTIMIZATION` / `PACKAGING_FULFILLMENT_OPTIMIZATION`，分别对应产品本体和包装履约两栏 |
| `title` | string | 改动方向标题 |
| `change_description` | string | 具体改动描述 |
| `pain_point_ids` | string[] | 该建议响应的痛点结论 ID，至少一项 |
| `snapshot_ref` | string | 同租户、同任务输入快照的稳定引用 |
| `evidence_refs` | string[] | 同租户、同任务快照中支持该建议的评论或片段 ID，不得为空 |

每条有效建议必须同时具备所属栏目、至少一个 `pain_point_ids`、同任务 `snapshot_ref` 和非空 `evidence_refs`。无证据的结论不能作为有效建议返回。

`warnings[]` 拟议字段：`{code,message,related_item_id?,evidence_refs?}`。

`model_metadata` 用于记录实际调用供应商、模型、Embedding 维度、prompt 版本等来源信息；字段结构尚未冻结，不得用猜测值填充。没有有效评论时，`data_quality="NO_DATA"`，`sample_metrics.valid_review_count=0`，`pain_points=[]`，`proposals=[]`，并给出明确 warning。

### 5.10 `Evidence`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `evidence_id` | string | 证据 ID |
| `source_type` | string | P0：`REVIEW_TEXT | CLEANED_FRAGMENT | METADATA` |
| `source_ref` | string | 内部稳定来源引用 |
| `excerpt` | string | 可展示文本片段 |
| `source_url` | string/null | 可获得时提供原始地址 |
| `published_at` | string/null | 来源发布时间 |
| `metadata` | object | 受控、有限长度的来源元数据 |
| `provenance` | object | 快照、清洗、模型或规则版本等追溯信息 |

## 6. P0 接口详细定义

### 6.1 创建任务

| 项目 | 内容 |
| --- | --- |
| 成熟度 | P0 拟议-未实现 |
| 方法 | `POST` |
| 路径 | `/api/v1/tasks` |
| 鉴权 | 需要 |
| 幂等 header | `Idempotency-Key`（待确认） |
| 请求 DTO | `TaskCreateRequest` |
| 成功状态 | `202 Accepted` |
| 成功 DTO | `TaskCreatedResponse` |

语义：

- API 在服务端校验身份、租户、ASIN、站点和时间窗。
- API 在同一 PostgreSQL 事务中持久化 task、task_items 与 outbox；返回成功仅表示任务已接受，不表示分析完成。
- 相同幂等键和相同请求返回原任务，`reused=true`。
- 相同幂等键但请求不同返回 `409 IDEMPOTENCY_CONFLICT`。

主要错误：`401 UNAUTHORIZED`、`422 VALIDATION_ERROR`、`409 IDEMPOTENCY_CONFLICT`、`429 RATE_LIMITED`、`503 SERVICE_UNAVAILABLE`。

### 6.2 查询任务列表

| 项目 | 内容 |
| --- | --- |
| 成熟度 | P0 拟议-未实现 |
| 方法 | `GET` |
| 路径 | `/api/v1/tasks` |
| 鉴权 | 需要 |
| 查询参数 | `status?`、`cursor?`、`limit?` |

`status` 只接受任务生命周期枚举之一。返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [],
    "next_cursor": null
  }
}
```

该接口的 `data` 为 `Page<TaskListItem>`。服务端只返回当前认证身份有权访问的任务；客户端传入其他租户标识不得改变范围。

### 6.3 获取任务快照

| 项目 | 内容 |
| --- | --- |
| 成熟度 | P0 拟议-未实现 |
| 方法 | `GET` |
| 路径 | `/api/v1/tasks/{task_id}` |
| 鉴权 | 需要 |
| 成功状态 | `200 OK` |
| 成功 DTO | `TaskSnapshot` |

该接口返回适用于恢复页面和刷新状态的接近一致性快照。`last_event_id` 用于页面恢复后向 SSE 接口传 `after`，不能假定浏览器会跨页面记住事件游标。

主要错误：`401`、`403` 或 `404`、`500`。

### 6.4 取消任务

| 项目 | 内容 |
| --- | --- |
| 成熟度 | P0 拟议-未实现 |
| 方法 | `POST` |
| 路径 | `/api/v1/tasks/{task_id}/cancel` |
| 鉴权 | 需要 |
| 请求 body | 无 |
| 已接受 | `202 Accepted` |
| 已终态无变化 | `200 OK` |

语义：

- 关闭 SSE 或浏览器窗口不会取消任务。
- 取消请求在处理节点的安全边界生效。
- 首次接受取消并非立即终态；响应应包含当前的取消请求状态或快照。
- 对同一任务重复取消不产生第二个取消动作。
- 已 `COMPLETED`、`FAILED` 或 `CANCELED` 的任务保持原终态，除非产品明确要求其他规则。

### 6.5 重试失败任务项

| 项目 | 内容 |
| --- | --- |
| 成熟度 | P0 拟议-未实现 |
| 方法 | `POST` |
| 路径 | `/api/v1/tasks/{task_id}/retry` |
| 鉴权 | 需要 |
| 幂等 header | `Idempotency-Key`（待确认） |
| 请求 body | `{"item_ids": ["itm_01J..."]}` |
| 成功状态 | `202 Accepted` |
| 成功 DTO | `TaskCreatedResponse`，其中 `parent_task_id` 为原任务 |

约束：

- `item_ids` 至少包含一个 item，且必须属于原任务。
- 仅终态任务中的 `FAILED` item 可重试。
- 重试创建新任务，不覆盖历史尝试和原报告。
- 非失败、跨任务或未知 item 返回 `409 ITEM_NOT_RETRYABLE` 或 `422 VALIDATION_ERROR`。
- 前端应为一次重试操作生成一个新的幂等键，并在网络重试中复用。

### 6.6 获取单 ASIN 报告

| 项目 | 内容 |
| --- | --- |
| 成熟度 | P0 拟议-未实现 |
| 方法 | `GET` |
| 路径 | `/api/v1/tasks/{task_id}/items/{item_id}/report` |
| 鉴权 | 需要 |
| 成功状态 | `200 OK` |
| 成功 DTO | `Report` |

规则：

- 报告必须属于指定任务与 item。
- 报告未完成时返回 `409 REPORT_NOT_READY`，`retryable=true`；前端应继续使用快照与 SSE，不应构造空报告。
- `NO_DATA` 报告是合法结果，返回数据不足说明和空痛点/建议数组。
- P0 `financial_state` 恒为 `NOT_EVALUATED`。
- 报告中的引用必须由 `evidence_refs` 指向可查询证据。

### 6.7 查询证据

| 项目 | 内容 |
| --- | --- |
| 成熟度 | P0 拟议-未实现 |
| 方法 | `GET` |
| 路径 | `/api/v1/tasks/{task_id}/items/{item_id}/evidence` |
| 鉴权 | 需要 |
| 查询参数 | `claim_id?`、`source_type?`、`cursor?`、`limit?` |
| 成功 DTO | `Page<Evidence>` |

规则：

- `claim_id` 可取报告中的 `pain_point_id` 或 `proposal_id`；为空时返回该 item 的可访问证据分页。
- `source_type` 只过滤本文档已声明类型。
- 证据必须属于指定任务和 item；跨租户或跨 item 查询返回 404/403。
- P0 不要求图片证据；图片引用、缺陷区域和视觉归因属于 P1。

## 7. SSE 接口

### 7.1 建立事件流

| 项目 | 内容 |
| --- | --- |
| 成熟度 | P0 拟议-未实现 |
| 方法 | `GET` |
| 路径 | `/api/v1/tasks/{task_id}/events` |
| 鉴权 | 需要 |
| Accept | `text/event-stream` |
| 查询参数 | `after?`：页面首次恢复或显式回放游标 |
| header | `Last-Event-ID`：断线自动重连时优先于 `after` |
| 响应 | `text/event-stream`，持续连接直到终态追平或客户端断开 |

首帧拟议发送：

```text
retry: 3000
```

无业务事件时使用 SSE 注释心跳，不伪造业务事件：

```text
: keep-alive 2026-09-14T08:30:00Z
```

### 7.2 事件格式

SSE `id` 与 data 中的 `id` 相同，均为任务内有序、可去重的不透明游标字符串：

```text
id: 42
event: task_item.node_progress
data: {"version":1,"id":"42","type":"task_item.node_progress","task_id":"tsk_01J...","task_item_id":"itm_01J...","time":"2026-09-14T08:30:00Z","payload":{"node_id":"ingestion","node_name":"collection","status":"RUNNING","duration_ms":null,"skip_reason":null,"error":null}}

```

事件信封：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `version` | integer | 是 | P0 草案为 `1` |
| `id` | string | 是 | 任务内有序事件 ID，同时用于 SSE `id:` |
| `type` | string | 是 | 事件类型 |
| `task_id` | string | 是 | 任务 ID |
| `task_item_id` | string/null | 是 | 批次事件为 null |
| `time` | string | 是 | ISO 8601 UTC |
| `payload` | object | 是 | 类型对应 payload |

### 7.3 P0 事件表

| 事件 | 发出时机 | payload |
| --- | --- | --- |
| `task.status_changed` | 批次进入新生命周期状态 | `{status,reason?}` |
| `task_item.status_changed` | 单 ASIN 工作单元进入新生命周期状态；payload 可携带事件发生时的数据质量快照 | `{status,data_quality?,reason?,error?}` |
| `task_item.node_progress` | 节点开始、成功、跳过、失败或取消 | `{node_id,node_name,status,duration_ms,skip_reason?,error?}` |

事件 payload 中的任务、item、节点状态必须分别使用第 5.1 节对应枚举。P0 不定义 `stream.reset` 等没有实现依据的事件。

### 7.4 回放、去重与终态

- 页面首次加载先调用任务快照，使用 `last_event_id` 作为 `after` 建立 SSE；没有游标时从该任务可保留的最早事件开始。
- 浏览器断线自动重连时发送 `Last-Event-ID`；后端以该 header 优先于查询参数，回放其后的持久事件。
- 客户端必须去重：收到 `id` 不大于本地最后已应用 ID 的事件时忽略。
- 游标非法或超出保留范围时，返回 `422 INVALID_EVENT_CURSOR`；前端重新获取快照并以新游标恢复，不能无限重连。
- 任务进入 `COMPLETED`、`FAILED` 或 `CANCELED` 后，服务端发送终态事件并关闭流；客户端收到终态后主动关闭连接并刷新快照/报告。
- 页面卸载只关闭客户端连接，不调用取消接口。
- 事件保留时间、最大重放量和反向代理空闲超时尚未冻结，列为待确认项。

## 8. P1/P2 能力边界

P1/P2 的具体路径和 DTO 尚未由 PRD 和目标架构冻结。本节只说明未来接口必须具备的边界，不把候选路径写成契约。

| 成熟度 | 能力 | 未来接口必须解决 |
| --- | --- | --- |
| P1 未来-未实现 | 财务评估 | 提交确定性财务输入、规则版本和币种；读取 `PASSED/VETOED`、可复算理由与替代建议；P0 不启用 |
| P1 未来-未实现 | 图片证据 | 图片资产访问、缺陷区域坐标、可核验归因和权限；不能把无来源视觉描述当证据 |
| P1 未来-未实现 | 工程改款任务书导出 | 异步导出任务、产物状态、下载授权和过期策略 |
| P2 探索-未实现 | 回测 | 历史样本、评估口径、结果版本和可复现输入 |
| P2 探索-未实现 | 跨平台扩展 | 非 Amazon 平台适配、站点能力和数据覆盖差异 |
| P2 探索-未实现 | 供应链能力 | 供应商、成本、MOQ、履约等数据边界与权限 |

在上述能力形成明确验收口径前，不应仅为了“预留”而添加空接口、空字段或未使用枚举。

## 9. 历史接口说明

`docs/前端设计.md` 记录了已删除历史后端的接口快照，包括：

- `POST /api/v1/insight/task`
- `GET /api/v1/insight/tasks`
- `GET /api/v1/insight/task/{task_id}`
- `POST /api/v1/insight/task/{task_id}/cancel`
- `POST /api/v1/insight/task/{task_id}/retry`
- `GET /api/v1/insight/task/{task_id}/events`
- 历史事件 `task.updated`、`node.updated`、`item.updated`、`task.completed`、`task.failed`、`task.canceled`、`stream.end`

这些路径、事件和字段对应旧异步实现，当前工作区没有对应代码，不应被当前前端调用、复制生成客户端或作为新后端兼容目标。

当前目标资源命名统一以 `/api/v1/tasks...` 为基线；如果未来明确需要兼容旧协议，必须单独设计迁移期和弃用策略。

## 10. 待确认决策

| 议题 | 本文档推荐 | 必须确认的时点 |
| --- | --- | --- |
| JSON 命名 | `snake_case` | 后端首个业务 DTO 落地前 |
| 成功信封 | `{code:0,message:"ok",data}` | 首个业务路由实现前 |
| 错误信封 | `{error:{code,message,details,retryable,request_id}}` | 全局异常处理器实现前 |
| 认证机制 | 服务端从认证身份推导租户；具体协议待定 | P0 鉴权实现前 |
| 多项目语义 | P0 不要求 `project_id`，服务端推导租户/项目 | 任务创建 DTO 冻结前 |
| 幂等键 | `Idempotency-Key` header | 创建/重试路由实现前 |
| 时间窗 | `window.preset=1m|3m|6m` | 任务创建 DTO 冻结前 |
| 重试模型 | 新任务 + `parent_task_id`，保留历史 | 重试路由实现前 |
| 节点状态 | `SUCCESS`，`NO_DATA` 归数据质量 | 事件 schema 导出前 |
| SSE 事件集 | 当前三个草案事件 | 事件 DTO 冻结前 |
| SSE 保留策略 | 保留时间、最大回放量、游标失效规则待定 | SSE 实现与压测前 |
| 报告/证据 | P0 只读、按 item 获取、文本证据优先 | P0 路由拆分前 |
| 模型元数据 | 记录供应商、model_id、维度、prompt/规则版本 | 报告 DTO 冻结前 |

这些决策应由后端 DTO 和对应测试固化，前端不得根据本文档单方面生成正式类型。

## 11. 契约演进规则

1. 后端先定义业务 DTO、事件 DTO 和错误语义，再导出 `contracts/openapi.json` 与 `contracts/task-events.schema.json`。
2. 前端从生成契约得到类型和客户端，不长期维护与后端重复的手写 wire type。
3. 新增或修改字段时，必须同时更新请求示例、响应示例、错误表、SSE 事件表和兼容性说明。
4. 删除字段、改变枚举、改变状态语义或改变重试行为属于破坏性变更，需要版本或迁移策略。
5. CI 应在契约生成后检查漂移：重新生成 OpenAPI/事件 schema/前端客户端，工作区无未解释差异。
6. 本文档作为评审入口，不替代导出契约。实现状态变化后，应更新第 1.3 节和接口总览，但不得把“计划实现”写成“已实现”。

## 12. 依据索引

| 主题 | 依据 |
| --- | --- |
| 当前健康接口 | `backend/src/insightx/api/v1/health.py`、`backend/tests/test_health.py` |
| 前后端通信与生成契约 | `docs/architecture.md` 第 5 节 |
| 创建任务与异步流程 | `PRD.md` 第 6 节、`docs/architecture.md` 第 4–5 节 |
| 状态边界 | `PRD.md` 第 6.2 节、`docs/architecture.md` 第 4.2 节 |
| 前端 SSE 草案 | `frontend/src/composables/useTaskEvents.ts`、`frontend/src/api/events.types.ts` |
| 前端新建任务草案 | `frontend/src/features/dashboard/NewTaskDialog.vue` |
| 历史接口快照 | `docs/前端设计.md` 第 4–5 节 |
