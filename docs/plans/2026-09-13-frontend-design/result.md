# InsightX 前端设计与 P0 基础实现（shadcn-vue · 浅色）：实施结果

## 完成状态

**已完成**（获批范围内的设计定稿、文档同步、前端脚手架、外壳/路由、共享组件、页面骨架与验证全部落地）。

## 实际变更

### 文档同步（UI 库决策修订，依据用户 2026-09-13 指令）

- `PRD.md`：头部技术方向表、P0-04 描述、MVP 表、M1 里程碑共 4 处 "Element Plus" → "shadcn-vue（Tailwind CSS v4）"。
- `README.md`：选型表前端行 → shadcn-vue（Reka UI + Tailwind CSS v4），职责改为"CSS 变量浅色主题，不叠加第二套组件库"。
- `docs/architecture.md`：3.1 组件与样式行、3.1 节末取舍说明、第 9 节取舍行（均注明 2026-09-13 用户指令修订）、S3 参考链接改为 shadcn-vue 官方文档。
- `AGENTS.md`：第 2 条强约束按用户指令补充"plan.md 必须可直接据以实施，不得只是元计划"（本轮对话中单独完成）。

### 前端实现（新建 `frontend/`，Vite 8.3 + Vue 3.5.42 + TypeScript 6.0.2 strict + Bun 1.4.2）

- **基座**：`bun create vite --template vue-ts`；Tailwind CSS 4.3.3（`@tailwindcss/vite`）；`@` 路径别名（TS6 已废弃 baseUrl，仅用 paths）。
- **shadcn-vue 2.8.2**：`init`（style=reka-nova、base=neutral、CSS variables）+ 26 个 UI 组件目录（25 个计划内 + toggle 依赖项），源码复制进 `src/components/ui/`，运行时依赖 reka-ui、@vueuse/core、vue-sonner、@lucide/vue、clsx、tailwind-merge、class-variance-authority、tw-animate-css。
- **设计令牌** `src/style.css`：浅色 `:root`；品牌主色 `#2563EB`、destructive `#DC2626`、语义色 success `#059669` / warning `#D97706` / info `#2563EB` + 5 个 soft 底色，全部经 `@theme inline` 映射为 Tailwind 类；系统字体栈（已移除 CLI 默认的 Geist Google Fonts 外链）；`--radius: 0.625rem`；`.dark` 变量保留 CLI 默认但未启用。
- **外壳与路由**：`AppSidebar`（collapsible="icon"，5 项导航，财务带 P1 徽章，品牌头 + 受控账号占位 footer）、`AppHeader`（h-14，Trigger + 面包屑 + 新建任务按钮 + 告警占位）、`router.ts`（5 业务路由 + `/`→`/dashboard` + 404）、`providers.ts`（QueryClient + Pinia）。
- **共享组件**：`KpiCard`（含未评估模式）、`EmptyState`（封装 ui/empty）、`StatusBadge` / `SeverityBadge` / `FinancialStateBadge`（严格按计划状态色映射）、`SseTimeline`（含 NO_DATA/SKIPPED 等真实节点态）、`ProposalCard`（数值缺失显示"未评估"）、`VChart`（ECharts 6.1 按需注册 Bar/Radar，空 option 渲染空态）、`lib/chart.ts`（8 色分类色板）。
- **页面骨架**（全空态，无假数据）：`DashboardPage`（4 KPI + Agent 执行流 + 推荐 + 最近任务 + 全局 `NewTaskDialog` 含 ASIN 校验/站点/时间窗/P1 财务折叠区/提交禁用）、`VocPage`（语言 Select + 星级 ToggleGroup + 痛点排行 + 柱状/雷达 Tabs + P1 画廊占位 + 原声卡）、`ReformulationPage`（双栏 + 证据 Sheet + 导出禁用）、`RadarPage`（批次表 + 两个 P2 占位 Tab）、`FinancialPage`（NOT_EVALUATED 说明页）、`NotFoundPage`。
- **契约占位**：`api/generated/README.md`（Hey API 生成说明）、`api/events.types.ts`（SSE 事件草案类型，文件头显式标注）、`composables/useTaskEvents.ts`（去重/终态关闭/卸载关闭，默认不连接）、`stores/ui.ts`（仅跨页 UI 状态）、`types/domain.ts`。

## 实施记录

