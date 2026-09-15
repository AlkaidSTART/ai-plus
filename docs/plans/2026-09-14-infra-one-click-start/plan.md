# infra 一键启动入口：实施计划

## 目标

在现有 `infra/` 部署目录中新增一个可执行脚本，让用户从仓库根目录执行单条命令即可完成镜像构建、四个容器启动和健康等待；启动成功后，终端明确显示 Web 访问地址和 API 健康检查地址。

预期入口：

```bash
./infra/start.sh
```

默认显示：

```text
Web：http://localhost:8080/
API 健康检查：http://localhost:8080/api/v1/health
```

支持通过 `APP_PORT` 覆盖 Web 端口，并继续使用 Compose 内置的四服务健康检查。

## 当前事实及依据

- `find infra -maxdepth 2 -type f` 当前只发现 `compose.yaml`、两个 Dockerfile、两个 dockerignore、`nginx.conf` 和 `README.md`，没有启动脚本。
- `infra/compose.yaml` 已定义 `db`、`redis`、`api`、`web` 四个服务及健康检查；Web 使用 `${APP_PORT:-8080}:80`，API 仅在 Compose 内部暴露 `8000`。
- `docker compose version` 为 `v5.0.2`；`docker compose up --help` 已确认当前版本支持 `--build`、`--detach`、`--wait` 和 `--wait-timeout`。
- 当前 `8080`、`18080` 端口均无监听进程。
- 当前后端 `/api/v1/health` 固定返回 HTTP 200，业务状态为 `degraded`、`db=false`、`redis=false`；脚本只等待容器健康检查成功，不伪造数据库或 Redis 已接入。
- `infra/README.md` 当前要求用户手工执行 `docker compose -f infra/compose.yaml up -d --build`，并静态列出默认访问地址，没有自动等待健康和集中输出实际访问地址的入口。
- 本机有 `/bin/bash`，没有 `shellcheck` 或 `shfmt`；验证以 Bash 语法检查和真实启动为准，不为此新增工具依赖。
- 工作区存在其他任务的后端和 Playwright 文档改动；本计划不读取后修改、不覆盖，也不把其他计划目录纳入变更范围。

## 预计变更文件

新增：

- `infra/start.sh`
  - 使用 `#!/usr/bin/env bash` 和 `set -Eeuo pipefail`。
  - 通过 `${BASH_SOURCE[0]}` 解析脚本绝对目录，因此从任意工作目录调用都可正确定位 `infra/compose.yaml`。
  - 检查 `docker`、`docker compose` 和 Docker daemon 可用性；缺失或未运行时输出中文错误并以非零状态退出。
  - 读取 `APP_PORT`（默认 `8080`）和 `STARTUP_TIMEOUT`（默认 `180` 秒）并导出给 Compose。
  - 执行 `docker compose -f "$SCRIPT_DIR/compose.yaml" up -d --build --wait --wait-timeout "$STARTUP_TIMEOUT"`。
  - 启动失败时输出失败提示、当前服务状态和日志查看命令，并保留非零退出码。
  - 启动成功后执行一次 `docker compose ... ps`，再输出 Web 与 API 健康检查访问地址。
  - 不自动打开浏览器，不修改服务配置，不删除数据卷。

修改：

- `infra/README.md`
  - 把 `./infra/start.sh` 作为首选启动入口。
  - 说明从任意目录执行均可、默认端口为 `8080`、可通过 `APP_PORT=18080 ./infra/start.sh` 覆盖。
  - 说明 `STARTUP_TIMEOUT` 可调整健康等待上限，脚本会在所有服务健康后显示访问地址。
  - 保留原手工 `docker compose` 命令作为替代方式，并继续说明健康接口为 `degraded` 的真实边界。

验证通过后新增：

- `docs/plans/2026-09-14-infra-one-click-start/result.md`：记录脚本实际内容、验证命令、真实输出、偏差和遗留项。

明确不修改：`infra/compose.yaml`、Dockerfile、Nginx 配置、前后端代码、依赖锁文件、根 `README.md` 和其他任务计划目录。

