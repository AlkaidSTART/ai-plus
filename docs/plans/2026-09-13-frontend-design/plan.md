# InsightX 前端设计与 P0 基础实现（shadcn-vue · 浅色）：详细实施计划

## 目标

一次性完成"设计定稿 + 代码落地"的前端基础任务：

1. **设计定稿（内嵌于本计划第 4–8 节，即最终设计规范，不再另产设计文档）**：浅色主题、字体/字号/字重标尺、色彩令牌（含业务状态语义色）、间距/圆角/阴影、布局尺寸、5 个页面的排版规格、组件清单、状态管理与 SSE 设计。
2. **代码落地**：初始化 `frontend/`（Vite + Vue 3 + TS strict + Bun + Tailwind CSS v4 + shadcn-vue），实现应用外壳（Sidebar + Header + 路由）、主题令牌、共享组件与 5 个页面的结构化骨架（全部空态/阶段说明态，无后端、无假数据）。
3. **文档同步**：将 `docs/architecture.md`、`PRD.md`、`README.md` 中"Element Plus、不使用 Tailwind"的既有决策修订为 shadcn-vue 方案（用户 2026-09-13 明确指令），并记录修订理由。

完成后 `bun run build` 与 `vue-tsc` 通过，开发服务器可访问，5 条路由可导航且全部以诚实空态呈现。

## 当前事实及依据

### 工作区与环境（已实测）

- `frontend/` 不存在；旧 `backend/` 等 127 个文件处于未暂存删除状态，本任务不触碰。
- Node.js `v24.20.0`、Bun `1.4.2` 可用；`uv`、Docker 未安装（本任务不需要）。
- 后端不存在，OpenAPI/SSE 契约未生成：本任务所有页面数据层只留接口位与空态，**不写假数据、不手写伪契约**。

### 需求与架构依据（已读文档）

- `PRD.md` 第四节（信息架构 5 模块）、第五节（4 个核心页面布局要点与诚实展示约束）、第 6.2 节（三类状态维度：生命周期 / 数据质量 / 财务裁决 `NOT_EVALUATED`/`PASSED`/`VETOED`）。
- `docs/architecture.md`：2.1（Bun + `frontend/bun.lock`）、2.2（前端 features 职责边界）、3.1（前端选型表——其中"Element Plus，不叠加 Tailwind"一条由本任务按用户指令修订；其余 Vue 3 / TS strict / Vite / Vue Router / TanStack Query / Pinia / ECharts / Hey API / 验证分层全部保留）、5.2（SSE 行为要求）、8.2（检查分层）。
- 后端路线图计划（2026-09-13）待审核，与本任务无依赖冲突；前端联调属于后续契约存在后的独立任务。

### shadcn-vue 官方事实（2026-09-13 检索，官网直连受本机 fake-IP/TUN SSRF 拦截，以下为搜索摘要与源码片段）

- **组件模式**：组件源码经 CLI 复制进项目（`@/components/ui/`），不是运行时依赖包；基于 Reka UI；新Tailwind v4 项目默认 `new-york` 风格，`components.json` 中 `tailwind.cssVariables: true` 为默认。
- **安装**：`create vite --template vue-ts` → 安装 `tailwindcss @tailwindcss/vite` → CSS 中 `@import "tailwindcss";` → `shadcn-vue@latest init`（配置别名、`cn` 工具与 CSS 变量）→ `shadcn-vue add <组件>`。
- **主题**：CSS 变量 + Tailwind v4 `@theme inline` 映射；`:root` 浅色、`.dark` 深色；基线变量含 `--background: oklch(1 0 0)`、`--foreground: oklch(0.145 0 0)`、`--card`、`--primary`、`--muted`、`--border` 等成对令牌；动画引入 `tw-animate-css`。
- **Sidebar**：由 `SidebarProvider`（折叠状态）+ `Sidebar` + `SidebarHeader/Footer`（吸顶/吸底）+ `SidebarContent`（滚动区）+ `SidebarGroup` + `SidebarTrigger` + `SidebarInset` 组合；官方默认常量（shadcn 注册表源码）：展开宽 `16rem`、图标折叠宽 `3rem`、移动端 `18rem`、快捷键 `b`、`sidebar_state` cookie 7 天。Vue 版以实施时 CLI 实际生成代码为准。

