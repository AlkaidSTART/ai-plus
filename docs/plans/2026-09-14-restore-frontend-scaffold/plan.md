# 恢复 frontend 前端脚手架：实施计划（修订 1）

## 目标
保留已从 `153baf8` 恢复的 15 个前端脚手架文件及其原始锁文件，使用支持 `lockfileVersion: 2` 的临时 Bun 1.4.2 完成冻结安装，并通过 `vue-tsc -b && vite build`，使 `frontend/` 重新可安装、可构建。

## 当前事实及依据
- 初版计划已获用户明确批准，批准原文为“开始”；该批准仅覆盖初版方案。
- 已按初版方案从 `153baf8` 恢复以下 15 个文件到工作区：
  `frontend/.gitignore`、`frontend/.vscode/extensions.json`、`frontend/README.md`、`frontend/bun.lock`、`frontend/index.html`、`frontend/package.json`、`frontend/public/favicon.svg`、`frontend/public/icons.svg`、`frontend/src/App.vue`、`frontend/src/main.ts`、`frontend/src/style.css`、`frontend/tsconfig.app.json`、`frontend/tsconfig.json`、`frontend/tsconfig.node.json`、`frontend/vite.config.ts`。
- 15 个文件已逐文件用 `git hash-object` 与 `git rev-parse 153baf8:<path>` 比较，全部一致。
- 这些文件在当前 `HEAD` 中仍属于“已删除”路径，因此 Git 将其显示为未跟踪文件；这不代表内容不一致。初版计划中的 `git diff --exit-code 153baf8 -- frontend` 无法覆盖未跟踪文件，该验证方式在本状态下无效。
- 本机 `/opt/homebrew/bin/bun` 版本为 `1.3.11`；执行 `bun install --frozen-lockfile` 时，Bun 报错 `Unknown lockfile version`，位置为 `bun.lock:2`，并因此拒绝冻结安装。
- 恢复后的 `bun.lock` 第 2 行为 `"lockfileVersion": 2`；`npm view bun version` 返回 `1.4.2`。
- 由于冻结安装未完成，`frontend/node_modules` 仍缺少 `vue-router`、`pinia`、`@tanstack/vue-query`、`@lucide/vue`、`reka-ui`、`clsx`、`tailwind-merge` 等包。
- 随后执行 `bun run build` 的真实结果为失败：`vue-tsc` 报告大量 `TS2307: Cannot find module`，直接原因是上述依赖未安装，而不是已恢复文件缺失。
- 初版 `docs/前端设计.md` 与当前源码在 Pinia、Tailwind、ECharts、UI 组件库及 Vite proxy 上仍存在既有文档/代码冲突；本修订仍不处理该冲突。

## 预计变更文件
- 不再修改 `frontend/` 中已恢复的 15 个文件，尤其禁止修改 `frontend/bun.lock`。
- `npx --yes bun@1.4.2 install --frozen-lockfile` 仅允许更新 `frontend/node_modules` 及其 Bun 安装产物；仓库内跟踪内容不得发生额外变化。
- `npx` 会将 Bun 1.4.2 下载到用户级 npm/npx 缓存，不属于项目依赖，也不全局替换 `/opt/homebrew/bin/bun`。
- 完成后更新本任务目录中的 `result.md`；再次修订计划时保留真实历史记录。
- 不修改 `backend/**`、其他 `frontend/src/**` 源码、历史计划或设计文档。

## 实施步骤与分工
1. 复核 15 个已恢复文件的 blob 哈希仍与 `153baf8` 一致，并记录 `frontend/bun.lock` 的 blob 哈希作为冻结基线。
2. 执行 `npx --yes bun@1.4.2 --version`，确认临时 Bun 可运行且版本为 `1.4.2`。
3. 在 `frontend/` 执行 `npx --yes bun@1.4.2 install --frozen-lockfile`。若仍失败，停止，不修改锁文件，不用非冻结安装绕过。
4. 重新计算 `frontend/bun.lock` 的 blob 哈希，确认与步骤 1 基线一致。
5. 在 `frontend/` 执行 `npx --yes bun@1.4.2 run build`，即执行 `vue-tsc -b && vite build`。
6. 若构建因源码类型错误失败，不擅自修复业务源码；如实记录并再次提交计划修订等待审批。
7. 成功或失败都在 `docs/plans/2026-09-14-restore-frontend-scaffold/result.md` 更新最终状态、命令与真实输出摘要。

本修订是在同一组文件上继续串行验证，没有可独立并行且不重叠的工作包，因此不启用子代理。

## 验证与验收
1. `npx --yes bun@1.4.2 --version`：输出 `1.4.2`。
2. `npx --yes bun@1.4.2 install --frozen-lockfile`：安装成功，不产生锁文件变更。
3. `git hash-object frontend/bun.lock`：安装前后哈希一致，并与 `git rev-parse 153baf8:frontend/bun.lock` 一致。
4. `npx --yes bun@1.4.2 run build`：`vue-tsc -b` 与 `vite build` 均以退出码 0 完成。
5. `test -f frontend/package.json && test -f frontend/bun.lock && test -f frontend/index.html && test -f frontend/src/main.ts && test -f frontend/src/App.vue`：退出码为 0。
6. `git status --short`：除任务目录外，只显示批准的 15 个前端恢复文件及被忽略的安装/构建产物；不得出现 `backend/**` 或额外源码改动。

验收条件：本机无需修改项目锁文件即可用临时 Bun 1.4.2 完成冻结安装；`frontend/bun.lock` 保持 `153baf8` 原内容；前端生产构建通过；未修改架构、文档冲突项或后端。

## 风险与非目标
- `npx --yes bun@1.4.2` 需要从 npm registry 下载临时工具；若网络或该版本不可用，任务将阻塞并如实记录。
- Bun 1.4.2 兼容锁文件格式不代表所有依赖在沙箱环境可下载；任一下载或构建失败都将停止超出既有范围的修复。
- 当前源码可能存在独立于安装问题的 TypeScript 错误；本修订不授权修改业务源码。
- 非目标：全局升级 Homebrew Bun；重写或删除 `bun.lock`；修改依赖声明；重构源码；处理 `docs/前端设计.md` 冲突；执行 commit、push、PR、部署或生产变更。

## 审核状态
- 状态：已批准（修订 1）
- 创建日期：2026-09-14
- 初次批准：2026-09-14 用户原文：“开始”（仅批准初版计划）
- 修订批准：2026-09-14 用户原文：“我更新了，开始执行吧”。

## 修订记录
- 2026-09-14 修订 1：初版执行时发现本机 Bun 1.3.11 不支持锁文件的 `lockfileVersion: 2`；拟改用临时 `bun@1.4.2`，保持锁文件冻结，重新等待审批。
