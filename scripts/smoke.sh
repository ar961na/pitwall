#!/usr/bin/env bash
# End-to-end smoke test of the running stack (nginx -> React build + /api -> FastAPI).
# Offline: touches no endpoint that needs OpenF1, so it's deterministic in CI.
#   docker compose up -d --wait && scripts/smoke.sh http://localhost:8080
set -euo pipefail
BASE="${1:-http://localhost:8080}"
pass() { printf '  \033[32mok\033[0m   %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; exit 1; }

echo "smoke test against $BASE"

html="$(curl -fsS "$BASE/")" || fail "index.html reachable"
grep -q '<div id="root">' <<<"$html" && pass "index.html served" || fail "index.html has #root"

# The JS bundle must be real JavaScript, not an SPA fallback to index.html (wrong base path).
js="$(grep -oE '/[^"]*assets/index-[^"]+\.js' <<<"$html" | head -1)"
ctype="$(curl -fsS -o /dev/null -w '%{content_type}' "$BASE$js")"
[[ "$ctype" == *javascript* ]] && pass "JS bundle $js ($ctype)" || fail "JS bundle content-type: $ctype"

curl -fsS "$BASE/api/health" | jq -e '.status == "ok"' >/dev/null && pass "GET /api/health" || fail "health"
curl -fsS "$BASE/api/sources" | jq -e '.sources | length == 3' >/dev/null \
  && pass "GET /api/sources (data attribution)" || fail "sources"
curl -fsS "$BASE/api/strategy/defaults" | jq -e '.total_laps > 0' >/dev/null \
  && pass "GET /api/strategy/defaults" || fail "defaults"
curl -fsS -X POST -H 'Content-Type: application/json' -d '{"n_sims": 300}' "$BASE/api/strategy/optimize" \
  | jq -e '.results[0].gap_s == 0 and (.results | length) > 5' >/dev/null \
  && pass "POST /api/strategy/optimize (Monte Carlo)" || fail "optimize"
code="$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  -d '{"n_sims": 5}' "$BASE/api/strategy/optimize")"
[[ "$code" == 422 ]] && pass "invalid request rejected (422)" || fail "validation returned $code"
code="$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/predict/2026/1")"
[[ "$code" == 501 ]] && pass "GET /api/predict -> 501 until TASK 5" || fail "predict returned $code"

echo "all smoke checks passed"
