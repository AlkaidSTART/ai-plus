# 侧边栏菜单命名简化：实施计划

## 目标

将 5 个主导航菜单的命名从长名称简化为简洁、等长的功能名，并同步到面包屑（路由 meta.title）与各页 H1，保持全站一致。页面内说明文案、路由路径、文档中的概念名不变。

## 候选方案

| 现名（复杂） | 方案 A（4 字，推荐） | 方案 B（2 字极简） | 方案 C（动作导向） |
| --- | --- | --- | --- |
| 战略决策大盘 | **决策大盘** | 总览 | 看全局 |
| 竞品时序监控 | **竞品雷达** | 雷达 | 盯竞品 |
| 多模态评论洞察 | **评论洞察** | 洞察 | 挖痛点 |
| 工厂级改款决策 | **改款决策** | 改款 | 做改款 |
| 逆向财务与风控 | **财务风控** | 风控 | 控风险 |

- **推荐 A**：4 字等长、节奏统一、保留完整语义；"竞品雷达"与 PRD 信息架构括号中的 "Competitor Radar" 一致。
- B 更短但语义损失（"改款"/"风控"丢主语）；C 口语化，与企业级工具气质不符。
- 若批准时未指明方案，按 **A** 实施；也可回复"用 B/C"或给出自定义名称。

## 当前事实及依据

- 菜单项定义在 `frontend/src/components/AppSidebar.vue`（items 数组）；面包屑取 `route.meta.title`（`src/app/router.ts`）；5 个页面各有 H1 与 meta.title 同文案。
- 图标（LayoutDashboard/Radar/MessageSquareText/Factory/ShieldCheck）与新名称语义仍匹配，不换图标。
- PRD 第四节的名称为信息架构概念名，本任务不修改文档（最小解释：仅 UI 文案）。

## 预计变更文件（7 个）

| 文件 | 变更 |
| --- | --- |
| `frontend/src/components/AppSidebar.vue` | items 的 5 个 title 改为新名 |
| `frontend/src/app/router.ts` | 5 条路由 meta.title 同步 |
| `frontend/src/features/dashboard/DashboardPage.vue` | H1 同步（如"决策大盘"） |
| `frontend/src/features/voc/VocPage.vue` | H1 同步（"评论洞察"） |
| `frontend/src/features/radar/RadarPage.vue` | H1 同步（"竞品雷达"） |
| `frontend/src/features/reformulation/ReformulationPage.vue` | H1 同步（"改款决策"） |
| `frontend/src/features/financial/FinancialPage.vue` | H1 同步（"财务风控"） |

URL 路径（/dashboard 等）、页面副标题说明文案均不变。

## 实施步骤与分工

1. 展示本计划与候选方案，等待批准（及方案选择）。
2. 获批后按获批方案替换 7 处文案；验证；写 `result.md`。

分工：主代理直接执行（纯文案替换，无并行价值）。

## 验证与验收

- `bun run build`（vue-tsc + vite）通过。
- grep 旧名（"战略决策大盘"等 5 个）在 `frontend/src` 零残留（注释除外）。
- 验收：侧边栏、面包屑、各页 H1 三处命名一致；图标不变；路由可达。

## 风险与非目标

- 不改 URL、图标、页面说明文案与任何文档；不调整菜单顺序与结构。
- 风险极低；若后续 PR #14 未合并，本次改动可追加 commit 到同一分支或等新分支，实施时按工作区状态决定（默认当前分支追加）。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-13
- 批准信息：2026-09-13 用户明确批准，原文“实施吧”；未指明方案，按计划约定默认采用方案 A（决策大盘/竞品雷达/评论洞察/改款决策/财务风控）。
