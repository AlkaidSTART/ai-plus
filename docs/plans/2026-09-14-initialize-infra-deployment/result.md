# 初始化 infra 部署目录：实施结果

## 完成状态

已完成。

`infra/` 单机 Docker Compose 部署基座、四个服务、前端构建与同域 Nginx 代理已落地；`README.md` 与 `docs/architecture.md` 已同步到当前真实状态。静态校验、前端镜像构建、Compose 启动、健康检查和清理均已执行，未发现阻断部署基座验收的失败。

## 实际变更

本任务直接新增或修改：

- `infra/compose.yaml`：定义 `db`、`redis`、`api`、`web` 四个服务、健康检查、启动依赖、内部网络及 `db_data`、`redis_data` 命名卷。
- `infra/backend.Dockerfile`：使用 uv 0.11.28 与 Python 3.12，多阶段冻结安装后端依赖并启动 FastAPI。
- `infra/backend.Dockerfile.dockerignore`：限制后端构建上下文，排除本地产物和虚拟环境。
- `infra/frontend.Dockerfile`：构建 Vue 静态资源，并由 Nginx 1.29 提供运行时服务。
- `infra/frontend.Dockerfile.dockerignore`：限制前端构建上下文，排除 `node_modules`、`dist` 等本地产物。
- `infra/nginx.conf`：提供 SPA fallback、`/api/` 同域反向代理、转发头和面向 SSE 的代理配置基础。
- `infra/README.md`：记录服务表、启动/检查/停止命令、配置、卷行为和非生产边界。
- `README.md`：更新当前状态、目录树、可执行命令和部署边界。
- `docs/architecture.md`：更新目录结构、运行拓扑和 8.1 部署基座现状。
- `docs/plans/2026-09-14-initialize-infra-deployment/plan.md`：记录真实批准信息和审核状态。
- `docs/plans/2026-09-14-initialize-infra-deployment/result.md`：本结果文件。

相关提交：

- `718f199 feat:add infra`
- `d469432 feat: 更新文档以反映当前项目状态和基础设施部署`
- `68f500c feat: Implement backend API for task management and persistence`，其中包含 `infra/frontend.Dockerfile` 的 Node 24 构建阶段修复。

`718f199` 同时包含工作区当时已有的 `.env.example`、`.gitignore`、`backend/README.md`、`docs/api.md` 和其他计划文件；这些不是本计划的目标变更，本结果不将其计为本任务完成内容。

## 实施记录

1. 按批准计划创建 `infra/`，统一四个服务的名称、端口、依赖顺序、健康检查和持久卷。
2. 为后端建立 uv 多阶段构建，只复制锁定依赖、项目元数据与后端源码，不复制本地虚拟环境或缓存。
3. 为前端建立 Bun 构建与 Nginx 运行的两阶段镜像，使用根构建上下文并保留 `infra/nginx.conf`。
4. 使用 Nginx 提供 SPA fallback 和 `/api/` 同域代理；API 不直接映射宿主机端口。
5. 首次构建发现 Bun 镜像内没有 Node 运行时，`vue-tsc` 报 `TS2307: Cannot find module './App.vue'`；在获批的前端 Dockerfile 范围内增加 `node:24-bookworm-slim` 阶段并复制 `node` 可执行文件后复验通过。
6. 更新根 README、架构文档和 `infra/README.md`，明确已经落地的基础设施与仍未实现的数据库连接、迁移、Worker、业务 API、SSE、契约和 CI。
7. 执行静态配置、独立前端构建、Compose 端到端健康检查、HTTP 探测、Nginx 配置测试和日志检查，并清理专用验证容器、网络和命名卷。

## 验证命令与真实结果

以下检查均已真实执行：

```bash
docker compose -f infra/compose.yaml config
docker compose -f infra/compose.yaml config --services
docker compose -f infra/compose.yaml config --images
git diff --check
```

- Compose 配置解析通过。
- 服务为 `db`、`redis`、`api`、`web`，共四个。
- 镜像为 `pgvector/pgvector:pg18`、`redis:8-alpine`、`insightx-api`、`insightx-web`。
- `git diff --check` 通过，无新增空白错误。

前端镜像独立构建：

```bash
docker build --progress=plain -f infra/frontend.Dockerfile -t insightx-web-check .
```

