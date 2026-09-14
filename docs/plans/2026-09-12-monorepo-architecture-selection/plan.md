# InsightX monorepo、前后端选型与 PRD 修订计划

## 1. 目标与本次边界

基于项目目标和官方资料，形成适合比赛/MVP 阶段、可以逐步演进的 monorepo 与前后端架构，并修正 PRD 中与该架构、阶段边界及可验证性不一致的描述。

本次用户所称“RPD”按根目录 `PRD.md` 理解。本次实施范围仅为**设计文档、PRD 和 README**；不是搭建整个项目，不创建代码脚手架、依赖清单、锁文件、数据库迁移、容器配置或 CI 文件。下文目录树与技术栈是获批的目标设计，不是已存在的实现。

推荐结论：**轻量异构 monorepo + 模块化单体 + 独立 Worker；保留 Vue/FastAPI/Python AI 生态，通过生成的 HTTP 契约衔接，不引入微服务或重型 monorepo 平台。**

**R1 修订约束（2026-09-12）：根据用户“修订吧，模型使用云端模型”，LLM、VLM 和 Embedding 全部通过云端 API 使用，不在开发机或项目服务器部署模型权重、GPU/CUDA 推理环境或本地推理服务。项目侧仅执行业务编排、数据清洗、CPU 聚类和存储。** 原计划中的 Worker 本地 BGE-M3 推理路径已取消；其余 monorepo、前后端与文档实施范围不变。本次云端修订版已获用户确认，真实审批信息见第 11 节；批准仅覆盖文档实施，不代表模型或业务功能已接通。

## 2. 当前事实与依据

- 已完整读取当前 `AGENTS.md`、`PRD.md`、`README.md`。PRD 的目标用户是能够真正改款的工贸一体企业与精细化卖家，不是通用聊天应用或纯铺货工具。
- `PRD.md:43–45` 将 P0 限定为 Amazon US、单品类、已验证 ASIN/时间窗、文本分析、双栏建议与看板；视觉取证和财务否决属于 P1，回测与多平台属于 P2。
- 当前工作区没有 `frontend/`、`backend/`、可执行代码、依赖清单或 API 契约。`git status` 保留 127 个既有未暂存删除；`AGENTS.md` 已有上一任务的未暂存修改，根目录 PRD 和上一任务记录尚未跟踪。不能从旧 README 推断功能已实现。
- README 仍列出无法运行的旧启动说明、缺失文档链接以及“接口为 501 占位”的旧状态，需随正式架构文档同步纠正。
- `docs/architecture.md` 当前不存在且没有同名已跟踪文件；新增此文件，不恢复已删除的 `docs/技术方案.md` 或 `docs/api.md`。
- 本任务开始前的 `AGENTS.md` SHA-256 为 `ec98dda0421d90474abb2d193f0d89b2743cf593077da24dc550565e3f35ddc6`；本次不修改该文件，也不改上一任务的计划和结果。

### PRD 中需要明确的问题

| 位置 | 当前问题 | 本次拟修正方向 |
| --- | --- | --- |
| 文档头、第 6 节 | 写死框架小版本与 Claude 3.7，未附兼容性实测 | 产品文档只列技术方向；实现阶段锁定经过验证的版本与有效模型 ID |
| P0-02、第 6 节、M2 | 将 pgvector 检索与聚类混为一谈，强制 HNSW | 区分向量存储/检索、聚类算法和标签生成；索引按规模实测决定 |
| P0-04、第 5.1 节 | P0 包含预测 FBA 金额、固定 7 节点和风险结果展示 | 未执行的 P1 能力明确未评估；看板跟随实际阶段与节点，而非假进度 |
| 第 6 节 | 通用链路默认执行视觉、财务；状态示意只包含单个 ASIN | 明确 P0 主路径、P1 可选分支、批次与单 ASIN 工作单元 |
| P0-01、第 8 节 | 前文说明采样目标非保证，后文仍简写“抓取 200–500 条” | 全文统一实际样本数、来源与缺失说明，不把配额当成功数据 |
| P0-02、第 8 节 | 固定 Top 5 容易变成补足五个痛点 | 展示有证据支持的最多 5 类；不足时如实展示 |
| 第 7 节 | 全链路 30–60 秒混入外部采集和 P1，其他性能/SLA 无测量条件 | 保留目标，但限定测量范围与环境，未实测不作交付保证 |
| 第 7.2 节 | 多租户、“强加密”缺乏可验收边界 | 明确身份、租户授权、TLS、受控存储加密、密钥与隔离测试 |

## 3. 设计假设与决策标准

