# InsightX REST / SSE API 契约

> V0.1 设计草案 · 2026-09-10。依据 [PRD V1.1](PRD.md) 与 [系统技术方案](04-技术方案.md)。  
> 当前仓库没有 backend，以下接口均为待实现设计。只有创建任务的路径来自 PRD，其他路径和字段是本轮建议。P0 契约细化到联调边界，P1/P2 接口在对应阶段补充。

## 1. 通用约定

- API 前缀 `/api/v1`；REST 使用 JSON，字段 snake_case；ID 为服务端生成的不透明字符串，示例 ID 仅说明关系。
- 时间戳使用 ISO 8601 UTC；日期使用 `YYYY-MM-DD`。查询日期窗为闭区间日历日期，服务端按站点时区转换成 UTC 半开区间，快照保存解析结果。日期仅有日粒度的来源保留原精度，不制造时分秒。
- 金额采用 Decimal 计算，JSON 用十进制定点字符串并带币种；比例为 0–1 数值，计数为非负整数。未知值为 `null`，不可用指标另附 reason，不使用 0、999 代替未知。
- P0 平台固定 `amazon`、站点固定 `US`；ASIN 规范化为大写，满足 `^[A-Z0-9]{10}$`。存在性、变体与品类在采集验证。
- 企业身份从已验证的服务端会话获得，不接受正文中的 tenant_id 作为授权。所有资源 ID 均校验所属企业；越权资源按 404 处理。
- 建议采用同源 HttpOnly 会话 Cookie。改变状态的请求验证 CSRF token 与 Origin；SSE 不用 URL 携带长期令牌。身份接入的登录/成员 API 另行按确定的身份方案细化，当前 mock 登录不是此会话。
- 列表采用不透明 cursor，limit 默认 20、最大 100（设计默认）；返回 `items`、`next_cursor`，末页为 null。同一查询中排序稳定，游标不得用于不同过滤条件。
- GET 200、创建异步任务 202、格式/字段错误 422、未登录 401、资源不存在 404、幂等冲突 409、限流 429。429 可携带 Retry-After。

错误格式：

```json
{
  "error": {
    "code": "INVALID_ASIN",
    "message": "ASIN 必须为 10 位字母或数字",
    "details": [{"field": "asins[0]", "reason": "invalid_format"}],
    "retryable": false,
    "request_id": "req_example"
  }
}
```

`code` 供前端逻辑判断，message 可本地化；不返回异常堆栈、密钥或第三方原始鉴权错误。任务执行中的错误通过分项与事件返回，不改变已经发出的创建响应。

## 2. 状态及公共对象

| 字段 | 枚举 / 语义 |
| --- | --- |
| task.status / item.status | QUEUED、RUNNING、COMPLETED、FAILED、CANCELED |
| node.status | PENDING、RUNNING、COMPLETED、FAILED、CANCELED、SKIPPED |
| veto_status | NOT_EVALUATED、PASSED、VETOED；P0 恒为 NOT_EVALUATED |
| report.availability | SUFFICIENT、LIMITED、INSUFFICIENT；不代表市场样本有统计代表性 |
| proposal.column | PRODUCT、PACKAGING |
| phase | P0；P1/P2 暂不接受 |
| report_id | 该分项有已发布结果时为字符串，否则 null |

`COMPLETED + VETOED` 在 P1 合法：任务成功算出财务否决。批量部分失败采用 COMPLETED 与分项计数/warnings 表示，不新增 PARTIAL 状态；全失败或被取消的规则见技术方案 §5.3。报告不足可以是正常执行结果，采集错误不能标为“无评论”。

公共 warnings 对象：`code`、`message`、`item_id`（任务级可为 null）。公共分项 error 使用通用错误中的 code/message/retryable，不暴露内部堆栈。

