# InsightX 前端 UI/UX 工作台改造

## 审核状态

已批准后撤销。
- 批准人：用户
- 批准时间：2026-09-10 19:58 (UTC+8)
- 批准指令：“开始实施docs/plans/2026-09-10-frontend-ux-workbench/plan.md”
- 撤销时间：2026-09-10 20:25 (UTC+8)
- 撤销指令：“撤销本次更改”
- 处置结果：已彻底回滚所有实施变更，恢复至实施前干净状态。

## 目标

把 InsightX 从「有 AI 分析结果的暗色 SaaS Dashboard」改造成「帮助卖家完成产品改款决策的浅色调查工作台」，满足：

1. 用户 10 秒内能回答：分析哪个产品、最大问题、多严重、如何改、改多少钱、多久回本、最终改不改。
2. Recommendation → Evidence 可追溯。
3. 保留 **5 个独立 Dashboard**；共享当前产品/ASIN 上下文，但不做强制线性调查路径。
4. 每页仅 1–2 个 Primary Action。
5. 通过 Frictionless / Quality Craft / Trustworthy / Evidence-driven 自检。

## 当前事实

- 前端在 `frontend/`，Vue 3.5 + Vite 8 + TS + Tailwind 4 + vue-i18n + GSAP + lucide。
- 无路由库；`App.vue` 用 `activeTab` 切 5 页。
- 数据 100% mock（`src/mock/data.ts`）；登录 mock 写 localStorage。
- 无 HTTP/SSE 调用；`docs/api.md` 是契约草案。
- 当前视觉：暗色 `#08090a`、半透明白表面、紫强调 `#5e6ad2`、大量卡片与圆角。
- README 仍是 Vite 模板；无 `vue-router`。

## UI 审查结论

### Blocking

1. **决策路径断裂**：首页是 4 张 KPI 卡 + 痛点列表，不直接给出「当前判断 / 最大机会 / 建议行动」，用户无法在 5–10 秒知道下一步。
2. **证据不可追溯**：Evidence Drawer 只接收 title+count，内部再塞固定 4 条 mock 评论；与选中的痛点/方案/视觉证据无真实绑定，违反 Evidence-driven。
3. **页面上下文丢失**：Header 有 ASIN 选择，但当前 Investigation（问题主题）不持久；VOC/视觉/改款/ROI 未围绕同一问题串联。
4. **AI 结论不透明**：改款与财务页缺少「为什么得出该结论」的置信度、支持/反例、局限说明。

### Major

5. **Dashboard 化 / 卡片滥用**：几乎每段信息包 `ln-surface` 卡片；首页 KPI 四宫格是典型 AI SaaS 模板。
6. **主 CTA 争抢**：Dashboard 同时有「查看改款方案」「运行新诊断」；页页都有多个同级按钮。
7. **暗色营销气质**：`IntroShowcase` 全屏 GSAP 电影开场 + 「消灭信息黑洞」类营销文案，与工程决策工作台气质冲突。
8. **数据割裂与硬编码**：Dashboard 峰值严重度、FBA 节约写死；改款页 netGain 写死；财务页独立滑块不回写改款参数；跨页数字可互相冲突。
9. **改款建议不够工程化**：以长段落描述为主，缺少 Before → After、是否开模、单件成本、置信度等结构化字段。
10. **财务页先参数后结论**：默认滑块+指标，而非 A/B/C 方案对比 + 先给推荐与否决理由。
11. **视觉取证过浅**：图库+标题列表，缺少大图、视觉结论、支持/反例、置信度。
12. **VOC 列表过平**：缺 Coverage / Severity / Rating Impact / Trend / Competitor / Confidence 同屏排序表。

### Minor

13. 中英混杂：标题营销中文，footer 英文技术栈秀。
14. Header 无产品缩略图、评分、评论数、数据更新时间等 Context Bar 信息。
15. README 未描述项目。
16. 圆角/阴影/发光选择色偏多，数字未统一等宽对齐。
17. Agent 工作流页以终端日志为主，对决策用户噪音大（可降级为辅助视图）。

## 新设计方向

### 定位