## 实施步骤与分工

1. 新增 `infra/start.sh`，按上述顺序实现环境检查、默认变量、Compose 启动等待、失败诊断和成功地址输出。
2. 对脚本执行 `chmod +x`，确保 Git 记录可执行权限。
3. 更新 `infra/README.md` 的“启动”章节，使一键命令、端口覆盖、健康等待和访问地址行为与脚本一致；不扩大到生产部署说明。
4. 执行静态检查：
   - `bash -n infra/start.sh`
   - `test -x infra/start.sh`
   - `git diff --check`
5. 使用隔离端口执行真实一键启动，例如 `APP_PORT=18080 ./infra/start.sh`，确认脚本自动构建、等待四个服务健康并打印 `http://localhost:18080/` 与 `http://localhost:18080/api/v1/health`。
6. 使用 `curl` 验证 Web 首页和 API 健康检查，再执行 `docker compose -p insightx -f infra/compose.yaml down` 清理本次验证容器，保留命名卷；如测试使用独立 `-p`，则执行对应项目名的 `down`。
7. 实施和验证结束后创建 `result.md`，不把结果写回本计划。

本任务文件少且顺序紧密耦合，不拆分给多个写子代理，避免启动脚本与文档说明出现不同步；主代理负责实现、验证和结果记录。

## 验证与验收

静态检查：

```bash
bash -n infra/start.sh
test -x infra/start.sh
git diff --check
```

预期：Bash 语法无误、脚本具有执行权限、无空白错误。由于本机没有 `shellcheck`/`shfmt`，不执行这两项，并在结果中明确记录。

真实启动：

```bash
APP_PORT=18080 ./infra/start.sh
```

预期：

- 脚本自行完成 `docker compose up -d --build --wait`。
- `db`、`redis`、`api`、`web` 四个服务均达到健康状态。
- 标准输出明确包含：
  - `http://localhost:18080/`
  - `http://localhost:18080/api/v1/health`
- 脚本退出码为 `0`。

HTTP 验收：

```bash
curl -fsS -D - http://127.0.0.1:18080/
curl -fsS -D - http://127.0.0.1:18080/api/v1/health
```

预期：Web 首页返回 HTTP 200；API 健康检查返回 HTTP 200，正文至少包含 `"code":0`，并继续反映后端当前真实依赖状态。

失败路径验收：

```bash
PATH=/usr/bin:/bin APP_PORT=18080 bash infra/start.sh
```

在保留 Bash 但刻意移除可访问的 `docker` 命令路径时，预期脚本输出明确错误并返回非零状态；不实际停止 Docker daemon。若当前环境的具体 PATH 仍能解析 Docker，则改用临时限制后的等价只读命令验证，并在结果中如实说明。

清理：

```bash
docker compose -p insightx -f infra/compose.yaml down
```

预期：四个容器和网络被移除；`db_data`、`redis_data` 命名卷按 `down` 的默认语义保留，不执行 `down -v`。

## 风险与非目标

- 首次运行需要拉取基础镜像和构建依赖，耗时和网络占用取决于本机缓存；`STARTUP_TIMEOUT` 只限制健康等待，不替代镜像下载和构建耗时。
- 如果 `APP_PORT` 已被占用，Docker/Compose 会拒绝映射端口；脚本应保留其错误输出，不自动选择随机端口或终止其他进程。
- 四容器健康只代表基础设施与基础入口可响应；健康接口仍可能返回 `degraded`，不代表数据库/Redis 业务接入或完整产品已实现。
- 脚本面向当前 macOS/Linux Shell；Windows 原生双击、PowerShell 包装脚本、桌面快捷方式、开机自启和后台守护进程均不在本次范围。
- 不新增停止脚本。停止仍使用现有 `docker compose ... down`，避免扩大本任务的入口和文件数量。
- 不修改 Compose 服务、端口、镜像、健康检查或数据卷语义；不执行生产部署、提交、推送或 `down -v`。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-14
- 批准信息：2026-09-14，用户原文：“开始”
