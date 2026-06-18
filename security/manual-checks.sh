#!/usr/bin/env bash
# =============================================================================
# Manual Penetration Test Checks — OWASP Top 10 + platform governance
#
# AUTHORIZATION NOTICE: Run this script ONLY against your own running instance
# of your application. Unauthorised testing of systems you do not own is
# illegal in most jurisdictions.
#
# Usage:
#   chmod +x security/manual-checks.sh
#   ./security/manual-checks.sh http://localhost:8000
#
# Each check prints PASS or FAIL with a description of the finding.
#
# TODO: this is a worked example against an API with a two-level owned
# resource hierarchy (a top-level resource owning a child resource owning a
# grandchild resource — e.g. projects -> tasks -> comments) and a 5-state
# status state machine on the child resource (TODO/IN_PROGRESS/IN_REVIEW/
# DONE/CANCELLED). The A01 (access control / IDOR) and A04 (insecure design /
# state machine) sections encode that shape. Adjust the ENDPOINTS block below
# for path/field names, and either adapt or delete the status-transition
# checks in A04 if your API doesn't have a similar workflow.
# =============================================================================

BASE_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0

# ─── Configuration — adjust these to match your API ─────────────────────────
# TODO: replace endpoint paths/field names with your own API's.
AUTH_REGISTER="/auth/register"
AUTH_LOGIN="/auth/login"
AUTH_LOGOUT="/auth/logout"
AUTH_DELETE_ME="/auth/users/me"
RESOURCE="/projects"             # top-level owned resource
CHILD="tasks"                    # nested resource under RESOURCE/{id}/<CHILD>
GRANDCHILD="comments"            # nested under RESOURCE/{id}/<CHILD>/{id}/<GRANDCHILD>
HEALTH="/health"
READY="/ready"
METRICS="/metrics"
SECURITY_TXT="/.well-known/security.txt"

_pass() { echo "  ✅  PASS — $1"; ((PASS++)); }
_fail() { echo "  ❌  FAIL — $1"; ((FAIL++)); }
_info() { echo ""; echo "── $1 ──────────────────────────────────────────"; }

echo ""
echo "Penetration Test — Manual Checks"
echo "Target: $BASE_URL"
echo "================================================================="

# ─── A01: Broken Access Control ──────────────────────────────────────────────
_info "A01 — Broken Access Control"

# Create two users
EMAIL_A="pentest_a_$(date +%s)@example.com"
EMAIL_B="pentest_b_$(date +%s)@example.com"

curl -sf -X POST "$BASE_URL$AUTH_REGISTER" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL_A\",\"full_name\":\"User A\",\"password\":\"PenTest123!\"}" > /dev/null

curl -sf -X POST "$BASE_URL$AUTH_REGISTER" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL_B\",\"full_name\":\"User B\",\"password\":\"PenTest123!\"}" > /dev/null

