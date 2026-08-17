#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
HOST="127.0.0.1"
API_PORT="${REVIEW_DEMO_API_PORT:-8010}"
WEB_PORT="${REVIEW_DEMO_WEB_PORT:-5173}"
DATABASE_VALUE="${REVIEW_DEMO_DATABASE_PATH:-$PROJECT_ROOT/data/demo-reviews.db}"
if [[ "$DATABASE_VALUE" = /* ]]; then
  DATABASE_PATH="$DATABASE_VALUE"
else
  DATABASE_PATH="$PROJECT_ROOT/$DATABASE_VALUE"
fi

backend_pid=""
frontend_pid=""

usage() {
  printf '%s\n' \
    "用法：./run-demo.sh [--check]" \
    "" \
    "  --check  只检查依赖与端口，不启动服务" \
    "" \
    "可选环境变量：" \
    "  REVIEW_DEMO_API_PORT       后端端口，默认 8010" \
    "  REVIEW_DEMO_WEB_PORT       前端端口，默认 5173" \
    "  REVIEW_DEMO_DATABASE_PATH  Demo 审核库，默认 data/demo-reviews.db"
}

fail() {
  printf '错误：%s\n' "$1" >&2
  exit 1
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  local stopped=0
  for pid in "$frontend_pid" "$backend_pid"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
      stopped=1
    fi
  done
  for pid in "$frontend_pid" "$backend_pid"; do
    if [[ -n "$pid" ]]; then
      wait "$pid" 2>/dev/null || true
    fi
  done
  if ((stopped)); then
    printf '\nDemo 服务已停止。\n'
  fi
  return "$exit_code"
}

validate_port() {
  local name=$1
  local port=$2
  if [[ ! "$port" =~ ^[0-9]+$ ]] || ((port < 1 || port > 65535)); then
    fail "$name 端口无效：$port"
  fi
}

check_port_available() {
  local name=$1
  local port=$2
  if ! "$PYTHON_BIN" -c \
    'import socket, sys; sock = socket.socket(); sock.bind(("127.0.0.1", int(sys.argv[1]))); sock.close()' \
    "$port" 2>/dev/null; then
    fail "$name 端口 $port 已被占用"
  fi
}

wait_for_service() {
  local name=$1
  local url=$2
  local pid=$3
  local attempt
  for ((attempt = 1; attempt <= 100; attempt++)); do
    if curl --silent --fail --max-time 1 "$url" >/dev/null 2>&1; then
      return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      fail "$name 启动失败"
    fi
    sleep 0.1
  done
  fail "$name 在 10 秒内未通过健康检查：$url"
}

mode="run"
case "${1:-}" in
  "") ;;
  --check) mode="check" ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac
if (($# > 1)); then
  usage >&2
  exit 2
fi

validate_port "API" "$API_PORT"
validate_port "Web" "$WEB_PORT"
if [[ "$API_PORT" == "$WEB_PORT" ]]; then
  fail "API 与 Web 端口不能相同"
fi

if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  fail "未找到 Python；请先按 README 安装后端环境"
fi

if ! "$PYTHON_BIN" -c 'import fastapi, pydantic, uvicorn' >/dev/null 2>&1; then
  fail "Python 环境缺少后端依赖；请先在 backend 中安装 .[dev]"
fi
command -v node >/dev/null 2>&1 || fail "未找到 Node.js"
command -v curl >/dev/null 2>&1 || fail "未找到 curl"
VITE_BIN="$FRONTEND_DIR/node_modules/.bin/vite"
[[ -x "$VITE_BIN" ]] || fail "前端依赖未安装；请先执行 cd frontend && npm install"

check_port_available "API" "$API_PORT"
check_port_available "Web" "$WEB_PORT"

printf '%s\n' \
  "Demo 预检通过" \
  "  Python：$PYTHON_BIN" \
  "  审核库：$DATABASE_PATH" \
  "  API：http://$HOST:$API_PORT" \
  "  Web：http://$HOST:$WEB_PORT"

if [[ "$mode" == "check" ]]; then
  exit 0
fi

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(
  cd "$BACKEND_DIR"
  exec env \
    REVIEW_ENABLE_DEMOS=1 \
    REVIEW_DATABASE_PATH="$DATABASE_PATH" \
    "$PYTHON_BIN" -m uvicorn app.main:app \
      --host "$HOST" \
      --port "$API_PORT" \
      --log-level warning
) &
backend_pid=$!
wait_for_service "后端" "http://$HOST:$API_PORT/api/health" "$backend_pid"

(
  cd "$FRONTEND_DIR"
  exec env \
    REVIEW_API_PROXY="http://$HOST:$API_PORT" \
    "$VITE_BIN" \
      --host "$HOST" \
      --port "$WEB_PORT" \
      --strictPort
) &
frontend_pid=$!
wait_for_service "前端" "http://$HOST:$WEB_PORT" "$frontend_pid"

printf '\nDemo 已启动：打开 http://%s:%s\n' "$HOST" "$WEB_PORT"
printf '文章和节点—关系模拟任务已启用；按 Ctrl+C 同时停止前后端。\n\n'

set +e
wait -n "$backend_pid" "$frontend_pid"
service_status=$?
set -e
printf '某个 Demo 服务意外退出。\n' >&2
if ((service_status == 0)); then
  service_status=1
fi
exit "$service_status"