- 以现有 PRD 的比赛/MVP、单区域、小规模初始部署为假设；真实团队人数、云平台、预算、数据授权、模型账户与访问区域均未提供，不捏造这些条件。云端模型是用户明确要求，不将本地 GPU 作为项目运行前提。
- 优先级：证据可信与隔离正确 > 完整最小业务闭环 > 故障可恢复 > 开发效率 > 大规模优化。
- 不将“最新版本”“目录更多”或“使用某个 monorepo 工具”等同于最佳实践。以下是针对本项目的工程判断，不是官方对 InsightX 的背书。
- 数据来源、模型实调用和性能验证沿用 PRD 已有的 M0-A 前置门禁；本次不通过架构文档伪造门禁通过。

## 4. 已批准的架构决策（R1）

### D1. Monorepo：保留 frontend/backend，语言工具分治

```text
ai-plus/
├── PRD.md
├── AGENTS.md
├── README.md
├── frontend/                         # 一个 Vue 应用；以下均为未来目标
│   ├── package.json
│   ├── bun.lock
│   ├── src/
│   │   ├── app/                      # 启动、路由、全局 provider
│   │   ├── features/                 # tasks、insights、proposals、evidence
│   │   ├── components/               # 真正跨功能复用的组件
│   │   └── api/generated/            # 后端契约生成的 TS 客户端，不手改
│   └── e2e/                          # 覆盖前后端真实闭环的 Playwright 测试
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── src/insightx/
│   │   ├── api/                      # HTTP、认证依赖、DTO、SSE
│   │   ├── modules/                  # tasks/reviews/analysis/reports 业务边界
│   │   ├── workflows/                # LangGraph 节点与图
│   │   ├── integrations/             # 数据供应方与云端模型 API 接入
│   │   ├── db/                       # 数据库会话与基础定义
│   │   ├── worker.py                 # 任务消费入口
│   │   └── dispatcher.py             # 事务 outbox 派发入口
│   ├── migrations/                   # Alembic 迁移
│   └── tests/                        # 单测、真实 PG 集成、质量评测样本
├── contracts/
│   ├── openapi.json                  # 从后端导出，不作为第二份手写契约
│   └── task-events.schema.json        # 从后端事件 DTO 导出
├── compose.yaml                      # 后续基础设施实施任务再创建
├── .github/workflows/                # 后续 CI 实施任务再创建
└── docs/
    ├── architecture.md               # 本次获批后新增的正式设计
    └── plans/                        # 保留任务计划与结果
```

- 这是一个 Git 仓库中的两个语言项目，不是两个仓库；前后端共享评审、契约与集成测试，不共享运行时业务代码。
- 继续使用 Bun 管理前端依赖、uv 管理后端依赖，各一个锁文件。不在 Python 项目套一层伪 `package.json`，不混用 bun/npm/pnpm 多份锁文件。
- P0 只有一个 JS 应用和一个 Python 包，不先引入 Bun workspace、uv workspace、Turborepo、Nx 或空的 `packages/shared`。出现第二个真实共享包后，再按依赖关系评估 workspace；uv workspace 会共享依赖解析和锁文件，不是所有 Python 子项目都适用。[S4–S6]
- API、Worker、派发器共享同一个 Python 业务包、模型定义和版本；不同进程不等于微服务。不拆独立 `worker` 包并复制数据库模型。
- 前端按照功能组织；后端按业务模块组织，不先造通用 Repository 框架、插件平台或层层空抽象。

### D2. 前端：Vue SPA，不为管理工作台引入 SSR

| 项目 | 推荐 | 取舍 |
| --- | --- | --- |
| 应用与构建 | Vue 3、TypeScript strict、Vite | 保留既有 Vue 方向，不为套用 FastAPI 模板而切换 React；工作台未要求 SEO/SSR，不引入 Next/Nuxt。Vue 官方推荐 create-vue/Vite。[S1] |
| 工具运行时 | Node.js 24 LTS；Bun 作为包管理器 | Node LTS 为构建工具兼容基线，不要求工具全部切到 Bun runtime；具体补丁版在初始化验证后锁定。[S4, S21] |
| 路由与状态 | Vue Router、TanStack Vue Query、Pinia | Query 管任务/报告等服务端状态；Pinia 仅管跨页 UI 状态，不维护第二份 API 数据缓存；局部表单用组件状态。[S2] |
| 组件与样式 | Element Plus + CSS variables / scoped CSS | B2B 表格、表单、抽屉、进度、确认操作优先成熟组件；明确替换 PRD 中默认 Tailwind 方案，不同时上第二套组件库或 Tailwind。[S3] |
| 图表 | ECharts，按使用模块导入 | 保留 PRD 图表方向；数据来自报告，不在前端重新计算财务裁决 |
| HTTP 契约 | Pydantic/OpenAPI → Hey API TS 客户端，使用 Fetch | 借鉴 FastAPI 官方生成 SDK 路径，避免双端手写接口类型；生成目录禁止手改。[S7] |
| 实时状态 | 原生 EventSource + 自有事件 DTO 契约 | REST 负责创建/取消/查询，SSE 负责状态观察；不引 WebSocket/Socket.IO |
| 验证 | vue-tsc、ESLint、Vitest + Vue Test Utils、Playwright | Vite 构建不代替类型检查；组件单测与真实浏览器闭环分层。[S1, S20] |