## 3. P0 端点清单

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/insight/task` | 创建 1–10 ASIN 的诊断任务 |
| GET | `/insight/tasks` | 当前企业的任务列表 |
| GET | `/insight/task/{task_id}` | 任务与全部分项的当前快照 |
| GET | `/insight/task/{task_id}/events` | SSE 状态事件与恢复 |
| POST | `/insight/task/{task_id}/cancel` | 请求取消尚未完成的分项 |
| POST | `/insight/task/{task_id}/retry` | 从失败分项创建新任务 |
| GET | `/insight/task/{task_id}/items/{item_id}/report` | 该分项当前已发布报告 |
| GET | `/insight/task/{task_id}/items/{item_id}/evidence` | 按报告、痛点/建议读取真实关联证据 |

表中路径均相对 `/api/v1`。P0 不新增一个返回 mock KPI 的 overview 接口，初期从任务列表与选中报告组织页面；真实企业级聚合有需要时再扩展。

## 4. 创建与查询任务

### 4.1 POST /insight/task

请求头要求 `Idempotency-Key`，由客户端为一次提交生成并在网络重试时复用。服务端保存规范化请求的哈希；相同企业、相同键与内容返回原任务（仍为 202，reused=true），同键不同内容返回 409 `IDEMPOTENCY_CONFLICT`。该保证在任务记录存续期内有效，记录删除策略确定后再明确更长期保证。

```json
{
  "project_id": "project_home",
  "asins": ["B012345678", "B087654321"],
  "platform": "amazon",
  "marketplace": "US",
  "window": {"start_date": "2026-03-10", "end_date": "2026-09-10"}
}
```

示例 ASIN 只用于格式说明，未验证商品存在。project_id 必须属于当前企业且匹配该品类/站点；P0 可由服务端预置一个项目并由前端固定使用，后续身份/项目启动配置需提供该 ID。

必需字段为 project_id、asins；platform/marketplace 缺省使用 amazon/US，其他值返回 422。window 缺省为站点当前日向前六个日历月（短月日期夹至月末）；返回完整解析日期。拒绝反向日期窗和未来结束日期，来源不支持的合法历史窗在覆盖报告中说明。

ASIN 去重后必须有 1–10 个；批次中任一格式非法则整个请求 422，不创建半份任务。异品类或商品不存在等来源验证错误属于异步分项错误。

响应 202：

```json
{
  "task_id": "task_example",
  "status": "QUEUED",
  "phase": "P0",
  "reused": false,
  "window": {"start_date": "2026-03-10", "end_date": "2026-09-10"},
  "items": [
    {"item_id": "item_a", "asin": "B012345678", "status": "QUEUED"},
    {"item_id": "item_b", "asin": "B087654321", "status": "QUEUED"}
  ],
  "links": {
    "self": "/api/v1/insight/task/task_example",
    "events": "/api/v1/insight/task/task_example/events"
  }
}
```

### 4.2 GET /insight/tasks

支持 project_id、status、cursor、limit；按 created_at 降序、id 降序稳定分页。返回 `items` 中每项含 task_id、project_id、created_at、status、asins、item_counts、warnings_count，及 next_cursor。空列表为 `items: []`。只查当前企业。

### 4.3 GET /insight/task/{task_id}

返回一个一致性快照：状态/分项与 last_event_id 从同一数据库读快照获取，避免“新游标搭配旧状态”。

```json
{
  "task_id": "task_example",
  "project_id": "project_home",
  "phase": "P0",
  "status": "RUNNING",
  "created_at": "2026-09-10T08:00:00Z",
  "completed_at": null,
  "cancel_requested_at": null,
  "last_event_id": "12",
  "item_counts": {"total": 2, "queued": 1, "running": 1, "completed": 0, "failed": 0, "canceled": 0},
  "items": [
    {
      "item_id": "item_a",
      "asin": "B012345678",
      "status": "RUNNING",
      "attempt": 1,
      "current_node": "clustering",
      "nodes": [
        {"key": "ingestion", "status": "COMPLETED", "duration_ms": 8200},
        {"key": "normalization", "status": "COMPLETED", "duration_ms": 400},
        {"key": "embedding", "status": "COMPLETED", "duration_ms": 3500},
        {"key": "clustering", "status": "RUNNING", "duration_ms": null},
        {"key": "proposal", "status": "PENDING", "duration_ms": null},
        {"key": "evidence_validation", "status": "PENDING", "duration_ms": null},
        {"key": "publish", "status": "PENDING", "duration_ms": null}
      ],
      "progress": {"completed_nodes": 3, "total_nodes": 7, "processed_reviews": 160, "total_reviews": 160},
      "report_id": null,
      "error": null
    },
    {
      "item_id": "item_b",
      "asin": "B087654321",
      "status": "QUEUED",
      "attempt": 1,
      "current_node": null,
      "nodes": [],
      "progress": {"completed_nodes": 0, "total_nodes": 7, "processed_reviews": 0, "total_reviews": null},
      "report_id": null,
      "error": null
    }
  ],
  "warnings": []
}
```

数值均为合成协议示例，不是性能实测。所有分项都返回，不分页。节点可增加 started_at、completed_at、output_summary、skip_reason，缺省为 null；output_summary 只包含业务摘要，不包含模型内部推理或完整提示词。

## 5. 报告与证据

### 5.1 GET /insight/task/{task_id}/items/{item_id}/report

执行中尚未发布：409 `REPORT_NOT_READY`。终态且没有报告：404 `REPORT_NOT_AVAILABLE`。分项不存在或不属于 task：404。正常零样本时返回 200 与 INSUFFICIENT 报告。

报告必需字段：

| 字段 | 结构与含义 |
| --- | --- |
| report_id、report_version、item_id、published_at | 已发布报告身份；后续查询证据必须携带同一 report_id |
| snapshot | id、source、observed_at、window、content_hash；来源不可缺省 |
| product | asin、marketplace、title、price、currency、bsr、observed_at；未知元数据可为 null |
| availability、limitations | 证据可用性和限制数组；不是成功率/置信度 |
| coverage | raw_count、valid_count、excluded_count、negative_count、rating_distribution、language_distribution、month_distribution、missing_reasons、sampling_mode |
| metrics | sample_average_rating、sample_negative_rate、issue_count、reform_potential_index、fba_savings_per_unit |
| clusters | 痛点对象数组，最多五个展示项；other_cluster_count 与 unclassified_review_count 单独返回 |
| proposals | `{product: [...], packaging: [...]}`；两键必须存在，任一可为空 |
| veto_status | P0 为 NOT_EVALUATED |
| provenance | embedding_model_revision、llm_model_id、prompt_version、pipeline_version、clustering_version |

coverage 的 rating_distribution 键为 1–5 星，language_distribution 使用来源/检测语言码（未知用 und），month_distribution 按 YYYY-MM；均统计有效去重评论。raw_count 是本快照内去重前收集的原始条目数；excluded_count 包含去重与无效条目，因此 raw_count = valid_count + excluded_count。negative_count 是 valid_count 中 1–3 星数。另保存排除原因分布用于核对。

每个 metric 采用 `{value, reason, basis}`；basis 包含 sample_count 和 denominator（不适用可为 null）。只有取样覆盖 1–5 星时才计算面向全样本的平均星级与低星比例，且仍标注样本口径；P0 未定义的潜力指数与 FBA 节约额返回 value=null、reason=NOT_EVALUATED。FBA 金额在 P1 再增加 currency 和情景引用，不提前返回固定数。

痛点对象：

```json
{
  "id": "cluster_a",
  "name_zh": "扶手连接处断裂",
  "name_en": "Armrest connection breakage",
  "category": "quality",
  "frequency": 12,
  "denominator": 40,
  "share_ratio": 0.3,
  "severity": 4,
  "severity_reason": "样本报告扶手承力功能失效",
  "sample_quote": {"review_id": "review_a", "text": "The armrest snapped.", "translation": null},
  "evidence_count": 12,
  "photo_count": 0
}
```

这是合成结构示例。category 使用 quality / function / size / accessory / instructions / packaging / other。frequency 与 evidence_count 都按真实关联的独立评论计数；severity 在 1–5，聚合规则绑定版本；share_ratio=frequency/denominator，分母为零时 null。

建议对象通用字段：id、column、title、action、target_cluster_ids、expected_effect、assumptions、verification_required、evidence_count、photo_count。PRODUCT 与 PACKAGING 的数组元素使用同一个通用结构；成本、工期、尺寸及 FBA 参数在 P1 按可验证来源扩展。

约束：target_cluster_ids 非空，全部属于当前报告；正文只能引用所关联痛点支持的事实。expected_effect 是定性预期，不允许无依据的精确收益百分比。verification_required 是待工厂验证的事项列表；evidence_count 为关联簇评论并集去重后的数量。P0 photo_count=0 表示没有纳入图像证据，不表示来源页面没有图片。

### 5.2 GET .../evidence

查询参数：report_id 必需；cluster_id / proposal_id 必须且只能指定一个；cursor、limit 用于分页。目标必须属于该 report，且报告属于当前 item/task/tenant。后续 P1 增加 rating、start_date、end_date、language 筛选；未实现的参数应返回 422，不能静默忽略。

```json
{
  "report_id": "report_example",
  "target": {"type": "cluster", "id": "cluster_a"},
  "total": 1,
  "items": [
    {
      "review_id": "review_a",
      "source_review_id": "source_example",
      "asin": "B012345678",
      "source_url": "https://www.amazon.com/gp/customer-reviews/EXAMPLE",
      "rating": 1,
      "language": "en",
      "reviewed_at": "2026-08-14",
      "observed_at": "2026-09-10T08:00:05Z",
      "text": "The armrest snapped.",
      "translation": null,
      "images": []
    }
  ],
  "next_cursor": null
}
```

本例独立演示一条证据，URL 是格式占位，不是有效买家评价。真实接口必须返回采集到的来源。total 表示目标全部去重证据数，不是当前页长度；P1 加筛选后另返回 filtered_total，保留 total 供卡片核对。

译文缺失为 null；P0 images 为空，因为尚未提供取证。P1 引用位置字段需明确使用 Unicode code point 偏移，前端按 code point 转换，避免多字节/emoji 高亮错位。

## 6. SSE 事件与断线恢复

### 6.1 GET /insight/task/{task_id}/events?after={seq}

响应 `Content-Type: text/event-stream`，禁止代理缓冲和响应缓存。服务端建议每 15 秒发送注释心跳（部署默认，非 PRD 保证），心跳不落业务事件库。

SSE 基础语法中的 event、data、id、retry 与注释心跳参考 [MDN 官方文档](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)。以下 seq、payload 与 reset 是应用协议设计。

```text
retry: 3000
id: 13
event: node.updated
data: {"schema_version":1,"task_id":"task_example","seq":13,"item_id":"item_a","attempt":1,"occurred_at":"2026-09-10T08:00:18Z","payload":{"node":"clustering","status":"COMPLETED","duration_ms":2300}}

