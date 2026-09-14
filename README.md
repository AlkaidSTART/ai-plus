# InsightX · 全球跨境电商 AI 市场洞察与动态决策系统

基于 **AI 多模态取证 + Agent 决策闭环** 的出海选品与改款决策平台：将 Amazon / TikTok Shop / Temu 的多语言评论与买家实拍图，转化为工厂级双栏改款工程清单与逆向财务熔断决策。

## 当前状态

**当前工作区已落地 Vue 3 + Vite + TypeScript 前端脚手架、FastAPI 基础入口与 `GET /api/v1/health`，以及 `infra/` 下 PostgreSQL/pgvector、Redis、API、Web 四服务单机 Compose 部署基座。** 数据库/Redis 应用接入与真实探针、Alembic/pgvector 初始化迁移、Celery Worker、outbox dispatcher、LangGraph 图与 PostgreSQL checkpointer、业务 API、SSE、契约和 CI 仍未实现；模型/数据来源可用性、质量、费用与性能仍待 M0/M1 验证。健康容器不等同于业务或模型已完成。

**LLM、VLM、Embedding 全部使用云端 API**；项目侧只做编排、清洗、CPU 聚类与存储，不部署模型权重或 GPU/CUDA 推理。LLM/VLM 保留 Claude 云端方向；Embedding 优先验证 SiliconFlow `BAAI/bge-m3`（1024 维基线），实际账户、型号与维度通过验证后锁定。

## 目标架构

采用**轻量异构 monorepo + 模块化单体 + 独立 Worker**。前后端分别构建，只通过 HTTP（REST + SSE）通信；API、Worker 与任务派发器共用一个 Python 业务包，不拆微服务。

```text
ai-plus/
├── frontend/         # Vue 3 + Vite + TypeScript；Bun + bun.lock
├── backend/          # FastAPI 基础入口；uv + uv.lock（任务与工作流待实现）
├── infra/            # 单机容器部署基座
│   ├── compose.yaml
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── nginx.conf
├── contracts/        # 后端生成的 OpenAPI 与 SSE 事件 schema（待生成）
├── docs/
│   ├── architecture.md
│   └── plans/
├── AGENTS.md
└── PRD.md
```

单仓库不要求统一跨语言包管理器。当前目标只有一个 JS 应用和一个 Python 包，先不引入 workspace、Turborepo/Nx 或空共享包；出现真实需求后再评估。

| 层 | 选型 | 职责 |
| --- | --- | --- |
| 前端 | Vue 3、Vite、TypeScript strict、shadcn-vue（Reka UI + Tailwind CSS v4）、ECharts | SPA 工作台；CSS 变量浅色主题，不叠加第二套组件库 |
| 状态 | Vue Router、TanStack Vue Query、Pinia | Query 管服务端数据；Pinia 管跨页 UI 状态 |
| 后端 | Python 3.12、FastAPI、Pydantic 2、SQLAlchemy 2、psycopg 3、Alembic | HTTP、身份/租户、短事务与业务规则 |
| 异步与工作流 | Celery + Redis、事务 outbox、LangGraph + PostgreSQL checkpointer | 可靠派发、节点编排、幂等恢复；不在 HTTP 请求中执行长任务 |
| 数据与分析 | PostgreSQL + pgvector、云端 Embedding、scikit-learn | 证据与向量存储/检索，CPU 聚类；HNSW 按规模与召回测试决定 |
| 云端模型 | Claude LLM/VLM；云端 BGE-M3 候选 | 仅后端持有凭证；受限流、预算、数据授权与质量验证约束 |
| 契约与实时 | 后端 DTO → OpenAPI/事件 schema → TS 客户端；EventSource | 契约生成、有序 SSE 回放与真实状态展示 |
| 验证 | vue-tsc、Vitest、Playwright；pytest、Ruff、mypy | 类型、组件、真实 PostgreSQL 集成、端到端与独立模型评测 |

前端工具运行时采用 Node.js 24 LTS 基线；PostgreSQL 18 为数据库候选基线。具体补丁版本、数据库扩展和容器组合在实际初始化中验证后锁定，不将选型表当成已经通过的兼容性矩阵。

## 分阶段交付

- **P0**：Amazon US 单品类、已验证 ASIN/时间窗的文本闭环；实际评论样本 → 云端 Embedding → CPU 聚类 → 云端 LLM 双栏建议 → 基础证据反查与 SSE 看板。样本不足不补造，财务为 `NOT_EVALUATED`。
- **P1**：云端视觉取证、确定性财务否决、图片与深度证据反查。
- **P2**：历史回测、TikTok/Temu 映射和供应链信号；不作为当前已实现功能。

## 开发与实施

当前可执行的基础命令如下；它们只能证明脚手架、基础入口和容器基座可运行，不能证明业务链路已实现。

```bash
# 前端开发
cd frontend
bun install
bun run dev

# 后端开发
cd backend
uv sync
uv run uvicorn insightx.main:app --reload --port 8000

# 单机容器基座
docker compose -f infra/compose.yaml up -d --build
```

当前 `/api/v1/health` 返回 `degraded`，因为数据库与 Redis 探针尚未接入。后续先完成 M0 数据/云端模型验证，再按独立计划补齐契约、迁移、任务链路和一个真实 ASIN 的端到端闭环；每次实施遵循“计划 → 确认 → 执行 → 验证 → 结果”。

目标部署优先采用同域反向代理与服务端会话；Windows 开发使用 Docker Desktop/WSL2 的 Linux Worker，不承诺 Celery 原生 Windows 支持。普通 CI 使用明确标识的 fixture/mock；真实云端调用单独批准并设置预算，不能以 mock 通过宣称模型已接通。

## 文档

- [PRD](PRD.md) — 产品需求、阶段边界与验收目标
- [架构与技术选型](docs/architecture.md) — monorepo、前后端、云端模型、任务/证据、安全、测试与官方参考
- [工作约定](AGENTS.md) — 强制计划、审批和结果记录流程
- [本次获批设计计划](docs/plans/2026-09-12-monorepo-architecture-selection/plan.md) — R1 云端方案与真实审批记录
