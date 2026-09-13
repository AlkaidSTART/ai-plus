# 去除页面 P0/P1/P2 阶段标识与相关描述：实施计划

## 目标

移除前端页面（含侧边栏、对话框、Tab、空态文案）中所有用户可见的 P0/P1/P2 阶段标识与"XX 阶段开放/属于 PX 阶段"类描述，并移除侧边栏品牌区的 IX 图标 logo（保留 InsightX 文字名）；保留「未评估」「暂未开放」等诚实状态表达。

## 当前事实及依据

已 grep 全部 `frontend/src`（不含 `components/ui/`）确认涉及位置。用户要求针对"页面上的"标识与描述，故最小解释为：**仅改可见 UI 文案与路由 meta，不动代码注释、不动 PRD/架构等文档**。「未评估」徽章属诚实展示要求（PRD），保留。

## 预计变更文件（7 个）

| 文件 | 变更 |
| --- | --- |
| `src/components/AppSidebar.vue` | 删财务导航项 `phase: 'P1'` 及 SidebarMenuBadge 渲染（Badge 导入随之清理）；footer 文案"P0 最小会话（占位）"→"本地会话（占位）"；移除品牌区 IX 图标方块（`bg-primary` 的 logo div），保留 "InsightX" 文字名与副标题 |
| `src/app/router.ts` | 删 5 条路由 meta 中的 `phase` 字段及注释中的阶段表述 |
| `src/features/dashboard/DashboardPage.vue` | KPI 卡 note"P0 不执行财务否决"→"当前不执行财务否决" |
| `src/features/dashboard/NewTaskDialog.vue` | "财务约束输入（P1，当前不可填）"→"财务约束输入（当前不可填）"；折叠区文案去 P0/P1，改为"…暂未开放；当前任务的财务裁决恒为「未评估」" |
| `src/features/voc/VocPage.vue` | 删"实拍画廊"Tab 的 P1 徽章（Badge 导入随之清理）；其空态 title"P1 阶段开放"→"暂未开放"，description→"实拍图缺陷取证能力暂未开放，当前不展示图片证据" |
| `src/features/radar/RadarPage.vue` | 删 BSR 走势/跨平台矩阵两个 Tab 的 P2 徽章（Badge 导入清理）；两处空态 title"P2 阶段开放"→"暂未开放"，description 去掉 P2 表述 |
| `src/features/financial/FinancialPage.vue` | Alert 文案"P0 阶段不执行财务否决"→"当前不执行财务否决"；CardTitle"P1 阶段开放"→"暂未开放"；空态 description→"当前版本支持文本诊断闭环，财务风控能力暂未开放" |
| `src/features/reformulation/ReformulationPage.vue` | 证据抽屉说明"P0 支持文本反查，图片证据为 P1"→"支持文本反查，图片证据暂未开放" |

## 实施步骤与分工

1. 展示本计划，等待明确批准。
2. 获批后按上表逐一编辑（保持其余文案与结构不变）。
3. 验证并生成 `result.md`。

分工：任务小且文件集中，主代理直接执行，不使用子代理。

## 验证与验收

- `cd frontend && bun run build`（vue-tsc + vite）通过、0 类型错误。
- grep 可见模板中无 `P0`/`P1`/`P2` 阶段标识残留（`grep -rn "P[012]" src/features src/components src/app --include="*.vue"` 仅允许命中代码注释行）。
- `bun run dev` 冒烟：主要路由 200。
- 验收：页面上不再出现任何 P0/P1/P2 字样及"PX 阶段开放"文案；财务页仍显示「未评估」徽章；侧边栏不再显示 IX 图标方块，InsightX 文字名保留。

## 风险与非目标

- 不改 PRD/架构文档中的阶段定义（文档属内部事实源）；不改代码注释（用户要求为"页面上的"）。
- 不调整页面结构、不删除禁用 Tab、不改动其他文案与样式。
- 风险极低；若个别文案删除后语句不通，按上表替换文案处理而非直接删除。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-13
- 批准信息：2026-09-13 用户明确批准，原文“实施”（含同日补充要求“同时去掉logo”）。
- 修订记录：2026-09-13 按用户补充要求并入「移除侧边栏 IX 图标 logo」（解释：去掉图标方块、保留 InsightX 文字名）。
