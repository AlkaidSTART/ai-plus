# 第四次冗余 rebase 脱困 + push（无损 abort 回 36b9344 后快进推送）

## 审核状态
已批准。用户在计划展示后明确回复“实施”（2026-09-14），批准本修订计划的 abort + 快进 push 范围；此前“解决冲突并push”仅记为任务请求，不算批准。

## 目标
退出当前卡住的 `rebase`，回到 `pull` 前的位置 `36b9344（本地 feature-myj）`，然后把 `feature-myj` 快进推送到 `origin/feature-myj`，让 `git diff --check` 不再因冲突标记失败。不改任何业务文件内容，不重写历史，不用 `--force`。

## 当前事实
- 当前为 detached HEAD，`rebasing feature-myj`，`.git/rebase-merge` 存在，`orig-head = 36b9344`，`onto = 14c705b = origin/feature-myj`，停在 `dafaa1e Step 1`。
- 未合并仍是 7 个：`.github/workflows/ci.yml(DU)`、`backend/main.py(DU)`、`backend/README.md(UU)`、`backend/pyproject.toml(UU)`、`backend/uv.lock(UU)`、`backend/tests/conftest.py(AA)`、`backend/tests/test_health.py(AA)`。
- 本次 `rebase` 由 `pull` 触发（`pull.rebase=true`，reflog 有 `pull --tags origin feature-myj (start)`），把已在历史里的老提交向旧基点重复重放，第一步必冲突，与前三次模式相同。
- `git rev-list --left-right --count origin/feature-myj...feature-myj = 0 38`，且 `origin/feature-myj` 是 `feature-myj` 的祖先：`abort` 回去后可快进推送，无需 `--force`。
- 约束：不开 subagent；不提交/推送之外的重写历史操作一律不做；最小闭环。

## 变更范围
- 跟踪文件：无手改。只做 `git rebase --abort`（恢复索引与工作区到 `36b9344`）+ `git push origin feature-myj`（快进 38 个提交）。
- 允许的写入：本任务目录、`plan.md` 修订；实施结束后同目录写 `result.md`。其他项目文件不改，不新建提交。

## 实施步骤
1. 确认仍处于本次 `rebase`（`status` 显示 `rebasing feature-myj` 且 `orig-head` 仍为 `36b9344`）。
2. 执行 `git rebase --abort`，回到 `36b9344`。
3. 复核：`status` 为 `## feature-myj` 无 `DU/UU/AA`，`log` 顶部为 `36b9344`，`diff --check` 干净，`ahead 38` 且可快进。
4. 执行 `git push origin feature-myj`（不用 `--force`；若远端在此期间新增提交导致非快进则停手并如实记录，不强推）。
5. 写同目录 `result.md` 并报告。

## 验证与验收
- `git status --short --branch` 显示 `## feature-myj`，无 `DU/UU/AA`，无 `rebasing`。
- `git log --oneline -3 feature-myj` 顶部为 `36b9344`。
- `git diff --check` 无输出。
- `git rev-list --left-right --count origin/feature-myj...feature-myj` 推送后为 `0 0`。
- 以上均记录真实命令输出；未运行的不写成通过。

## 风险与非目标
- `abort` 会丢弃本次 `rebase` 中的冲突解决进度；当前均为未解决标记，无有效进度可丢。
- 若 `push` 时远端已新增提交，本计划不强推、不改历史，停手并在 `result.md` 如实记录。
- 不做“逐个解决 20+ 个重放冲突并继续 rebase”（高风险重写历史），不做“严格以 `origin/main` 对齐删 `backend/`”，不改 `pull.rebase` 配置，不提交新内容。上述如需做，另立任务。