**专业分析 Dashboard 组** — 5 个可独立进入的业务看板，服务「产品改款决策」，不是营销站，也不是强制流水线 Wizard。

参考气质：Dovetail / Enterpret / Product Opportunity Explorer / Specright / Makersite。不复制界面。

产品目标约束：每个 Dashboard 自己闭环回答问题；跨页可跳转，但**不以「必须按 1→5 走完」为组织原则**。

### Design Tokens

```
Background   #F4F4F3   canvas paper
Surface      #FFFFFF   workspace panel
Surface-2    #FAFAFA   inset / table header
Border       #E4E4E2   1px hairline
Border-strong #D0D0CD
Ink          #1A1A1A   body
Ink-2        #5C5C5C   secondary
Ink-3        #8A8A88   muted / meta
Accent       #1F4B3F   deep engineering green — primary action, selection
Accent-soft  #E8F0ED
Risk         #9A5B12   amber — elevated risk
Veto         #9B2C2C   red — veto / blocking
Positive     #1F4B3F   same family as accent
Mono-num     tabular, ui-monospace
Radius       2–4px（几乎直角）
Shadow       默认无；仅 Drawer 用弱阴影
```

### Typography

```
UI        system-ui, "Segoe UI", "PingFang SC", sans-serif
Mono      ui-monospace, "Cascadia Code", Consolas, monospace
Title     20 / 600 / 1.3     页面主标题
Section   13 / 600 / 1.4     区域标题，letter-spacing 0.02em
Body      13 / 400 / 1.55    正文
Meta      11 / 400 / 1.4     标签、时间、来源
Data      13 / 500 mono      金额、比例、数量，tabular-nums
```

### 布局系统

```
┌─────────────────────────────────────────────────────────────┐
│ Sidebar        │  Context Bar (52)   [SidebarTrigger][user] │
│ Header: 品牌   ├─────────────────────────────────────────────┤
│ Group 分析     │                                             │
│  决策概览      │           SidebarInset / Main Workspace     │
│  VOC 痛点      │           （当前 Dashboard 全权负责）       │
│  视觉取证      │                    ┌───────────────────────┤
│  双栏改款      │                    │ Evidence Drawer (可选) │
│  财务决策      │                    │  Reviews / Images /   │
│ Group 运行     │                    │  Counter / Confidence │
│  诊断流程      │                    │                       │
│ ───────────    │                    │                       │
│ Footer: 当前产品│                    │                       │
│ ASIN / 站点    │                    │                       │
└─────────────────────────────────────────────────────────────┘
```

### Left Nav：整体采用 shadcn-vue Sidebar 组件规范

调研了 Vue 3 侧栏主流方案（PrimeVue Sidebar、shadcn-vue Sidebar、Element Plus Menu 等）。本轮**整个页面布局壳直接采用 shadcn-vue 官方 Sidebar 组件**（https://www.shadcn-vue.com/docs/components/sidebar），不再自研侧栏：

| 方案 | 评价 | 本轮 |
|---|---|---|
| **shadcn-vue Sidebar** | Vue+Tailwind 事实标准结构；Header/Content/Group/Menu/Footer、icon 折叠、移动端 offcanvas、键盘可达、Ctrl+B 快捷键 | **整页采用（组件本体 + 布局规范）** |
| PrimeVue Sidebar | 组件完整，但引入完整 PrimeVue + 独立主题体系，与现有 Tailwind 4 冲突 | 不引入 |
| Element Plus / Naive / AntDV | 太重，气质偏通用后台 | 不引入 |
| 完全自创导航 | 易再次偏离「现成菜单」预期 | 不采用 |

**落地方式（修订：不再零依赖自研）**：

