# 安装 InsightX 后端依赖：实施计划

## 目标
让 `backend/` 的 Python 3.12 + uv 环境具备 `docs/architecture.md` 明确选定的后端、迁移、队列、PostgreSQL checkpoint 和云端模型客户端依赖，同时不引入架构禁止的本地推理依赖。

## 当前事实及依据
- `docs/architecture.md` §3.2 规定：Python 3.12、uv、FastAPI、Pydantic 2/settings、SQLAlchemy 2 + psycopg 3、Alembic、Celery 5 系列 + Redis broker、LangGraph + PostgreSQL checkpointer、scikit-learn（CPU）。
- `docs/architecture.md` §6.1–6.2 规定：模型调用使用云端 Anthropic Claude SDK/HTTP API；Embedding 使用 SiliconFlow 等供应商 API；禁止在项目环境中安装 PyTorch、Transformers、FlagEmbedding 做本地推理。
- `backend/pyproject.toml` 目前已声明 FastAPI、LangGraph、SQLAlchemy、psycopg 3、redis、pydantic-settings、httpx、pgvector 及开发工具，但缺少 architecture 明确要求的 Alembic、Celery、scikit-learn、LangGraph PostgreSQL checkpointer 和 Anthropic 客户端。
- `backend/pyproject.toml` 当前有一个 `embedding = ["sentence-transformers>=5.0"]` 可选依赖组；`sentence-transformers` 会引入 PyTorch/Transformers，与 §6.2 的禁止项冲突。
- `backend/.venv` 已是 Python 3.12.13；`uv 0.11.28` 可用。`backend/uv.lock` 当前包含由 `embedding` extra 解析出的 scikit-learn、sentence-transformers、torch、transformers 记录，但这些包不在默认安装环境中。
- PyPI 元数据检查结果（2026-09-14）：`alembic` 1.20.0、`celery` 5.6.3、`scikit-learn` 1.9.1、`langgraph-checkpoint-postgres` 3.1.2、`anthropic` 1.5.0 均支持 Python 3.12。
- `langgraph` 本体不提供 PostgreSQL checkpointer 实现；官方包名是 `langgraph-checkpoint-postgres`，需显式声明。
- 所有具体包版本和命令仍需在实施后由 `uv` 解析结果验证，不能以当前检索结果替代真实安装结果。

## 预计变更文件
- `backend/pyproject.toml`
  - 新增项目依赖：`alembic>=1.20.0`、`celery>=5.6.3,<6`、`scikit-learn>=1.9.1`、`langgraph-checkpoint-postgres>=3.1.2`、`anthropic>=1.5.0`。
  - 移除与架构冲突的 `[project.optional-dependencies]` 中 `embedding = ["sentence-transformers>=5.0"]` 条目；若移除后该表为空，则同时清理由 uv 生成的空表。
  - 不新增 `psycopg-pool` 直接依赖；它由 `langgraph-checkpoint-postgres` 传递安装。
- `backend/uv.lock`
  - 由 `uv` 重新解析和生成；绝不手工编辑。
- `backend/.venv/`
  - 由 `uv sync` 同步到获批的锁文件；不将虚拟环境文件纳入提交。
- 本任务目录：`docs/plans/2026-09-14-backend-dependencies/plan.md`、实施完成后的 `result.md`。

范围边界：只处理后端依赖清单、锁文件和本地虚拟环境；不修改后端源代码、配置、数据库 schema 或架构文档。

## 实施步骤与分工
主代理顺序执行；本任务的核心写入集中在同一个 `pyproject.toml` 和 `uv.lock`，并行写子代理会增加冲突风险，因此不使用写子代理。已有只读依赖审计子代理未返回结果，不作为本计划依据；若其在实施前返回，仅用于交叉核对，不改变本计划范围。

1. 记录当前仓库状态和 `backend/pyproject.toml` 基线，确认工作区没有与依赖变更无关的待处理修改；若出现新的实质冲突，暂停并回到计划审核。
2. 在 `backend/` 执行：
   ```bash
   uv remove --optional embedding sentence-transformers
   ```
   目的：移除与架构禁止项冲突的可选依赖组；不安装 `sentence-transformers`。
3. 在 `backend/` 执行：
   ```bash
   uv add 'alembic>=1.20.0' 'celery>=5.6.3,<6' 'scikit-learn>=1.9.1' 'langgraph-checkpoint-postgres>=3.1.2' 'anthropic>=1.5.0'
   ```
   由 uv 更新 `pyproject.toml`、重新解析 `uv.lock` 并同步 `.venv`。若解析结果显示与架构版本边界或现有依赖冲突，停止实施并记录真实冲突，不通过放宽 version bound 掩盖问题。
4. 检查 `backend/pyproject.toml` 和 `backend/uv.lock` 的实际 diff，确认只包含上述依赖变更及必要的 lockfile 传递解析变化。
5. 不创建 Alembic migration、不初始化 Celery app、不创建 LangGraph checkpoint 表、不启动 Redis/PostgreSQL、不调用 Anthropic 或 SiliconFlow API。

## 验证与验收
批准后在 `backend/` 执行以下命令，并以真实输出为准：

```bash
uv lock --check
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python -c "import alembic, anthropic, celery, langgraph.checkpoint.postgres, sklearn; print('backend dependencies import ok')"
uv run python -c "import importlib.util as u; assert u.find_spec('torch') is None and u.find_spec('transformers') is None, 'local inference dependency present'; print('no local inference dependencies')"
uv tree
```

验收条件：
- `uv lock --check` 与 `uv sync` 均成功，锁文件与 manifest 一致。
- `pytest`、Ruff、mypy 命令实际通过；若当前仓库存在与本次依赖变更无关的既有失败，如实记录，不能声称全部通过。
- Alembic、Anthropic、Celery、LangGraph PostgreSQL checkpointer、scikit-learn 均可在 Python 3.12 环境中导入。
- 默认虚拟环境中不存在 `torch` 和 `transformers`。
- `uv.lock` 中不再因项目 `embedding` extra 保留 sentence-transformers 依赖链；若 uv 因其他原因保留，明确报告来源，不手工删除。
- `git diff --check` 无空白错误；不执行 git commit/push。

## 风险与非目标
风险：
- 网络或 PyPI 可用性会影响解析和下载；失败时如实记录，不伪造安装成功。
- `anthropic` 1.5.0 的传递依赖当前包含独立的 `httpx2` 包，而非项目现有的 `httpx`；是否可接受以 uv 实际解析和导入测试为准。
- 移除 `embedding` optional extra 会使任何依赖 sentence-transformers 的本地流程不再可直接安装。这是按架构禁止本地 AI 权重推理所做的明确取舍；如用户希望保留该 optional extra，必须在批准前提出，因为那将改变本计划的依赖边界。
- 新增依赖只证明运行时可安装；不证明数据库连接、Celery worker、LangGraph checkpoint 或供应商 API 已经配置可用。

非目标：
- 不安装 PostgreSQL、Redis、Docker 或其他系统服务。
- 不运行数据库迁移、不创建运行时环境变量文件、不配置密钥。
- 不调用任何外部模型供应商。
- 不修改业务代码、测试、架构文档或其他前端/后端模块。
- 不做无关依赖升级、重构或格式清理。
- 不执行 git commit、push、PR 或部署。

## 审核状态
- 状态：已批准
- 创建日期：2026-09-14
- 批准信息：2026-09-14，用户原文“开始”
