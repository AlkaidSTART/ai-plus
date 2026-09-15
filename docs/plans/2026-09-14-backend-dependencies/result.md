# 安装 InsightX 后端依赖：实施结果

## 完成状态
已完成。后端依赖清单、锁文件和本地 Python 3.12 虚拟环境已按获批计划更新；计划内规定的自动化验证均通过。

## 实际变更
- `backend/pyproject.toml`
  - 新增默认依赖：`alembic>=1.20.0`、`celery>=5.6.3,<6`、`scikit-learn>=1.9.1`、`langgraph-checkpoint-postgres>=3.1.2`、`anthropic>=1.5.0`。
  - 移除原 `embedding = ["sentence-transformers>=5.0"]` optional extra；执行 `uv remove` 后该表只剩空extra，随后删除了空的 `[project.optional-dependencies]` 段。
- `backend/uv.lock`
  - 由 uv 重新解析生成，包含新增依赖及其传递依赖。
  - 项目锁文件中已不再包含 `sentence-transformers`、`torch`、`transformers` 或 `FlagEmbedding`。
- `backend/.venv/`
  - 已通过 `uv sync --frozen` 与锁文件同步；实际安装 `alembic 1.20.0`、`anthropic 1.5.0`、`celery 5.6.3`、`langgraph-checkpoint-postgres 3.1.2`、`scikit-learn 1.9.1` 等依赖。
- `docs/plans/2026-09-14-backend-dependencies/plan.md`
  - 已记录真实审批信息：2026-09-14，用户原文“开始”。
- `docs/plans/2026-09-14-backend-dependencies/result.md`
  - 本结果文件。

未修改任何业务源代码、测试代码、数据库配置、架构文档或外部服务状态。

## 实施记录
1. 将 `plan.md` 状态更新为“已批准”，记录用户原文“开始”。
2. 在 `backend/` 执行 `uv remove --optional embedding sentence-transformers`，成功移除冲突的可选依赖。
3. 在 `backend/` 执行 `uv add 'alembic>=1.20.0' 'celery>=5.6.3,<6' 'scikit-learn>=1.9.1' 'langgraph-checkpoint-postgres>=3.1.2' 'anthropic>=1.5.0'`。uv 解析 115 个包并安装 29 个包；新增依赖版本与计划一致。
4. 检查 `pyproject.toml` 后，删除 uv 遗留的空 `embedding` extra 和空 optional 段，再执行 `uv lock` 重新生成锁文件。
5. 依次执行锁文件检查、冻结同步、测试、静态检查、依赖导入和禁用本地推理依赖检查。
6. 额外验证 Celery 所依赖的 Kombu 已注册 Redis transport，确认现有直接 `redis` 依赖能够支撑 Redis broker 选择。

## 验证命令与真实结果
以下命令均在 `backend/` 目录执行：

| 命令 | 真实结果 |
| --- | --- |
| `uv lock --check` | 成功，锁文件与 manifest 一致。 |
| `uv sync --frozen` | 成功，环境与锁文件同步。 |
| `uv run pytest -q` | 通过，`6 passed in 0.02s`。 |
| `uv run ruff check .` | 通过，`All checks passed!`。 |
| `uv run mypy src` | 通过，`Success: no issues found in 6 source files`。 |
| `uv run python -c "import alembic, anthropic, celery, langgraph.checkpoint.postgres, sklearn; print('backend dependencies import ok')"` | 成功输出 `backend dependencies import ok`。 |
| `uv run python -c "import importlib.util as u; assert u.find_spec('torch') is None and u.find_spec('transformers') is None, 'local inference dependency present'; print('no local inference dependencies')"` | 成功输出 `no local inference dependencies`。 |
| `uv tree --depth 1` | 显示 `alembic 1.20.0`、`anthropic 1.5.0`、`celery 5.6.3`、`langgraph-checkpoint-postgres 3.1.2`、`scikit-learn 1.9.1` 已作为项目直接或运行时依赖出现。 |
| `uv run python -c "from kombu.transport import TRANSPORT_ALIASES; assert 'redis' in TRANSPORT_ALIASES; print(TRANSPORT_ALIASES['redis'])"` | 成功输出 `kombu.transport.redis:Transport`。 |
| `uv pip list` 过滤关键包 | 确认 `alembic`、`anthropic`、`celery`、`langgraph-checkpoint-postgres`、`scikit-learn` 实际安装；未出现 `torch`、`transformers`、`FlagEmbedding`。 |
| `git diff --check` | 通过，无空白错误。 |

补充说明：`uv add` 输出了三条来自第三方包元数据的 warning，内容为 uv 自动修正带尾逗号的版本约束；命令成功退出，未影响依赖解析或后续验证。

## 计划偏差
无实质性偏差。

执行细节与计划的差异仅在于：`uv remove --optional embedding sentence-transformers` 没有自动删除空的 optional 段，而是在 `pyproject.toml` 中留下 `embedding = []`；随后按计划中“该表为空时清理”的要求删除了空段。未改变依赖范围、验收标准或架构边界。

## 遗留问题与未执行检查
- 未初始化 Alembic、未生成或执行 migration；当前只完成依赖安装。
- 未初始化 Celery 应用或启动 Redis/Celery worker；只验证了 Redis transport 可注册。
- 未创建或运行 LangGraph PostgreSQL checkpointer 表，也未连接真实 PostgreSQL。
- 未调用 Anthropic 或 SiliconFlow API，未创建运行时配置或密钥。
- 未执行数据库集成、恢复、租户隔离、真实 PostgreSQL 或端到端任务检查；这些不在本次获批计划范围内。
- 工作区还存在与本任务无关的 `AGENTS.md` 修改和 `docs/plans/2026-09-14-agents-sync-docs-env-links/` 未跟踪目录，本次未触碰。
- 未执行 git commit、push、PR 或部署。