# Register GDPR test user here (before the rate-limit test) so the login
# does not land inside the throttled window used by the rate-limit check below.
GDPR_EMAIL="gdpr_test_$(date +%s)@example.com"
curl -sf -X POST "$BASE_URL$AUTH_REGISTER" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$GDPR_EMAIL\",\"full_name\":\"GDPR Test\",\"password\":\"GdprTest1!\"}" > /dev/null
GDPR_TOKEN=$(curl -sf -X POST "$BASE_URL$AUTH_LOGIN" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$GDPR_EMAIL\",\"password\":\"GdprTest1!\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

TOKEN_A=$(curl -sf -X POST "$BASE_URL$AUTH_LOGIN" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL_A\",\"password\":\"PenTest123!\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

TOKEN_B=$(curl -sf -X POST "$BASE_URL$AUTH_LOGIN" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL_B\",\"password\":\"PenTest123!\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

# User A creates a top-level resource
RESOURCE_A=$(curl -sf -X POST "$BASE_URL$RESOURCE" \
  -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
  -d '{"name":"User A Private Resource"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

# IDOR check: User B tries to read User A's resource
if [ -n "$RESOURCE_A" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN_B" \
    "$BASE_URL$RESOURCE/$RESOURCE_A")
  if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    _pass "IDOR: User B cannot read User A's resource (HTTP $STATUS)"
  else
    _fail "IDOR: User B received HTTP $STATUS on User A's resource — potential data leak"
  fi
fi

# IDOR: User B tries to delete User A's resource
if [ -n "$RESOURCE_A" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
    -H "Authorization: Bearer $TOKEN_B" \
    "$BASE_URL$RESOURCE/$RESOURCE_A")
  if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    _pass "IDOR: User B cannot delete User A's resource (HTTP $STATUS)"
  else
    _fail "IDOR: User B received HTTP $STATUS when deleting User A's resource — unauthorized deletion"
  fi
fi

# User A creates a child resource
CHILD_A=$(curl -sf -X POST "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD" \
  -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
  -d '{"title":"Secret Item","priority":"HIGH"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

# IDOR: User B tries to list User A's child resources
if [ -n "$RESOURCE_A" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN_B" \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD")
  if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    _pass "IDOR: User B cannot list $CHILD in User A's resource (HTTP $STATUS)"
  else
    _fail "IDOR: User B received HTTP $STATUS when listing User A's $CHILD — enumeration possible"
  fi
fi

# IDOR: User B tries to read User A's child resource
if [ -n "$CHILD_A" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN_B" \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD/$CHILD_A")
  if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    _pass "IDOR: User B cannot read User A's $CHILD item (HTTP $STATUS)"
  else
    _fail "IDOR: User B received HTTP $STATUS when reading User A's $CHILD item — data leak"
  fi
fi

# IDOR: User B tries to update User A's child resource
if [ -n "$CHILD_A" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD/$CHILD_A" \
    -H "Authorization: Bearer $TOKEN_B" -H "Content-Type: application/json" \
    -d '{"status":"IN_PROGRESS"}')
  if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    _pass "IDOR: User B cannot modify User A's $CHILD item (HTTP $STATUS)"
  else
    _fail "IDOR: User B received HTTP $STATUS when modifying User A's $CHILD item — privilege escalation"
  fi
fi

# IDOR: User B tries to delete User A's child resource
if [ -n "$CHILD_A" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD/$CHILD_A" \
    -H "Authorization: Bearer $TOKEN_B")
  if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    _pass "IDOR: User B cannot delete User A's $CHILD item (HTTP $STATUS)"
  else
    _fail "IDOR: User B received HTTP $STATUS when deleting User A's $CHILD item — unauthorized deletion"
  fi
fi

# IDOR: User B tries to list grandchild resources on User A's child resource
if [ -n "$CHILD_A" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN_B" \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD/$CHILD_A/$GRANDCHILD")
  if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    _pass "IDOR: User B cannot list $GRANDCHILD on User A's $CHILD item (HTTP $STATUS)"
  else
    _fail "IDOR: User B received HTTP $STATUS when listing User A's $GRANDCHILD — enumeration possible"
  fi
fi

# IDOR: User B tries to create a grandchild resource on User A's child resource
if [ -n "$CHILD_A" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD/$CHILD_A/$GRANDCHILD" \
    -H "Authorization: Bearer $TOKEN_B" -H "Content-Type: application/json" \
    -d '{"body":"IDOR attempt"}')
  if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    _pass "IDOR: User B cannot add $GRANDCHILD to User A's $CHILD item (HTTP $STATUS)"
  else
    _fail "IDOR: User B received HTTP $STATUS when adding to User A's $CHILD item — cross-user write"
  fi
fi

# Unauthenticated access to protected resource
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$RESOURCE")
if [ "$STATUS" = "401" ] || [ "$STATUS" = "403" ]; then
  _pass "Unauthenticated request to $RESOURCE returns HTTP $STATUS"
else
  _fail "Unauthenticated request to $RESOURCE returned HTTP $STATUS (expected 401)"
fi

# ─── A02: Cryptographic Failures ─────────────────────────────────────────────
_info "A02 — Cryptographic Failures"

# JWT with 'none' algorithm (alg:none attack)
NONE_TOKEN="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIn0."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $NONE_TOKEN" "$BASE_URL$RESOURCE")
if [ "$STATUS" = "401" ] || [ "$STATUS" = "403" ]; then
  _pass "JWT alg:none rejected (HTTP $STATUS)"
else
  _fail "JWT alg:none accepted — critical authentication bypass vulnerability"
fi

# Tampered JWT (valid structure, invalid signature)
TAMPERED="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5OTk5OTkifQ.INVALIDSIGNATURE"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TAMPERED" "$BASE_URL$RESOURCE")
if [ "$STATUS" = "401" ] || [ "$STATUS" = "403" ]; then
  _pass "Tampered JWT signature rejected (HTTP $STATUS)"
else
  _fail "Tampered JWT accepted — JWT signature validation is broken"
fi

# Expired token simulation (can't easily create one without the secret — just note it)
echo "  ℹ️   NOTE: Test token expiry manually by waiting past your access token's"
echo "       lifetime, or temporarily shortening it and retrying a request"

# ─── A03: Injection ───────────────────────────────────────────────────────────
_info "A03 — Injection"

if [ -z "$TOKEN_A" ] || [ -z "$RESOURCE_A" ]; then
  echo "  ⚠️   SKIP — A01 setup did not complete (rate limiting or registration failed)."
  echo "       Wait 60 s after a previous run and retry, or use a fresh IP address."
else
  # SQL injection probe in child resource title
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD" \
    -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
    -d "{\"title\":\"'; DROP TABLE items; --\",\"priority\":\"LOW\"}")
  if [ "$STATUS" = "201" ] || [ "$STATUS" = "422" ]; then
    # 201 = stored safely; 422 = rejected by validation; both acceptable
    # A 500 would indicate the SQL was executed
    _pass "SQL injection in $CHILD title: HTTP $STATUS (payload treated as data, not SQL)"
  else
    _fail "SQL injection probe returned HTTP $STATUS — investigate server logs for errors"
  fi

  # XSS probe in top-level resource name
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "$BASE_URL$RESOURCE" \
    -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
    -d '{"name":"<script>alert(1)</script>"}')
  if [ "$STATUS" = "201" ] || [ "$STATUS" = "422" ]; then
    _pass "XSS payload in resource name: HTTP $STATUS (stored/rejected safely — API returns JSON, not HTML)"
  else
    _fail "XSS probe returned HTTP $STATUS — investigate"
  fi
fi

# ─── A04: Insecure Design ────────────────────────────────────────────────────
# TODO: this section assumes a status state machine on the child resource
# (TODO -> IN_PROGRESS -> IN_REVIEW -> DONE, any non-terminal -> CANCELLED,
# DONE/CANCELLED terminal). Adapt the transitions tested below to your own
# workflow, or delete this section if your API has no such state machine.
_info "A04 — Insecure Design"

# Status transition bypass: attempt TODO -> DONE (skipping intermediate states)
CHILD_B=$(curl -sf -X POST "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD" \
  -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
  -d '{"title":"Transition Test","priority":"MEDIUM"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -n "$CHILD_B" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD/$CHILD_B" \
    -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
    -d '{"status":"DONE"}')
  if [ "$STATUS" = "422" ]; then
    _pass "Business rule enforced: TODO->DONE rejected with 422"
  else
    _fail "Business rule bypass: TODO->DONE returned HTTP $STATUS (expected 422)"
  fi
fi

# Terminal state irreversibility: cancel CHILD_B, then try to reopen it
if [ -n "$CHILD_B" ]; then
  # First cancel the item (TODO -> CANCELLED is a valid transition)
  curl -s -o /dev/null -X PATCH \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD/$CHILD_B" \
    -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
    -d '{"status":"CANCELLED"}'
  # Now try to escape the terminal state (CANCELLED -> IN_PROGRESS must be rejected)
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH \
    "$BASE_URL$RESOURCE/$RESOURCE_A/$CHILD/$CHILD_B" \
    -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
    -d '{"status":"IN_PROGRESS"}')
  if [ "$STATUS" = "422" ]; then
    _pass "Terminal state CANCELLED is irreversible: CANCELLED->IN_PROGRESS rejected with 422"
  else
    _fail "Terminal state bypass: CANCELLED->IN_PROGRESS returned HTTP $STATUS (expected 422)"
  fi
fi

# Rate limiting check: 20 rapid login attempts
echo "  ⏱️   Testing login rate limiting (20 rapid requests)..."
FAIL_COUNT=0
for i in $(seq 1 20); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$AUTH_LOGIN" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"nonexistent$i@example.com\",\"password\":\"wrong\"}")
  if [ "$STATUS" = "429" ]; then
    _pass "Rate limiting active: received 429 after $i requests"
    FAIL_COUNT=-1  # signal that rate limiting was found
    break
  fi
done
if [ "$FAIL_COUNT" = "0" ]; then
  _fail "No rate limiting on $AUTH_LOGIN — 20 consecutive failed logins all returned 200/401 without throttling"
fi

# User enumeration: does login distinguish "email not found" vs "wrong password"?
RESP_EXIST=$(curl -s -X POST "$BASE_URL$AUTH_LOGIN" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL_A\",\"password\":\"wrongpassword\"}" 2>/dev/null)
RESP_NOEXIST=$(curl -s -X POST "$BASE_URL$AUTH_LOGIN" \
  -H "Content-Type: application/json" \
  -d '{"email":"definitelynotreal@example.com","password":"wrongpassword"}' 2>/dev/null)
if [ "$RESP_EXIST" = "$RESP_NOEXIST" ]; then
  _pass "Login error responses are identical (no user enumeration)"
else
  _fail "Login responses differ for existing vs non-existing email — user enumeration possible"
  echo "       Existing user response:     $(echo "$RESP_EXIST" | python3 -m json.tool 2>/dev/null | head -3)"
  echo "       Non-existing user response: $(echo "$RESP_NOEXIST" | python3 -m json.tool 2>/dev/null | head -3)"
fi

# ─── A05: Security Misconfiguration ─────────────────────────────────────────
_info "A05 — Security Misconfiguration"

# Check CORS headers
CORS=$(curl -sI -X OPTIONS "$BASE_URL$RESOURCE" \
  -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: GET" | grep -i "access-control-allow-origin")
if echo "$CORS" | grep -q "evil.example.com\|\*"; then
  _fail "CORS: API allows requests from evil.example.com or wildcard origin — check allow_origins"
else
  _pass "CORS: API does not reflect arbitrary origins"
fi

# Check for server version disclosure in headers
SERVER=$(curl -sI "$BASE_URL$HEALTH" | grep -i "^server:")
if echo "$SERVER" | grep -qiE "uvicorn|fastapi|python|version"; then
  _fail "Server header discloses technology: $SERVER"
else
  _pass "Server header does not disclose technology versions"
fi

# ─── A07: Auth Failures ──────────────────────────────────────────────────────
_info "A07 — Identification and Authentication Failures"

# Weak password accepted?
WEAK_EMAIL="weakpass_$(date +%s)@example.com"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$AUTH_REGISTER" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$WEAK_EMAIL\",\"full_name\":\"Weak\",\"password\":\"123\"}")
if [ "$STATUS" = "422" ]; then
  _pass "Weak password '123' rejected with 422"
else
  _fail "Weak password '123' accepted (HTTP $STATUS) — no minimum password length enforced"
fi

# Empty password
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$AUTH_REGISTER" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"empty_$(date +%s)@example.com\",\"full_name\":\"Empty\",\"password\":\"\"}")
if [ "$STATUS" = "422" ]; then
  _pass "Empty password rejected with 422"
else
  _fail "Empty password accepted (HTTP $STATUS)"
fi

# ─── Governance & Compliance ─────────────────────────────────────────────────
_info "Governance & Compliance"

# Security headers
HEADERS=$(curl -sI "$BASE_URL$HEALTH")
if echo "$HEADERS" | grep -qi "x-content-type-options"; then
  _pass "Security header X-Content-Type-Options present"
else
  _fail "Security header X-Content-Type-Options missing — add a security-headers middleware"
fi
if echo "$HEADERS" | grep -qi "x-xss-protection"; then
  _pass "Security header X-XSS-Protection present"
else
  _fail "Security header X-XSS-Protection missing"
fi
if echo "$HEADERS" | grep -qi "x-frame-options"; then
  _pass "Security header X-Frame-Options present"
else
  _fail "Security header X-Frame-Options missing"
fi
if echo "$HEADERS" | grep -qi "strict-transport-security"; then
  _pass "Security header Strict-Transport-Security (HSTS) present"
else
  _fail "Security header Strict-Transport-Security missing"
fi
if echo "$HEADERS" | grep -qi "content-security-policy"; then
  _pass "Security header Content-Security-Policy present"
else
  _fail "Security header Content-Security-Policy missing"
fi
if echo "$HEADERS" | grep -qi "referrer-policy"; then
  _pass "Security header Referrer-Policy present"
else
  _fail "Security header Referrer-Policy missing"
fi
if echo "$HEADERS" | grep -qi "cache-control:.*no-store"; then
  _pass "Security header Cache-Control: no-store present (prevents proxy caching of API responses)"
else
  _fail "Cache-Control: no-store missing — API responses with user data may be stored by intermediate proxies"
fi
if echo "$HEADERS" | grep -qi "permissions-policy"; then
  _pass "Security header Permissions-Policy present (restricts camera/mic/geolocation)"
else
  _fail "Permissions-Policy header missing — browser features not explicitly restricted"
fi

# RFC 9116 security disclosure policy
SEC_TXT=$(curl -s "$BASE_URL$SECURITY_TXT")
SEC_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$SECURITY_TXT")
if [ "$SEC_STATUS" = "200" ] && echo "$SEC_TXT" | grep -q "Contact:"; then
  _pass "Security disclosure: GET $SECURITY_TXT returns 200 with Contact field (RFC 9116)"
else
  _fail "Security disclosure: $SECURITY_TXT returned HTTP $SEC_STATUS or missing Contact field"
fi

# Readiness probe
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$READY")
if [ "$STATUS" = "200" ]; then
  _pass "Readiness probe GET $READY returns 200"
else
  _fail "Readiness probe GET $READY returned HTTP $STATUS (expected 200)"
fi

# Token revocation via logout
if [ -n "$TOKEN_B" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $TOKEN_B" "$BASE_URL$AUTH_LOGOUT")
  if [ "$STATUS" = "204" ]; then
    _pass "Logout POST $AUTH_LOGOUT returns 204"
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $TOKEN_B" "$BASE_URL$RESOURCE")
    if [ "$STATUS" = "401" ]; then
      _pass "Revoked token rejected with 401 — token revocation working"
    else
      _fail "Revoked token still accepted (HTTP $STATUS) — token revocation broken"
    fi
  else
    _fail "Logout returned HTTP $STATUS (expected 204)"
  fi
fi

# GDPR / data-subject account deletion
if [ -n "$GDPR_TOKEN" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
    -H "Authorization: Bearer $GDPR_TOKEN" "$BASE_URL$AUTH_DELETE_ME")
  if [ "$STATUS" = "204" ]; then
    _pass "GDPR deletion DELETE $AUTH_DELETE_ME returns 204"
    # Verify the token is now invalid (soft-deleted user not found by current_user dep)
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $GDPR_TOKEN" "$BASE_URL$RESOURCE")
    if [ "$STATUS" = "401" ]; then
      _pass "Soft-deleted user's token rejected with 401"
    else
      _fail "Soft-deleted user's token still accepted (HTTP $STATUS) — GDPR soft delete broken"
    fi
  else
    _fail "GDPR deletion returned HTTP $STATUS (expected 204)"
  fi
else
  _fail "GDPR test skipped — could not obtain token (registration or login failed)"
fi

# Body size limit
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$AUTH_REGISTER" \
  -H "Content-Type: application/json" \
  -H "Content-Length: 1048577" \
  -d '{}')
if [ "$STATUS" = "413" ]; then
  _pass "Body size limit: Content-Length > 1 MiB rejected with 413"
else
  _fail "Body size limit not enforced: Content-Length > 1 MiB returned HTTP $STATUS (expected 413)"
fi

# Input length validation
if [ -n "$TOKEN_A" ]; then
  LONG_NAME=$(python3 -c "print('x'*256)")
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$RESOURCE" \
    -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
    -d "{\"name\":\"$LONG_NAME\"}")
  if [ "$STATUS" = "422" ]; then
    _pass "Input validation: resource name > 255 chars rejected with 422"
  else
    _fail "Input validation: resource name > 255 chars returned HTTP $STATUS (expected 422)"
  fi
else
  _fail "Input validation check skipped — TOKEN_A not available"
fi

# Observability: /metrics endpoint (Prometheus scrape target)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -L "$BASE_URL$METRICS")
if [ "$STATUS" = "200" ]; then
  _pass "Observability: GET $METRICS returns 200 (Prometheus scrape target active)"
else
  _fail "Observability: GET $METRICS returned HTTP $STATUS (expected 200) — check OTel is enabled"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "================================================================="
echo "  Pen Test Summary"
echo "  PASS: $PASS   FAIL: $FAIL"
echo "================================================================="
echo ""
if [ "$FAIL" -gt 0 ]; then
  echo "  ❌  $FAIL check(s) failed. Review the findings above and either"
  echo "      fix the vulnerability or document the accepted risk in docs/adr/."
  exit 1
else
  echo "  ✅  All manual checks passed."
  exit 0
fi
