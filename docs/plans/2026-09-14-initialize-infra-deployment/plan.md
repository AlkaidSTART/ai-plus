# 初始化 infra 部署目录：实施计划

## 目标

在仓库中新增集中管理部署文件的 `infra/`，用 Docker Compose 提供当前真实可运行的最小容器基座：PostgreSQL/pgvector、Redis、FastAPI API、Vue 静态构建与同域 Nginx 代理。同步 `README.md` 和 `docs/architecture.md`，使文档准确区分“已经落地的脚手架与部署基座”和“仍未实现的数据库连接、任务、业务 API、SSE、迁移与 CI”。

可验收结果：`docker compose -f infra/compose.yaml config` 校验通过；四个服务可用指定镜像/构建上下文启动并达到健康状态；访问 Web 首页返回构建后的 SPA，访问同域 `/api/v1/health` 由 Nginx 正确代理到 FastAPI；文档不再声称前后端尚未初始化，也不再引用根级 `compose.yaml`。

## 当前事实及依据

- `git status --short --untracked-files=all`：当前仅有 `docs/plans/2026-09-14-frontend-backend-api-contract/plan.md` 的用户/既有改动，以及未跟踪的 `docs/api.md`；本计划不修改这两项。
- `test -d infra` 返回不存在；`find` 未发现根级或 `infra/` 下的 Compose、Dockerfile、Nginx 配置。
- `frontend/package.json` 已存在，scripts 为 `dev`、`build`、`preview`，构建命令为 `vue-tsc -b && vite build`；`frontend/bun.lock`、`frontend/vite.config.ts`、`frontend/src/` 和 `frontend/public/` 已存在。
- `frontend/vite.config.ts` 仅在 Vite 开发服务器中把 `/api` 代理到 `http://localhost:8000`；容器运行时的同域代理需要由 Nginx 提供。
- `backend/pyproject.toml` 与 `backend/uv.lock` 已存在；Python 要求 `>=3.12`，Hatchling 打包路径为 `src/insightx`，启动目标为 `insightx.main:app`。
- `backend/src/insightx/api/v1/health.py` 当前固定返回 HTTP 200、`status=degraded`、`db=false`、`redis=false`；数据库和 Redis 探针尚未接入。
- 数据库连接、Alembic、Celery Worker、outbox dispatcher、LangGraph 图、业务 API、SSE、contracts 和 CI 均尚未实现，不能由部署文件伪装成已完成。
- `README.md` 仍写“尚无可运行的前后端实现”、前后端“待初始化”、根级 `compose.yaml` 和“当前没有可执行的项目安装/启动命令”。
- `docs/architecture.md` 状态仍写“尚无可运行实现”，目录树仍使用根级 `compose.yaml`；第 8.1 节要求 Compose 作为 Linux 联调/部署基线，并明确启动顺序不等于 ready、单机 Compose 不提供已验证高可用。
- 本机 `docker --version` 为 `29.2.1`，`docker compose version` 为 `v5.0.2`，Docker daemon 为 Linux；`docker manifest inspect` 已确认以下标签存在：`pgvector/pgvector:pg18`、`redis:8-alpine`、`nginx:1.29-alpine`、`oven/bun:1.4.2`、`ghcr.io/astral-sh/uv:0.11.28`、`python:3.12-slim-bookworm`。
- `frontend/dist/`、`frontend/node_modules/`、`backend/.venv/` 和 Python 缓存在工作区可能存在；镜像构建应只复制必要的锁定依赖和源码，不把本地产物或虚拟环境带入构建上下文。
- 本次是小型、紧密耦合的单目录部署初始化，文件之间需要统一服务名、端口和代理路径；不拆给多个写子代理，由主代理按顺序实施和验证，避免重叠写入。

## 预计变更文件

新增：

- `infra/compose.yaml`：定义 `db`、`redis`、`api`、`web` 四个服务、健康检查、依赖顺序、内部网络和持久卷。
- `infra/backend.Dockerfile`：多阶段安装 uv，冻结同步后端依赖，构建并启动 FastAPI。
- `infra/backend.Dockerfile.dockerignore`：限制后端镜像上下文为 `backend/pyproject.toml`、`backend/uv.lock`、`backend/README.md` 与 `backend/src/`。
- `infra/frontend.Dockerfile`：Bun 构建 Vue 静态资源，再由 Nginx 提供运行时镜像。
- `infra/frontend.Dockerfile.dockerignore`：限制前端构建上下文，保留 `frontend/` 的构建输入和 `infra/nginx.conf`，排除 `node_modules`、`dist` 等本地产物。
- `infra/nginx.conf`：配置 SPA fallback、`/api/` 同域反向代理和上游转发头。
- `infra/README.md`：记录服务表、启动/停止/日志/健康检查命令、数据卷行为、当前边界和非生产属性。

修改：

- `README.md`：更新当前状态、目录树、实际可执行命令和部署边界；不修改未跟踪的 `docs/api.md`。
- `docs/architecture.md`：更新文档版本/状态、monorepo 目录树、运行拓扑说明和第 8.1 节部署基座现状。
- `docs/plans/2026-09-14-initialize-infra-deployment/plan.md`：仅在用户批准后写入真实批准日期与原文，并更新审核状态。

