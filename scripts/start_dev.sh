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
  echo "[dev] Starting MongoDB and Redis"
  MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" \
    docker compose -f "${BACKEND_DIR}/docker-compose.yml" up -d mongo redis >"${LOG_DIR}/compose.log" 2>&1
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
wait_for_url "http://localhost:${BACKEND_PORT}/health/ready" "backend readiness"
start_frontend
wait_for_url "http://localhost:${FRONTEND_PORT}" "frontend"

echo "Backend URL: http://localhost:${BACKEND_PORT}"
echo "Frontend URL: http://localhost:${FRONTEND_PORT}"
echo "Swagger URL: http://localhost:${BACKEND_PORT}/docs"
echo "Logs: ${LOG_DIR}"
