#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
PID_DIR="${ROOT_DIR}/.dev/pids"
LOG_DIR="${ROOT_DIR}/.dev/logs"
BACKEND_PORT=8010
FRONTEND_PORT=8080
MONGO_PORT=27018
REDIS_PORT=6380
COMPOSE=(
  docker compose
  -f "${BACKEND_DIR}/docker-compose.yml"
)

stop_pid() {
  local name="$1"
  local pid_file="${PID_DIR}/${name}.pid"
  if [[ ! -f "${pid_file}" ]]; then
    return
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    echo "Stopping ${name} PID ${pid}"
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

mkdir -p "${PID_DIR}" "${LOG_DIR}"
stop_pid frontend
stop_pid backend

if command -v docker >/dev/null 2>&1; then
  echo "Stopping MongoDB and Redis containers"
  MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" BACKEND_PORT="${BACKEND_PORT}" \
    "${COMPOSE[@]}" stop mongo redis >"${LOG_DIR}/compose.log" 2>&1 || {
      echo "WARNING: failed to stop MongoDB/Redis with Docker Compose." >&2
      echo "Last lines from ${LOG_DIR}/compose.log:" >&2
      tail -n 80 "${LOG_DIR}/compose.log" >&2 || true
    }
fi

find "${PID_DIR}" -type f \( -name 'backend.pid' -o -name 'frontend.pid' \) -delete 2>/dev/null || true
echo "SentinelXDR stopped"
