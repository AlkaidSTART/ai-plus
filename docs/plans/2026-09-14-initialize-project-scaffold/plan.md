# 初始化项目脚手架：实施计划

## 目标

按架构文档完成 M1 的首个最小可验收切片：建立可安装的 `backend/src/insightx` Python 包，提供 `GET /api/v1/health`，让现有后端测试脱离不存在的顶层 `main.py`，并在 Vite 中建立 `/api` 到 `http://localhost:8000` 的开发代理。完成后，后端可通过 uv 安装、测试、静态检查和本地启动；前端构建不受影响，并可在开发模式经 Vite 同源代理访问健康接口。

本次不宣称完成 M1 全部交付物。数据库、迁移、容器编排、任务队列、LangGraph 运行时、正式契约生成、前端测试工具链和 CI 均为明确的后续切片。

## 当前事实及依据

- 架构目标布局为 `frontend/`、`backend/src/insightx/`、`contracts/`、根级 `compose.yaml` 和 `.github/workflows/`，见 `docs/architecture.md:24-61`。M1 包含 monorepo 初始化、依赖锁定、数据库与迁移、契约生成和原型，见 `docs/architecture.md:271`、`PRD.md:366`；这些是一个阶段，不是一次原子实施。
- 后端目标技术栈为 Python 3.12、uv、FastAPI、Pydantic 2、SQLAlchemy 2 + psycopg 3 同步会话、Alembic、Celery/Redis、LangGraph，见 `docs/architecture.md:100-116`。验证工具目标为 pytest、Ruff、mypy。
- 前端已存在完整 Vue 3 页面骨架及 shadcn-vue 组件；`frontend/package.json` 当前只有 `dev`、`build`、`preview` 脚本。SSE 占位代码已按 `/api/v1/tasks/...` 地址编写，见 `frontend/src/composables/useTaskEvents.ts:37`。
- 当前 `backend/pyproject.toml` 使用 `sqlalchemy[asyncio]` 与 `asyncpg`，没有 Hatchling 构建配置，pytest 的 `pythonpath` 为 `["."]`；测试从 `main` 导入，但 `backend/main.py` 不存在，见 `backend/tests/conftest.py:5`、`backend/tests/test_health.py:5`。
- `backend/uv.lock` 当前不可解析：`uv lock --check` 报告 `Dependency 'sqlalchemy' has missing 'source' field but has more than one matching package`，且残留重复项目/依赖条目，必须由 uv 重新生成，不能手工修补。
- 现有健康测试已固化接口契约：应用标题为 `InsightX API`；`GET /api/v1/health` 返回 `code=0`、`message=ok`、`data.status=degraded`、`data.version=0.1.0`、布尔值 `data.db` 与 `data.redis`；OpenAPI 路径必须是 `/api/v1/health`；未知路由保留 Starlette 原生 404 `{"detail":"Not Found"}`，不增加全局 Envelope 异常处理器。
- `frontend/vite.config.ts` 尚未配置 `/api` 代理；架构要求开发环境沿用同源 `/api` 边界，见 `docs/architecture.md:225`。
- 工作区当前位于 `feature-myj`，执行计划撰写前 `git status --short` 为空。环境已确认可用：Bun `1.4.2`、uv `0.11.28`、Docker `29.2.1`。`backend/.venv` 已有 Python 3.12 和部分依赖，但本次验证仍以 uv 管理的锁文件和命令结果为准。

## 预计变更文件

```text
docs/plans/2026-09-14-initialize-project-scaffold/plan.md
backend/pyproject.toml
backend/uv.lock
backend/README.md
backend/src/insightx/__init__.py
backend/src/insightx/main.py
backend/src/insightx/api/__init__.py
backend/src/insightx/api/router.py
backend/src/insightx/api/v1/__init__.py
backend/src/insightx/api/v1/health.py
backend/tests/conftest.py
backend/tests/test_health.py
frontend/vite.config.ts
```

文件内容边界：

- `backend/pyproject.toml`：加入 Hatchling `[build-system]`，wheel 包路径设为 `src/insightx`；保留 Python `>=3.12` 和现有 FastAPI、LangGraph、Redis、Pydantic Settings、httpx、pgvector 依赖；将 `sqlalchemy[asyncio] + asyncpg` 替换为 `sqlalchemy>=2.0.40 + psycopg[binary]>=3.2`；开发依赖加入 `ruff>=0.9.0` 与 `mypy>=1.14.0`；增加最小 Ruff（`target-version=py312`、`line-length=88`、基础 E/F/I/UP/B 规则）和 mypy（`python_version=3.12`、`mypy_path=src`、禁止未标注定义）配置；pytest `pythonpath` 改为 `["src"]`。
- `backend/uv.lock`：由 `uv lock` 重新生成，记录实际解析版本；不手工编辑。
- `backend/src/insightx/__init__.py`：定义 `__version__ = "0.1.0"`。
- `backend/src/insightx/main.py`：定义有类型的 `create_app() -> FastAPI`，创建标题为 `InsightX API`、版本来自包版本的 FastAPI 应用；添加 CORS，明确允许 `http://localhost:5173`，允许凭据、常用方法和请求头；仅以 `/api/v1` 前缀挂载聚合路由一次；定义模块级 `app = create_app()`。
- `backend/src/insightx/api/router.py`：创建聚合 `APIRouter` 并包含 v1 健康路由。
- `backend/src/insightx/api/v1/health.py`：创建 `GET /health` 的有类型处理函数，返回固定 Envelope；在未实施真实 DB/Redis 探针前，`db=false`、`redis=false`、`status="degraded"`，不得因存在配置值而报告 `true`。
- `backend/src/insightx/api/__init__.py`、`backend/src/insightx/api/v1/__init__.py`：包标记文件，不添加未使用逻辑。
- `backend/tests/conftest.py`、`backend/tests/test_health.py`：改为 `from insightx.main import create_app`；保留现有契约断言；CORS 测试增加 `access-control-allow-origin == http://localhost:5173` 的真实断言；将未知路由测试名改为准确描述 Starlette 原生 404，不改响应语义。
- `backend/README.md`：删除不存在示例配置的复制步骤；启动命令改为 `uv run uvicorn insightx.main:app --reload --port 8000`；目录说明改为 `src/insightx` 当前实际结构，并明确数据库、迁移与 Worker 尚未接入。
- `frontend/vite.config.ts`：在 Vite `server.proxy` 中增加 `/api` 到 `http://localhost:8000` 的代理，保留 `changeOrigin: true`，不改现有插件和别名配置。

