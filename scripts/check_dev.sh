#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
MONGO_PORT="${MONGO_PORT:-27017}"
REDIS_PORT="${REDIS_PORT:-6379}"
BACKEND_DIR="${ROOT_DIR}/backend"

failed=0

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; failed=1; }

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
  if MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" docker compose -f "${BACKEND_DIR}/docker-compose.yml" ps --status running mongo 2>/dev/null | grep -q "mongo"; then
    pass "MongoDB container running"
  else
    fail "MongoDB container running"
  fi
  if MONGO_PORT="${MONGO_PORT}" REDIS_PORT="${REDIS_PORT}" docker compose -f "${BACKEND_DIR}/docker-compose.yml" ps --status running redis 2>/dev/null | grep -q "redis"; then
    pass "Redis container running"
  else
    fail "Redis container running"
  fi
else
  fail "docker command available"
fi

check_url "backend live" "http://localhost:${BACKEND_PORT}/health/live"
check_url "backend ready" "http://localhost:${BACKEND_PORT}/health/ready"
check_url "frontend reachable" "http://localhost:${FRONTEND_PORT}"

if curl --silent --fail "http://localhost:${BACKEND_PORT}/health/live" >/dev/null 2>&1; then
  if python3 "${ROOT_DIR}/scripts/demo_smoke_check.py" --api-base-url "http://localhost:${BACKEND_PORT}" >/tmp/sentinelxdr-demo-smoke.log 2>&1; then
    pass "demo smoke check"
  else
    fail "demo smoke check ($(cat /tmp/sentinelxdr-demo-smoke.log))"
  fi
fi

exit "${failed}"