### 既有决策冲突（必须同步修订）

`PRD.md`（头部技术方向表、P0-04、MVP 表）、`docs/architecture.md`（3.1 选型表、第 9 节取舍行）、`README.md`（选型表）均写"Element Plus，不叠加 Tailwind"。用户已明确改用 shadcn-vue（其技术底座即 Tailwind CSS v4 + Reka UI）。本计划获批即视为对该架构决策修订的批准；修订内容见"预计变更文件"。ECharts 保留（PRD 指定的图表库，与 shadcn-vue 无冲突；不引入 shadcn 图表块/Unovis，避免第二套图表体系）。

## 第 1 节 · 设计令牌：色彩（浅色，oklch/hex 双写，实施以 hex 经 Tailwind 转换）

**基线**：CLI init 生成 neutral 色系 `:root` 变量（`--background` 纯白、`--foreground` 近黑、`--card`、`--muted`、`--border`、`--input`、`--ring` 等），保持默认不逐一覆写。以下为**项目决策值**，在默认基础上新增/覆写：

### 品牌与语义色

| 令牌 | 浅色值（hex） | 用途 |
| --- | --- | --- |
| `--primary` / `--primary-foreground` | `#2563EB` / `#FFFFFF` | 主按钮、链接、运行中状态、品牌强调（覆写 neutral 默认近黑） |
| `--success` / `-foreground` | `#059669` / `#FFFFFF` | 完成、PASSED |
| `--warning` / `-foreground` | `#D97706` / `#FFFFFF` | 部分缺失、Moderate |
| `--danger` / `-foreground` | `#DC2626` / `#FFFFFF` | 失败、VETOED、Critical（复用 shadcn `destructive` 槽位） |
| `--info` / `-foreground` | `#2563EB` / `#FFFFFF` | 提示性横幅，与 primary 同色 |
| 各色 soft 底 | `*-50` 阶（如 `#FEF2F2`、`#ECFDF5`、`#FFFBEB`、`#EFF6FF`、`#F8FAFC`） | Badge/Banner 底色，前景用对应 600 阶 |

### 业务状态色映射（唯一事实源，组件不得自创颜色）

| 维度 | 取值 → 颜色 |
| --- | --- |
| 任务生命周期 | QUEUED 灰 `#64748B` · RUNNING 蓝 `#2563EB` · COMPLETED 绿 `#059669` · FAILED 红 `#DC2626` · CANCELED 灰 `#94A3B8` 描边款 |
| 数据质量 | 充足 绿 · 部分缺失 琥珀 · 无有效数据 灰（不渲染红，避免误判为失败） |
| 财务裁决 | `VETOED` 红底横幅 · `PASSED` 绿 · `NOT_EVALUATED` 灰虚线描边徽章（**不得渲染为 0 或绿色通过**） |
| 痛点严重度 | Critical `#DC2626` · Moderate `#D97706` · Minor `#64748B` |

### 图表色板（ECharts categorical，8 色循环）

`#2563EB` `#059669` `#D97706` `#DC2626` `#7C3AED` `#0891B2` `#DB2777` `#65A30D`

## 第 2 节 · 设计令牌：字体与排版标尺

**字体栈**（不引入字体包，系统栈；中文回退 PingFang/雅黑）：

```
--font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
  "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif
```

数字（KPI、金额、百分比）一律 `font-variant-numeric: tabular-nums`（Tailwind `tabular-nums`）。

| 语义 | Tailwind 类 | 字号/行高 | 字重 | 用途 |
| --- | --- | --- | --- | --- |
| KPI 大数字 | `text-3xl` | 30px/36px | 600 | 指标卡数值 |
| 页面标题 | `text-2xl tracking-tight` | 24px/32px | 600 | 每页 H1 |
| 卡片/区块标题 | `text-base` | 16px/24px | 600 | Card 标题、面板标题 |
| 正文/表格 | `text-sm` | 14px/20px | 400 | 默认正文、表格、表单 |
| 强调正文 | `text-sm` | 14px/20px | 500 | 侧边栏菜单、关键标签 |
| 辅助说明 | `text-xs text-muted-foreground` | 12px/16px | 400 | 口径注释、时间戳、徽章 |

