# InsightX API 接口文档

| 文档版本 | V1.0 | 编制日期 | 2026-09-05 |
| :--- | :--- | :--- | :--- |
| Base URL | `http://localhost:8000/api/v1` | 通信协议 | REST (JSON) + SSE |
| 上游依据 | [PRD](PRD.md) · [04-技术方案](04-技术方案.md) | 适用阶段 | MVP（P0）→ 复赛（P1/P2） |

本文档是前后端并行开发的接口契约。所有端点以 PRD 功能编号（P0-01 ~ P2-03）为优先级依据；后端实现后由 FastAPI `/docs` 自动生成的 OpenAPI 文档为准，本文档负责约定路径、入参出参与时序语义。

---

## 一、通用约定

### 1.1 鉴权
- 采用 JWT Bearer：`Authorization: Bearer <token>`。
- **MVP 阶段（比赛 Demo）可先关闭鉴权**，后端预留中间件位，单租户演示模式直接放行；P1 阶段接入登录后启用。

### 1.2 统一响应结构
所有 REST 接口返回统一信封：

```json
{ "code": 0, "message": "ok", "data": { } }
```

- `code = 0` 表示成功，非 0 见[错误码表](#六错误码表)。
- 时间字段统一 ISO 8601 UTC（`2026-09-05T08:00:00Z`）；金额单位 USD，保留 2 位小数；比率字段用 0~1 小数。
- 分页参数：`page`（从 1 起）、`page_size`（默认 20，最大 100）；分页响应 `data` 为 `{ "items": [...], "total": 128, "page": 1, "page_size": 20 }`。

### 1.3 前端部署形态与连接方式
前端采用**独立部署 SPA**（Vue 3.5 + Vite 8，`vite.base: '/'`、`createWebHistory('/')`），不再由 Astro 落地页同源代理；Astro 仅承载官网/落地页，通过 `PUBLIC_SPA_URL` 跳转到 SPA 独立地址。

连接后端的方式由 `VITE_USE_MOCK` 与 `VITE_API_BASE_URL` 两个环境变量控制（见 [frontend/.env.example](../frontend/.env.example)）：

| 环境 | `VITE_USE_MOCK` | `VITE_API_BASE_URL` | 行为 |
| :--- | :--- | :--- | :--- |
| 前端演示（默认） | `true` | `/api/v1`（任意） | 全部接口走前端 Mock 数据层，无需后端 |
| 本地联调 | `false` | `http://localhost:8000/api/v1` | REST 走 Vite `/api` 代理（`vite.config.ts` `server.proxy`） |
| 生产直连 | `false` | `https://api.example.com/api/v1` | 直接请求后端域名，**不经任何代理** |

- **REST**：`request<T>()` 将 `API_BASE + 路径` 作为最终 URL；开发环境相对路径 `/api/v1` 由 Vite 代理转发，生产环境为绝对地址直连。
- **SSE（EventSource 直连）**：前端用原生 `EventSource(\`${API_BASE}/insight/tasks/{task_id}/events\`)` 直连后端事件流，**不经过 Vite/Astro 代理**；后端需在响应头返回 `Content-Type: text/event-stream`、`Cache-Control: no-cache`、`X-Accel-Buffering: no`（防 nginx 缓冲），并通过 `CORSMiddleware` 放行 SPA 域名（`Access-Control-Allow-Origin: <SPA 域名>`，`allow_credentials` 视鉴权方式而定）。若后端经 nginx 反代，需关闭该路径的 `proxy_buffering`。
- Mock 模式下 SSE 由前端 `setInterval` 按 8 步任务规格播放预置事件（首个事件 `QUEUED`），用于脱离后端演示完整流程。

### 1.4 幂等与缓存
- 同一 ASIN 在缓存期内（建议 24h）重复创建分析任务时，复用已抓取的评论数据切片，仅重算后续 Agent 节点（对应 PRD NFR 数据幂等性）。

---

## 二、接口总览

| 模块 | 方法 | 路径 | 优先级 | 说明 | PRD 功能 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 系统 | GET | `/health` | P0 | 健康检查 | — |
| 认证 | POST | `/auth/login` | P1 | 登录换取 JWT | — |
| 认证 | GET | `/auth/me` | P1 | 当前用户信息 | — |
| **洞察任务** | POST | `/insight/tasks` | **P0** | 创建诊断任务（1-10 个 ASIN，批量则生成多个任务） | P0-01 |
| 洞察任务 | GET | `/insight/tasks` | P0 | 任务列表（分页） | P0-04 |
| 洞察任务 | GET | `/insight/tasks/{task_id}` | P0 | 任务详情（状态、节点、进度） | P0-04 |
| 洞察任务 | GET | `/insight/tasks/{task_id}/events` | **P0** | SSE 实时事件流 | P0-04 |
| 洞察任务 | POST | `/insight/tasks/{task_id}/cancel` | P1 | 取消任务 | — |
| 洞察任务 | POST | `/insight/tasks/{task_id}/retry` | P1 | 重试失败任务 | — |
| 洞察任务 | GET | `/insight/tasks/{task_id}/report` | P0 | 聚合最终报告（聚类+双栏+财务+回测） | P0-03 |
| **大盘** | GET | `/dashboard/overview` | P0 | KPI 卡片聚合数据 | P0-04 |
| 大盘 | GET | `/dashboard/recommendations` | P1 | Top 3 高潜改款项目推荐 | P0-04 |
| **竞品** | GET | `/products` | P0 | 竞品列表 | P0-01 |
| 竞品 | GET | `/products/{product_id}` | P0 | 竞品详情（元数据） | P0-01 |
| 竞品 | GET | `/products/{product_id}/price-history` | P1 | 价格 / BSR / Buy Box 时序 | — |
| **VOC** | GET | `/products/{product_id}/reviews` | P0 | 评论列表（星级/语言/时间筛选） | P0-02 |
| VOC | GET | `/insight/tasks/{task_id}/clusters` | **P0** | 痛点聚类结果（Top N） | P0-02 |
| **取证** | GET | `/insight/tasks/{task_id}/visual-evidences` | P1 | VLM 实拍图缺陷取证画廊 | P1-01 |
| **改款决策** | GET | `/insight/tasks/{task_id}/proposals` | **P0** | 双栏改款清单 | P0-03 |
| 改款决策 | GET | `/proposals/{proposal_id}` | P0 | 单条提案详情 | P0-03 |
| 改款决策 | GET | `/proposals/{proposal_id}/evidence` | P1 | 证据链穿透（原始评论+实拍图） | P1-03 |
| 改款决策 | POST | `/insight/tasks/{task_id}/export` | P2 | 导出工程改款 RFC（PDF/Excel） | — |
| **财务风控** | POST | `/financial/simulate` | P1 | ROI / 回本周期 / FBA 降档模拟（无副作用） | P1-02 |
| 财务风控 | GET | `/insight/tasks/{task_id}/financial` | P1 | 任务财务否决决议结果 | P1-02 |
| **回测** | POST | `/backtest/run` | P2 | 发起历史时间切片回测 | P2-01 |
| 回测 | GET | `/backtest/{backtest_id}` | P2 | 回测结果与吻合度评分 | P2-01 |
| **跨平台** | GET | `/cross-platform/mapping` | P2 | 跨平台同款 SKU 映射与价差 | P2-02 |
| **告警** | GET | `/alerts` | P1 | 告警中心（价格异动/供应链/熔断） | P2-03 |
| 告警 | PATCH | `/alerts/{alert_id}` | P1 | 标记告警已读 | — |

> 注：PRD 时序图中的 `POST /api/v1/insight/task` 在本文档统一为 RESTful 复数形式 `/insight/tasks`，后端路由实现以本文档为准。

---

## 三、系统与认证

### 3.1 健康检查 `GET /health`
无鉴权。返回 `data: { "status": "ok", "version": "0.1.0", "db": true, "redis": true }`，用于部署验证与前端连接探测。

### 3.2 登录 `POST /auth/login`
```json
// 请求
{ "username": "demo@insightx.ai", "password": "******" }
// data
{ "access_token": "eyJhbGciOi...", "token_type": "bearer", "expires_in": 86400 }
```

### 3.3 当前用户 `GET /auth/me`
返回 `data: { "user_id": "usr_01", "username": "demo@insightx.ai", "tenant_id": "tnt_01", "role": "owner" }`。

---

## 四、洞察任务模块（核心）

### 4.1 创建诊断任务 `POST /insight/tasks`（P0-01）

单次提交 1-10 个 ASIN；因 LangGraph `InsightState` 以单 ASIN 为驱动，批量提交时**后端为每个 ASIN 各创建一个任务**并一并返回。若传 `amazon_url` 则自动解析其中的 ASIN，与 `asins` 至少提供一项。

```json
// 请求
{
  "asins": ["B0C1234ABC"],
  "amazon_url": null,
  "platform": "amazon",
  "marketplace": "US",
  "review_window_months": 6,
  "max_reviews": 500,
  "financial_constraint": {
    "mold_cost_usd": 8000,
    "moq": 1000,
    "current_gross_margin": 0.32,
    "expected_price_usd": 29.99,
    "unit_cost_increase_usd": 1.8,
    "expected_payback_months": 6,
    "sea_freight_usd_per_cbm": 180
  },
  "options": {
    "enable_vision_audit": true,
    "enable_backtest": false
  }
}
```

```json
// data
{
  "tasks": [
    {
      "task_id": "tsk_9f2c81a4",
      "asin": "B0C1234ABC",
      "product_id": "0d1f3a5e-...",
      "status": "PENDING",
      "cache_hit": false,
      "estimated_seconds": 45,
      "created_at": "2026-09-05T08:00:00Z"
    }
  ]
}
```

校验规则（对应 P0-01 验收标准）：
- ASIN 必须为标准 10 位（`^[A-Z0-9]{10}$`），不合法返回 `42201`；
- 数量超出 1-10 返回 `40001`；抓取成功率与无意义短评（"ok"、"fast"）过滤由后端采集管道保证，接口层只做参数校验。

### 4.2 任务列表 `GET /insight/tasks`
Query：`status`（PENDING/RUNNING/COMPLETED/FAILED/CANCELED）、`asin`、`page`、`page_size`。`items` 元素结构与 [4.5 任务详情](#45-任务详情-get-insighttaskstask_id) 相同（`summary` 仅保留概要字段）。

### 4.3 任务事件流 `GET /insight/tasks/{task_id}/events`（SSE，P0-04）

- 响应头：`Content-Type: text/event-stream`，`Cache-Control: no-cache`，`X-Accel-Buffering: no`。
- 每条事件 `event: message`，`data` 为 JSON：

```json
{
  "task_id": "tsk_9f2c81a4",
  "step": "VISION_AUDIT",
  "progress": 45,
  "message": "Claude Vision 完成 18 张买家实拍图质检",
  "extra": { "reviews_fetched": 320, "images_audited": 18 },
  "timestamp": "2026-09-05T08:00:23Z"
}
```

**`step` 枚举**（与 LangGraph 节点一一对应，供前端播放 7 步节点推进动画）：

| step | 含义 | 约定进度区间 |
| :--- | :--- | :--- |
| `QUEUED` | 任务已入队等待调度 | 0-5 |
| `FETCHING_DATA` | 数据采集与清洗（Playwright/HTTPX 抓取评论与买家图） | 5-25 |
| `VISION_AUDIT` | Claude Vision 实拍图取证 | 25-45 |
| `SEMANTIC_CLUSTER` | bge-m3 向量化与痛点聚类 | 45-65 |
| `DUAL_DECISION` | 双栏改款建议生成 | 65-85 |
| `FINANCIAL_VETO` | 财务否决审核（被 VETO 打回重试时再次推送本 step，`extra.retry_count` 递增） | 85-92 |
| `EVIDENCE_TRACE` | 证据链反向索引校验 | 92-96 |
| `BACKTEST_EVAL` | 历史回测（`enable_backtest=false` 时跳过） | 96-99 |
| `COMPLETED` | 终态：任务完成，前端应关闭连接并拉取 `report` | 100 |
| `FAILED` | 终态：任务失败，`message` 携带失败原因 | — |

补充约定：
- 心跳：服务端每 15s 下发一行 SSE 注释 `: ping`，防止代理断连。
- 前端在收到 `COMPLETED` / `FAILED` 后 `EventSource.close()`；断线可依赖 EventSource 自动重连，服务端支持从 Redis 补发最近状态。
- `progress` 为 0-100 整数，仅供展示，后端不保证严格单调。

### 4.4 取消 / 重试
- `POST /insight/tasks/{task_id}/cancel`：仅 `PENDING/RUNNING` 可取消，否则 `40901`。
- `POST /insight/tasks/{task_id}/retry`：仅 `FAILED` 可重试；复用 `task_id` 或生成新任务由后端实现定夺，响应返回最新任务详情。

### 4.5 任务详情 `GET /insight/tasks/{task_id}`

```json
// data
{
  "task_id": "tsk_9f2c81a4",
  "asin": "B0C1234ABC",
  "product_id": "0d1f3a5e-...",
  "platform": "amazon",
  "marketplace": "US",
  "status": "RUNNING",
  "current_node": "semantic_cluster",
  "progress": 65,
  "retry_count": 0,
  "financial_constraint": { "mold_cost_usd": 8000, "moq": 1000 },
  "summary": {
    "review_count": 318,
    "cluster_count": 5,
    "proposal_count": 6,
    "veto_status": "PENDING",
    "backtest_score": null
  },
  "error_message": null,
  "created_at": "2026-09-05T08:00:00Z",
  "started_at": "2026-09-05T08:00:03Z",
  "finished_at": null
}
```

### 4.6 聚合报告 `GET /insight/tasks/{task_id}/report`

一次性返回大盘渲染所需的全部结果（前端亦可在 `COMPLETED` 后分别调 clusters / proposals / financial）。

```json
// data（结构示意，子对象完整字段见各明细接口）
{
  "task": { "...": "任务详情同 4.5，status=COMPLETED" },
  "clusters": { "items": [ "..." ] },
  "proposals": { "items": [ "..." ] },
  "financial": { "...": "同 8.2，无则 null" },
  "visual_evidences": { "items": [ "..." ] }
}
```

---

## 五、战略决策大盘

### 5.1 KPI 总览 `GET /dashboard/overview`（P0-04）
对应大盘 Top KPI Row，可传 `days`（默认 30）限定统计窗口。

```json
// data
{
  "monitored_product_count": 12,
  "running_task_count": 2,
  "pain_point_cluster_count": 23,
  "fba_saving_pool_usd": 42800.00,
  "veto_triggered_count": 3,
  "avg_rating": 4.1,
  "negative_review_rate": 0.18
}
```

### 5.2 高潜改款推荐 `GET /dashboard/recommendations`
返回近期分析完成的 Top 3 推荐项目（PRD 5.1）。

```json
// data.items[]
{
  "task_id": "tsk_9f2c81a4",
  "product_id": "0d1f3a5e-...",
  "asin": "B0C1234ABC",
  "title": "LED 台灯 Pro",
  "main_image_url": "https://...",
  "estimated_roi": 2.4,
  "return_rate_reduction": 0.35,
  "veto_status": "PASSED",
  "finished_at": "2026-09-04T22:10:00Z"
}
```

---

## 六、竞品监控

### 6.1 竞品列表 `GET /products`
Query：`platform`、`marketplace`、`keyword`（标题/ASIN 模糊）、分页。

```json
// data.items[]
{
  "product_id": "0d1f3a5e-...",
  "asin": "B0C1234ABC",
  "platform": "amazon",
  "marketplace": "US",
  "title": "LED Desk Lamp Pro",
  "category": "Home & Kitchen",
  "current_price": 29.99,
  "currency": "USD",
  "main_image_url": "https://...",
  "review_count": 318,
  "avg_rating": 4.1,
  "bsr": 1240,
  "updated_at": "2026-09-05T06:00:00Z"
}
```

### 6.2 竞品详情 `GET /products/{product_id}`
在列表字段基础上追加尺寸重量（供抛重测算）：`length_cm / width_cm / height_cm / weight_kg`、`bsr_category`、`created_at`。

### 6.3 价格 / BSR / Buy Box 时序 `GET /products/{product_id}/price-history`（P1）
Query：`start_date`、`end_date`（默认近 90 天）、`interval`（`6h`/`1d`，默认 `1d`）。

```json
// data.points[]
{ "ts": "2026-09-01T00:00:00Z", "price": 27.99, "bsr": 1150, "buy_box_price": 27.99, "has_coupon": false }
```

---

## 七、评论洞察（VOC）

### 7.1 评论列表 `GET /products/{product_id}/reviews`
Query：`rating_min` / `rating_max`（差评筛选用 1-3 星）、`language`（如 `en`/`de`/`ja`）、`verified_only`、`start_date` / `end_date`、`keyword`、分页。支持多语言原声与翻译对照视图（PRD 5.2）。

```json
// data.items[]
{
  "review_id": "rev_88c2...",
  "rating": 1.0,
  "review_date": "2026-03-12",
  "language": "de",
  "title": "Griff nach einer Woche gebrochen",
  "content": "Der Griff ist nach einer Woche gebrochen...",
  "translated_content": "把手一周后就断了……",
  "verified_purchase": true,
  "helpful_votes": 12,
  "image_urls": ["https://minio/.../img1.jpg"],
  "cluster_ids": ["clu_01"]
}
```

### 7.2 痛点聚类结果 `GET /insight/tasks/{task_id}/clusters`（P0-02）
返回该任务聚类出的 Top N 痛点（默认 Top 5），按严重度 × 频次加权排序。

```json
// data.items[]
{
  "cluster_id": "clu_01",
  "cluster_name": "把手易断裂",
  "issue_type": "product_defect",
  "frequency": 128,
  "frequency_ratio": 0.34,
  "severity_score": 4.6,
  "severity_level": "critical",
  "keywords": ["broke", "handle", "crack"],
  "sample_quotes": [
    {
      "review_id": "rev_88c2...",
      "language": "de",
      "content": "Der Griff ist gebrochen...",
      "translated_content": "把手断了……",
      "rating": 1.0
    }
  ],
  "sample_image_ids": ["img_a1", "img_b2"]
}
```

- `issue_type` 枚举：`product_defect`（质量）/ `function_defect`（功能）/ `size_spec`（尺寸）/ `accessory`（配件）/ `manual`（说明书）/ `packaging_delivery`（包装履约）/ `other`。
- `severity_level` 映射（前端徽章 Critical / Moderate / Minor）：`>= 4.0` critical，`>= 2.5` moderate，其余 minor。

---

## 八、多模态取证与改款决策

### 8.1 VLM 实拍图取证画廊 `GET /insight/tasks/{task_id}/visual-evidences`（P1-01）
Query：`defect_category`、`min_confidence`（默认 0.6）、分页。

```json
// data.items[]
{
  "image_id": "img_a1",
  "review_id": "rev_88c2...",
  "storage_url": "https://minio:9000/buyer-review-images/img_a1.jpg",
  "defect_category": "craft_flaw",
  "description": "把手根部应力集中处断裂，断口平整，疑为模具公差或材质强度不足",
  "confidence": 0.92,
  "bbox": [120, 80, 420, 360],
  "cluster_ids": ["clu_01"]
}
```

`defect_category` 枚举：`color_difference`（色差）/ `broken_package`（运输破损）/ `craft_flaw`（工艺瑕疵/断裂）/ `dimension_issue`（尺寸问题）/ `other`。`bbox` 为 `[x0, y0, x1, y1]` 像素坐标，供前端叠加缺陷边界框。

### 8.2 双栏改款清单 `GET /insight/tasks/{task_id}/proposals`（P0-03）
按 `track_type` 区分左栏（产品本体）与右栏（包装履约），前端以双栏卡片对照展示。

```json
// data.items[]
{
  "proposal_id": "prp_5b7e...",
  "task_id": "tsk_9f2c81a4",
  "track_type": "BODY_OPTIMIZATION",
  "title": "替换把手材质为阻燃 PC 并增加防呆卡扣",
  "description": "针对 34% 断裂差评，将 ABS 把手替换为玻纤增强 PC，卡扣处增加 0.5mm 防呆结构，拔模斜度修正至 2°……",
  "cost_estimation_usd": 8500,
  "mold_opening_required": true,
  "mold_cycle_days": 60,
  "estimated_roi": 2.4,
  "defect_rate_reduction": 0.62,
  "status": "PASSED",
  "veto_reason": null,
  "fallback_applied": false,
  "source_cluster_ids": ["clu_01"],
  "evidence_review_count": 42,
  "evidence_image_count": 8,
  "created_at": "2026-09-05T08:01:40Z"
}
```

包装履约轨（`track_type = "PACKAGING_FULFILLMENT"`）额外携带以下字段，供 FBA 降档对比展示：

```json
{
  "package_size_old_cm": [30, 20, 12],
  "package_size_new_cm": [26, 18, 9],
  "volumetric_weight_old_kg": 1.44,
  "volumetric_weight_new_kg": 0.84,
  "fba_tier_old": "Large Standard",
  "fba_tier_new": "Small Standard",
  "fulfillment_saving_usd_per_unit": 1.35
}
```

- `status`：`PASSED` / `VETOED`（对应财务熔断决议，红色警示展示 `veto_reason`）。
- `fallback_applied`：被否决后是否已由 Agent 生成降级替代方案（如免开模小改、仅优化包装）。

### 8.3 提案详情 `GET /proposals/{proposal_id}`
字段同 8.2 单元素。

### 8.4 证据链穿透 `GET /proposals/{proposal_id}/evidence`（P1-03）
支撑改款抽屉弹窗：点击建议后拉取原始证据，支持按星级、时间筛选（Query：`rating_max`、`start_date`、`end_date`、分页）。

```json
// data
{
  "proposal_id": "prp_5b7e...",
  "total": 50,
  "reviews": [
    {
      "review_id": "rev_88c2...",
      "rating": 1.0,
      "review_date": "2026-03-12",
      "language": "de",
      "content": "Der Griff ist nach einer Woche gebrochen...",
      "translated_content": "把手一周后就断了……",
      "highlight_keywords": ["gebrochen", "Griff"],
      "images": [
        {
          "image_id": "img_a1",
          "storage_url": "https://minio:9000/.../img_a1.jpg",
          "defect_category": "craft_flaw",
          "confidence": 0.92
        }
      ]
    }
  ]
}
```

前端依据 `highlight_keywords` 在原文中高亮核心抱怨词（对应 P1-03 验收第 3 条）；卡片上的引用数直接使用 8.2 的 `evidence_review_count / evidence_image_count`。

### 8.5 导出工程改款任务书 `POST /insight/tasks/{task_id}/export`（P2）
```json
// 请求
{ "format": "pdf", "proposal_ids": ["prp_5b7e..."] }
// data
{ "download_url": "https://.../rfc_tsk_9f2c81a4.pdf", "expires_in": 3600 }
```

> **前端 Mock 契约注记**：前端 Mock 层当前返回 `{ task_id, format, filename, content }`（`content` 为 Markdown 文本），用于演示导出内容预览，**与后端契约 `{ download_url, expires_in }` 不一致**。切换真实后端（`VITE_USE_MOCK=false`）后，前端将按本契约下载文件；两种形态互不兼容，联调时以后端契约为准。

---

## 九、财务风控

### 9.1 参数模拟 `POST /financial/simulate`（P1-02，无副作用）
供风控页财务参数滑块拖动时**实时重算**（盈亏平衡与敏感度曲线），不落库、不触发 Agent。

```json
// 请求
{
  "mold_cost_usd": 8000,
  "moq": 1000,
  "current_gross_margin": 0.32,
  "expected_price_usd": 29.99,
  "unit_cost_increase_usd": 1.8,
  "expected_payback_months": 6,
  "sea_freight_usd_per_cbm": 180,
  "package_size_old_cm": [30, 20, 12],
  "package_size_new_cm": [26, 18, 9],
  "expected_return_rate_reduction": 0.35,
  "product_lifecycle_days": 180
}
```

```json
// data
{
  "volumetric_weight_old_kg": 1.44,
  "volumetric_weight_new_kg": 0.84,
  "fba_tier_old": "Large Standard",
  "fba_tier_new": "Small Standard",
  "fulfillment_saving_usd_per_unit": 1.35,
  "monthly_profit_delta_usd": 2100.00,
  "payback_months": 4.8,
  "roi": 2.4,
  "veto_status": "PASSED",
  "veto_reasons": [],
  "fallback_suggestions": [],
  "payback_curve": [
    { "return_rate_reduction": 0.10, "payback_months": 9.6 },
    { "return_rate_reduction": 0.35, "payback_months": 4.8 },
    { "return_rate_reduction": 0.60, "payback_months": 3.1 }
  ]
}
```

否决规则（与 04-技术方案 §2.4 一致，`veto_reasons` 逐条返回中文劝退理由）：
- `预计开模改造周期 > 90 天` 且 `预期品类生命周期 < 180 天` → 强制否决；
- `单位改进成本增加额 > 当前毛利额 × 35%` 且无法提价 → 强制否决；
- 触发否决时 `fallback_suggestions` 返回降级替代方案提示。

### 9.2 任务财务决议 `GET /insight/tasks/{task_id}/financial`（P1-02）
返回任务运行期 Agent 真实执行的财务否决结果（与 9.1 的沙盒模拟区分）。

```json
// data
{
  "task_id": "tsk_9f2c81a4",
  "veto_status": "PASSED",
  "checked_proposals": 6,
  "vetoed_proposal_ids": ["prp_6c8f..."],
  "veto_reasons": ["开模回收期长达 14 个月，已超出该品类 6 个月生命周期"],
  "fallback_applied": true,
  "retry_count": 1,
  "financial_constraint": { "...": "任务创建时录入的参数" }
}
```

---

## 十、扩展模块（P2）

### 10.1 历史回测 `POST /backtest/run` / `GET /backtest/{backtest_id}`（P2-01）
发起：`{ "task_id": "tsk_9f2c81a4", "slice_date": "2026-03-01" }` → `{ "backtest_id": "bt_77aa...", "status": "PENDING" }`。
查询返回：

```json
// data
{
  "backtest_id": "bt_77aa...",
  "task_id": "tsk_9f2c81a4",
  "slice_date": "2026-03-01",
  "status": "COMPLETED",
  "accuracy_score": 0.78,
  "cluster_verdicts": [
    { "cluster_id": "clu_01", "cluster_name": "把手易断裂", "hit": true, "actual_trend": "同品类 2026 Q2 断裂类差评上升 22%" }
  ]
}
```

### 10.2 跨平台 SKU 映射 `GET /cross-platform/mapping`（P2-02）
Query：`product_id`、`min_match_score`（默认 0.7）、分页。

```json
// data.items[]
{
  "product_id": "0d1f3a5e-...",
  "asin": "B0C1234ABC",
  "amazon_price_usd": 29.99,
  "matches": [
    {
      "platform": "temu",
      "external_sku": "TM-88213",
      "title": "LED 台灯 折叠款",
      "price_usd": 12.90,
      "match_score": 0.91,
      "commission_usd": 0.90,
      "fulfillment_usd": 2.10
    }
  ],
  "max_price_gap_usd": 17.09
}
```

### 10.3 告警中心 `GET /alerts`（P1/P2）
Query：`type`（`price_movement` 价格异动 / `buy_box` 跟卖与 Buy Box / `supply_chain` 供应链与原材料 / `veto` 风控熔断）、`is_read`、`severity`（`high`/`medium`/`low`）、分页。

```json
// data.items[]
{
  "alert_id": "alr_01",
  "type": "price_movement",
  "severity": "high",
  "title": "竞品 B0C1234ABC 降价 12%",
  "message": "目标竞品 2 小时内降价 $3.4，可能发起促销对冲",
  "related_product_id": "0d1f3a5e-...",
  "related_task_id": null,
  "is_read": false,
  "created_at": "2026-09-05T07:30:00Z"
}
```

标记已读：`PATCH /alerts/{alert_id}` 请求体 `{ "is_read": true }`。

---

## 十一、错误码表

| code | HTTP | 含义 |
| :--- | :--- | :--- |
| 0 | 200 | 成功 |
| 40001 | 400 | 通用参数错误（数量超限、日期区间非法等） |
| 40101 | 401 | 未认证 / Token 失效 |
| 40401 | 404 | 资源不存在（任务、提案、商品等） |
| 40901 | 409 | 状态冲突（如对已完成任务发起取消） |
| 42201 | 422 | ASIN 格式不合法 |
| 42901 | 429 | 触发采集限频 / 缓存冷却期内重复提交 |
| 50001 | 500 | 服务内部错误 |
| 50201 | 502 | 上游依赖失败（电商平台抓取、LLM/VLM 调用超限，已按指数退避重试 3 次仍失败） |

---

## 十二、典型调用时序（前端参考）

1. `POST /insight/tasks` 创建任务，取得 `tasks[].task_id`；
2. 对每个任务 `GET /insight/tasks/{task_id}/events` 建立 SSE 连接，按 `step` 播放 7 步节点推进动画；
3. 收到 `COMPLETED` 后关闭连接，`GET /insight/tasks/{task_id}/report` 拉取聚合结果渲染双栏看板；
4. 用户点击"查看证据链" → `GET /proposals/{proposal_id}/evidence` 滑出抽屉；
5. 老板拖动财务滑块 → `POST /financial/simulate` 实时刷新盈亏曲线与熔断横幅。

---

## 十三、接口可用性验证矩阵

> 说明：后端当前为占位实现（`backend/main.py` 未提供真实 API），因此"接口可用"的验证落在**前端 Mock 数据层**。验证方式：`frontend/src/api/api.test.ts` 以 Vitest 对 **26 个 API 函数 + SSE 订阅**逐一断言契约（28 个用例，全部通过）；真实路径的可用性待后端实现后按本矩阵复测。

| # | 接口 | 前端函数 | Mock 路径 | 真实路径 | 验证用例要点 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `GET /health` | `getHealth` | ✅ | ⏳ | 返回 `{status, version, db, redis}` |
| 2 | `POST /auth/login` | `login` | ✅（localStorage 邮箱+密码） | ⏳ | 正确凭据成功、错误凭据抛错 |
| 3 | `GET /auth/me` | `getMe` | ✅ | ⏳ | 返回当前用户 |
| 4 | `POST /insight/tasks` | `createTask` | ✅ | ⏳ | 批量 ASIN 生成多任务、financial_constraint 透传 |
| 5 | `GET /insight/tasks` | `listTasks` | ✅ | ⏳ | `status` 筛选、分页 |
| 6 | `GET /insight/tasks/{id}` | `getTask` | ✅ | ⏳ | 未知名抛 `40401` |
| 7 | `GET /insight/tasks/{id}/events` | `subscribeTaskEvents` | ✅（setInterval 播放 8 步） | ⏳（EventSource 直连） | 首事件 `QUEUED`、取消后停止推进 |
| 8 | `POST /insight/tasks/{id}/cancel` | `cancelTask` | ✅ | ⏳ | 仅 `PENDING/RUNNING` 可取消 |
| 9 | `POST /insight/tasks/{id}/retry` | `retryTask` | ✅ | ⏳ | 仅 `FAILED` 可重试 |
| 10 | `GET /insight/tasks/{id}/report` | `getInsightReport` | ✅ | ⏳ | 聚合报告结构完整 |
| 11 | `GET /dashboard/overview` | `getDashboardOverview` | ✅ | ⏳ | `days` 参数、KPI 7 字段 |
| 12 | `GET /dashboard/recommendations` | `getRecommendations` | ✅ | ⏳ | Top 3 推荐列表 |
| 13 | `GET /products` | `listProducts` | ✅ | ⏳ | `platform`/`marketplace`/`keyword` 筛选 |
| 14 | `GET /products/{id}` | `getProduct` | ✅ | ⏳ | 未知名抛 `40401` |
| 15 | `GET /products/{id}/price-history` | `getPriceHistory` | ✅ | ⏳ | `start_date`/`end_date`/`interval` |
| 16 | `GET /products/{id}/reviews` | `listReviews` | ✅ | ⏳ | 星级/语言/关键词筛选 |
| 17 | `GET /insight/tasks/{id}/clusters` | `getClusters` | ✅ | ⏳ | 痛点聚类 Top N |
| 18 | `GET /insight/tasks/{id}/visual-evidences` | `getVisualEvidences` | ✅ | ⏳ | `defect_category`/`min_confidence` 筛选 |
| 19 | `GET /insight/tasks/{id}/proposals` | `getProposals` | ✅ | ⏳ | 双栏改款清单 |
| 20 | `GET /proposals/{id}` | `getProposal` | ✅ | ⏳ | 未知名抛 `40401` |
| 21 | `GET /proposals/{id}/evidence` | `getProposalEvidence` | ✅ | ⏳ | 证据链（评论+实拍图） |
| 22 | `POST /insight/tasks/{id}/export` | `exportRfc` | ✅（注：返回 Markdown，见 8.5 注记） | ⏳ | 下载契约与后端不同 |
| 23 | `POST /financial/simulate` | `simulateFinancialApi` | ✅ | ⏳ | 健康 `PASSED` / 越限 `VETOED` |
| 24 | `GET /insight/tasks/{id}/financial` | `getFinancialDecision` | ✅ | ⏳ | 否决决议结构 |
| 25 | `POST /backtest/run` / `GET /backtest/{id}` | `runBacktest` / `getBacktest` | ✅ | ⏳ | 回测结果与吻合度 |
| 26 | `GET /cross-platform/mapping` | `getCrossPlatformMapping` | ✅ | ⏳ | 同款 SKU 映射与价差 |
| 27 | `GET /alerts` | `getAlerts` | ✅ | ⏳ | `type`/`is_read`/`severity` 筛选 |
| 28 | `PATCH /alerts/{id}` | `markAlertRead` | ✅ | ⏳ | 标记已读后 `is_read=true` |

- ✅ = 已通过 `frontend/src/api/api.test.ts` 验证（Mock 路径契约，28/28 用例通过）。
- ⏳ = 待后端实现真实 API 后验证（前端真实路径分支已就绪，切换 `VITE_USE_MOCK=false` 即可联调）。
- 运行验证：`cd frontend && npx vitest run`（当前 60/60 全绿，含 mock.test.ts / api.test.ts / utils 测试）。

---

## 附录：与 PRD / 技术方案的对应关系

| 接口模块 | 支撑 PRD 功能 | 备注 |
| :--- | :--- | :--- |
| 洞察任务 + SSE | P0-01 采集引擎、P0-04 任务流看板 | `InsightState` 驱动，Celery + Redis 异步调度 |
| clusters / reviews | P0-02 痛点聚类 | bge-m3 + pgvector HNSW，多语言标签对齐 |
| proposals | P0-03 双栏改款 | `track_type` 对应 `reform_proposals.track_type` |
| visual-evidences | P1-01 VLM 取证 | 对应 `review_images.vlm_analysis` |
| financial simulate / 决议 | P1-02 财务否决 | 否决阈值见 9.1 |
| evidence | P1-03 证据溯源 | 对应 `reform_proposals.evidence_review_ids / evidence_image_ids` |
| backtest | P2-01 回测验证 | 输出 Backtest Accuracy Score |
| cross-platform mapping | P2-02 跨平台映射 | 三平台价差与佣金履约测算 |
| alerts | P2-03 供应链预警 | 兼容价格异动与风控熔断告警 |