- 通过 shadcn-vue CLI 安装：`cd frontend && bunx shadcn-vue@latest add sidebar`（自动连带安装其依赖的 Button / Sheet / Separator / Skeleton / Tooltip 等基础组件与 `cn()` 工具）。
- 接受 shadcn-vue 所需的 peer 依赖：`reka-ui`、`class-variance-authority`、`clsx`、`tailwind-merge`、`tw-animate-css`；图标沿用已有 lucide（shadcn-vue 官方使用 `@lucide/vue`，本仓库已有 `lucide-vue-next`，安装后按实际兼容择一并统一）。
- 生成 `components.json`，按 Tailwind 4 方式在 `style.css` 中定义 `--sidebar-*` 等 CSS 变量；`--sidebar-*` 变量值映射到本计划 Design Tokens（sidebar-background = `#FAFAFA` Surface-2、sidebar-accent = `#E8F0ED` Accent-soft、sidebar-primary/foreground 用 Ink/Accent 系）。
- 组件源码落在 `src/components/ui/sidebar/`（shadcn-vue 拷贝式组件，非黑盒 npm 包），允许按气质微调 class，但**不改其 anatomy 与状态管理结构**。
- 本次为引入 shadcn-vue 的**唯一例外**，范围仅限 Sidebar 及其必需基础组件；不借机全量引入其他 shadcn 组件。

标准结构（无序号，整页采用官方 anatomy）：

```
SidebarProvider
├── AppSidebar.vue（<Sidebar collapsible="icon">）
│   ├── SidebarHeader      品牌 / 工作区名（InsightX，SidebarMenuButton size="lg"）
│   ├── SidebarContent
│   │   ├── SidebarGroup「分析」SidebarGroupLabel
│   │   │   └── SidebarMenu → SidebarMenuItem → SidebarMenuButton（isActive 标选中）
│   │   │       ├── 决策概览 / VOC 痛点 / 视觉取证 / 双栏改款 / 财务决策
│   │   └── SidebarGroup「运行」
│   │       └── 诊断流程
│   ├── SidebarFooter      当前产品摘要（ASIN / 站点 / 数据更新）
│   └── SidebarRail        折叠态悬停切换
└── SidebarInset           主内容区
    ├── header（ContextBar + SidebarTrigger）
    └── Main Workspace（当前 Dashboard 全权负责 + Evidence Drawer）
```

交互规范（以官方组件行为为准，不再自定义实现）：

- 选中态：`SidebarMenuButton is-active`（官方样式映射到 Accent-soft 底 + Accent 字，非大圆角胶囊）
- 桌面：`collapsible="icon"`（官方默认 16rem 展开 ↔ 3rem 图标栏）
- 移动端：官方 offcanvas + 遮罩（`useSidebar` 的 `openMobile` / `isMobile`）
- 快捷键：官方内置 `Ctrl+B` 切换；展开状态持久化用 `SidebarProvider` 的 storage key（`insightx_sidebar`）
- 可访问性：沿用官方组件的键盘与 ARIA 实现；选中项附加 `aria-current="page"`
- 图标：lucide（LayoutDashboard / ListTree / ScanEye / Wrench / Calculator / Activity）

同时左栏仍有：**无序号**标准导航；一项 = 一个独立 Dashboard。下方「当前产品」只保留共享上下文（ASIN/站点/窗口），**不出现步骤编号或路径进度**。
- **不做**主路径条 / Wizard 步骤指示。跨页只通过页面内明确链接（如「在财务决策中评估该方案」）。
- 顶栏 Context Bar：缩略图、产品名、ASIN、站点、类目、价格、星级、评论数、数据更新时间。
- 主区：每个 Dashboard 自答「看到什么 / 该做什么 / 下一步可做什么」。
- 右栏 Evidence Drawer：默认关闭；点「查看依据」打开。

### 信息架构（5 个独立 Dashboard）

| Dashboard | NAV 文案 | 本页职责（独立成立） | Primary Action |
|---|---|---|---|
| Overview | 决策概览 | 一眼看清当前产品最大问题与系统建议 | 查看问题依据 |
| Workflow | 诊断流程 | 触发/观察采集与分析任务状态 | 运行诊断 |
| VOC | VOC 痛点 | 痛点排序、覆盖、严重度、代表性原声 | 查看痛点证据 |
| Visual | 视觉取证 | 买家图与损坏模式判断 | 查看视觉依据 |
| Reform | 双栏改款 | 产品本体 vs 包装/履约工程清单 | 导出 RFC / 查看方案证据 |
| Finance | 财务决策 | 方案成本、回本、是否建议改/开模 | 确认财务结论 |

