# InsightX · 全球跨境电商 AI 市场洞察与动态决策系统

基于 **AI 多模态取证 + Agent 决策闭环** 的出海选品与改款决策平台：将 Amazon / TikTok Shop / Temu 的多语言评论与买家实拍图，转化为工厂级双栏改款工程清单与逆向财务熔断决策。

## 技术架构

项目采用**前后端分离架构**，前后端仅通过 HTTP 协议通信（REST + SSE），由 FastAPI 的 CORS 中间件实现跨域放行：

```
ai-plus/
├── frontend/    # Vue 3.5 + Vite 8 + TypeScript 前端 SPA
│                 （Vue Router + Pinia + TailwindCSS + ECharts，bun 管理依赖）
└── backend/     # Python FastAPI 后端（统一 REST API + SSE 流式推送 + JWT 鉴权）
                  （LangGraph Agent 编排 + Celery + Redis，uv 管理依赖）
```

| 层 | 技术栈 | 说明 |
| :--- | :--- | :--- |
| 前端 | Vue 3.5 / Vite 8 / TypeScript | 独立部署 SPA，`EventSource` 直连后端 SSE |
| 后端 | FastAPI 0.141 / Python 3.12 | REST 业务接口 + SSE 实时事件流 + CORS |
| AI 引擎 | LangGraph 1.2 / Claude / bge-m3 | 7 步 Agent 状态机：采集 → 取证 → 聚类 → 双栏改款 → 财务否决 → 溯源 → 回测 |
| 数据层 | PostgreSQL 18 + pgvector / Redis 8 / MinIO | 结构化与向量混合检索、任务队列、多模态图像存储 |

## 快速开始

### 前端（Vue 3 + Vite）

```bash
cd frontend
bun install        # 或 npm install
bun run dev        # 开发服务器默认 http://localhost:5173
```

开发环境下 Vite 会将 `/api` 请求代理至后端；生产环境通过 `VITE_API_BASE_URL` 指定后端地址。

### 后端（FastAPI）

```bash
cd backend
uv sync            # 安装依赖
uv run uvicorn main:app --reload --port 8000
```

启动后访问 `http://localhost:8000/docs` 查看自动生成的 OpenAPI 文档。

## 文档

完整方案文档见 [`docs/`](docs/)：

- [01-基本信息](docs/01-基本信息.md) / [02-方案名称](docs/02-方案名称.md) / [03-方案概述](docs/03-方案概述.md)
- [04-技术方案](docs/04-技术方案.md) — 模型选型、Agent 工作流、数据管道与前后端架构
- [05-附加材料-系统架构与流程图](docs/05-附加材料-系统架构与流程图.md) — 架构图、状态机、部署拓扑
- [PRD](docs/PRD.md) — 产品需求文档与里程碑排期
- [API 接口文档](docs/api.md) — REST + SSE 接口契约（前后端并行开发依据）