字重仅使用 400/500/600 三档，不用 700+。行内禁用裸 `font-bold`。

## 第 3 节 · 设计令牌：间距、圆角、阴影、布局尺寸

- **间距**：4px 基准栅格（Tailwind 默认标尺）。页面容器 `p-4 lg:p-6`；区块间距 `space-y-6`；卡片网格 `gap-4`（KPI）/ `gap-6`（双栏）；卡片内边距沿用 shadcn Card 默认 `p-6`。
- **圆角**：`--radius: 0.625rem`（10px，CLI 默认）；卡片 `rounded-xl`，控件 `rounded-md`，徽章 `rounded-full`。
- **阴影**：卡片 `shadow-sm`；浮层 `shadow-md`；不使用重阴影。
- **布局尺寸**：
  - Sidebar：展开 `16rem` / 图标折叠 `3rem`（官方默认常量），`collapsible="icon"`，cookie 记忆。
  - 顶栏：高 `h-14`（56px）、`border-b`、`px-4`、内容与侧边栏分隔线对齐。
  - 主内容：`mx-auto w-full max-w-[1440px]`，纵向 `space-y-6`。
  - KPI 行：`grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4`。
  - 双栏改款：`grid grid-cols-1 xl:grid-cols-2 gap-6`。
  - 证据抽屉：右侧 Sheet，宽 `sm:max-w-xl`（576px）。

## 第 4 节 · 信息架构与路由

导航 = PRD 第四节 5 模块；P1/P2 菜单**可见但带阶段徽章**，对应页面为"阶段说明页"（诚实展示，不藏不伪装）。

| 路由 | 菜单 | 阶段 | 页面内容 |
| --- | --- | --- | --- |
| `/dashboard` | 战略决策大盘 | P0 | KPI 卡片区、新建任务 Dialog、SSE 执行流面板、推荐卡片区（空态） |
| `/radar` | 竞品时序监控 | P0 最小 | 任务批次/单 ASIN 状态表；BSR 走势、跨平台矩阵以"P2"说明卡占位 |
| `/voc` | 多模态评论洞察 | P0 | 痛点排行 + 严重度徽章 + ECharts 柱/雷达 + 语言/星级过滤；实拍画廊"P1"占位 |
| `/reformulation` | 工厂级改款决策 | P0 | 双栏卡片 + 证据 Sheet 抽屉；工程数值缺失一律"未评估"徽章 |
| `/financial` | 逆向财务与风控 | P1 说明页 | `NOT_EVALUATED` 说明卡 + P1 开放条件说明 |
| `/` | — | — | 重定向 `/dashboard`；`/:pathMatch(.*)*` → 404 空态页 |

## 第 5 节 · 页面排版规格

每页统一骨架：`PageHeader`（H1 + `text-sm text-muted-foreground` 口径说明行 + 右侧操作位）→ 内容区块 `space-y-6`。无后端数据时所有区块呈空态（图标 + 标题 + 说明 + 可选操作），**不渲染假数据**。

### 5.1 `/dashboard` 战略决策大盘

```
PageHeader: 标题 + [新建诊断任务 Button(primary,size=sm)]
├─ KPI 行（4 卡）: 监控 ASIN 数 / 实际样本量 / 有证据痛点数 / 财务熔断数
│   卡 = Card(p-6): 上 text-sm muted 标签 + 下 text-3xl tabular-nums 数值；
│   "财务熔断" P0 恒显示 "未评估" 灰徽章而非数字；每卡右下 text-xs 统计口径
├─ 主区 grid xl:grid-cols-3 gap-6
│   ├─ col-span-2: Agent 执行流面板 Card
│   │   任务列表(左, Table) + 选中任务节点时间线(右, 自研 SseTimeline)
│   │   节点状态点色=生命周期色；区分 跳过/无数据/失败/取消
│   └─ 高潜推荐 Card: 空态（"完成任务后展示有支撑数据的推荐，不足 Top 3 不补齐"）
└─ 新建任务 Dialog: ASIN 文本域(1–10, 10 位校验提示) + 站点 Select(Amazon US)
   + 时间窗 Select(近 6 个月) + 财务输入折叠区(disabled, 标注 P1)
```