说明：
- 6 个导航项 = 5 业务看板 + 诊断流程（与现状一致的业务面，不是线性步骤）。
- 各页可交叉引用，但任何一页单独打开都有完整语义。
- Overview 是推荐入口，不是强制第一站。

### Evidence Pattern

统一 `openEvidence(target)`：

```ts
type EvidenceTarget = {
  title: string;
  kind: 'cluster' | 'proposal' | 'visual' | 'metric';
  id: string;
  summary: {
    reviewCount: number;
    imageCount: number;
    competitorCount: number;
    confidence: number;
    supporting?: number;
    counter?: number;
  };
  reviews: MockReview[];   // 真实关联 mock 列表，非全局固定 4 条
  images?: VisualEvidence[];
  explanation?: string;    // AI 为什么这么判断
  limitations?: string;
  source: { marketplace: string; updatedAt: string };
};
```

所有关键数字旁提供「依据」入口；抽屉展示 Summary → Supporting → Counter → Confidence → Limitation → Source。

### AI 内容原则

- 不再大段 `AI Insight` / `AI Recommendation` 标签墙。
- 在结论旁小字：置信度、证据数、最近分析时间、简短「为何」。
- 反例必须出现：视觉结论旁显示 Supporting 31 / Counter 7。

## Mock 数据一致性（主线 ASIN B08N5WRWNW）

全站共用一套可对齐数字：

| 指标 | 值 |
|---|---|
| 产品 | ErgoPro 人体工学椅 / B08N5WRWNW / US |
| 价格 / BSR / 评分 | $189.99 / #142 / 4.1 |
| 评论样本 | 3,840 有效；负评 645；负评率 16.8% |
| Top 问题 | 3D 扶手卡扣脆断 |
| 问题覆盖 | 14.8% 负评覆盖；-0.72★；68 图；6/8 竞品；182 评；Confidence 94% |
| 建议行动 | 优先包装限位；其次局部结构加强；暂缓整套开模 |
| 方案 B | 包装改款：投入 $2,400；FBA 省 $4.60/件；Payback ~2.1 月 |
| 方案 C | 本体+包装：Tooling $12,000；Δ成本 $1.45；Payback 3.8 月（阈值 6） |
| 否决示例 | 破壁机 C：Payback 14.8 月 > 6 → VETOED |

跨页不得冲突。

## 变更范围

**优先改（布局与业务页）：**

- `src/style.css` — 浅色 design tokens、shadcn-vue 所需 `--sidebar-*` 等 CSS 变量（映射到本计划 Tokens）
- `src/App.vue` — 布局壳改为 `SidebarProvider` + `AppSidebar` + `SidebarInset`（header 内含 `SidebarTrigger` + ContextBar）+ Evidence Drawer；investigation / Evidence 状态
- `src/mock/data.ts` — 统一 mock、Evidence 关联数据、ROI 方案
- `src/types/index.ts` — 扩展 ProductContext / Evidence / Proposal 字段（不改 api.md）
- `src/components/AppSidebar.vue` — 新建，基于官方 `Sidebar*` 组件拼装无序号独立 Dashboard 导航
- `src/components/ui/` — shadcn-vue CLI 生成的 sidebar 及其依赖基础组件（拷贝式源码）
- `src/components/ContextBar.vue` — 新建顶栏当前产品上下文（置于 SidebarInset 的 header）
- `src/components/DecisionOverviewTab.vue` — 决策概览 Dashboard
- `src/components/AgentWorkflowTab.vue` — 诊断流程 Dashboard（保留，视觉收敛）
- `src/components/VocPainTab.vue` — VOC 痛点 Dashboard
- `src/components/VisualForensicsTab.vue` — 视觉取证 Dashboard
- `src/components/ReformProposalsTab.vue` — 双栏改款 Dashboard
- `src/components/RoiDecisionTab.vue` — 财务决策 Dashboard
- `src/components/EvidenceDrawer.vue` — 真实 target 驱动
- `src/components/Header.vue` — 简化或并入 ContextBar/AppSidebar
- `src/i18n/locales/*.ts` — 文案去营销化、对齐 6 导航项
- `index.html` — 去掉 dark class，浅色 body
- `frontend/components.json`、`frontend/package.json` — shadcn-vue 初始化及其限定依赖（reka-ui、class-variance-authority、clsx、tailwind-merge、tw-animate-css，图标库二选一统一）