1. 审批后更新 plan.md 审核状态 → 2. 三份文档精确替换（grep 复核无残留，仅保留修订说明中的历史引述）→ 3. create-vite 脚手架 + bun install（48 包）→ 4. Tailwind v4 接入 → 5. shadcn-vue init → **6. 注册表网络受阻（详见偏差），通过 GitHub API 下载注册表 JSON + 本地 Bun 镜像服务 + `REGISTRY_URL` 环境变量完成 26 个组件安装** → 7. 安装 vue-router 5.3.1 / pinia 4.0.3 / @tanstack/vue-query 5.102.8 / echarts 6.1.0 → 8. style.css 令牌落地 → 9. 外壳/路由/组件/页面/占位文件 → 10. 验证（下节）。分工：无可调用子代理，主代理直接执行。

## 验证命令与真实结果

| 检查 | 命令 | 真实结果 |
| --- | --- | --- |
| 依赖安装 | `bun install` / `bun add ...` | 成功；生成 `frontend/bun.lock`（锁文件随评审） |
| 类型检查+构建 | `bun run build`（= `vue-tsc -b && vite build`） | 通过，0 类型错误；产物 dist/（最大 chunk VocPage 534KB，含 ECharts，见遗留问题） |
| 开发冒烟 | `bun run dev --port 5173` + curl | `/` `/dashboard` `/radar` `/voc` `/reformulation` `/financial` `/nope` 全部 200（SPA 回退正常，404 由客户端页呈现） |
| 文档一致性 | `grep -n "Element Plus" PRD.md README.md docs/architecture.md` | 仅余 2 处修订说明中的历史引述（"替代原 Element Plus 方案"），符合预期 |
| 设计令牌 | grep `2563EB/059669/D97706/DC2626` style.css | 6 处命中，与计划第 1 节一致 |
| 依赖偏差自查 | grep `lucide-vue-next` | 无（实际使用 CLI 安装的 `@lucide/vue`，见偏差） |
| 工作区洁净 | `git status --short` + `git diff --check` | 新增/修改范围符合计划（frontend/、3 份文档、AGENTS.md、本任务目录）；15 个旧跟踪的 frontend 路径被新脚手架覆盖为 M，其余 112 个旧删除项原样未动；无行尾空白错误（仅 LF→CRLF 提示） |

## 计划偏差

1. **shadcn-vue 注册表网络受阻（环境风险兑现）**：本机 fake-IP/TUN 代理导致 `shadcn-vue.com`、raw.githubusercontent.com、codeload 均不可达，jsdelivr 对该仓库为改名前陈旧快照。变通：GitHub Contents API 下载 26+3 个注册表 JSON 至本地，Bun 起 `127.0.0.1:8399` 镜像，利用 CLI 的 `REGISTRY_URL` 环境变量完成安装；组件源码与官方注册表一致，镜像服务已关闭，临时文件均在系统 Temp 目录，未污染仓库。
2. **CLI 默认预设变化**：shadcn-vue 2.8.2 默认 style 为 `reka-nova`（非计划写的 new-york），默认字体 Geist 已按计划换为系统栈。图标库为 `@lucide/vue@1.45.0`（非计划写的 `lucide-vue-next`，系 CLI 自动选择的新包名）。
3. **TS6 适配**：TypeScript 6.0.2 废弃 `baseUrl`，路径别名仅用 `paths` 实现。
4. 以上均为批准范围内的实现细节调整，无范围/验收标准变化，无需重新审批。

## 遗留问题与未执行检查

- **未执行**（计划内声明）：浏览器视觉走查与 Playwright、ESLint 配置、真实后端联调/SSE 实连、移动端、深色模式验收、可访问性审计。
- **chunk 体积**：VocPage 懒加载 chunk 534KB（ECharts 按需引入后仍较大）；后续可评估进一步细分 echarts 模块或调整分包策略（非 P0 目标）。
- **待后端契约**：Query 键形、SSE 事件类型、新建任务提交均为占位/草案，须在 `contracts/openapi.json` 与 `task-events.schema.json` 生成后的契约接入任务中定稿替换。
- **版本留意**：vue-router 5.3.1 / pinia 4.0.3 / echarts 6.1.0 / vite 8.3.0 为安装时最新主版本，API 已通过本次类型检查与构建验证；长期兼容性在后续任务中持续观察。
- **运行时渲染**：curl 仅验证 HTTP 200 与 HTML 外壳；组件实际渲染（Sidebar 折叠、Dialog、Tabs 交互）未经浏览器验证，建议用户本地 `bun run dev` 目检。
