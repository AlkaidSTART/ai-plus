# 前端基础提交拆分与 PR 发起：实施计划

## 目标

将当前工作区按逻辑拆分为 **5 个 commit**，在新分支 `feat/frontend-foundation` 上提交，推送至 `origin` 并向 `main` 发起一个 PR。

## 当前事实及依据

- 远端：`https://github.com/AlkaidSTART/ai-plus.git`；gh 已认证（账号 nextroad-dev，含 repo/workflow scope）。
- 当前分支 `feature/backend-skeleton`（HEAD = bdad9a6，PR#13 合并点），全部改动均未提交。
- 工作区含三类内容：
  1. **112 个已跟踪文件删除**（用户既有的工作区重置）：backend/ 56、plan/ 旧目录 30、frontend/ 旧文件 19、docs/ 旧文件 5、docker-compose.yml 等；
  2. **文档修改/新增**：AGENTS.md、README.md（M）、PRD.md、docs/architecture.md（未跟踪）、docs/plans/ 四个任务目录（未跟踪）；
  3. **新前端** frontend/（脚手架 + 外壳 + 组件 + 页面，部分覆盖了旧 frontend 跟踪路径）。
- 最后一次 `bun run build`（vue-tsc + vite）已通过；本任务不改代码内容，无需重新构建（提交前做 `git diff --cached --check` 与状态核对）。
- **关键决策（推荐）**：旧文件删除纳入本 PR。理由：删除是用户既有的工作区重置事实，新前端建立在重置后的状态上；剔除删除会让 PR 语义残缺（旧 backend 与新架构文档矛盾）。如不希望纳入，请在审批时指出，我将改为仅提交 2、3 类内容。

## 预计变更文件

| 文件 | 内容 |
| --- | --- |
| `docs/plans/2026-09-13-commit-and-pr/plan.md`、`result.md` | 本计划与结果 |
| Git 副作用 | 新分支 `feat/frontend-foundation`、5 个 commit、push 至 origin、PR（base: main） |

不修改任何代码/文档内容文件。

## 实施步骤与分工

1. 展示本计划，等待明确批准（重点确认：删除纳入 PR、分支名、PR 目标 main）。
2. 获批后记录审批信息；`git switch -c feat/frontend-foundation`（自当前 HEAD 切出，工作区改动随之携带，不丢失）。
3. **按以下拆分顺序提交**（每步 `git diff --cached --check` 后提交）：
   - C1 `chore: 清理旧实现，工作区进入设计文档阶段`：`git ls-files -d` 的全部删除（backend/、plan/ 旧目录、docs/ 旧文件、frontend/ 旧文件、docker-compose.yml）。
   - C2 `docs: PRD/架构/工作约定定稿与 UI 库决策修订（shadcn-vue）`：AGENTS.md、README.md、PRD.md、docs/architecture.md、docs/plans/（四个任务目录）。
   - C3 `feat(frontend): Vite+Vue3+TS+Tailwind v4+shadcn-vue 脚手架`：frontend/ 根配置（package.json、bun.lock、components.json、tsconfig×3、vite.config.ts、index.html、.gitignore、.vscode/、public/、README.md）。
   - C4 `feat(frontend): 浅色设计令牌与应用外壳（侧边栏/顶栏/路由/Provider/共享组件）`：src/ 下 style.css、main.ts、App.vue、app/、components/（含 ui/）、lib/、types/、stores/、composables/、api/。
   - C5 `feat(frontend): 五大模块页面骨架与空态`：src/features/。
   - 说明：去阶段标识与动画已含在对应文件最终态中（同一文件无法按任务拆历史），在 C4/C5 提交信息中注明。
4. `git push -u origin feat/frontend-foundation`。
5. `gh pr create --base main`：标题 `feat(frontend): InsightX 前端基础（shadcn-vue 浅色主题）与工作区重置`；正文含摘要、commit 清单、设计依据（docs/plans 路径）、验证结果、删除说明与风险。
6. 生成 result.md（含 PR 链接）。

分工：主代理直接执行（单线性 git 操作，无并行价值）。

## 验证与验收

- 每次提交前 `git diff --cached --check`；全部提交后 `git status` 干净、`git log --oneline -6` 恰为 5 个新 commit。
- push 后 `gh pr view` 确认 PR 创建成功、base=main、包含 5 个 commit。
- 验收：远端 PR 可打开，CI 状态（若有）如实记录，不把未运行检查说成通过。

## 风险与非目标

- **删除纳入 PR 的影响面**：PR 将删除旧 backend/ 等 112 个文件——评审者需知晓这是既定工作区重置；若误期，可在合并前通过 revert C1 调整。
- 不做：合并 PR（需另行授权）、改动远端其他分支、force push、设置分支保护。
- 若 push 被拒（权限/保护规则），如实记录并停止，不绕过。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-13
- 批准信息：2026-09-13 用户明确批准，原文“实施”（批准范围含：删除纳入 PR、分支 feat/frontend-foundation、PR 目标 main、5 个 commit 拆分）。