**降级/保留：**

- `IntroShowcase.vue` — 缩短或改为可跳过的轻量引导；默认直接进决策概览
- `AuthModal.vue` — 视觉对齐浅色，逻辑不动

**不改：**

- `docs/api.md`、后端契约
- 除上述 shadcn-vue 限定依赖外，不加 vue-router / echarts / 其他 UI 库
- 业务 mock 语义（仍可演示完成/进行中/否决）

## 实施步骤

1. 初始化 shadcn-vue：`bunx shadcn-vue@latest init`（按 Tailwind 4 选项），`bunx shadcn-vue@latest add sidebar`；核对生成的依赖与 `components.json`。
2. 写入浅色 tokens 与全局排版（`style.css`、`index.html`），把 `--sidebar-*` 变量映射到本计划 Design Tokens。
3. 重构 `App.vue` 布局：`SidebarProvider` + `AppSidebar`（官方 anatomy）+ `SidebarInset`（header：SidebarTrigger + ContextBar）+ Workspace + Drawer；导航为 6 个独立 Dashboard。
4. 重建一致性 mock：product context、pain ranking、evidence bundles、A/B/C ROI。
5. 逐个实现独立 Dashboard + Evidence Drawer 真实绑定（可互跳，无强制路径）。
6. 更新 i18n 中文文案；必要时补 en。
7. 处理 Intro / Auth 的视觉收敛。
8. 响应式：侧栏官方 icon 折叠 / 移动端 offcanvas，抽屉全宽，表格可横滚。
9. 自检三支柱 + Evidence-driven；修 Blocking。
10. 写 `result.md`。

## 验证与验收

- `cd frontend && bun run build`（含 vue-tsc）必须通过。
- 尽可能 `bun run dev` 冒烟：任选一个 Dashboard 进入，都能独立理解在看什么、能做什么；证据抽屉展示关联数据；改款 Before/After 清晰；财务先结论后参数；切换 Dashboard 时当前产品上下文保留。
- 对照验收十条（用户第一次打开能否回答产品/问题/严重度/为何/证据/怎么改/多少钱/回本/改不改）。
- 侧栏行为符合 shadcn-vue 官方规范：`Ctrl+B` 切换、icon 折叠、移动端 offcanvas、`SidebarTrigger` 可用。
- 新增依赖仅限 shadcn-vue 所需清单（reka-ui / class-variance-authority / clsx / tailwind-merge / tw-animate-css，及图标库统一）；`docs/api.md` 未改。

## 风险与非目标

**风险**

- 组件大改可能引入未使用 import / TS 错误 → build 卡住。
- shadcn-vue CLI 对 Tailwind 4 / bun 的初始化路径可能与现有配置冲突（`style.css` 变量命名、`components.json` 别名），需边装边核对。
- `reka-ui` 等新依赖体积与现有 GSAP 动画并存，注意不要把侧栏过渡与 GSAP 冲突。
- IntroShowcase 与浅色工作台气质冲突，过度删减可能损失演示效果。
- mock 一致性工作量大，遗漏一处会破坏信任感。
- 无真实路由，深链/刷新恢复仍弱（保持现状，不引入 vue-router 除非批准）。

**非目标**

- 不实现真实 API/SSE/登录。
- 不引入 ECharts / vue-router；除 shadcn-vue Sidebar 及其必需基础组件外不引入其他 UI 库/组件。
- 不做 P2 回测与跨平台。
- 不重写 Agent 模拟逻辑本体。
- 不提交 git / 不部署。

## 授权边界

批准本计划仅授权上述前端改造，含安装 shadcn-vue 及上述限定依赖。不授权 commit、push、改后端、改 API 契约、安装清单之外的依赖。