### 5.2 `/voc` 多模态评论洞察

```
PageHeader + 过滤条(语言 Select[中文/德/日/西] · 星级 1-3 ToggleGroup · 时间窗)
├─ grid xl:grid-cols-5 gap-6
│   ├─ col-span-2 痛点排行 Card: 列表行 = SeverityBadge + 名称(text-sm font-medium)
│   │   + 频次%(tabular-nums) + 样本数；选中行高亮 bg-muted
│   └─ col-span-3 Card + Tabs[柱状分布 | 雷达对比 | 实拍画廊(P1 徽标,禁用)]
│       ECharts 容器 h-80；无数据→EmptyState；"不足 5 类不补齐"注释 text-xs
└─ 评论原声卡: Table(星级/语言/时间/片段)，空态
```

### 5.3 `/reformulation` 工厂级双栏改款决策

```
PageHeader + [导出工程任务书 Button(variant=outline, disabled, 标注"后续阶段")]
├─ grid xl:grid-cols-2 gap-6
│   ├─ 左栏 Card list: 标题行"产品物理本体优化"(text-base font-semibold + count Badge)
│   │   ProposalCard: 改动描述(text-sm) + 关联痛点 Badge 列表
│   │   + 参数行(开模费/周期/缺陷率: 值或"未评估"灰徽章)
│   │   + [查看证据链 Button(variant=ghost,size=sm)] → 右滑 Sheet
│   └─ 右栏: "包装与履约优化"，同构（尺寸/抛重/FBA Tier/运费节省）
├─ Sheet(sm:max-w-xl): "Based on N Reviews" 标题 + 星级/时间筛选 + 证据 Table(空态)
└─ 底部注释: "工程数值仅在输入及评估依据齐全时展示" text-xs muted
```

### 5.4 `/financial`（P1 说明页）

EmptyState（图标 + "P1 阶段开放" + 三段式说明：NOT_EVALUATED 含义、P1 将提供的滑块/曲线/熔断横幅、开放条件），不渲染测算器。

### 5.5 `/radar` 竞品时序监控

```
PageHeader
└─ Tabs[任务批次(P0) | BSR 走势(P2) | 跨平台矩阵(P2)]
    P0 Tab: Table(任务 ID/ASIN 数/状态 StatusBadge/样本量/创建时间/失败原因 Tooltip)
    P2 Tabs: EmptyState 阶段说明卡
```

## 第 6 节 · 组件清单

**shadcn-vue CLI 引入**（复制进 `src/components/ui/`，仅此一批，按需不再扩）：`sidebar button card badge separator breadcrumb dropdown-menu tooltip skeleton table tabs sheet dialog input label select textarea progress alert sonner scroll-area avatar collapsible toggle-group empty`（`empty`/`toggle-group` 若当前注册表不可用，则以 Card+图标自绘空态、Button 组替代，并在 result.md 记录）。

**自研业务组件**（`src/components/`，仅下列有真实需求的）：

| 组件 | 说明 |
| --- | --- |
| `AppSidebar` / `AppHeader` | 外壳：Logo、5 项 NavMain（带 P1/P2 徽章）、NavUser 占位；顶栏 Trigger+面包屑+新建任务+告警图标 |
| `KpiCard` | 标签+数值(tabular-nums)+口径注脚+"未评估"模式 |
| `StatusBadge` / `SeverityBadge` / `FinancialStateBadge` | 严格映射第 1 节状态色 |
| `SseTimeline` | 节点时间线（状态点+名称+耗时 text-xs） |
| `ProposalCard` | 双栏建议卡（描述+痛点徽章+参数行+证据按钮） |
| `VChart` | ECharts 薄封装：`echarts/core` 按需注册 Bar/Radar + Grid/Tooltip/Legend，ResizeObserver 自适应，空数据渲染 EmptyState |
| `EmptyState` | 图标+标题+说明+可选操作（若 ui/empty 不可用则落于此） |

## 第 7 节 · 状态管理与 SSE

