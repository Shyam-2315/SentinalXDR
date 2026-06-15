#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
PID_DIR="${ROOT_DIR}/.dev/pids"
LOG_DIR="${ROOT_DIR}/.dev/logs"
MONGO_PORT="${MONGO_PORT:-27017}"
REDIS_PORT="${REDIS_PORT:-6379}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-backend}"
COMPOSE=(
  docker compose
  --project-name "${COMPOSE_PROJECT_NAME}"
  --project-directory "${BACKEND_DIR}"
  -f "${BACKEND_DIR}/docker-compose.yml"
)

stop_pid() {
  local name="$1"
  local pid_file="${PID_DIR}/${name}.pid"
  if [[ ! -f "${pid_file}" ]]; then
    return
  fi
  local pid
  pid="$(cat "${pid_file}")"
  if kill -0 "${pid}" 2>/dev/null; then
    echo "[dev] Stopping ${name} PID ${pid}"
    kill -- "-${pid}" 2>/dev/null || kill "${pid}" 2>/dev/null || true
    for _ in $(seq 1 15); do
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

mkdir -p "${LOG_DIR}" "${PID_DIR}"
stop_pid frontend
stop_pid backend

if command -v docker >/dev/null 2>&1; then
  echo "[dev] Stopping MongoDB and Redis"
  BACKEND_PORT="${BACKEND_PORT}" MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" \
    "${COMPOSE[@]}" stop mongo redis >"${LOG_DIR}/compose.log" 2>&1 || true
fi

find "${PID_DIR}" -type f -name '*.pid' -delete 2>/dev/null || true
echo "[dev] Stopped"
