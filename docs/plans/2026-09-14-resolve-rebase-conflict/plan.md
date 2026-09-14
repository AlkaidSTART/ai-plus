# 处理 feature-myj 冗余 rebase 冲突（以 master/主线内容为主）

## 审核状态
已批准。用户于 2026-09-14 在计划展示后明确回复“开始”，批准按本计划执行 `git rebase --abort`。本次修订仍未使用 subagent。

## 目标
安全结束当前冗余 rebase，清除 5 个未合并路径，并把 `feature-myj` 恢复到 rebase 前提交 `ca6e00f`。最终状态以主线内容为主：保持与 `origin/main` 一致的“无 `backend/` 目录”结果，同时保留 `feature-myj` 已有提交，不逐块重放已被主线取代的旧实现。

## 当前事实及依据
- 当前为 `HEAD (no branch, rebasing feature-myj)`，基点 `onto = 14c705b`，原分支头 `orig-head = ca6e00f`，当前停在 `3e56e1a chore: 删除 backend 后端目录及全部文件`。
- 已完成 9 个 pick，剩余 12 个 pick（`git-rebase-todo` 中仍有 `Delete .github/workflows/ci.yml`、前端脚手架/设计令牌/五大模块骨架等，以及最后的 `ca6e00f` 本身）。
- 未合并路径共 5 个（`git diff --name-only --diff-filter=U`）：
  - `backend/.gitignore`
  - `backend/Dockerfile`
  - `backend/pyproject.toml`
  - `backend/tests/__init__.py`
  - `backend/uv.lock`
- 主线映射结论：仓库没有本地或远端 `master` 分支（`git branch -a | grep -i master` 为空，`refs/heads/master` 与 `refs/remotes/origin/master` 均不存在）。本地 `main = 9f0be2b` 落后 `origin/main = 153baf8` 共 28 个提交，因此用户所说“master”只能理解为 `origin/main`，不能按本地过期 `main` 解决。
- `origin/main` 顶层树为 `.gitignore、AGENTS.md、LICENSE、PRD.md、README.md、docs、frontend`，无 `backend/`；`ca6e00f` 顶层树与 `origin/main` 完全一致，同样无 `backend/`。
- `git rev-list --left-right --count origin/main...ca6e00f` 为 `0 1`，共同祖先即 `origin/main`；`ca6e00f` 的父提交就是 `origin/main`，`feature-myj` 相对 `origin/feature-myj` 为领先 35、落后 0（实施前需复核）。
- `14c705b` 是 `origin/main` 的祖先（`origin/main` 包含该提交），其顶层仍含 `backend/、docker-compose.yml、plan/` 等旧结构；当前 rebase 是把已在主线中的旧后端 Step1–5、文档补丁、删除 backend、前端基建等历史重新播放到旧基点上，属于向后冗余重放。
- 如果只看当前停住的 `3e56e1a`，主线一致的选择也是“删除/不存在”，而不是保留重放中出现的旧 backend 更新；但不对该提交单独做保留式合并，因为整个重放完成后仍会与主线产生大量重复冲突。
- 本次只读探索未使用 subagent，结论来自直接执行的 Git 只读命令；未修改冲突文件或业务代码。

## 预计变更文件
- 修订：`docs/plans/2026-09-14-resolve-rebase-conflict/plan.md`（本文件，本次审核前唯一允许的写入）。
- 实施时仅改变 Git rebase 状态：执行 `git rebase --abort`，回到 `ca6e00f`；不编辑 `backend/`、`frontend/`、`docs/` 业务内容。
- 实施结束后新增：同目录 `result.md`（审核前不创建）。
- 不执行 commit、push、强制更新、分支删除或历史重写。

## 实施步骤
1. 记录实施前状态（只读）：
   - `git rev-parse HEAD`
   - `git status --short --branch`
   - `git diff --name-only --diff-filter=U`
   - `.git/rebase-merge/orig-head`、`.git/rebase-merge/onto`、已完成/剩余 pick 数量。
2. 执行 `git rebase --abort`，回到 rebase 前的 `feature-myj`（预期为 `ca6e00f`）。
3. 核验分支与工作树：
   - 当前分支为 `feature-myj`；
   - `git rev-parse HEAD` 为 `ca6e00f`；
   - `git status --short --branch` 无已修改、未合并异常（除本任务 `plan.md` 未跟踪项外按实记录）；
   - `git diff --name-only --diff-filter=U` 为空；
   - `git diff --check` 无输出；
   - `git rev-list --left-right --count origin/main...HEAD` 为 `0 1`；
   - `git ls-tree --name-only HEAD` 无 `backend/`。
4. 在同一任务目录写入 `result.md`，记录真实命令输出、完成状态、偏差和遗留事项，并向用户提供结果路径和摘要。

## 验证与验收
- 验收标准：rebase 已结束；当前分支为 `feature-myj`；`HEAD` 恢复为 `ca6e00f`；不存在未合并路径；分支仍以 `origin/main` 为父提交且只领先一个提交；顶层无 `backend/`，与主线一致。
- 因不修改业务内容，不运行前后端测试。若状态检查与预期不一致，停止并如实记录，不继续执行其它恢复命令。

## 风险与非目标
- `git rebase --abort` 会丢弃当前冗余重放过程，但被重放提交的逻辑仍保留在原 `feature-myj` 历史中；不删除既有提交或分支引用备份。
- 本计划不是把分支精确重置为 `origin/main`，不会丢弃 `ca6e00f` 的已有提交；如需彻底丢弃 `ca6e00f` 回到纯 `origin/main`，须另立计划并重新审核。
- 本计划不把 `feature-myj` 线性化，也不手工 `git rm + git rebase --continue` 逐个解决剩余 12 个 pick；后者会继续重放已在主线中的前后端历史，冲突面大且违背最小闭环。
- 不推送远端；推送需后续单独授权。
- 不开 subagent（按用户要求，主 agent 直接执行）。
