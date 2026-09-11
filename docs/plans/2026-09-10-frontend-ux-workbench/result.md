# InsightX 前端 UI/UX 工作台改造 — 实施结果

## 完成状态

已撤销（根据用户指令“撤销本次更改”完成代码回滚）。

- 回滚记录：已通过 git checkout 与文件清理将 `frontend/` 目录的所有代码、样式、类型、组件、配置及相关依赖彻底恢复至实施前提交状态（commit `bc6d45e96f42500ac01af36b53132c93438b33e5`）。
- 验证状态：回滚后 `frontend/` 状态干净（`working tree clean`），且 `bun run build`（含 vue-tsc）验证通过（耗时 603ms，0 错误）。

## 对应计划

[plan.md](plan.md)

## 实际变更与实施记录

### 1. 布局骨架与侧栏导航（shadcn-vue Sidebar 规范落地）
- 通过 shadcn-vue CLI 完成初始化与官方 Sidebar anatomy 组件引入（落于 `frontend/src/components/ui/`，包含 `sidebar`, `sheet`, `tooltip`, `skeleton`, `separator`, `button`, `input` 及 `lib/utils.ts`）。
- 新增限定依赖：`reka-ui`, `@vueuse/core`, `@lucide/vue`, `class-variance-authority`, `clsx`, `tailwind-merge`, `tw-animate-css`。
- 新建 [AppSidebar.vue](file:///d:/Project/ai-plus/frontend/src/components/AppSidebar.vue)：整页采用官方 Anatomy（`SidebarHeader` + `SidebarContent` 分组「决策分析」与「系统运行」 + `SidebarFooter` 当前产品摘要 + `SidebarRail`），支持 `collapsible="icon"`、`Ctrl+B` 切换与快捷悬停。
- 新建 [ContextBar.vue](file:///d:/Project/ai-plus/frontend/src/components/ContextBar.vue)：置于 `SidebarInset` 顶部，展示 `SidebarTrigger`、ASIN 快捷切换、站点、价格、BSR、星级评级、负评率及用户角色认证信息。

### 2. Design Tokens 与浅色工程风排版
- 修改 [index.html](file:///d:/Project/ai-plus/frontend/index.html)：移除 `dark` 类，全局采用浅色画布背景 `#F4F4F3` 与墨黑文字 `#1A1A1A`。
- 重构 [style.css](file:///d:/Project/ai-plus/frontend/src/style.css)：
  - 映射 `--sidebar-*` 变量至 Design Tokens（`sidebar-background: #FAFAFA`, `sidebar-accent: #E8F0ED`, `sidebar-primary: #1F4B3F` 等）。
  - 设定高对比工作台层级：Canvas `#F4F4F3`, Surface `#FFFFFF`, Border `#E4E4E2`, Deep Green Accent `#1F4B3F`。
  - 收敛旧 `.ln-surface`, `.ln-card`, `.ln-btn`, `.ln-btn-primary` 为平整克制的直角 (2–4px) 工程表面。

### 3. 数据契约与统一 Mock 对齐
- 修改 [types/index.ts](file:///d:/Project/ai-plus/frontend/src/types/index.ts)：扩展 `ProductContext`, `DecisionBrief`, `MockReview`, `RoiScenario`, `EvidenceBundle`，在 `PainPointCluster`, `VisualEvidence`, `PhysicalProposal`, `PackagingProposal` 中补齐 `ratingImpact`, `supportingCount`, `counterCount`, `before`, `after`, `needsMold` 等结构化字段。
- 完善 [mock/data.ts](file:///d:/Project/ai-plus/frontend/src/mock/data.ts)：围绕主线 ASIN `B08N5WRWNW` 对齐全局数据指标（3,840 评、645 负评、14.8% 扶手脆断覆盖、-0.72★ 影响、推荐方案 B 回本 2.1 个月、备选方案 C 回本 3.8 个月、否决案例破壁机 14.8 个月），为全部痛点、提案、图像与财务提供独立的 `EVIDENCE_BUNDLES` 真实绑定。

### 4. 业务看板与全链路证据绑定
- 新建 [DecisionOverviewTab.vue](file:///d:/Project/ai-plus/frontend/src/components/DecisionOverviewTab.vue)：首屏 10 秒清晰解答当前产品最大痛点、严重度、推荐改款方案与财务结论；提供「查看决策研判依据」Primary Action 及直达改款/财务的 Secondary Actions。
- 新建 [VocPainTab.vue](file:///d:/Project/ai-plus/frontend/src/components/VocPainTab.vue)：同屏展现覆盖率、评分冲击、严重度、竞品重合度与双语原声，支持分类筛选与按项调取依据抽屉。
- 新建 [VisualForensicsTab.vue](file:///d:/Project/ai-plus/frontend/src/components/VisualForensicsTab.vue)：大图检视、标本切换、Bounding Box 缺陷定位、支持例/反例对比及 VLM 结构根因归因说明。
- 新建 [ReformProposalsTab.vue](file:///d:/Project/ai-plus/frontend/src/components/ReformProposalsTab.vue)：双栏区分产品物理本体改款 vs 包装履约优化，结构化展示 Before → After 对比、是否开模、单件增量/节约、工期及 RFC 导出。
- 新建 [RoiDecisionTab.vue](file:///d:/Project/ai-plus/frontend/src/components/RoiDecisionTab.vue)：结论先行对比 A/B/C 方案及破壁机否决对照，下方提供动态敏感性与盈亏平衡测算滑块。
- 重构 [AgentWorkflowTab.vue](file:///d:/Project/ai-plus/frontend/src/components/AgentWorkflowTab.vue)：收敛视觉至浅色工程风格，展示 LangGraph 5 节点管道运行与实时 SSE 日志。
- 重构 [EvidenceDrawer.vue](file:///d:/Project/ai-plus/frontend/src/components/EvidenceDrawer.vue)：受真实 `EvidenceBundle` 驱动，展示评论/图片计数、置信度、支持原声、反例原声、AI 归因推导及数据局限性声明。
- 更新 [AuthModal.vue](file:///d:/Project/ai-plus/frontend/src/components/AuthModal.vue)：视觉对齐浅色工作台风格。
- 清理废弃旧组件：`DashboardTab.vue`, `DualColumnProposalsTab.vue`, `FinancialVetoTab.vue`, `VocClusterTab.vue`, `Header.vue`。
- 更新 [i18n/locales/zh.ts](file:///d:/Project/ai-plus/frontend/src/i18n/locales/zh.ts) 与 [i18n/locales/en.ts](file:///d:/Project/ai-plus/frontend/src/i18n/locales/en.ts)：对齐 6 个独立看板导航名称，去除过度营销化词汇。
- 重构 [App.vue](file:///d:/Project/ai-plus/frontend/src/App.vue)：整合 `SidebarProvider` + `AppSidebar` + `SidebarInset` + `ContextBar` + 6 大独立看板 + `EvidenceDrawer` + `AuthModal`。

## 验证结果

### 1. 静态类型检查与生产构建
```bash
cd frontend && bun run build
```
输出：
```text
$ vue-tsc -b && vite build
vite v8.2.2 building client environment for production...
transforming...
✓ 4154 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                           0.64 kB │ gzip:   0.47 kB
dist/assets/Product_logo-0P87Bvip.webp   17.47 kB
dist/assets/index-DSwHn_ja.css           64.12 kB │ gzip:  11.64 kB
dist/assets/index-CQ8lwiNU.js           510.18 kB │ gzip: 174.13 kB
✓ built in 1.10s
```
结果：通过（0 错误）。

### 2. 开发服务器冒烟测试
```bash
cd frontend && bun run dev
```
输出：
```text
VITE v8.2.2 ready in 448 ms
➜ Local: http://localhost:5175/
```
HTTP GET `http://localhost:5175/` 响应正常，返回应用主入口 HTML 与渲染资源，测试完毕后安全退出后台进程。

### 3. 验收十条对照自检
1. **分析哪个产品**：顶栏 Context Bar 与侧栏 Footer 始终显示 `ErgoPro High-Back Mesh Ergonomic Office Chair` / `B08N5WRWNW` / `US`。
2. **最大问题是什么**：首屏明确展示 Top 1「3D 扶手卡扣脆断」。
3. **多严重**：覆盖 14.8% 负评、评分冲击 -0.72★、严重度 4.8/5.0。
4. **为何得出该结论**：VLM 视觉分析与评论归因表明断口呈放射状、R角仅 0.4mm、受侧向载荷应力集中脆断。
5. **证据在哪里**：点击「查看依据」打开 Evidence Drawer，含真实支持原声、反例原声、实拍图标本与置信度。
6. **如何改**：双栏改款清单分别给出方案 B（包装 45° 倾斜内嵌防跌落）与方案 C（本体加厚与 Zamak 3 嵌件）。
7. **改要花多少钱**：方案 B 一次性 $2,400，单件物流省 $4.60；方案 C 局部模具 $12,000，单件 Δ成本 +$1.45。
8. **多久回本**：方案 B 约 2.1 个月；方案 C 约 3.8 个月。
9. **最终改不改**：系统结论「推荐方案 B 包装改款优先，方案 C 作为销量爬坡备选，暂缓整套开模」。
10. **独立性与上下文**：5 个 Dashboard 均可独立进入理解业务，切换导航时保持当前产品上下文不变。

## 计划偏差

- **TypeScript 6.0 配置调整**：在 `tsconfig.app.json` 与 `tsconfig.json` 中补充 `"ignoreDeprecations": "6.0"` 以消除 TS 6.0 对 `baseUrl` 的弃用阻断。
- **废弃组件移除**：按计划将已被新组件替代的 `DashboardTab.vue`, `DualColumnProposalsTab.vue`, `FinancialVetoTab.vue`, `VocClusterTab.vue`, `Header.vue` 物理移除，避免冗余和潜在类型干扰。

## 遗留事项与未执行检查

- **真实网络接口**：本轮改造按计划使用一致性 Mock 数据，未接入真实后端 HTTP/SSE 接口（待后续契约落地）。
- **路由深链接**：当前采用组件级 `activeTab` 切换，未引入 `vue-router`（按计划保持零外部冗余）。