组件库选择是效率取舍，不声称 Element Plus 在所有设计或性能场景中优于替代品。自定义品牌视觉通过主题 token 实现；如果后续目标变成高度定制的营销站，再独立评估无样式组件体系。

### D3. 后端与数据：可理解的模块化单体

| 项目 | 推荐 | 边界 |
| --- | --- | --- |
| 语言与 HTTP | Python 3.12、uv、FastAPI、Pydantic 2 / settings | 保留 Python AI 生态和 HTTP 分离；具体依赖版本以兼容性验证和 uv.lock 为准 |
| 关系数据 | PostgreSQL 18 候选基线、SQLAlchemy 2、psycopg 3、Alembic | PostgreSQL 是业务任务、报告、证据与事件的事实源；生产镜像/扩展组合需 M0/M1 实测，不宣称当前已兼容。[S8, S9, S12] |
| 初始数据库并发模型 | 同步 SQLAlchemy；常规数据库路由使用 def | 适配同步 Celery/分析生态，避免 P0 同时维护两套数据访问服务；SSE 异步循环将短数据库查询交给线程池，Session 在访问单元内创建/关闭，禁止并发共享。[S8] |
| 长任务 | Celery 5 系列 + Redis broker | 采集、向量化与模型调用不放在 FastAPI BackgroundTasks 或请求进程中执行；队列重投按至少一次语义设计。[S7, S10] |
| 工作流 | LangGraph + PostgreSQL checkpointer | 管节点、分支和恢复，不代替队列；业务表不代替 checkpoint，checkpoint 也不代替业务报告和前端事件。[S11] |
| 云端推理 | 云端 LLM/VLM API + 独立 Embedding API | Worker 调用服务商 API；项目侧不安装本地模型权重或推理引擎；不能假定 Claude 提供 Embedding。[S22, S23] |
| 向量与聚类 | 云端 BGE-M3 Embedding（1024 维基线）+ pgvector + scikit-learn | Embedding 在云端生成，pgvector 管存储/检索，CPU 聚类仍在 Worker 内执行；实际云端返回维度由 M0 验证。[S12–S14, S22] |
| 测试与质量 | pytest、Ruff、mypy；真实 PostgreSQL 集成测试 | 不用 SQLite 替代 pgvector、并发、事务和迁移测试；模型质量评测与普通确定性测试分开 |
| 多模态资产 | P1 采用 S3 兼容对象存储 | P0 文本快照留 PostgreSQL；不提前部署 MinIO 或把大图片塞进 checkpoint |

普通 REST 查询与 SSE 的数据库访问均保持短事务。网络采集、推理与长时间等待期间不占用数据库事务。是否全面异步化由连接量与压测决定，而不是为了“用了 FastAPI”就假定所有库均为异步。

### D4. 任务可靠性、事件和进程职责

拟定主链路（不是现有 API）：

1. 浏览器以幂等键提交 `POST /api/v1/tasks`；API 校验用户/租户、1–10 个 ASIN、站点和时间窗。
2. 在同一 PostgreSQL 事务中记录 task、task_items 和待派发 outbox，然后返回 `202 + task_id`。避免“数据库已提交但 Redis 未入队”的无声丢任务窗口。[S17]
3. 轻量 dispatcher 从 outbox 派发到 Celery；它与 API/Worker 同包、可独立运行，不引入另一个业务服务。派发重复是允许的，消费必须幂等。
4. Worker 以单 ASIN 工作单元运行 LangGraph；记录尝试编号、限时、心跳/失效处理和有效执行所有权，避免重复投递及旧尝试覆盖新结果。外部调用、节点重试与队列重投共享预算，防止多层重试放大成本。[S10, S11]
5. PostgreSQL 持久记录单调有序的任务事件；SSE 从事件记录读取并支持断线续传，不把 Redis Pub/Sub 当唯一事件来源。浏览器断开不取消任务；取消通过 REST 显式提交，并由节点边界检查。[S16]
6. 看板按真实节点与工作单元展示状态。任务生命周期、报告数据质量、财务裁决分离；P0 财务状态为 `NOT_EVALUATED`，不能显示伪造的绿灯或 0 美元收益。

