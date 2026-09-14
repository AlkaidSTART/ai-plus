#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
COMPOSE_FILE="$SCRIPT_DIR/compose.yaml"

APP_PORT="${APP_PORT:-8080}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-180}"
export APP_PORT

if ! command -v docker >/dev/null 2>&1; then
  echo "错误：未找到 docker 命令，请先安装并启动 Docker Desktop。" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "错误：当前 Docker 环境不支持 docker compose 命令。" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "错误：Docker daemon 未运行，请先启动 Docker Desktop。" >&2
  exit 1
fi

echo "正在构建并启动 InsightX 服务，健康等待上限为 ${STARTUP_TIMEOUT} 秒..."

if ! docker compose -f "$COMPOSE_FILE" up -d --build --wait --wait-timeout "$STARTUP_TIMEOUT"; then
  echo "错误：服务启动或健康等待失败。" >&2
  echo "如需放宽健康等待上限，可通过 STARTUP_TIMEOUT 调整（当前值：${STARTUP_TIMEOUT} 秒）。" >&2
  docker compose -f "$COMPOSE_FILE" ps >&2 || true
  echo "查看状态：docker compose -f \"$COMPOSE_FILE\" ps" >&2
  echo "查看日志：docker compose -f \"$COMPOSE_FILE\" logs api web db redis" >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" ps

echo
echo "启动完成，访问地址："
echo "Web：http://localhost:${APP_PORT}/"
echo "API 健康检查：http://localhost:${APP_PORT}/api/v1/health"