## 实施步骤与分工

本次改动是单条、紧耦合的安装/启动闭环，文件数虽多但依赖顺序明确；不再拆分子代理并避免并行写同一后端包。主代理负责全部实现、集成和验证；已完成的独立只读审查仅用于确认范围与风险，不作为实施或验证证据。

1. 更新 `backend/pyproject.toml` 的构建系统、依赖、开发依赖、pytest、Ruff 和 mypy 配置。
2. 创建 `backend/src/insightx` 包及 `api/router.py`、`api/v1/health.py`，按上述契约实现应用工厂、模块级应用和健康接口。
3. 修改两处测试导入，并强化 CORS 断言、校正 404 测试名称；不新增业务端点或全局异常处理器。
4. 在 `backend/` 执行 uv 锁文件重新生成与同步，生成新的 `backend/uv.lock`。
5. 更新 `backend/README.md`，只记录本切片真实可用的启动方式和目录。
6. 在 `frontend/vite.config.ts` 增加 `/api` 开发代理。
7. 依次执行后端静态检查、单元测试、启动/HTTP 冒烟测试，以及前端构建和代理冒烟测试；发现问题只在获批范围内修正并重跑。
8. 检查 `git diff --check` 和工作区状态，随后单独创建 `result.md`，如实记录命令、结果和偏差。

## 验证与验收

后端静态和测试验证：

```bash
cd /Users/allure/Desktop/ai-plus/backend
uv lock --check
uv run pytest -q
uv run ruff check .
uv run mypy src
```

预期：锁文件可解析且未因检查产生修改；测试全部通过；Ruff 和 mypy 无错误。

后端运行时验证：

```bash
cd /Users/allure/Desktop/ai-plus/backend
uv run uvicorn insightx.main:app --host 127.0.0.1 --port 8000
curl -i http://127.0.0.1:8000/api/v1/health
curl -i http://127.0.0.1:8000/openapi.json
curl -i http://127.0.0.1:8000/not-found
```

预期：健康接口返回 HTTP 200 和既定 Envelope；携带 `Origin: http://localhost:5173` 时返回对应 CORS 头；OpenAPI 仅包含 `/api/v1/health` 而非重复前缀；未知路由返回 Starlette 原生 404；验证后关闭本地服务进程。

前端验证：

```bash
cd /Users/allure/Desktop/ai-plus/frontend
bun run build
bun run dev --host 127.0.0.1 --port 5173
curl -i http://127.0.0.1:5173/api/v1/health
```

预期：`vue-tsc` 与 Vite 构建成功；在前端开发服务器启动且后端服务可访问时，代理请求返回后端健康响应；验证后关闭本地进程。

最终检查：

```bash
cd /Users/allure/Desktop/ai-plus
git diff --check
git status --short
```

预期：无空白错误；变更仅包含获批范围内文件及本任务计划文件。提交、推送、PR、容器启动、数据库迁移和生产变更均不执行。

## 风险与非目标

风险与假设：

- 新增 psycopg 依赖会增加锁文件和安装体积，但这是对齐架构的必需变更；本次不会用它建立真实连接。
- `health` 在没有真实探针时只能报告 `degraded`，这会让接口暂不显示为 healthy；这是避免伪造数据库/Redis 可用性的有意行为。
- 最终锁定的 Ruff、mypy、psycopg 等补丁版本由 uv 在实际解析时确定；计划中的下限是兼容性约束，结果文件将记录命令输出和实际产物。
- 前端当前依赖树已存在且 Node 环境为 v26；若构建出现与本切片无关的既有失败，将如实记录，不在本任务中顺手升级或重构前端。
- `docs/architecture.md:6` 和根 README 的“尚无可运行实现”状态已滞后于现有前端；本次不混改文档状态，建议另立文档同步任务。

非目标：

- 不创建 `compose.yaml`，不启动 PostgreSQL/pgvector 或 Redis 容器。
- 不创建 Alembic、`backend/migrations/`、数据库模型、会话或真实健康探针。
- 不创建 Celery、outbox、`worker.py`、`dispatcher.py` 或任务队列。
- 不创建 LangGraph 图、节点、checkpointer，也不宣称 LangGraph 运行时已验证。
- 不生成 `contracts/openapi.json`、事件 schema 或 Hey API 前端客户端；FastAPI 自动 `/openapi.json` 不等于正式契约快照。
- 不新增前端 ESLint、Vitest、Playwright、`frontend/e2e/` 或相关依赖。
- 不创建 CI workflow、根级新文档、空占位目录或未使用抽象。
- 不读取或输出任何密钥，不修改本地私密配置。
- 不做无关重构、格式化全仓、升级现有前端依赖、提交、推送、创建 PR 或部署。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-14
- 批准信息：2026-09-14，用户原文：“开始执行”