- `bun install --frozen-lockfile` 成功，安装 500 个包。
- `vue-tsc -b` 通过。
- Vite 成功转换 3408 个模块并生成 `dist`。
- 仅有单个 chunk 超过 500 kB 的 Vite 警告，不影响构建成功。

Compose 端到端验收：

```bash
COMPOSE_BAKE=false APP_PORT=18080 docker compose \
  -p insightx-infra-check -f infra/compose.yaml up -d --build
COMPOSE_BAKE=false APP_PORT=18080 docker compose \
  -p insightx-infra-check -f infra/compose.yaml up -d --wait --wait-timeout 120
docker compose -p insightx-infra-check -f infra/compose.yaml exec -T web nginx -t
curl -fsS -D - http://127.0.0.1:18080/
curl -fsS -D - http://127.0.0.1:18080/api/v1/health
docker compose -p insightx-infra-check -f infra/compose.yaml logs --no-color api web db redis
docker compose -p insightx-infra-check -f infra/compose.yaml down -v
```

- `db`、`redis`、`api`、`web` 均达到 Compose 健康状态。
- `nginx -t` 通过。
- Web 首页返回 HTTP 200，正文 715 bytes，包含页面标题、Vue entry 资源和 `<div id="app"></div>`。
- `/api/v1/health` 返回 HTTP 200，正文为：

```json
{"code":0,"message":"ok","data":{"status":"degraded","version":"0.1.0","db":false,"redis":false}}
```

- 日志保存于 `/tmp/insightx-compose-logs.txt`，共 158 行；未发现应用启动失败、Nginx 配置错误或异常堆栈。失败关键词扫描仅命中 Redis 的 `bf-error-rate` 配置项，不是运行错误。
- 验收完成后执行 `down -v`，验证用容器、网络和命名卷均已清理。

文档一致性检查：

```bash
rg -n 'compose\.yaml|尚无可运行|待初始化|当前没有可执行|OpenAPI 文档' \
  README.md docs/architecture.md infra/README.md
```

- 未再引用根级 `compose.yaml`。
- 未再声称前后端尚未初始化。
- 匹配项仅为合法的 `infra/compose.yaml` 命令与目录树，以及当前未通过 Web 同域代理暴露 OpenAPI 文档的边界说明。

## 计划偏差

- 前端构建阶段增加了 `node:24-bookworm-slim` 镜像和 Node 可执行文件复制。原计划的表述为“Bun 构建 Vue 静态资源”，实际 Bun 镜像没有 Node 运行时，`vue-tsc` 无法解析 `.vue` 模块；该修复位于获批的 `infra/frontend.Dockerfile` 范围内，不改变运行时、API、依赖锁文件或业务行为，无需扩展审批范围。
- 计划预期将架构文档同步为 `V1.1`，实际当前文档为 `V1.2，2026-09-14，独立 DOM 爬虫闭环同步`。后续提交 `6f825c1` 已把独立爬虫和 MongoDB 状态纳入最新文档；本任务保留当前 V1.2 事实，没有回退版本。
- 端到端验证显式设置 `COMPOSE_BAKE=false`，避免 Compose Bake 干扰本地验证；不影响 Compose 配置和服务定义。

## 遗留问题与未执行检查

- 本次交付是单机 Compose 部署基座，不是生产部署；TLS、生产密钥管理、备份恢复、监控、容量验证和高可用未实施。
- Redis 当前仅位于 Compose 内部网络且未启用认证；这只适用于本地开发边界，正式环境必须另行设计认证、网络和密钥策略。
- 数据库和 Redis 的真实应用连接与探针、Alembic/pgvector 初始化迁移、Celery Worker、outbox dispatcher、LangGraph checkpointer、业务 REST/SSE、契约生成和 CI 均未实现；因此健康接口仍真实返回 `degraded`、`db=false`、`redis=false`。
- 镜像使用明确标签但未固定 digest；镜像升级和供应链校验不在本任务范围。
- 未执行生产环境部署、压力测试、高可用故障演练、备份恢复演练和外部网络长期稳定性检查。
- 本文件创建时，工作区另有后端任务留下的 `backend/src/insightx/models.py` 修改及 `backend/alembic.ini`、`backend/migrations/` 未跟踪文件；它们不属于本任务，未读取后修改，也未纳入本任务的完成或验证结论。
