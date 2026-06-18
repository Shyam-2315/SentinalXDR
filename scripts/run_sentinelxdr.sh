#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
DEV_DIR="${ROOT_DIR}/.dev"
LOG_DIR="${DEV_DIR}/logs"
PID_DIR="${DEV_DIR}/pids"
BACKEND_PORT=8010
FRONTEND_PORT=8080
MONGO_PORT=27018
REDIS_PORT=6380
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
COMPOSE_LOG="${LOG_DIR}/compose.log"
BACKEND_PID="${PID_DIR}/backend.pid"
FRONTEND_PID="${PID_DIR}/frontend.pid"
COMPOSE=(
  docker compose
  -f "${BACKEND_DIR}/docker-compose.yml"
)

mkdir -p "${LOG_DIR}" "${PID_DIR}"

stop_pid() {
  local name="$1"
  local pid_file="$2"
  if [[ ! -f "${pid_file}" ]]; then
    return
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    echo "Stopping existing ${name} process PID ${pid}"
    kill -- "-${pid}" 2>/dev/null || kill "${pid}" 2>/dev/null || true
    for _ in $(seq 1 10); do
      if ! kill -0 "${pid}" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    if kill -0 "${pid}" 2>/dev/null; then
      kill -9 -- "-${pid}" 2>/dev/null || kill -9 "${pid}" 2>/dev/null || true
    fi
  fi
  rm -f "${pid_file}"
}

port_in_use() {
  local port="$1"
  python3 - "${port}" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    raise SystemExit(0)
finally:
    sock.close()
raise SystemExit(1)
PY
}

check_port_free() {
  local port="$1"
  local label="$2"
  if port_in_use "${port}"; then
    echo "ERROR: ${label} port ${port} is already in use. Stop that process and retry." >&2
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local log_file="$3"
  for _ in $(seq 1 30); do
    if curl --silent --fail "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "ERROR: ${label} did not start within 30 seconds." >&2
  echo "Last lines from ${log_file}:" >&2
  tail -n 80 "${log_file}" >&2 || true
  exit 1
}

print_backend_dependency_logs() {
  local label="$1"
  echo "ERROR: ${label} health check failed." >&2
  echo "Backend environment:" >&2
  echo "- MONGODB_URI=${MONGODB_URI}" >&2
  echo "- REDIS_URL=${REDIS_URL}" >&2
  echo "Last lines from ${BACKEND_LOG}:" >&2
  tail -n 80 "${BACKEND_LOG}" >&2 || true
  echo "Last lines from ${COMPOSE_LOG}:" >&2
  tail -n 80 "${COMPOSE_LOG}" >&2 || true
  if command -v docker >/dev/null 2>&1; then
    echo "Docker Compose logs for mongo and redis:" >&2
    MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" BACKEND_PORT="${BACKEND_PORT}" \
      "${COMPOSE[@]}" logs --tail=80 mongo redis >&2 || true
  fi
}

wait_for_dependency_health() {
  local url="$1"
  local label="$2"
  for _ in $(seq 1 30); do
    if curl --silent --fail "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  print_backend_dependency_logs "${label}"
  exit 1
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command '${cmd}' is not installed." >&2
    exit 1
  fi
}

stop_pid "frontend" "${FRONTEND_PID}"
stop_pid "backend" "${BACKEND_PID}"

require_cmd docker
require_cmd curl
require_cmd python3

check_port_free "${BACKEND_PORT}" "Backend"
check_port_free "${FRONTEND_PORT}" "Frontend"

if [[ ! -f "${BACKEND_DIR}/.venv/bin/activate" ]]; then
  echo "ERROR: backend virtualenv not found at backend/.venv" >&2
  exit 1
fi

export MONGODB_URI="mongodb://localhost:${MONGO_PORT}"
export REDIS_URL="redis://localhost:${REDIS_PORT}/0"
export BACKEND_PORT
export FRONTEND_PORT

echo "Starting MongoDB on localhost:${MONGO_PORT} and Redis on localhost:${REDIS_PORT}"
if ! MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" BACKEND_PORT="${BACKEND_PORT}" \
  "${COMPOSE[@]}" up -d mongo redis >"${COMPOSE_LOG}" 2>&1; then
  echo "ERROR: failed to start MongoDB/Redis with Docker Compose." >&2
  echo "Last lines from ${COMPOSE_LOG}:" >&2
  tail -n 80 "${COMPOSE_LOG}" >&2 || true
  exit 1
fi

echo "Starting SentinelXDR backend on port ${BACKEND_PORT}"
setsid bash -c '
  cd "$1"
  source .venv/bin/activate
  exec uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" --reload
' _ "${BACKEND_DIR}" >"${BACKEND_LOG}" 2>&1 &
echo "$!" >"${BACKEND_PID}"

wait_for_url "http://localhost:${BACKEND_PORT}/health/live" "Backend" "${BACKEND_LOG}"
wait_for_dependency_health "http://localhost:${BACKEND_PORT}/health/db" "MongoDB"
wait_for_dependency_health "http://localhost:${BACKEND_PORT}/health/redis" "Redis"

echo "Starting SentinelXDR frontend on port ${FRONTEND_PORT}"
setsid bash -c '
  cd "$1"
  exec env VITE_API_BASE_URL="http://localhost:${BACKEND_PORT}" npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}"
' _ "${FRONTEND_DIR}" >"${FRONTEND_LOG}" 2>&1 &
echo "$!" >"${FRONTEND_PID}"

wait_for_url "http://localhost:${FRONTEND_PORT}" "Frontend" "${FRONTEND_LOG}"

cat <<'EOF'
SentinelXDR started successfully
Backend: http://localhost:8010
Frontend: http://localhost:8080
Swagger: http://localhost:8010/docs
Logs:
- .dev/logs/backend.log
- .dev/logs/frontend.log
- .dev/logs/compose.log
EOF
