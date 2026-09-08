# InsightX Web 前端 UI 现代化重构与交互动效落地计划

## 目标
构建工业级、简约高端（Obsidian 暗色磨砂玻璃 + 流体微动效）的跨境电商 AI 市场洞察与动态决策前端界面，完整落地 PRD 核心闭环：全景大盘、LangGraph 实时智能诊断任务流、多模态视觉取证 & VOC 痛点聚类、工厂级双栏改款决策引擎（本体+包装）、逆向财务熔断与动态模拟器。

## 技术选型与风格
- 框架：Vue 3.5 + TypeScript + Vite 8
- 样式：Tailwind CSS v4 (`@tailwindcss/vite`)
- 图标库：`lucide-vue-next`
- 视觉风格：Codex 极简黑曜石深色系、毛玻璃微反光、高对比度荧光语义点缀（翡翠绿/青蓝/琥珀金/警示红）、精细边框微发光、细腻流动动效。

## 变更文件列表
- `frontend/package.json`：新增 `tailwindcss`, `@tailwindcss/vite`, `lucide-vue-next` (已安装完成)
- `frontend/vite.config.ts`：集成 `@tailwindcss/vite` (已配置完成)
- `frontend/src/style.css`：Tailwind v4 入口、深色玻璃基座与发光微动效类 (已验证通过)
- `frontend/src/types/index.ts`：数据模型定义（任务、竞品、聚类、实拍证据、双栏改款、财务风控）
- `frontend/src/mock/data.ts`：高真实度业务样本数据集（符合 PRD 与 api.md）
- `frontend/src/components/Header.vue`：顶部导航、ASIN 快速选择、Agent 运行健康指示、标签栏
- `frontend/src/components/DashboardTab.vue`：全景监控大盘、4 大核心 KPI、风险雷达分布、任务概览
- `frontend/src/components/AgentWorkflowTab.vue`：LangGraph 5 节点动态执行工作流看板与实时模拟
- `frontend/src/components/VocClusterTab.vue`：多模态 VOC 痛点聚类与 Claude Vision 买家实拍缺陷取证画廊
- `frontend/src/components/DualColumnProposalsTab.vue`：工厂级双栏改款决策引擎（产品本体优化 vs 包装履约优化）
- `frontend/src/components/FinancialVetoTab.vue`：逆向财务约束与现金流熔断模拟器 + 历史回测验证
- `frontend/src/components/EvidenceDrawer.vue`：全链路证据端到端穿透抽屉
- `frontend/src/App.vue`：主界面组装与全局状态协同

## 验证步骤
1. 执行 `bun run build`（含 `vue-tsc -b` 类型静态校验与 vite 生产编译）确保 0 报错。
2. 启动 `vite preview` 或验证无损打包产物，确保所有交互与动效正常呈现。