验证通过后新增：

- `docs/plans/2026-09-14-initialize-infra-deployment/result.md`：按项目模板记录实际变更、命令、结果、偏差和遗留项。

明确不修改：`frontend/`、`backend/` 的代码、依赖和锁文件，`docs/api.md`，现有 API 合同计划，`PRD.md` 以及任何 CI、迁移、Worker、SSE 实现。

## 实施步骤与分工

1. **创建部署目录**
   - 新建 `infra/`，所有 Compose、Dockerfile、Nginx 和运维说明集中放在该目录。
   - 主代理按步骤实施，不创建额外空目录或空服务。

2. **实现 `infra/compose.yaml`**
   - 使用项目名 `insightx`，不写顶层 `version`。
   - `db`：镜像 `pgvector/pgvector:pg18`；环境变量数据库、用户均设为 `insightx`，密码使用 `${POSTGRES_PASSWORD:-insightx-dev}`；命名卷挂载到 PostgreSQL 18 基础镜像的数据根目录；`pg_isready -U insightx -d insightx` 健康检查；不映射宿主端口。
   - `redis`：镜像 `redis:8-alpine`；命令启用 AOF；命名卷挂载到 `/data`；`redis-cli ping` 健康检查；不映射宿主端口。
   - `api`：从仓库根构建 `infra/backend.Dockerfile`；仅 `expose: 8000`；等待 `db`、`redis` 均为 `service_healthy`；使用容器内 Python 标准库请求 `/api/v1/health` 作为健康检查；不注入应用尚未读取的数据库/Redis 配置变量。
   - `web`：从仓库根构建 `infra/frontend.Dockerfile`；发布 `"${APP_PORT:-8080}:80"`；等待 `api` 为 `service_healthy`；使用容器内 `wget` 检查首页。
   - 声明 `db_data`、`redis_data` 两个命名卷；四个服务统一使用 `restart: unless-stopped`。
   - 不创建空的 `migrate`、`worker`、`dispatcher` 或 LangGraph 服务。

3. **实现后端镜像**
   - 构建阶段镜像使用 `ghcr.io/astral-sh/uv:0.11.28`，运行基础镜像使用 `python:3.12-slim-bookworm`。
   - 设置无缓冲 Python、uv 复制链接模式，并将 `/app/.venv/bin` 放入 PATH。
   - 先复制 `backend/pyproject.toml`、`backend/uv.lock`、`backend/README.md`，执行 `uv sync --frozen --no-dev --no-install-project` 缓存依赖。
   - 再复制 `backend/src/`，执行 `uv sync --frozen --no-dev` 安装项目。
   - 暴露 8000，启动命令固定为 `uvicorn insightx.main:app --host 0.0.0.0 --port 8000`；不安装 Playwright 浏览器或本地模型权重。

4. **实现前端镜像**
   - 构建阶段使用 `oven/bun:1.4.2`，复制 `frontend/package.json` 和 `frontend/bun.lock` 后执行 `bun install --frozen-lockfile`，再复制前端构建输入并执行 `bun run build`。
   - 运行阶段使用 `nginx:1.29-alpine`，将构建出的 `/app/dist` 复制到 `/usr/share/nginx/html`，将 `infra/nginx.conf` 放入 Nginx 镜像默认配置目录，并替换默认 server 配置。
   - `infra/frontend.Dockerfile.dockerignore` 保留完整的前端构建输入与 `infra/nginx.conf`，排除 `frontend/node_modules/`、`frontend/dist/` 及其他无关仓库内容。

5. **实现 Nginx 同域代理**
   - 监听 80，静态根目录指向 `/usr/share/nginx/html`，SPA 使用 `try_files $uri $uri/ /index.html`。
   - `/api/` 使用 `proxy_pass http://api:8000;`，保留完整 `/api/v1/...` 路径，不能改成会剥掉前缀的尾斜杠形式。
   - 启用 HTTP/1.1；传递 `Host`、`X-Real-IP`、`X-Forwarded-For`、`X-Forwarded-Proto`；关闭代理缓冲并设置适合未来长连接的读取超时。文档只说明该配置兼容后续 SSE 边界，不宣称 SSE 已实现。

6. **补齐 `infra/README.md`**
   - 给出服务、端口、依赖、卷和镜像表。
   - 给出从仓库根运行 `docker compose -f infra/compose.yaml up -d --build`、查看 `ps`/`logs`、访问 `http://localhost:8080/` 与 `/api/v1/health`、执行 `down`/`down -v` 的命令。
   - 明确 `db`、`redis` 只在 Compose 内部网络暴露；`down -v` 会删除本部署的数据库和 Redis 命名卷。
   - 明确当前 health 返回 `degraded` 是应用尚未接入依赖的真实结果，不代表容器启动失败或依赖已经接通。
   - 明确默认数据库密码、无 TLS、无备份、无高可用、无迁移/Worker/业务 SSE，仅用于单机联调和部署基座验证。