落地时必须验证：DB 提交后派发器崩溃、broker 暂时不可用、Worker 被终止、重复消息、节点恢复、取消与断线重连。Redis 持久化和超时需明确配置；不能仅靠默认设置宣称零丢失或 exactly-once。自动恢复、手动重试与不可恢复错误的产品提示要有明确边界。

### D5. AI 与证据：先可信，再谈“智能”

- P0 主路径：采集/导入已验证来源 → 清洗与评论片段 → 调用云端 Embedding API → CPU 聚类与云端 LLM 标签/双栏建议 → 引用校验与报告。P1 的 VLM 同样调用云端 API；视觉与财务不伪装为 P0 已执行节点。
- 采集供应方需在既有 M0-A 验证原文授权、分页、时间覆盖、child ASIN、字段质量和费用。架构不指定一个未经测试的供应商，也不承诺普遍获得全量评论。Fixture 必须标记为合成/演示，不能充当真实采集成果。
- Embedding 保留 BGE-M3 Dense 1024 作为基线，但仅使用云端托管 API。优先验证候选为 SiliconFlow 的 `BAAI/bge-m3`，其官方 Embedding 文档列有该模型；实际账户可用性、返回维度、输入/批量限制、质量、费用和数据处理条款在 M0-A 验证后确认，不把文档列举当成账号已开通或当前无条件可用。[S14, S22]
- P0 聚类基线采用 scikit-learn 的凝聚层次聚类（cosine + average linkage，阈值由小样评测确定，不写死虚构阈值）。按单 ASIN/限定快照处理，避免无限扩大距离矩阵；小簇标记低支持，不声称该算法自动识别噪声。HDBSCAN 仅作为对照候选，不同时上线两套算法。[S13]
- 按有证据支撑的结果展示最多 5 类；不足 5 类不补造，零有效评论不生成建议。“采样中的差评占比”不能冒充商品总体差评率。
- pgvector 初始使用精确检索与业务过滤索引。HNSW 是后续经过召回、租户过滤和容量测试的优化，不是 P0 无条件前置；近似索引过滤可能影响返回数量，需要实测。[S12]
- LLM/VLM 保留 Anthropic Claude 云端 API 方向，不再把 Claude 3.7 写成固定依赖；在 M0-A 依据账户/区域可用性、官方生命周期、结构化输出质量、语言和成本选择 Active 模型并记录准确 model_id。Anthropic 官方说明其不提供自有 Embedding 模型，故 Embedding 独立接入，不假定两类 API 或密钥可以通用。[S15, S23]
- 每条建议引用同任务/同租户的真实评论或片段 ID；保存来源、采集/评论时间、内容哈希、快照、模型与 prompt 版本、用量。格式验证不能替代语义证据校验；无支持的结论标记不足，不能凭空填工程尺寸和收益数字。
- P1 视觉框与归因是需要验证的模型输出，不是物理测量或因果证明；坐标必须处理图像缩放并抽样复核。[S15]
- P1 财务判断由确定性、版本化公式执行，保留输入与费率依据；LLM 仅解释/建议。P2 回测要区分时间截断数据与模型可能已有知识，不声称实现了严格因果验证。

#### 云端模型接入与运行约束

- 云端模型仅由后端 Worker 通过服务商支持的官方 SDK 或 HTTP API 调用；前端只访问 InsightX 后端，不持有模型密钥、不直连供应商。优先实现选定供应商的最小接入，不增加通用多模型网关或默认跨厂商自动路由。
- 不安装用于本地模型推理的 PyTorch、Transformers、FlagEmbedding，不部署 Ollama、vLLM、GPU/CUDA 服务，不下载模型权重作为开发或故障兜底步骤。scikit-learn 的 CPU 聚类不是托管大模型推理，仍按既定算法在 Worker 执行。
- 每次外部调用有明确的超时与任务总预算；按供应商限制确定批量大小和并发。区分鉴权失败、模型不可用、额度不足、限流、超时和服务端错误；只重试可恢复错误，响应含 `Retry-After` 时遵守它，SDK 重试与节点/任务重试纳入统一预算，不对所有 429 无限重试。[S24]
- 云端不可用时只复用合法、同租户且匹配快照/模型配置的已验证缓存，或明确失败/标记受影响部分未完成；不静默切回本地模型、不生成假向量/假报告，也不自动切换成未验证的另一个 Embedding 模型。
- Embedding 存储与缓存记录供应商、准确 model_id、实际维度、应用侧 embedding 版本及可获取的供应商版本信息。不同模型/维度不得混入同一向量空间；同名模型的不同托管实现也不预设等价。切换供应商或模型时单独评审质量回归与重建向量/索引的范围。
- 调用日志保存可取得的供应商请求 ID、实际用量和耗时；费用按可核验的供应商计费口径计算并标识估算，不把模型 token 数直接当成已支付账单。输入/输出只传和保留业务所需数据，凭证与敏感原文不进入普通日志。