: heartbeat

```

| event | payload |
| --- | --- |
| task.updated | status、cancel_requested_at、item_counts |
| item.updated | status、current_node、progress、report_id、error |
| node.updated | node、status、duration_ms、output_summary、skip_reason |
| warning | code、message |
| task.completed | status=COMPLETED、item_counts、warnings_count |
| task.failed | status=FAILED、item_counts、error |
| task.canceled | status=CANCELED、item_counts |
| stream.reset | reason、snapshot_url；控制事件，无业务 seq/id |
| stream.end | last_event_id、status；控制事件，无业务 seq/id |

持久事件通用字段为 schema_version=1、task_id、seq、item_id、attempt、occurred_at、payload；任务级 item_id/attempt 为 null。seq 是任务内递增整数，SSE id 是它的十进制字符串；不同任务的 seq 不可比较。warning 文本不含原始凭据/评论全文。

### 6.2 前端恢复顺序

1. GET 任务快照得到 last_event_id，再用 `after=last_event_id` 建立流；若快照已终结，直接读取报告，无需新建流。
2. 自动重连优先使用请求头 Last-Event-ID；没有时使用 after；两者均无则从 0 开始。非法/超前游标返回 422 `INVALID_EVENT_CURSOR`。服务端补发所有 seq 大于游标的事件，再继续等待新增记录，数据库查询是补发与实时的共同来源，避免切换订阅时漏事件。
3. 浏览器按 seq 去重，忽略已经应用的事件；断线仅标“连接恢复中”，不得把业务任务改为 FAILED。切 task 时关闭旧 EventSource 并清空该任务的游标上下文。
4. 若游标早于保留范围，返回 stream.reset 后关闭连接。客户端主动 close，重新 GET 快照并用新游标连接；reset 本身不推进业务游标。
5. 收到任务终态事件后 close，并 GET 最终快照和报告。若终态事件已被游标消费，服务端发送 stream.end 让客户端关闭，避免不断重连一个已结束的任务。
6. 首次/重连鉴权失效不降级成匿名流。EventSource 报错后客户端用任务 GET 检查 HTTP 状态；401 时关闭流并显示登录失效。服务端在会话失效后关闭长连接。

原生 EventSource 使用命名事件监听器处理上述事件；每个打开的任务工作区只维持一个连接，而非每个 ASIN 一个连接。前端最终状态以 GET 快照为准。

## 7. 取消与重试

### 7.1 POST /insight/task/{task_id}/cancel

无正文，操作天然幂等。活动任务返回 202：task_id、当前 status、cancel_requested_at；持久记录取消请求，worker 在安全边界停止。返回 202 不代表外部调用已被强制终止。

终态任务返回 200 与原终态；重复取消不创建新请求时间。取消与发布在数据库事务中串行检查：先提交发布的结果保留，先提交取消标记的分项不再发布新报告。活动任务的取消最终落实为 CANCELED，但已完成分项仍可查；未提交产物的当前节点为 CANCELED，后续节点为 SKIPPED 且 skip_reason=CANCELED。

### 7.2 POST /insight/task/{task_id}/retry

需 Idempotency-Key，与创建接口相同的冲突规则。源任务必须已终结；正文：

```json
{"item_ids": ["item_b"]}
```

item_ids 必须非空、去重后不超过 10，全部属于源任务且为 FAILED；否则 409 `ITEM_NOT_RETRYABLE`。新建任务沿用原项目、站点和时间窗，绑定 parent_task_id 与所选 ASIN，返回创建接口的 202 结构及 parent_task_id。重试成功不改写源失败任务；取消后的重新分析使用普通创建接口。

## 8. P1 / P2 契约扩展边界

- P1 图片证据增加观察、假设、bbox、source/image ID 与模型版本；bbox 缺失允许 null，不假定每次模型都能定位。
- P1 财务单独建立“输入情景 → 计算结果”接口，绑定 report_id/version；必须定义币种、单位、费用版本、输入缺失与规则版本后再冻结路径与 schema。UI 调参不会重跑采集或改写原任务状态。
- P2 回测与跨平台映射各有独立资源，先确认数据及评估指标；不在现有 task 上追加一个常量 backtest_accuracy。
- 兼容性：新增可选字段不改变现有字段语义；新增必须字段、枚举解释或金额口径要升级契约。前端对未知事件忽略并刷新快照，不将未知状态视为完成。

## 9. 联调验收清单

1. 相同幂等请求返回同一个 task；同键不同输入 409；不产生重复计费任务。
2. 两个 ASIN 一个成功一个失败时，报告只展示成功分项，任务带完整分项结果与警告；全失败返回 FAILED。
3. 报告、图表、证据使用相同 item/report 上下文；跨任务引用和跨租户读取被拒绝。
4. SSE 断开期间的状态可补发；重复事件不重复渲染；过期游标 reset 后恢复；终态关闭连接。
5. 成功采集但零有效评论与来源失败具有不同结果；没有证据时不生成建议、不生成 FBA/ROI 假数据。
6. 取消不等于断开浏览器连接；取消/发布竞态、worker 租约过期、重试新任务均保持历史一致性。
7. 多痛点共享评论时，建议证据数按并集去重，与抽屉 total 一致；分页和 P1 筛选不改变总体证据数。
8. 后端实际 OpenAPI 与本草案逐项对照，前端执行 `bun run build`；实现前不可把本文件当作已部署接口证明。
