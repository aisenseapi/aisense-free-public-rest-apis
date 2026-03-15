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
check "Datetime"              GET "$BASE/time/datetime"
check "Datetime (with offset)" GET "$BASE/time/datetime/1"
check "Timestamp"             GET "$BASE/time/timestamp"
check "Microtimestamp"        GET "$BASE/time/microtimestamp"
check "Timezones"             GET "$BASE/time/timezones"
check "Swatch Internet Time"  GET "$BASE/time/swatchinternettime"
echo ""

# ── RANDOM ───────────────────────────────────────────────────
echo -e "${YELLOW}🎲  Random${NC}"
check "Random Number (default)"  GET "$BASE/random/number"
check "Random Number (1–100)"    GET "$BASE/random/number/1/100"
check "Random Color"             GET "$BASE/random/color"
check "UUID"                     GET "$BASE/random/uuid"
check "GUID"                     GET "$BASE/random/guid"
echo ""

# ── TRANSFORM ────────────────────────────────────────────────
echo -e "${YELLOW}🔄  Transform${NC}"
check "Base64 Encode"   POST "$BASE/transform/base64_encode"  '{"data":"Hello, world!"}'
check "Base64 Decode"   POST "$BASE/transform/base64_decode"  '{"data":"SGVsbG8sIHdvcmxkIQ=="}'
check "Base58 Encode"   POST "$BASE/transform/base58_encode"  '{"data":"Hello"}'
check "Base58 Decode"   POST "$BASE/transform/base58_decode"  '{"data":"9Ajdvzr"}'
check "Base32 Encode"   POST "$BASE/transform/base32_encode"  '{"data":"Hello"}'
check "Base32 Decode"   POST "$BASE/transform/base32_decode"  '{"data":"JBSWY3DP"}'
check "JWT Encode"      POST "$BASE/transform/jwt_encode"     '{"data":{"user":"test"},"secret":"mysecret"}'
check "JWT Decode"      POST "$BASE/transform/jwt_decode"     '{"data":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidGVzdCJ9.4oHDP2OHjcBwO-OiCg8ILaGC8DUjOmMJN5mQ8xR1yUo","secret":"mysecret"}'
check "QR Code Encode"  POST "$BASE/transform/qrcode_encode"  '{"data":"https://example.com"}'
echo ""

# ── HASH ─────────────────────────────────────────────────────
echo -e "${YELLOW}🔐  Hash${NC}"
check "MD5"    POST "$BASE/hash/md5"    '{"data":"Hello"}'
check "SHA1"   POST "$BASE/hash/sha1"   '{"data":"Hello"}'
check "SHA256" POST "$BASE/hash/sha256" '{"data":"Hello"}'
check "SHA512" POST "$BASE/hash/sha512" '{"data":"Hello"}'
echo ""

# ── WEB ──────────────────────────────────────────────────────
echo -e "${YELLOW}🌐  Web${NC}"
check "Ping"       GET "$BASE/web/ping"
check "Health"     GET "$BASE/web/health"
check "Client IP"  GET "$BASE/web/ip"
check "IP Lookup"  GET "$BASE/web/ip_reverse_lookup/8.8.8.8"

# Storage: store then retrieve
echo -ne "  Testing Storage (store)... "
store_response=$(curl -s -X POST "$BASE/web/storage" \
  -H "Content-Type: application/json" \
  -d '{"data":{"test":"skill-test"}}')
store_uuid=$(echo "$store_response" | grep -o '"uuid":"[^"]*"' | cut -d'"' -f4)
if [ -n "$store_uuid" ]; then
  echo -e "${GREEN}✓${NC} got UUID: $store_uuid"
  PASS=$((PASS + 1))
  check "Storage (retrieve)" GET "$BASE/web/storage/$store_uuid"
else
  echo -e "${RED}✗${NC} no UUID returned"
  FAIL=$((FAIL + 1))
fi

# URL Shortener
echo -ne "  Testing URL Shortener... "
short_response=$(curl -s -X POST "$BASE/web/url_shortener" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}')
short_url=$(echo "$short_response" | grep -o '"short_url":"[^"]*"' | cut -d'"' -f4)
if [ -n "$short_url" ]; then
  echo -e "${GREEN}✓${NC} short URL: $short_url"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} no short_url returned"
  FAIL=$((FAIL + 1))
fi

check "Webhook Capture" POST "$BASE/web/webhook_capture" '{"event":"test"}'

# Webhook Action
check "Webhook Action" POST "$BASE/web/webhook_action" \
  '{"title":"Test action","fields":[{"type":"radio","name":"choice","label":"Pick one","options":["Yes","No"]}]}'
echo ""

# ── CRYPTO ───────────────────────────────────────────────────
echo -e "${YELLOW}🪙  Crypto${NC}"
check "Solana Wallet"   GET "$BASE/crypto/solana_wallet"
check "Bitcoin Wallet"  GET "$BASE/crypto/bitcoin_wallet"
check "Ethereum Wallet" GET "$BASE/crypto/ethereum_wallet"
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
