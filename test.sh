#!/usr/bin/env bash
# ============================================================
# test.sh — Verify all AI SENSE AS free public REST API endpoints
# Usage: chmod +x test.sh && ./test.sh
# ============================================================

BASE="https://aisenseapi.com/services/v1"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check() {
  local label="$1"
  local method="$2"
  local url="$3"
  local data="$4"
  local content_type="${5:-application/json}"

  if [ "$method" = "GET" ]; then
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  else
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" \
      -H "Content-Type: $content_type" \
      -d "$data")
  fi

  if [ "$status" -ge 200 ] && [ "$status" -lt 300 ]; then
    echo -e "${GREEN}✓${NC} $label (HTTP $status)"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}✗${NC} $label (HTTP $status)"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "============================================================"
echo " AI SENSE AS — Free Public REST API Endpoint Tests"
echo "============================================================"
echo ""

# ── TIME ─────────────────────────────────────────────────────
echo -e "${YELLOW}⏱  Time${NC}"
check "Datetime"               GET "$BASE/datetime"
check "Datetime (with offset)" GET "$BASE/datetime/1"
check "Timestamp"              GET "$BASE/timestamp"
check "Microtimestamp"         GET "$BASE/microtimestamp"
check "Timezones"              GET "$BASE/timezones"
check "Swatch Internet Time"   GET "$BASE/swatchinternettime"
echo ""

# ── RANDOM ───────────────────────────────────────────────────
echo -e "${YELLOW}🎲  Random${NC}"
check "Random Number (default)"  GET "$BASE/random_number"
check "Random Number (1–100)"    GET "$BASE/random_number/1/100"
check "Random Color"             GET "$BASE/random_color"
check "UUID"                     GET "$BASE/uuid"
check "GUID"                     GET "$BASE/guid"
echo ""

# ── TRANSFORM ────────────────────────────────────────────────
echo -e "${YELLOW}🔄  Transform${NC}"
check "Base64 Encode"   POST "$BASE/base64_encode"  '{"data":"Hello, world!"}'
check "Base64 Decode"   POST "$BASE/base64_decode"  '{"data":"SGVsbG8sIHdvcmxkIQ=="}'
check "Base58 Encode"   POST "$BASE/base58_encode"  '{"data":"Hello"}'
check "Base58 Decode"   POST "$BASE/base58_decode"  '{"data":"9Ajdvzr"}'
check "Base32 Encode"   POST "$BASE/base32_encode"  '{"data":"Hello"}'
check "Base32 Decode"   POST "$BASE/base32_decode"  '{"data":"JBSWY3DP"}'
check "JWT Encode"      POST "$BASE/jwt_encode"     '{"data":{"user":"test"},"secret":"mysecret"}'
check "JWT Decode"      POST "$BASE/jwt_decode"     '{"data":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidGVzdCJ9.4oHDP2OHjcBwO-OiCg8ILaGC8DUjOmMJN5mQ8xR1yUo","secret":"mysecret"}'
check "QR Code Encode"  POST "$BASE/qrcode_encode"  '{"data":"https://example.com"}'
echo ""

# ── HASH ─────────────────────────────────────────────────────
echo -e "${YELLOW}🔐  Hash${NC}"
check "MD5"    POST "$BASE/md5_hash"    '{"data":"Hello"}'
check "SHA1"   POST "$BASE/sha1_hash"   '{"data":"Hello"}'
check "SHA256" POST "$BASE/sha256_hash" '{"data":"Hello"}'
check "SHA512" POST "$BASE/sha512_hash" '{"data":"Hello"}'
echo ""

# ── WEB ──────────────────────────────────────────────────────
echo -e "${YELLOW}🌐  Web${NC}"
check "Ping"       GET "$BASE/ping"
check "Health"     GET "$BASE/health"
check "Client IP"  GET "$BASE/client_ip"
check "IP Lookup"  GET "$BASE/ip_reverse_lookup/8.8.8.8"

# Storage: store then retrieve
echo -ne "  Testing Storage (store)... "
store_response=$(curl -s -X POST "$BASE/storage" \
  -H "Content-Type: application/json" \
  -d '{"data":{"test":"skill-test"}}')
store_uuid=$(echo "$store_response" | grep -o '"uuid":"[^"]*"' | cut -d'"' -f4)
if [ -n "$store_uuid" ]; then
  echo -e "${GREEN}✓${NC} got UUID: $store_uuid"
  PASS=$((PASS + 1))
  check "Storage (retrieve)" GET "$BASE/storage/$store_uuid"
else
  echo -e "${RED}✗${NC} no UUID returned"
  FAIL=$((FAIL + 1))
fi

# URL Shortener
check "URL Shortener" GET "$BASE/url_shortener/https://example.com"

# Webhook Capture: init → update → read
echo -ne "  Testing Webhook Capture (init)... "
capture_response=$(curl -s -X POST "$BASE/webhook_capture")
capture_id=$(echo "$capture_response" | grep -o '"capture_id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$capture_id" ]; then
  echo -e "${GREEN}✓${NC} got capture_id: $capture_id"
  PASS=$((PASS + 1))
  check "Webhook Capture (update)" POST "$BASE/webhook_capture/$capture_id/update" '{"event":"test"}'
  check "Webhook Capture (read)"   GET  "$BASE/webhook_capture/$capture_id"
else
  echo -e "${RED}✗${NC} no capture_id returned"
  FAIL=$((FAIL + 1))
fi

# Webhook Action: init only (human touch required to complete)
check "Webhook Action (init)" POST "$BASE/webhook_action" \
  '{"title":"Test action","fields":[{"type":"radio","name":"choice","label":"Pick one","options":["Yes","No"]}]}'
echo ""

# ── CRYPTO ───────────────────────────────────────────────────
echo -e "${YELLOW}🪙  Crypto${NC}"
check "Solana Wallet"   GET "$BASE/solana/generate_new_wallet"
check "Bitcoin Wallet"  GET "$BASE/bitcoin/generate_new_wallet"
check "Ethereum Wallet" GET "$BASE/ethereum/generate_new_wallet"
echo ""

# ── SUMMARY ──────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo "============================================================"
echo -e " Results: ${GREEN}$PASS passed${NC} / ${RED}$FAIL failed${NC} / $TOTAL total"
echo "============================================================"
echo ""

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