- **TanStack Query**：`QueryClient` 挂 `app/`；查询键草案 `['tasks', filter]`、`['task', id]`、`['report', itemId]`、`['evidence', proposalId]`——全部标注"键形随后端契约定稿"；本任务无后端，`enabled: false` 占位 + 空态渲染，不写 mock。
- **Pinia**：仅一个 `ui` store：当前品类选择器值、VOC 语言/星级筛选（跨页保留）。不复制 Query 数据。
- **SSE**：`useTaskEvents(taskId)` composable——EventSource 连接草案地址 `/api/v1/tasks/{id}/events`；按事件 ID 去重、终态/组件卸载 `close()`、断线由后端 `Last-Event-ID` 回放（前端只记录最后 ID）；**每页至多一条连接**。事件 TS 类型集中在 `src/api/events.types.ts`，文件头显式注释"草案，以 contracts/task-events.schema.json 为准，生成后删除"。
- **HTTP 客户端**：`src/api/generated/` 留空（仅 `README.md` 说明由 Hey API 从后端契约生成）；本任务**不安装** Hey API，不手写请求函数。

## 第 8 节 · 目录结构（落地后）

```text
frontend/
├── package.json / bun.lock / vite.config.ts / tsconfig*.json / components.json
├── index.html
└── src/
    ├── style.css              # Tailwind v4 导入 + @theme inline + 全部设计令牌（浅色）
    ├── main.ts / App.vue
    ├── app/                   # router.ts、providers.ts（QueryClient/Pinia 挂载）
    ├── components/
    │   ├── ui/                # shadcn-vue CLI 生成（不手改样式逻辑）
    │   ├── AppSidebar.vue AppHeader.vue KpiCard.vue EmptyState.vue
    │   ├── StatusBadge.vue SeverityBadge.vue FinancialStateBadge.vue
    │   ├── SseTimeline.vue ProposalCard.vue VChart.vue
    ├── features/
    │   ├── dashboard/ voc/ reformulation/ radar/ financial/
    │   │   # 各含页面 .vue + 局部子组件；无后端时只渲染结构与空态
    ├── api/
    │   ├── generated/README.md   # 契约生成占位说明
    │   └── events.types.ts       # SSE 事件草案类型（显式标注）
    ├── composables/useTaskEvents.ts
    └── stores/ui.ts
```

## 预计变更文件

| 文件/目录 | 变更 |
| --- | --- |
| `frontend/`（新建） | 上述完整脚手架 + 外壳 + 5 页面骨架 + 设计令牌，约 40–60 个文件（含 CLI 生成的 ui 组件） |
| `docs/architecture.md` | 3.1 表"组件与样式"行改为"shadcn-vue（Reka UI + Tailwind CSS v4）+ CSS 变量"；图表行保留 ECharts 并注明不使用 shadcn 图表块；第 9 节取舍表对应行改写为"shadcn-vue，而非 Element Plus+自绘主题"并记录决策日期与来源（用户指令）；2.2 表不变 |
| `PRD.md` | 头部技术方向表、P0-04 描述、MVP 表中"Element Plus"→"shadcn-vue（Tailwind CSS v4）"；保留"不引入第二套 UI 体系"语义（ECharts 为图表库不计入） |
| `README.md` | 选型表前端行同步更新 |
| `docs/plans/2026-09-13-frontend-design/plan.md` | 本计划（获批后仅更新审批信息） |
| `docs/plans/2026-09-13-frontend-design/result.md` | 完成后如实记录 |

**不改**：`AGENTS.md`（本轮已按用户指令单独修改）、后端路线图、`plan/`、Git 中已有删除项。

## 实施步骤与分工

