# 第三次处理 feature-myj 冗余 rebase 冲突（以主线内容为主）

## 审核状态
已批准。用户在计划展示后明确指示实施，原话：“解决报错”（此前另有长期约束：“解决合并冲突，不要开subagent”“按照master分支的内容为主”）。据此执行本计划，主线按 `origin/main` 理解。批准时间：2026-09-14，实施人：主 agent（未开 subagent）。

## 目标
安全结束当前第三次冗余 rebase，清除 7 个未合并路径，回到本次 rebase 前提交 `ef3658e`。最终方向以主线内容为主：不把旧后端 Step1–Step5 历史重新播放到旧基点上；本次先结束 rebase，`ef3658e` 自带的 5 个 `backend/` 文件与主线的差异留作遗留事项另行决策。

## 当前事实及依据
- 当前为 `HEAD (no branch, rebasing feature-myj)`，`HEAD = 14c705b`（即 onto 本身）。
- `.git/rebase-merge/head-name = refs/heads/feature-myj`；`orig-head = ef3658e`；`onto = 14c705b`；`stopped-sha = dafaa1e feat(backend): Step 1 正式后端基础设施`。
- 已完成 1 个 pick（`dafaa1e`），剩余 22 个 pick；最后两个 pick 是 `a4bac8e` 与 `ef3658e`，说明仍是把主线已含历史（含前端重建及上次计划文档）整体向后重放到旧基点。
- 未合并路径共 7 个（`git diff --name-only --diff-filter=U` 实测）：
  - `.github/workflows/ci.yml`（DU）
  - `backend/README.md`（UU，有 `<<<<<<< HEAD` 残留）
  - `backend/main.py`（DU）
  - `backend/pyproject.toml`（UU，有冲突标记残留）
  - `backend/tests/conftest.py`（AA，有冲突标记残留）
  - `backend/tests/test_health.py`（AA，有冲突标记残留）
  - `backend/uv.lock`（UU，有冲突标记残留）
- 另有大量已暂存新增的 `backend/__pycache__/*.pyc` 编译产物，若继续 rebase 会污染重写历史。
- 主线映射：仓库无本地或远端 `master`；“master/主线”统一理解为 `origin/main = 153baf8`，不按本地过期 `main` 解决。
- `origin/main` 顶层为 `.gitignore、AGENTS.md、LICENSE、PRD.md、README.md、docs、frontend`，无 `backend/`、无 `.github/`；`14c705b` 是 `origin/main` 的祖先且顶层仍含旧 `backend/、docker-compose.yml、plan/` 等。
- `feature-myj` 当前引用为 `ef3658e`，链条为 `ef3658e -> a4bac8e -> ca6e00f -> 153baf8（origin/main）`；`git rev-list --left-right --count origin/main...ef3658e` 为 `0 3`。
- 关键变化（与上次不同）：`ef3658e` 本身已包含 5 个 `backend/` 文件（`backend/README.md、backend/pyproject.toml、backend/tests/conftest.py、backend/tests/test_health.py、backend/uv.lock`，由 `git diff-tree --name-only -r ef3658e` 实测）及 `docs/plans/2026-09-14-resolve-rebase-conflict-02/` 文档；`git ls-tree --name-only ef3658e` 含 `backend`，而 `origin/main` 无 `backend/`。因此本次 `abort` 只能回到“带 5 个 backend 文件的 `ef3658e`”，不能像上次一样直接恢复到无 `backend/` 状态。
- 本次只读探索未开 subagent；未修改冲突文件或业务代码。

## 预计变更文件
- 新建：`docs/plans/2026-09-14-resolve-rebase-conflict-03/plan.md`（本文件，审核前唯一允许的写入；用 `-03` 后缀避免覆盖已有任务）。
- 实施时仅改变 Git rebase 状态：执行 `git rebase --abort`，回到 `ef3658e`；不编辑业务文件内容，不做手工合并。
- 实施结束后新增：同目录 `result.md`（审核前不创建）。
- 不执行 commit、push、强制更新、分支删除或历史重写；不清理或提交 `__pycache__`。

## 实施步骤
1. 记录实施前状态（只读）：`git rev-parse HEAD`、`git status --short --branch`、`git diff --name-only --diff-filter=U`、`orig-head/onto/stopped-sha`、已完成/剩余 pick 数量。
2. 执行 `git rebase --abort`，回到 `ef3658e`。
3. 核验分支与工作树：
   - 当前分支为 `feature-myj`；
   - `git rev-parse HEAD` 为 `ef3658e`；
   - `git diff --name-only --diff-filter=U` 为空；
   - `git diff --check` 无输出；
   - `git rev-list --left-right --count origin/main...HEAD` 为 `0 3`；
   - `.git/rebase-merge` 已消失。
4. 在同一任务目录写入 `result.md`，记录真实命令输出、完成状态、偏差和遗留事项，并向用户提供结果路径和摘要。

## 验证与验收
- 验收标准：rebase 已结束；当前分支为 `feature-myj`；`HEAD` 为 `ef3658e`；不存在未合并路径；与 `origin/main` 相比为 `0 3`。
- 因不修改业务内容，不运行前后端测试。若状态检查与预期不一致，停止并如实记录，不继续执行其它恢复命令。
- 特别说明：验收不包含“顶层无 `backend/`”，因为 `ef3658e` 自带 5 个 `backend/` 文件；如需严格对齐 `origin/main`（删除该 5 文件），须另立计划并重新审核。

## 风险与非目标
- `git rebase --abort` 会丢弃当前冗余重放过程，但 `feature-myj` 历史（含 `ef3658e` 的 5 个 backend 文件与 02 计划文档）完整保留。
- 本计划不手工解决 7 个冲突后 `git rebase --continue`；后面还有 22 个 pick（含删除 backend、前端脚手架重建等），会继续引入大面积重复冲突且可能把 `__pycache__` 带入历史，违背最小闭环。
- 本计划不删除 `ef3658e` 自带的 5 个 `backend/` 文件以强行恢复无 `backend/` 状态；不推送远端；不开 subagent，由主 agent 直接执行。
