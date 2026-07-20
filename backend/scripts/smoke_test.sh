#!/usr/bin/env bash
# smoke_test.sh — quick end-to-end smoke test against a running API
# Works in bash / Git Bash on Windows.
# Requirements: curl, jq

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"
EMAIL="${SMOKE_EMAIL:-admin@example.com}"
PASSWORD="${SMOKE_PASSWORD:-admin1234}"
TEST_EMAIL="smoke_$(date +%s)@example.com"

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
RESET='\033[0m'

pass() { echo -e "${GREEN}[OK]${RESET}  $1"; }
fail() { echo -e "${RED}[FAIL]${RESET} $1"; EXIT_CODE=1; }
section() { echo -e "\n${CYAN}--- $1 ---${RESET}"; }

EXIT_CODE=0

# ---------------------------------------------------------------------------
# Helper: perform curl and check expected HTTP status
# Usage: do_request <label> <expected_status> <curl_args...>
# Sets global RESPONSE and STATUS.
# ---------------------------------------------------------------------------
do_request() {
  local label="$1"
  local expected="$2"
  shift 2

  # Write response body to a temp file so we can capture both body and status
  local tmpfile
  tmpfile=$(mktemp)

  STATUS=$(curl -s -o "$tmpfile" -w "%{http_code}" "$@")
  RESPONSE=$(cat "$tmpfile")
  rm -f "$tmpfile"

  if [ "$STATUS" -eq "$expected" ]; then
    pass "$label — HTTP $STATUS"
  else
    fail "$label — expected HTTP $expected, got HTTP $STATUS"
    echo "  Response: $RESPONSE"
  fi
}

# ---------------------------------------------------------------------------
# 1. Health
# ---------------------------------------------------------------------------
section "Health"

do_request "GET /health" 200 \
  -X GET "$BASE_URL/health"

do_request "GET /health/db" 200 \
  -X GET "$BASE_URL/health/db"

# ---------------------------------------------------------------------------
# 2. Login — extract token
# ---------------------------------------------------------------------------
section "Auth / Login"

do_request "POST /auth/login" 200 \
  -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}"

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token // empty')

if [ -z "$TOKEN" ]; then
  fail "Could not extract access_token — aborting remaining tests"
  echo -e "\n${RED}Smoke test FAILED${RESET}"
  exit 1
fi

pass "access_token extracted"

# ---------------------------------------------------------------------------
# 3. GET /auth/me
# ---------------------------------------------------------------------------
section "Auth / Me"

do_request "GET /auth/me" 200 \
  -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN"

ME_EMAIL=$(echo "$RESPONSE" | jq -r '.email // empty')
if [ "$ME_EMAIL" = "$EMAIL" ]; then
  pass "email matches ($ME_EMAIL)"
else
  fail "email mismatch — expected $EMAIL, got $ME_EMAIL"
fi

# ---------------------------------------------------------------------------
# 4. POST /users/ — create a new user
# ---------------------------------------------------------------------------
section "Users / Create"

do_request "POST /users/" 201 \
  -X POST "$BASE_URL/users/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"Sm0ke_Test!\", \"full_name\": \"Smoke User\"}"

CREATED_ID=$(echo "$RESPONSE" | jq -r '.id // empty')
if [ -n "$CREATED_ID" ]; then
  pass "created user id: $CREATED_ID"
else
  fail "response did not contain an id"
fi

# ---------------------------------------------------------------------------
# 5. GET /users/
# ---------------------------------------------------------------------------
section "Users / List"

do_request "GET /users/" 200 \
  -X GET "$BASE_URL/users/" \
  -H "Authorization: Bearer $TOKEN"

USER_COUNT=$(echo "$RESPONSE" | jq 'length // 0')
pass "listed $USER_COUNT user(s)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
if [ "$EXIT_CODE" -eq 0 ]; then
  echo -e "${GREEN}All smoke tests passed.${RESET}"
else
  echo -e "${RED}Some smoke tests FAILED. Review output above.${RESET}"
fi

exit "$EXIT_CODE"