### D6. 前后端契约、鉴权与部署

- 后端 Pydantic DTO 是 HTTP/事件结构的单一来源；导出 OpenAPI、事件 schema 和前端客户端，CI 重新生成后检测漂移。不能同时维护互不校验的手写 TS/Python 类型。[S7]
- SSE 不是普通 JSON 请求：事件版本、id、type、task/item、时间和 payload 要有契约；后端实现事件回放，前端去重并更新 Query cache。终态或组件卸载关闭连接。不能以 OpenAPI 客户端生成代替 SSE 协议实现。[S16]
- 部署保持独立前后端构建，但优先由同域反向代理分流 SPA 与 `/api`。采用服务端会话与 HttpOnly/Secure/SameSite cookie，避免浏览器持久化 bearer token 或把长期 token 放 SSE URL；写操作做 CSRF 防护。同源并不破坏前后端分离。[S18]
- P0 使用受控账号与最小登录/退出会话，不扩展公开注册、支付和完整身份管理平台；公开多租户部署前仍必须完成租户隔离验收，不以演示身份冒充真实鉴权。
- 用户提供的 tenant_id 只能作为选择器，后端必须核验成员关系；REST、SSE 回放、缓存、证据和 Worker 均验证租户边界，不能仅靠前端隐藏按钮。[S18]
- HTTPS、基础设施存储/备份加密、最小权限和服务端密钥管理取代笼统“强加密”描述；生产所用云服务的具体实现另行审核。日志不记录密钥、完整会话或不必要的原文敏感数据。
- 云端推理涉及第三方数据处理：上传前最小化非必要个人信息，不默认上传完整企业财务资料或工程图纸；数据授权、服务区域、保留/训练条款与跨境要求按选定供应商核对。不未经核验承诺“零保留”或“不会用于训练”。
- 采用 Docker Compose 的 Linux 容器作为联调/部署基线；Celery 官方不支持 Windows 原生，Windows 开发环境明确使用 Docker Desktop/WSL2 的 Linux Worker，不用未支持模式作承诺。[S10]
- 依赖健康检查、数据库迁移完成和服务就绪分别处理；Compose 的启动顺序不等于服务已 ready。[S19]
- P0 先做结构化日志与 request_id/task_id/item_id、节点耗时、重试、模型用量的关联；不默认安装整套可观测平台。单机 Compose 不宣称自带高可用。

### D7. 测试、版本与渐进交付

- 前端与后端分别执行 lint/typecheck/test/build；涉及 contracts/backend DTO 的修改必须触发前端生成与集成检查，不能只按目录跳过消费者。
- 关键闭环测试覆盖：任务创建、无数据、部分 ASIN 失败、真实证据引用、租户越权、取消、重试、Worker 恢复、SSE 回放和 P0 未评估财务状态。普通 CI 使用明确标识的云端响应 fixture/mock，不下载真实模型或无预算调用云 API；它们不能冒充真实模型质量证据。真实模型调用作为单独、经批准且有预算的 M0/质量验证。[S20]
- 云端接入门禁还覆盖：凭证/区域可用性、模型 ID、Embedding 返回维度与顺序、输入/批量限制、限流/额度/超时处理、结构化结果、用量和恢复行为；通过前不得宣称模型已接通。
- 依赖、Node/Python、数据库扩展和容器版本在首次真实初始化时锁定并走冻结安装；本次不写未经验证的“最新小版本矩阵”。版本升级以兼容性和质量回归为门禁。
- 先完成已有 M0-A 数据/模型验证，再实施仓库骨架与契约，再打通一个真实 ASIN 的文本链路，然后批次/恢复/隔离验收；P1/P2 不同时开工。

## 5. 正式 PRD 的修订范围