1. 展示本计划，等待明确批准；获批后记录真实审批信息。
2. **文档同步**：按"预计变更文件"修改 3 份文档的 UI 库表述（精确替换，不动其他内容）。
3. **脚手架**：`bun create vite@latest frontend --template vue-ts`（若交互则选 Vue+TS）；`cd frontend && bun add tailwindcss @tailwindcss/vite`；配置 `vite.config.ts` 插件与 `@` 别名、`tsconfig` paths；`src/style.css` 写入 `@import "tailwindcss";`。
4. **shadcn-vue 接入**：`bunx shadcn-vue@latest init`（style=new-york、base=neutral、CSS variables=on；选项记录于 result.md）；`bunx shadcn-vue@latest add` 第 6 节组件清单；`bun add vue-router pinia @tanstack/vue-query echarts lucide-vue-next`。
5. **主题令牌**：在 `style.css` 以 `@theme inline` + `:root` 落第 1–3 节全部令牌（浅色；`.dark` 保留 CLI 默认但不启用、不验收）；语义色经 `@utility` 或 badge 变体类暴露。
6. **外壳与路由**：实现 `AppSidebar`（5 项导航+P1/P2 徽章、`collapsible="icon"`）、`AppHeader`（Trigger+面包屑+新建任务+告警）、`router.ts`（第 4 节路由表+重定向+404）、`providers.ts`。
7. **共享组件**：按第 6 节实现 `KpiCard`、三枚 Badge、`EmptyState`、`VChart`、`SseTimeline`、`ProposalCard`。
8. **页面骨架**：按第 5 节实现 5 个页面（全部空态/阶段说明态；KPI 卡演示"未评估"模式；ECharts 容器挂空态）。
9. **API/SSE 占位**：写 `api/generated/README.md`、`events.types.ts`（草案注释）、`useTaskEvents.ts`（结构完整、默认不连接）。
10. **验证**：执行下节全部命令；回读关键文件自查令牌/色值与本计划一致；`git status --short` 核对范围；生成本目录 `result.md`。

分工：无可调用子代理，主代理直接执行；不为形式化分工安装工具。

## 验证与验收

| 检查 | 命令/方式 | 预期 |
| --- | --- | --- |
| 依赖安装 | `cd frontend && bun install` | 成功并生成 `bun.lock` |
| 类型检查 | `bunx vue-tsc --noEmit` | 0 错误 |
| 生产构建 | `bun run build` | 成功，产物 `dist/` |
| 开发冒烟 | `bun run dev` 后台启动 + `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/` | 200 |
| 路由检查 | curl 各路由（SPA 回退同源 200）+ 代码自查路由表 | 5 条业务路由 + 重定向 + 404 |
| 设计一致性 | 人工回读 `style.css` 与 Badge 组件，对照第 1–3 节令牌表 | 色值/字号/字重/间距一致 |
| 文档一致性 | grep 3 份文档无残留 "Element Plus"（除修订说明中的历史引述） | 一致 |
| 工作区洁净 | `git status --short` | 新增仅 `frontend/`、3 份文档修改、本任务目录；旧删除项原样 |

**不执行（如实记录为未检查项）**：浏览器视觉走查与 Playwright（后续联调任务）、ESLint 配置（后续任务）、真实后端联调、SSE 实连、真机/移动端、深色模式、可访问性审计。

## 风险与非目标

- **CLI 交互性**：`shadcn-vue init` 交互选项可能随版本变化；以官方文档为准作答并记录，失败则改为手动安装（官方 Manual Installation 路径）并在 result.md 记录。
- **注册表差异**：个别组件（`empty`、`toggle-group`）在 shadcn-vue 注册表可能缺失或命名不同；按第 6 节备选方案降级，不因此引入第二套库。
- **文档修订敏感性**：本计划含对已获批架构文档的决策修订，依据为用户 2026-09-13 明确指令；修订处在文档中注明来源与日期。
- **版本漂移**：Tailwind v4 / shadcn-vue / Vite 的次版本行为以安装时 lock 为准；出现不兼容时记录实际版本与变通，不回退到 npm/pnpm。
- **非目标**：不接后端、不写假数据/假接口、不实现 P1/P2 功能、不做深色模式/i18n/移动端适配、不配 ESLint/Playwright、不生成 API 客户端、不装字体包。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-13
- 批准信息：2026-09-13 用户明确批准，原文“开始实施”。此前同日用户已给出设计要求：更具体的字号/颜色/字重/页面排版、浅色主题、使用 shadcn-vue sidebar，并要求 plan.md 即详细实施计划（本版已据此重写）。
- 修订记录：2026-09-13 按用户指令重写为详细实施计划（设计规范内嵌、浅色、shadcn-vue），替代原“产出设计文档”的元计划版本。
