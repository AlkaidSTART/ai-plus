# 清理 gitignore 与已跟踪的缓存文件：实施计划

## 目标
从 git 索引移除 29 个 `__pycache__/*.pyc` 文件，补全 `.gitignore` 缺失条目。

## 当前事实及依据
- `git ls-files --cached | grep __pycache__` 返回 29 个 `.pyc` 文件
- `.gitignore` 仅 6 行，缺少 `__pycache__/`、`*.pyc`、`.venv/`、`dist/`、`*.egg-info/`

## 预计变更文件
- `.gitignore` — 添加缺失条目
- git 索引 — `git rm --cached` 移除 29 个 pyc 文件（磁盘文件不删）

## 实施步骤与分工
1. `git rm -r --cached` 所有 `__pycache__/` 目录
2. `.gitignore` 追加缺失条目

## 验证与验收
- `git ls-files --cached | grep -c __pycache__` → 0
- `git diff --cached --name-only` 显示删除的 pyc 文件 + 修改的 .gitignore

## 风险与非目标
- 不删磁盘文件，不影响运行
- 不处理 `uv.lock` / `bun.lock`（lock 文件通常应提交）

## 审核状态
- 状态：已批准
- 创建日期：2025-07-27
- 批准信息：2025-07-27 用户回复「直接开始」确认批准