1. 文档版本更新为 V1.2，记录本次实际修订日期与目的；更新高层技术栈并链接正式架构，明确 LLM、VLM、Embedding 统一云端 API、无本地模型推理部署。不搬入底层库 API 或完整实施步骤。
2. 保留目标用户、价值主张和 P0/P1/P2 产品方向；按 D2 将默认组件/样式方案调整为 Element Plus，其他页面设计不顺手重写。
3. 修正 P0 评论采样、聚类职责、最多 5 类、数据不足和看板指标说明；不降低“不得造假、证据可追溯”的要求。
4. 更新第 6 节 Mermaid 和状态示意，区分 API/异步 Worker、外部云端 LLM/VLM 与 Embedding 服务、批次与单 ASIN、持久事件、P0 主路径和 P1 分支；Worker 不承担模型权重推理。接口路径改为架构中的拟定任务资源风格，并注明实际契约待代码导出，而不是已实现 API。
5. 保留 P0 基础证据关联、P1 多模态深度反查的层次；明确视觉定位/物理归因需要验证，财务裁决来自确定性计算而非模型“决定”。
6. 修改 NFR 的验收口径：数据库基础查询 P95、SSE 时延、向量检索与整体任务时间分别注明数据量、硬件/并发、测量起止点及是否包含外部等待；30–60 秒、50ms、99.5% 均不得写成已实现的无条件保证，M0/M1 形成基线后再确认承诺值，不凭空换一个更宽松数字。
7. 细化多租户、加密和云端数据处理的可验收边界；重复执行、供应商限流/额度与统一重试预算、无数据/降级状态与证据完整性可追踪；M0 明确云端模型与 Embedding 接入验证，而非本地推理环境验证。
8. 同步第 8 节 MVP 范围和第 9 节里程碑：消除采样承诺冲突，移除强制 HNSW 和“固定七步”，加入现有目标所需的契约、恢复与隔离验收，不提前承诺 P1/P2 完成。

## 6. 预计变更文件

| 文件 | 实际实施范围 |
| --- | --- |
| 本目录 `plan.md` | 当前计划；批准后补真实审批记录，重大修订重新审核 |
| `docs/architecture.md` | 新增正式 monorepo、前后端、任务/数据/证据、安全、部署测试设计，含取舍、阶段、官方参考与未验证项 |
| `PRD.md` | 按第 5 节局部修订产品需求，不整篇改成技术实施文档 |
| `README.md` | 同步目标布局、技术摘要、当前“仅文档”状态与有效链接；移除旧可运行/501 断言，命令只在有真实脚手架后再加入 |
| 本目录 `result.md` | 实施和验证后独立记录真实结果；失败或中止也如实记录 |

**不修改** `AGENTS.md`、`.gitignore`、`LICENSE`、上一任务记录；**不恢复**任何既有删除。目录树中的代码、contracts、compose、CI、依赖文件本次均不创建。

## 7. 实施步骤与分工

1. 向用户展示推荐架构、主要取舍、PRD 修订范围和计划路径，停止等待明确批准。上一任务的“开始实施”不适用于本次新计划。
2. 批准后记录用户原文和真实日期，复核工作区。若用户要求更换框架、包管理器、队列、布局、鉴权或扩大到脚手架，先修订本计划并重新确认。
3. 根据 D1–D7 编写 `docs/architecture.md`，明确“选型决定”“后续验证门禁”“已实现状态”三者，不把官方资料表述成基准测试。
4. 按第 5 节对 `PRD.md` 做有范围的修改，并同步 README。保留产品业务方向，不额外新增运营监控、完整 SSO、多平台爬虫等功能。
5. 执行文档检查，逐项对照需求和本计划检查一致性。
6. 生成本目录 `result.md`，报告真实改动、验证、偏差、限制和未执行项。

分工：当前没有可直接调用的子代理工具，Paseo CLI 也未发现；由主代理完成本地核对、官方资料多主题调研、设计、修改和验证。不为形式化分工安装工具或启动其他外部服务。

## 8. 验证与验收

### 本次实际应执行的文档验证

- 完整回读 `PRD.md`、`README.md`、`docs/architecture.md` 和本任务记录；核对目标布局、模型/任务职责、P0/P1 边界、样本与状态说明一致。
- `git diff --check -- PRD.md README.md docs/architecture.md docs/plans/2026-09-12-monorepo-architecture-selection/`。由于 PRD 和新增文件可能未跟踪，另用只读文本检查验证这些文件的格式、围栏与行尾空白，不依赖 Git 覆盖它们。
- 用 `git diff -- README.md`、完整文件回读和源文件基线对照审核改动。旧 PRD Mermaid 存在行尾空白，修订涉及的段落可清除这些空白，不扩展为全仓格式化。
- 用 `rg` 检查残留的已作废架构描述及固定型号/阶段冲突，特别检查三份正式文档没有把本地模型推理、下载权重或 GPU/CUDA 写成运行前提；上下文审阅区分禁止事项、历史说明与现行要求，不能为了零命中删除真实历史记录。
- 用现有 Node.js 只读脚本检查 Markdown 本地链接确有对应文件，区分代码块中的未来目录与实际链接；代码块/表格完整性做文本和人工检查。不安装 Markdown/Mermaid 渲染器，不冒称完成视觉渲染验证。
- `git status --short` 与 `sha256sum` 核对只修改获批文件，127 个既有删除和上一任务记录不变；不暂存或提交。
- 本次不运行应用构建、业务测试、数据库、模型或付费采集调用；这些属于后续实施和 M0 验证，不能计入本次完成证据。

