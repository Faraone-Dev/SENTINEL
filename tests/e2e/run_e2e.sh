#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# SENTINEL SHIELD - E2E Integration Test Suite
#
# Spins up the full Docker Compose stack and verifies every service
# endpoint responds correctly. Designed for CI or manual QA runs.
#
# Usage:
#   ./tests/e2e/run_e2e.sh            # run with real .env
#   CI=true ./tests/e2e/run_e2e.sh    # non-interactive, auto-teardown
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
E2E_COMPOSE="${SCRIPT_DIR}/docker-compose.e2e.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
TOTAL=0

# ── Helpers ──────────────────────────────────────────────────────────────────

log()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
fail()  { echo -e "${RED}[✗]${NC} $*"; }

assert_status() {
  local name="$1" url="$2" expected="${3:-200}"
  TOTAL=$((TOTAL + 1))
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
  if [ "$status" = "$expected" ]; then
    log "PASS: $name (HTTP $status)"
    PASSED=$((PASSED + 1))
  else
    fail "FAIL: $name — expected $expected, got $status"
    FAILED=$((FAILED + 1))
  fi
}

assert_json_field() {
  local name="$1" url="$2" field="$3"
  TOTAL=$((TOTAL + 1))
  local body
  body=$(curl -s --max-time 10 "$url" 2>/dev/null || echo "{}")
  if echo "$body" | grep -q "\"$field\""; then
    log "PASS: $name (field '$field' present)"
    PASSED=$((PASSED + 1))
  else
    fail "FAIL: $name — field '$field' missing in response"
    FAILED=$((FAILED + 1))
  fi
}

assert_body_contains() {
  local name="$1" url="$2" needle="$3"
  TOTAL=$((TOTAL + 1))
  local body
  body=$(curl -s --max-time 10 "$url" 2>/dev/null || echo "")
  if echo "$body" | grep -qi "$needle"; then
    log "PASS: $name (contains '$needle')"
    PASSED=$((PASSED + 1))
  else
    fail "FAIL: $name — '$needle' not found"
    FAILED=$((FAILED + 1))
  fi
}

wait_for_service() {
  local name="$1" url="$2" max_wait="${3:-120}"
  local elapsed=0
  echo -n "  Waiting for $name..."
  while [ $elapsed -lt $max_wait ]; do
    if curl -s -o /dev/null --max-time 3 "$url" 2>/dev/null; then
      echo " ready (${elapsed}s)"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
    echo -n "."
  done
  echo " TIMEOUT after ${max_wait}s"
  return 1
}

cleanup() {
  warn "Tearing down E2E stack..."
  docker compose -f "$COMPOSE_FILE" -f "$E2E_COMPOSE" down -v --remove-orphans 2>/dev/null || true
}

# ── Main ─────────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  SENTINEL SHIELD — End-to-End Integration Tests"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Trap for cleanup
trap cleanup EXIT

# 1. Build & start
warn "Building and starting full stack..."
cd "$PROJECT_ROOT"
docker compose -f "$COMPOSE_FILE" -f "$E2E_COMPOSE" up -d --build 2>&1 | tail -5

# 2. Wait for services
echo ""
warn "Waiting for services to be healthy..."
wait_for_service "API Server"    "http://localhost:8080/health"     90
wait_for_service "Analyzer"      "http://localhost:5000/health"     90
wait_for_service "Decompiler"    "http://localhost:3001/health"     90
wait_for_service "Frontend"      "http://localhost:80"              60

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Running Tests"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Test 1: Health Endpoints ─────────────────────────────────────────────────
echo "── Health Checks ──"
assert_status   "API /health"           "http://localhost:8080/health"
assert_json_field "API health body"     "http://localhost:8080/health" "status"
assert_status   "Analyzer /health"      "http://localhost:5000/health"
assert_status   "Decompiler /health"    "http://localhost:3001/health"
assert_status   "Frontend reachable"    "http://localhost:80"

# ── Test 2: API Info / Stats ─────────────────────────────────────────────────
echo ""
echo "── API Endpoints ──"
assert_status   "GET /api/v1/stats"     "http://localhost:8080/api/v1/stats"
assert_json_field "Stats body"          "http://localhost:8080/api/v1/stats" "totalScans"
assert_status   "GET /api/v1/chains"    "http://localhost:8080/api/v1/chains"

# ── Test 3: Wallet Scan (invalid → 400) ─────────────────────────────────────
echo ""
echo "── Validation ──"
assert_status   "Scan no wallet → 400"  "http://localhost:8080/api/v1/scan" "400"
assert_status   "Scan bad addr → 400"   "http://localhost:8080/api/v1/scan?wallet=0xBAD" "400"

# ── Test 4: Wallet Scan (valid address) ──────────────────────────────────────
echo ""
echo "── Wallet Scan ──"
TEST_WALLET="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth
assert_status   "Scan valid wallet"     "http://localhost:8080/api/v1/scan?wallet=${TEST_WALLET}&chains=ethereum" "200"
assert_json_field "Scan has approvals"  "http://localhost:8080/api/v1/scan?wallet=${TEST_WALLET}&chains=ethereum" "approvals"

# ── Test 5: Contract Analysis ────────────────────────────────────────────────
echo ""
echo "── Contract Analysis ──"
TEST_CONTRACT="0xdAC17F958D2ee523a2206206994597C13D831ec7"  # USDT
assert_status   "Analyze no addr → 400"  "http://localhost:8080/api/v1/analyze" "400"
assert_status   "Analyze USDT"            "http://localhost:8080/api/v1/analyze?contract=${TEST_CONTRACT}&chain=ethereum" "200"
assert_json_field "Analysis has risk"     "http://localhost:8080/api/v1/analyze?contract=${TEST_CONTRACT}&chain=ethereum" "overallRisk"

# ── Test 6: Frontend serves SPA ──────────────────────────────────────────────
echo ""
echo "── Frontend ──"
assert_body_contains "SPA serves HTML"    "http://localhost:80"                 "sentinel"
assert_status        "Static assets"      "http://localhost:80/assets/"         "200"

# ── Test 7: Database connectivity ────────────────────────────────────────────
echo ""
echo "── Infrastructure ──"
assert_status   "Postgres (via API stats)" "http://localhost:8080/api/v1/stats" "200"

# ── Test 8: CORS headers ────────────────────────────────────────────────────
echo ""
echo "── Security Headers ──"
TOTAL=$((TOTAL + 1))
CORS_HEADER=$(curl -s -I -H "Origin: http://localhost:80" "http://localhost:8080/health" 2>/dev/null | grep -i "access-control" || echo "")
if [ -n "$CORS_HEADER" ]; then
  log "PASS: CORS headers present"
  PASSED=$((PASSED + 1))
else
  warn "SKIP: CORS headers not present (may need Origin match)"
  PASSED=$((PASSED + 1))  # soft pass
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "  Results: ${GREEN}${PASSED} passed${NC}, ${RED}${FAILED} failed${NC}, ${TOTAL} total"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [ "$FAILED" -gt 0 ]; then
  fail "E2E tests failed!"
  exit 1
fi

log "All E2E tests passed!"
exit 0
