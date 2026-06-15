#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
MONGO_PORT="${MONGO_PORT:-27017}"
REDIS_PORT="${REDIS_PORT:-6379}"
BACKEND_DIR="${ROOT_DIR}/backend"
LOG_DIR="${ROOT_DIR}/.dev/logs"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-backend}"
COMPOSE=(
  docker compose
  --project-name "${COMPOSE_PROJECT_NAME}"
  --project-directory "${BACKEND_DIR}"
  -f "${BACKEND_DIR}/docker-compose.yml"
)

failed=0

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; failed=1; }

tail_log() {
  local label="$1"
  local file="$2"
  if [[ -f "${file}" ]]; then
    echo "--- ${label} log tail (${file}) ---"
    tail -n 80 "${file}" || true
    echo "--- end ${label} log tail ---"
  fi
}

show_compose_logs() {
  if command -v docker >/dev/null 2>&1; then
    echo "--- compose service status ---"
    BACKEND_PORT="${BACKEND_PORT}" MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" "${COMPOSE[@]}" ps mongo redis || true
    echo "--- compose logs tail ---"
    BACKEND_PORT="${BACKEND_PORT}" MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" "${COMPOSE[@]}" logs --tail=80 mongo redis || true
    echo "--- end compose logs tail ---"
  fi
}

show_openapi_api_paths() {
  python3 - "http://localhost:${BACKEND_PORT}/openapi.json" <<'PY' || true
import json
import sys
from urllib.error import URLError
from urllib.request import urlopen

try:
    with urlopen(sys.argv[1], timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
except (OSError, URLError, json.JSONDecodeError) as exc:
    print(f"Could not inspect OpenAPI paths: {exc}")
    raise SystemExit(0)

paths = sorted(
    path
    for path in payload.get("paths", {})
    if path.startswith("/api/auth") or path.startswith("/api/v1/auth")
)
if paths:
    print("Detected auth API paths:")
    for path in paths:
        print(f"  {path}")
else:
    print("No /api auth paths detected in /openapi.json.")
PY
}

check_url() {
  local label="$1"
  local url="$2"
  if curl --silent --fail "${url}" >/dev/null 2>&1; then
    pass "${label}"
  else
    fail "${label} (${url})"
  fi
}

if command -v docker >/dev/null 2>&1; then
  compose_failed=0
  if BACKEND_PORT="${BACKEND_PORT}" MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" "${COMPOSE[@]}" ps --status running mongo 2>/dev/null | grep -q "mongo"; then
    pass "MongoDB container running"
  else
    fail "MongoDB container running"
    compose_failed=1
  fi
  if BACKEND_PORT="${BACKEND_PORT}" MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" "${COMPOSE[@]}" ps --status running redis 2>/dev/null | grep -q "redis"; then
    pass "Redis container running"
  else
    fail "Redis container running"
    compose_failed=1
  fi
  if [[ "${compose_failed}" -eq 1 ]]; then
    show_compose_logs
    tail_log "compose" "${LOG_DIR}/compose.log"
  fi
else
  fail "docker command available"
fi

check_url "backend live" "http://localhost:${BACKEND_PORT}/health/live"
check_url "backend ready" "http://localhost:${BACKEND_PORT}/health/ready"
if curl --silent --fail "http://localhost:${FRONTEND_PORT}" >/dev/null 2>&1; then
  pass "frontend reachable"
else
  fail "frontend reachable (http://localhost:${FRONTEND_PORT})"
  tail_log "frontend" "${LOG_DIR}/frontend.log"
fi

if curl --silent --fail "http://localhost:${BACKEND_PORT}/health/live" >/dev/null 2>&1; then
  if python3 "${ROOT_DIR}/scripts/demo_smoke_check.py" --api-base-url "http://localhost:${BACKEND_PORT}" >/tmp/sentinelxdr-demo-smoke.log 2>&1; then
    pass "demo smoke check"
  else
    fail "demo smoke check ($(cat /tmp/sentinelxdr-demo-smoke.log))"
    if grep -qi "auth" /tmp/sentinelxdr-demo-smoke.log; then
      show_openapi_api_paths
    fi
  fi
fi

exit "${failed}"
