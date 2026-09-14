# 界面动画细节（浅色仪表盘微交互）：实施计划

## 目标

在不引入新依赖的前提下（复用已安装的 `tw-animate-css` + Tailwind v4 + Vue Transition），为现有前端加入克制、统一的动画细节：路由页面过渡、区块错峰入场、卡片悬停反馈、Tab 切换淡入、空态入场；并支持 `prefers-reduced-motion` 降级。动画只服务质感，不改变任何布局与文案。

## 当前事实及依据

- `tw-animate-css@1.4.0` 已由 shadcn-vue CLI 安装并在 `style.css` 引入；Dialog/Sheet/Dropdown 等组件的进出动画已由生成代码自带（本次不动 `components/ui/`）。
- `SseTimeline` 的 RUNNING 节点已有 `animate-pulse`；侧边栏折叠动画由 shadcn sidebar 内置。
- 页面当前无任何过渡：路由切换生硬，区块直接闪现。
- KPI 数值当前恒为"—"（无后端数据），不做数字滚动动画（列入非目标，避免假动感）。

## 预计变更文件（6 个）

| 文件 | 变更 |
| --- | --- |
| `src/style.css` | 新增：`@keyframes ix-enter`（opacity 0→1、translateY 8px→0，300ms ease-out）；`@utility animate-enter`（含 `both` fill-mode，配合内联 `animation-delay` 错峰）；`.page-enter-*`/`.page-leave-*` 路由过渡类（淡入+轻微上移，入场 200ms / 出场 120ms）；`@media (prefers-reduced-motion: reduce)` 中关闭上述自定义动画与过渡 |
| `src/App.vue` | `RouterView` 包 `<Transition name="page" mode="out-in">`，按 `route.fullPath` 作 key |
| `src/components/KpiCard.vue` | 根节点加 `animate-enter` + `hover:shadow-md transition-shadow`；延迟由父级经 `style` 传入（组件加可选 `delayMs` prop） |
| `src/components/EmptyState.vue` | 图标容器加 `animate-in zoom-in-95 fade-in-0 duration-300`（tw-animate-css） |
| `src/features/dashboard/DashboardPage.vue` | PageHeader 与三个区块加 `animate-enter`，KPI 四卡按 0/60/120/180ms 错峰，主区块 180/240ms |
| `src/features/voc/VocPage.vue`、`radar/RadarPage.vue`、`reformulation/ReformulationPage.vue`、`financial/FinancialPage.vue` | 顶层区块加 `animate-enter`（顺序错峰）；`TabsContent` 加 `animate-in fade-in-0 duration-200` |

（实际 9 个文件：style.css、App.vue、KpiCard、EmptyState + 5 个页面。）

## 实施步骤与分工

1. 展示本计划，等待明确批准。
2. 获批后：style.css 定义动画令牌/工具类 → App.vue 路由过渡 → KpiCard/EmptyState → 5 个页面错峰类。
3. 验证并生成 `result.md`。

分工：任务小且集中，主代理直接执行，不使用子代理。

## 验证与验收

- `bun run build`（vue-tsc + vite）通过。
- grep 确认：5 页面均含 `animate-enter`；style.css 含 `prefers-reduced-motion` 块。
- `bun run dev` 冒烟：主要路由 200。
- 验收：动画参数统一（入场 300ms ease-out、过渡 200/120ms、错峰 ≤60ms 步进）；不改变布局/文案；减少动态偏好下动画关闭。视觉效果建议用户 `bun run dev` 目检（本会话无法浏览器验证）。

## 风险与非目标

- 不做：数字滚动（无数据）、骨架屏加载动画（无请求）、图表动画定制（ECharts 默认即可）、Lottie/三方动画库、深色模式适配。
- 动画时长保持 ≤300ms，避免影响操作效率感；不动 `components/ui/` 生成代码。
- 风险低：纯 CSS/Vue Transition，失败时仅表现为无动画。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-13
- 批准信息：2026-09-13 用户明确批准，原文“实施”。
