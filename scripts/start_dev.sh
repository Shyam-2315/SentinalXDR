#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
DEV_DIR="${ROOT_DIR}/.dev"
LOG_DIR="${DEV_DIR}/logs"
PID_DIR="${DEV_DIR}/pids"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
MONGO_PORT="${MONGO_PORT:-27017}"
REDIS_PORT="${REDIS_PORT:-6379}"

mkdir -p "${LOG_DIR}" "${PID_DIR}"

COMPOSE=(docker compose --project-directory "${BACKEND_DIR}" -f "${BACKEND_DIR}/docker-compose.yml")

suggest_alt_ports() {
  echo "Try alternate ports:" >&2
  echo "  BACKEND_PORT=8010 FRONTEND_PORT=5174 MONGO_PORT=27018 REDIS_PORT=6380 make dev" >&2
}

tail_log() {
  local label="$1"
  local file="$2"
  if [[ -f "${file}" ]]; then
    echo "[dev] Last lines from ${label} (${file}):" >&2
    tail -n 80 "${file}" >&2 || true
  fi
}

detect_frontend_pm() {
  if [[ -f "${FRONTEND_DIR}/bun.lock" || -f "${FRONTEND_DIR}/bun.lockb" ]]; then
    echo "bun"
  elif [[ -f "${FRONTEND_DIR}/pnpm-lock.yaml" ]]; then
    echo "pnpm"
  elif [[ -f "${FRONTEND_DIR}/yarn.lock" ]]; then
    echo "yarn"
  elif [[ -f "${FRONTEND_DIR}/package-lock.json" ]]; then
    echo "npm"
  else
    echo "npm"
  fi
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command '${cmd}' is not installed." >&2
    exit 1
  fi
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
except PermissionError:
    raise SystemExit(2)
except OSError:
    raise SystemExit(0)
finally:
    sock.close()
raise SystemExit(1)
PY
}

check_port_available() {
  local label="$1"
  local port="$2"
  local status=0
  port_in_use "${port}" || status=$?
  if [[ "${status}" -eq 0 ]]; then
    echo "ERROR: ${label} port ${port} is already in use." >&2
    suggest_alt_ports
    exit 1
  elif [[ "${status}" -eq 2 ]]; then
    echo "[dev] Skipping ${label} port ${port} preflight; socket checks are not permitted here." >&2
  fi
}

compose_service_running() {
  local service="$1"
  MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" \
    "${COMPOSE[@]}" ps --status running "${service}" 2>/dev/null | grep -q "${service}"
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"
  for _ in $(seq 1 "${attempts}"); do
    if curl --silent --fail "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "ERROR: timed out waiting for ${label} at ${url}" >&2
  return 1
}

start_backend_deps() {
  require_cmd docker
  require_cmd python3
  if ! compose_service_running mongo; then
    check_port_available "MongoDB" "${MONGO_PORT}"
  fi
  if ! compose_service_running redis; then
    check_port_available "Redis" "${REDIS_PORT}"
  fi
  echo "[dev] Starting MongoDB and Redis"
  if ! MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" \
    "${COMPOSE[@]}" up -d mongo redis >"${LOG_DIR}/compose.log" 2>&1; then
    echo "ERROR: failed to start MongoDB/Redis with Docker Compose." >&2
    tail_log "compose" "${LOG_DIR}/compose.log"
    suggest_alt_ports
    exit 1
  fi
}

start_backend() {
  if [[ -f "${PID_DIR}/backend.pid" ]] && kill -0 "$(cat "${PID_DIR}/backend.pid")" 2>/dev/null; then
    echo "[dev] Backend already running with PID $(cat "${PID_DIR}/backend.pid")"
    return
  fi
  if [[ ! -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
    echo "ERROR: backend virtualenv not found at backend/.venv" >&2
    exit 1
  fi
  check_port_available "backend" "${BACKEND_PORT}"
  echo "[dev] Starting backend on port ${BACKEND_PORT}"
  setsid nohup bash -c '
    cd "$1"
    MONGODB_URI="$2" REDIS_URL="$3" "$4" -m uvicorn app.main:app --host 0.0.0.0 --port "$5"
  ' _ \
    "${BACKEND_DIR}" \
    "${MONGODB_URI:-mongodb://localhost:${MONGO_PORT}}" \
    "${REDIS_URL:-redis://localhost:${REDIS_PORT}/0}" \
    "${BACKEND_DIR}/.venv/bin/python" \
    "${BACKEND_PORT}" \
    >"${LOG_DIR}/backend.log" 2>&1 &
  echo "$!" >"${PID_DIR}/backend.pid"
}

start_frontend() {
  if [[ -f "${PID_DIR}/frontend.pid" ]] && kill -0 "$(cat "${PID_DIR}/frontend.pid")" 2>/dev/null; then
    echo "[dev] Frontend already running with PID $(cat "${PID_DIR}/frontend.pid")"
    return
  fi
  local pm
  pm="$(detect_frontend_pm)"
  if [[ "${pm}" == "bun" ]] && ! command -v bun >/dev/null 2>&1; then
    if command -v npm >/dev/null 2>&1; then
      echo "[dev] Bun lockfile detected, but bun is not installed; falling back to npm"
      pm="npm"
    else
      echo "ERROR: bun is required by frontend/bun.lock and npm fallback is unavailable." >&2
      exit 1
    fi
  fi
  require_cmd "${pm}"
  check_port_available "frontend" "${FRONTEND_PORT}"
  echo "[dev] Starting frontend with ${pm} on port ${FRONTEND_PORT}"
  setsid nohup bash -c '
    cd "$1"
    pm="$2"
    port="$3"
    case "${pm}" in
      bun) bun run dev --host 0.0.0.0 --port "${port}" ;;
      pnpm) pnpm run dev -- --host 0.0.0.0 --port "${port}" ;;
      yarn) yarn dev --host 0.0.0.0 --port "${port}" ;;
      npm) npm run dev -- --host 0.0.0.0 --port "${port}" ;;
      *) echo "ERROR: unsupported package manager ${pm}" >&2; exit 1 ;;
    esac
  ' _ "${FRONTEND_DIR}" "${pm}" "${FRONTEND_PORT}" >"${LOG_DIR}/frontend.log" 2>&1 &
  echo "$!" >"${PID_DIR}/frontend.pid"
}

start_backend_deps
start_backend
if ! wait_for_url "http://localhost:${BACKEND_PORT}/health/ready" "backend readiness"; then
  tail_log "backend" "${LOG_DIR}/backend.log"
  tail_log "compose" "${LOG_DIR}/compose.log"
  exit 1
fi
start_frontend
if ! wait_for_url "http://localhost:${FRONTEND_PORT}" "frontend"; then
  tail_log "frontend" "${LOG_DIR}/frontend.log"
  exit 1
fi

echo "Backend URL: http://localhost:${BACKEND_PORT}"
echo "Frontend URL: http://localhost:${FRONTEND_PORT}"
echo "Swagger URL: http://localhost:${BACKEND_PORT}/docs"
echo "Logs: ${LOG_DIR}"
