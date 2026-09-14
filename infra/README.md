# InsightX Infra

集中管理 InsightX 当前的单机 Docker Compose 部署基座。

## 当前范围

本目录提供四个实际服务：

| 服务 | 镜像/构建 | 网络 | 说明 |
| --- | --- | --- | --- |
| `db` | `pgvector/pgvector:pg18` | 仅 Compose 内部 | PostgreSQL 18 + pgvector，数据写入 `db_data` |
| `redis` | `redis:8-alpine` | 仅 Compose 内部 | 启用 AOF，数据写入 `redis_data` |
| `api` | `backend.Dockerfile` | 仅 Compose 内部 `8000` | FastAPI 基础入口 |
| `web` | `frontend.Dockerfile` | 宿主 `${APP_PORT:-8080}` → `80` | Vue 静态资源、SPA fallback 与 `/api` 同域代理 |

数据库连接、Alembic 迁移、Celery Worker、outbox dispatcher、LangGraph、业务 REST/SSE 和 CI 尚未接入。当前 `/api/v1/health` 返回 `status=degraded`、`db=false`、`redis=false`，这是应用尚未实现真实探针的真实状态。

## 启动

在仓库根目录执行：

```bash
docker compose -f infra/compose.yaml up -d --build
```

默认访问地址：

- Web：<http://localhost:8080/>
- API 健康检查：<http://localhost:8080/api/v1/health>
- OpenAPI 文档：<http://localhost:8080/docs>

如需更换宿主端口：

```bash
APP_PORT=18080 docker compose -f infra/compose.yaml up -d --build
```

首次启动需要拉取基础镜像并构建前后端镜像。

## 检查

```bash
docker compose -f infra/compose.yaml ps
docker compose -f infra/compose.yaml logs api web db redis
docker compose -f infra/compose.yaml exec -T web nginx -t
curl -fsS http://localhost:8080/api/v1/health
```

四个服务都应为运行状态；`db`、`redis`、`api`、`web` 的健康检查应通过。健康接口的业务状态仍可能是 `degraded`，因为应用尚未接入数据库和 Redis。

## 停止与数据

```bash
docker compose -f infra/compose.yaml down
```

命名卷会保留。以下命令会删除本部署的 PostgreSQL 和 Redis 数据卷，仅用于需要完全清理联调环境时：

```bash
docker compose -f infra/compose.yaml down -v
```

## 配置

- `APP_PORT`：Web 暴露到宿主机的端口，默认 `8080`。
- `POSTGRES_PASSWORD`：PostgreSQL 密码，未设置时使用仅供本地开发的 `insightx-dev`。

正式环境必须通过受控的密钥管理方式注入密码，不能沿用开发默认值。

## 边界

- 这是单机联调/部署基座，不提供已验证高可用、TLS、备份恢复、监控或生产密钥管理。
- `db` 和 `redis` 不映射宿主机端口，只能由 Compose 网络中的服务访问。
- Nginx 已使用 HTTP/1.1 和关闭代理缓冲作为后续 SSE 的兼容基础，但当前没有 SSE 端点或事件协议实现。
- CI、迁移、Worker、业务 API、云模型接入和真实数据端到端验证均不在本目录当前范围内。