7. **同步文档**
   - `README.md` 当前状态改为：前端 Vue/Vite 脚手架、后端 FastAPI 基础入口与 `/api/v1/health`、`infra/` 四服务容器基座已经落地；数据库/Redis 应用接入、业务链路、迁移、Worker、SSE、云端模型与 CI 仍未实现。
   - `README.md` 目录树把根级 `compose.yaml` 改为 `infra/compose.yaml`，并列出 `backend.Dockerfile`、`frontend.Dockerfile`、`nginx.conf`；前后端不再标为“待初始化”。
   - `README.md` 开发与实施部分改为列出当前可执行的本地前后端命令和 Compose 容器命令，同时保留“不把健康容器等同于业务/模型已完成”的边界。
   - `docs/architecture.md` 将版本更新为 `V1.1，2026-09-14，部署基座同步`；状态改为已有前端脚手架、FastAPI 基础入口和 `infra/` 单机容器基座，其余目标能力未实现。
   - `docs/architecture.md` 第 2 节目录树把根级 `compose.yaml` 替换为 `infra/` 及其四个核心部署文件；第 4 节拓扑说明改为当前只落地 Web、API、DB、Redis 容器，API 尚未连接 DB/Redis，Dispatcher/Worker/LangGraph 未部署。
   - `docs/architecture.md` 第 8.1 节增加当前 Compose 基座的服务与边界说明，保留原有“启动顺序不等于 ready”“迁移/ready 分离”“单机不提供已验证高可用”的约束。

8. **执行验证与结果记录**
   - 获批后按“验证与验收”执行静态校验、Docker 构建启动检查、健康接口检查和清理。
   - 只有实施和验证真实完成后，才创建 `result.md`；若失败或部分完成，如实记录，不预建成功结论。

## 验证与验收

静态校验：

```bash
docker compose -f infra/compose.yaml config
docker compose -f infra/compose.yaml config --services
docker compose -f infra/compose.yaml config --images
git diff --check
git diff --name-only
git status --short --untracked-files=all
```

验收条件：Compose 文件无解析错误；服务至少且仅包含 `db`、`redis`、`api`、`web`；构建上下文、Dockerfile、端口、卷和健康检查解析为计划值；`git diff --check` 无空白错误。

容器运行验证：

```bash
docker info
APP_PORT=18080 docker compose -p insightx-infra-check -f infra/compose.yaml up -d --build
docker compose -p insightx-infra-check -f infra/compose.yaml ps
docker compose -p insightx-infra-check -f infra/compose.yaml exec -T web nginx -t
curl -fsS -D - http://127.0.0.1:18080/ -o /tmp/insightx-web-index.html
curl -fsS -D - http://127.0.0.1:18080/api/v1/health
docker compose -p insightx-infra-check -f infra/compose.yaml logs --no-color api web db redis
docker compose -p insightx-infra-check -f infra/compose.yaml down -v
```

验收条件：四个容器启动，`db`、`redis`、`api`、`web` 达到 Compose 健康状态；Nginx 配置测试成功；首页返回 HTTP 200 且文件包含前端入口内容；`/api/v1/health` 返回 HTTP 200 和当前真实 JSON：

```json
{"code":0,"message":"ok","data":{"status":"degraded","version":"0.1.0","db":false,"redis":false}}
```

日志不得出现应用启动失败或 Nginx 配置错误；验证结束后用专属项目名清理容器和命名卷。如构建因网络、镜像或平台问题失败，记录原始错误和已完成的局部验证，不宣称通过。

文档一致性检查：

```bash
rg -n "compose\\.yaml|尚无可运行|待初始化|当前没有可执行" README.md docs/architecture.md
```

验收条件：不再引用根级 `compose.yaml`；不再声称前后端尚未初始化；保留对未实现能力的明确边界。`docs/api.md` 和现有 API 合同计划保持不变。

## 风险与非目标

- 这是单机 Compose 联调/部署基座，不是生产部署：不含 TLS、密钥管理、外部反向代理、备份恢复、监控、高可用或容量验证。
- `db`、`redis` 容器会健康，但 FastAPI 当前没有真实探针与连接逻辑，因此健康接口按现有实现返回 `degraded`；本次不修改应用来制造 `ok`。
- 数据库迁移、pgvector 初始化、Celery Worker、outbox dispatcher、LangGraph checkpointer、业务 REST/SSE、契约生成、CI 和云模型接入均不在本次范围。
- 默认数据库密码仅供本地开发；正式环境必须另行注入密钥并定义安全部署方案。
- 镜像使用明确标签但不固定 digest；后续可用性与升级策略需在部署硬化任务中审核。
- 构建需要拉取镜像和依赖，可能受网络、架构或 Docker Desktop 资源限制；验证端口使用 `18080` 以避免影响本机默认服务。
- 工作区已有未提交/未跟踪的 API 合同改动，本次不触碰、不覆盖；如文档引用产生冲突，以当前文件实际内容为准并在结果中说明。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-14
- 批准信息：2026-09-14；用户原文：“开始”
