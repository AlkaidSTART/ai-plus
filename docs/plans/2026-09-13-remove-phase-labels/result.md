# 去除页面 P0/P1/P2 阶段标识与相关描述：实施结果

## 完成状态

已完成。

## 实际变更

按计划修改 7 个前端文件（均为可见 UI 文案/结构，未动代码注释与项目文档）：

- `src/components/AppSidebar.vue`：财务导航 P1 徽章及 SidebarMenuBadge/Badge 导入移除；footer 文案改"本地会话（占位）"；品牌区 IX 图标方块移除，保留 InsightX 文字名与副标题。
- `src/app/router.ts`：5 条路由 meta 的 `phase` 字段及注释阶段表述移除。
- `src/features/dashboard/DashboardPage.vue`：财务熔断 KPI 注脚 →"当前不执行财务否决"。
- `src/features/dashboard/NewTaskDialog.vue`：折叠区标题 →"财务约束输入（当前不可填）"，说明文案去 P0/P1。
- `src/features/voc/VocPage.vue`：实拍画廊 Tab 的 P1 徽章及 Badge 导入移除；空态 →"暂未开放 / 实拍图缺陷取证能力暂未开放，当前不展示图片证据"。
- `src/features/radar/RadarPage.vue`：BSR 走势/跨平台矩阵两个 Tab 的 P2 徽章及 Badge 导入移除；两处空态 →"暂未开放"。
- `src/features/financial/FinancialPage.vue`：Alert 与空态文案去 P0/P1；卡片标题 →"暂未开放"；NOT_EVALUATED「未评估」徽章保留。
- `src/features/reformulation/ReformulationPage.vue`：证据抽屉说明 →"支持文本反查，图片证据暂未开放"。

## 实施记录

审批记录已于实施前写入 plan.md（用户原文"实施"，含补充要求"同时去掉logo"）。按获批计划逐文件编辑，未扩大范围；主代理直接执行，未使用子代理。

## 验证命令与真实结果

| 检查 | 命令 | 真实结果 |
| --- | --- | --- |
| 类型+构建 | `bun run build`（vue-tsc -b && vite build） | 通过，0 错误 |
| 残留检查 | `grep -rn "P[012]" src/features src/components src/app` | 仅剩 2 行 JSDoc 代码注释（RadarPage/VocPage 头部的 PRD 引用说明），页面可见文案零残留 |
| dev 冒烟 | `bun run dev` + curl `/dashboard` `/voc` `/financial` | 全部 200 |

## 计划偏差

无。

## 遗留问题与未执行检查

- 未做浏览器视觉走查（移除后侧边栏头部、Tab 外观建议本地 `bun run dev` 目检）。
- 代码注释中保留的 PRD 阶段引用为有意保留（用户要求范围为"页面上的"）。