### 验收条件

- 用户能明确知道仓库怎么分、每个语言用什么工具、API/Worker/队列/数据库/图的职责、为什么保留或不采用候选方案。
- PRD 与架构、README 不互相冲突，不包含“实际上尚无代码却可以启动”的描述；正式文档有清楚的当前状态和演进门禁。
- 版本、数据、模型和性能等未实测项如实标识；安全、恢复与证据需求不因“最小化”被取消。
- LLM、VLM、Embedding 均为后端调用的云端服务；正式文档一致说明无本地模型部署、供应商与维度验证、凭证/数据边界及失败处理，普通 CPU 聚类与模型推理职责明确分开。
- 前后端仍只经 HTTP 通信，跨语言共享的是生成契约，不通过导入对方源码连接业务。
- 只产生第 6 节获批文档改动和本任务记录，未提前搭建目标目录。

## 9. 官方资料、证据强度与调研限制

调研日期：2026-09-12。以下链接均来自本次检索返回的官方项目文档或官方模型卡；用于支持工具能力和风险边界，具体架构组合是本任务建议。

| 编号 | 官方来源 | 支持的决策 |
| --- | --- | --- |
| S1 | [Vue Tooling](https://vuejs.org/guide/scaling-up/tooling)、[TypeScript](https://vuejs.org/guide/typescript/overview) | create-vue/Vite、独立类型检查 |
| S2 | [TanStack Query 与 Pinia 的职责](https://tanstack.com/query/latest/docs/framework/vue/guides/does-this-replace-client-state) | 服务端状态与客户端状态分离 |
| S3 | [Element Plus Quick Start](https://element-plus.org/en-US/guide/quickstart)、[Theming](https://element-plus.org/en-US/guide/theming) | 组件导入和主题定制 |
| S4 | [Bun Workspaces](https://bun.sh/docs/pm/workspaces)、[Lockfile](https://bun.sh/docs/pm/lockfile) | Bun 工作区和冻结锁文件能力，不将 workspace 视为单包必需品 |
| S5 | [uv Workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) | 共享解析/锁文件及不适合使用 workspace 的场景 |
| S6 | [Turborepo 结构](https://turborepo.com/docs/crafting-your-repository/structuring-a-repository)、[pnpm Workspace](https://pnpm.io/workspaces) | 备选工具的工作区结构；不声称它们不能编排 Python |
| S7 | [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)、[Generating SDKs](https://fastapi.tiangolo.com/advanced/generate-clients/)、[Full Stack Template](https://fastapi.tiangolo.com/project-generation/) | 长任务外置、生成客户端、借鉴工程实践但不照搬 React 模板 |
| S8 | [FastAPI async/await](https://fastapi.tiangolo.com/async/)、[SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) | 同步路由线程池与会话并发边界 |
| S9 | [Alembic Autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) | 迁移只是候选结果，需审核与验证 |
| S10 | [Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)、[Redis broker](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)、[Windows FAQ](https://docs.celeryq.dev/en/stable/faq.html) | 幂等、迟确认/可见性超时、Windows 不受官方支持 |
| S11 | [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)、[Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)、[Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api) | 持久恢复、thread_id 和副作用重复执行风险 |
| S12 | [pgvector 官方 README](https://github.com/pgvector/pgvector/blob/master/README.md) | 默认精确检索、ANN 取舍、过滤风险与 PostgreSQL 支持信息 |
| S13 | [AgglomerativeClustering](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.AgglomerativeClustering.html)、[HDBSCAN](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html) | 聚类基线与对照算法能力，不虚构阈值或精度 |
| S14 | [BAAI/bge-m3 模型卡](https://huggingface.co/BAAI/bge-m3) | 多语言向量基线 |
| S15 | [Claude 模型生命周期](https://platform.claude.com/docs/en/about-claude/model-deprecations)、[Vision](https://platform.claude.com/docs/en/build-with-claude/vision)、[Vision Coordinates](https://platform.claude.com/docs/en/build-with-claude/vision-coordinates) | 不固定旧型号；图像坐标与缩放需要处理 |
| S16 | [MDN SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)、[EventSource 构造器](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource) | event id、重连、凭证边界 |
| S17 | [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) | 数据库与消息双写、重复消息和幂等消费 |
| S18 | [OWASP Session](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)、[CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)、[Multi Tenant](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html) | cookie/CSRF、服务端租户授权 |
| S19 | [Docker Compose Startup Order](https://docs.docker.com/compose/how-tos/startup-order/) | 启动顺序不等于就绪，依赖健康检查 |
| S20 | [Vue Testing](https://vuejs.org/guide/scaling-up/testing)、[Playwright CI](https://playwright.dev/docs/ci) | 分层测试与可重复 CI |
| S21 | [Node.js 24 LTS 公告](https://nodejs.org/en/blog/release/v24.11.0) | 采用受支持的 Node LTS 作为工具运行时基线 |
| S22 | [SiliconFlow Embeddings API](https://docs.siliconflow.cn/en/api-reference/embeddings/create-embeddings)、[Embedding 输入说明](https://docs.siliconflow.cn/docs/api/embeddings-post) | 云端 BGE-M3 候选、批量输入与模型限制；实际账户能力仍需验证 |
| S23 | [Claude Embeddings](https://platform.claude.com/docs/en/build-with-claude/embeddings) | Anthropic 不提供自有 Embedding 模型，需独立供应方 |
| S24 | [Claude API Errors](https://platform.claude.com/docs/en/api/errors)、[Rate Limits](https://platform.claude.com/docs/en/api/rate-limits) | 区分限流与额度限制、SDK 重试及 Retry-After 行为 |

### 证据限制（不得省略）

- `web_search` 已返回上述官方来源的索引摘要或正文片段；没有将第三方比较文章当作官方能力保证。
- `fetch_content` 直连 6 个官方站点均被本机 fake-IP/TUN 地址的 SSRF 安全检查阻止，自动正文获取也未成功。因此**未声称完整抓取或通读远端页面正文**，未修改代理或安全配置绕过检查。
- 一次 `source_check` 返回 `missing-evidence`，个别严格查询返回无可用结果/提供者；这些不作为核验通过。关键职责结论改由可用官方索引片段交叉核对；本计划不采用未经独立确认的精确退役日期或某一最新小版本的全栈兼容断言。
- 没有真实安装、启动、账号模型调用、数据采集、压测或费用账单验证。正式架构必须保留这些 M0/M1 门禁，而不能把资料调研当作运行测试。

## 10. 风险与非目标

- Celery/Redis/outbox/checkpoint 增加一定运维与可靠性实现成本，但与 PRD 的异步任务和恢复目标直接相关。PostgreSQL 队列（如 Procrastinate）是减少 broker 的备选；本次不因少一个服务就采用尚未验证的替代集成，也不从零自建通用队列。
- Element Plus 替代 Tailwind 是本计划明确请求审核的前端取舍；若用户更重视完全定制视觉，应在批准前调整，不在实施中悄悄双栈叠加。
- 云端 LLM/VLM/Embedding 的账户、区域、模型可用性、限流、费用、向量兼容性，以及真实评论供应方权限和数据保留合规仍待验证；不以“使用云端”推导无限容量、固定价格或必然达到时延目标。SiliconFlow 为待验证候选，不是已采购/开通的服务。
- 单机 Compose 不是高可用方案；Redis/其他依赖具体版本、许可证及生产托管条件需在选定发行版时核对。
- 不引入微服务、Kubernetes、Kafka、独立向量数据库、SSR、付费后台模板、完整身份平台、本地模型推理/权重/GPU 集群、额外多平台能力或新的产品角色。
- 不安装依赖、不创建脚手架、不恢复旧实现、不改变 `AGENTS.md` 的计划审批流程、不暂存/提交/推送/部署。

## 11. 审核状态

- 状态：**已批准**（R1：云端模型修订版）。
- 创建日期：2026-09-12（来自本机 `date` 命令）。
- R1 修订日期：2026-09-12（修订时通过本机 `date` 命令核对）。
- 用户原始要求：根据项目目标设计 monorepo 和包括前后端在内的技术选型，可以修改 PRD，并查找最佳实践。
- 上一版展示后的用户原文：**“修订吧，模型使用云端模型”**。
- 修订原因与范围：用户要求模型全部云端化，改变了原先 Worker 本地 BGE-M3 的部署路径及资源、凭证/数据处理、计费与故障边界。R1 明确三类模型均云端 API，取消本地推理，增加云端验证和治理要求；其他架构和文档变更文件范围不变。
- R1 批准原文：**“确定”**（云端修订版计划路径及差异展示后收到）。
- 批准记录日期：2026-09-12（实施前以本机 `date` 命令核对日期，不补造用户消息时间戳）。
- 批准范围：按本 R1 计划修订 `PRD.md`、`README.md`，新增 `docs/architecture.md`，完成文档验证并生成同目录 `result.md`；不授权脚手架、依赖安装、模型/采集调用、迁移、提交或部署。
