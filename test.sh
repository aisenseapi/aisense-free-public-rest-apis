#!/usr/bin/env bash
# ============================================================
# test.sh — verify the AI SENSE AS free public REST API
#
# This suite asserts on response bodies, not status codes.
#
# That is not a stylistic preference. This API answers HTTP 200 for most
# failures, returns 200 with a debug echo for paths that do not exist, and
# has in the past returned 200 with a PHP warning prepended to the JSON.
# A status-code-only suite reports every one of those as a pass, which is
# exactly what the previous version of this file did.
#
# Usage: chmod +x test.sh && ./test.sh
# Exits 1 if anything fails. Safe for CI.
# ============================================================

BASE="${AISENSE_BASE:-https://aisenseapi.com/services/v1}"
PASS=0
FAIL=0
XFAIL=0
FIXED=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

ok()      { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
bad()     { echo -e "${RED}✗${NC} $1"; [ -n "$2" ] && echo -e "    ${RED}$2${NC}"; FAIL=$((FAIL + 1)); }
expected(){ echo -e "${BLUE}~${NC} $1 ${BLUE}(known bug, not counted)${NC}"; XFAIL=$((XFAIL + 1)); }
fixed()   { echo -e "${GREEN}★${NC} $1 ${GREEN}— known bug is FIXED, promote it in test.sh${NC}"; FIXED=$((FIXED + 1)); }

# ── Core request helper ──────────────────────────────────────
# Sets $BODY and $STATUS. Never inspects them itself.
request() {
  local method="$1" url="$2" data="$3" ctype="${4:-application/json}" accept="$5"
  local args=(-s -m 30 -w '\n%{http_code}')
  [ -n "$accept" ] && args+=(-H "Accept: $accept")
  if [ "$method" = "GET" ]; then
    RAW=$(curl "${args[@]}" "$url")
  else
    RAW=$(curl "${args[@]}" -X POST "$url" -H "Content-Type: $ctype" -d "$data")
  fi
  STATUS="${RAW##*$'\n'}"
  BODY="${RAW%$'\n'*}"
}

# ── Assertions every response must survive ───────────────────
# Returns non-zero and prints the reason if the body is structurally wrong,
# regardless of what the individual test was looking for.
body_is_sane() {
  local label="$1"
  if [ -z "$BODY" ]; then
    REASON="empty body"; return 1
  fi
  # Unknown paths answer 200 with ["<ip>",<ts>]["/services/v1/x","1","x"]
  case "$BODY" in
    '["'*']["'*) REASON="endpoint does not exist — got the debug echo, check the path"; return 1 ;;
  esac
  # A PHP notice ahead of the JSON makes the body unparseable for every client
  case "$BODY" in
    *"Warning:"*|*"Fatal error:"*|*"Notice:"*|*"Deprecated:"*)
      REASON="PHP diagnostic leaked into the body: $(echo "$BODY" | head -c 120)"; return 1 ;;
  esac
  # Absolute server paths must never reach a client
  case "$BODY" in
    */var/www/*) REASON="server filesystem path leaked into the body"; return 1 ;;
  esac
  return 0
}

# ── Test forms ───────────────────────────────────────────────

# Body must contain "<key>": and must not be an error
has_key() {
  local label="$1" method="$2" url="$3" key="$4" data="$5" ctype="$6" accept="$7"
  request "$method" "$url" "$data" "$ctype" "$accept"
  if ! body_is_sane "$label"; then bad "$label" "$REASON"; return; fi
  case "$BODY" in
    *'"error"'*) bad "$label" "error: $(echo "$BODY" | head -c 140)"; return ;;
  esac
  case "$BODY" in
    *"\"$key\""*) ok "$label  → $key" ;;
    *) bad "$label" "no \"$key\" in: $(echo "$BODY" | head -c 140)" ;;
  esac
}

# Body must contain an exact expected fragment — catches silently wrong output
has_value() {
  local label="$1" method="$2" url="$3" want="$4" data="$5" ctype="$6" accept="$7"
  request "$method" "$url" "$data" "$ctype" "$accept"
  if ! body_is_sane "$label"; then bad "$label" "$REASON"; return; fi
  case "$BODY" in
    *"$want"*) ok "$label  = $want" ;;
    *) bad "$label" "expected [$want], got: $(echo "$BODY" | head -c 140)" ;;
  esac
}

# For endpoints with an open upstream bug. Reports, does not fail the build,
# and shouts if the bug ever goes away so the entry can be promoted.
known_bug() {
  local label="$1" method="$2" url="$3" want="$4" data="$5"
  request "$method" "$url" "$data"
  if body_is_sane "$label" && [ "${BODY#*$want}" != "$BODY" ]; then
    fixed "$label"
  else
    expected "$label"
  fi
}

echo ""
echo "============================================================"
echo " AI SENSE AS — Free Public REST API"
echo " $BASE"
echo "============================================================"
echo ""

# ── TIME ─────────────────────────────────────────────────────
echo -e "${YELLOW}⏱  Time${NC}"
has_key   "Datetime"                GET "$BASE/datetime"            "datetime"
has_value "Datetime (offset +0200)" GET "$BASE/datetime/+0200"      "+02:00"
has_value "Datetime (offset -0530)" GET "$BASE/datetime/-0530"      "-05:30"
has_key   "Timestamp"               GET "$BASE/timestamp"           "timestamp"
has_key   "Microtimestamp"          GET "$BASE/microtimestamp"      "microtimestamp"
has_key   "Timezones"               GET "$BASE/timezones"           "timezones"
has_value "Timezones (objects)"     GET "$BASE/timezones"           '{"timezone":'
has_value "Timezones (filtered)"    GET "$BASE/timezones/+0200"     '"offset":"+0200"'
has_key   "Swatch Internet Time"    GET "$BASE/swatchinternettime"  "beat"

# An hour-only offset is not a valid route. If this ever starts working the
# documentation is wrong, so assert the current contract explicitly.
request GET "$BASE/datetime/1"
case "$BODY" in
  '["'*']["'*) ok "Datetime (offset '1') correctly unrouted" ;;
  *) bad "Datetime (offset '1')" "now routes — API.md says only 4-digit offsets work" ;;
esac
echo ""

# ── RANDOM ───────────────────────────────────────────────────
echo -e "${YELLOW}🎲  Random${NC}"
has_key   "Random Number"           GET "$BASE/random_number"       "random_number"
has_value "Random Number (range)"   GET "$BASE/random_number/1/100" '"range":{"from":1,"to":100}'
has_value "Random Number (single)"  GET "$BASE/random_number/30"    '"to":30'
has_key   "Random Color"            GET "$BASE/random_color"        "random_color"

# Shape, not just presence. dechex() without padding returned "#111d1" for any
# value below 0x100000 — a key with a plausible-looking but invalid value, which
# is precisely the failure a has_key check waves through.
#
# This one has to be sampled, and sampling is probabilistic: the bad branch is
# hit on 1/16 of draws, so N samples miss a live bug with probability
# (15/16)^N. At 48 that is about 4.5%; at 20 it would be 27%, which is too
# likely to wave a regression through. Raise COLOR_SAMPLES if that is still not
# tight enough for your CI.
COLOR_SAMPLES=48
COLOR_BAD=0
for _ in $(seq 1 "$COLOR_SAMPLES"); do
  request GET "$BASE/random_color"
  C=$(echo "$BODY" | grep -o '"random_color":"#[0-9a-fA-F]*"' | grep -o '#[0-9a-fA-F]*')
  case "$C" in
    '#'??????) : ;;
    *) COLOR_BAD=$((COLOR_BAD + 1)); LAST_BAD="$C" ;;
  esac
done
if [ "$COLOR_BAD" -eq 0 ]; then
  ok "Random Color (6 hex digits, $COLOR_SAMPLES samples)"
else
  bad "Random Color (6 hex digits)" "$COLOR_BAD of $COLOR_SAMPLES malformed, e.g. [$LAST_BAD] — dechex() is not zero-padding"
fi
has_key   "UUID"                    GET "$BASE/uuid"                "uuid"
has_key   "GUID"                    GET "$BASE/guid"                "guid"
has_key   "Password"                GET "$BASE/password"            "password"
has_value "Password (length 16)"    GET "$BASE/password/16"         '"password_length":16'
echo ""

# ── TRANSFORM ────────────────────────────────────────────────
echo -e "${YELLOW}🔄  Transform${NC}"
has_value "Base64 Encode" POST "$BASE/base64_encode" '"base64_encoded_data":"SGVsbG8gd29ybGQ="' '{"data":"Hello world"}'
has_value "Base64 Decode" POST "$BASE/base64_decode" 'Hello world'                              '{"data":"SGVsbG8gd29ybGQ="}'
has_value "Base64 Decode (Accept json)" POST "$BASE/base64_decode" '"type":"json"' '{"data":"eyJrZXkiOiJ2YWx1ZSJ9"}' "application/json" "application/json"
has_value "Base58 Encode" POST "$BASE/base58_encode" '"base58_encoded_data":"9Ajdvzr"'          '{"data":"Hello"}'
has_value "Base58 Decode" POST "$BASE/base58_decode" 'Hello'                                    '{"data":"9Ajdvzr"}'
has_value "Base32 Encode" POST "$BASE/base32_encode" '"base32_encoded_data":"JBSWY3DP"'         '{"data":"Hello"}'
has_value "Base32 Decode" POST "$BASE/base32_decode" 'Hello'                                    '{"data":"JBSWY3DP"}'

# jwt_encode requires data to be a STRING. Assert the rejection too, because a
# client passing an object is the single most common mistake against this API.
has_key   "JWT Encode"          POST "$BASE/jwt_encode" "jwt"             '{"data":"{\"user\":\"alice\"}","secret":"s3cret"}'
has_value "JWT Encode (rejects object)" POST "$BASE/jwt_encode" "Expected a string" '{"data":{"user":"alice"},"secret":"s3cret"}'
has_value "JWT Decode"          POST "$BASE/jwt_decode" '"decoded_payload"' '{"data":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiYWxpY2UifQ.JkljdqTAf6ecEkEDPjNjlzj-sddlArcJogtn-ajE29E","secret":"s3cret"}'

has_key   "QR Encode"           POST "$BASE/qrcode_encode" "qrcode_image" '{"payload":"https://aisenseapi.com/"}'
has_value "QR Encode (image_type)" POST "$BASE/qrcode_encode" '"image_type":"png"' '{"payload":"test"}'
has_value "QR Encode (rejects data field)" POST "$BASE/qrcode_encode" "No payload" '{"data":"test"}'
echo ""

# ── QR ROUND TRIP ────────────────────────────────────────────
# Encoding can succeed and still produce an unscannable image. Only a decode
# proves the Reed-Solomon output is intact.
echo -e "${YELLOW}🔁  QR round trip${NC}"
request POST "$BASE/qrcode_encode" '{"payload":"https://aisenseapi.com/"}'
if body_is_sane "QR round trip"; then
  IMG=$(echo "$BODY" | grep -o '"qrcode_image":"[^"]*"' | sed 's/"qrcode_image":"//; s/"$//' | tr -d '\\')
  if [ -n "$IMG" ]; then
    printf '{"payload":"%s"}' "$IMG" > /tmp/aisense-qr-rt.json
    request POST "$BASE/qrcode_decode" "@/tmp/aisense-qr-rt.json"
    RT=$(curl -s -m 30 -X POST "$BASE/qrcode_decode" -H 'Content-Type: application/json' -d @/tmp/aisense-qr-rt.json | tr -d '\\')
    case "$RT" in
      *"https://aisenseapi.com/"*) ok "QR round trip  encode → decode preserves content" ;;
      *) bad "QR round trip" "decoded to: $(echo "$RT" | head -c 140)" ;;
    esac
    rm -f /tmp/aisense-qr-rt.json
  else
    bad "QR round trip" "no qrcode_image in encode response"
  fi
else
  bad "QR round trip" "$REASON"
fi
echo ""

# ── HASH ─────────────────────────────────────────────────────
# Exact digests. A hash endpoint that returns the right key with the wrong
# value is worse than one that is plainly down.
echo -e "${YELLOW}🔐  Hash${NC}"
has_value "MD5"    POST "$BASE/md5_hash"       '"md5_hash":"8b1a9953c4611296a827abf8c47804d7"' '{"data":"Hello"}'
has_value "SHA1"   POST "$BASE/sha1_hash"      '"sha1_hash":"f7ff9e8b7bb2e09b70935a5d785e0cc5d9d0abf0"' '{"data":"Hello"}'
has_value "SHA256" POST "$BASE/sha256_hash"    '"sha256_hash":"185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969"' '{"data":"Hello"}'
has_key   "SHA512" POST "$BASE/sha512_hash"    "sha512_hash" '{"data":"Hello"}'
has_value "CRC32"  POST "$BASE/crc32_checksum" '"crc32_checksum":4157704578' '{"data":"Hello"}'
has_value "SHA256 (text/plain)" POST "$BASE/sha256_hash" '"sha256_hash":"185f8db3' 'Hello' 'text/plain'
echo ""

# ── WEB ──────────────────────────────────────────────────────
echo -e "${YELLOW}🌐  Web${NC}"
has_value "Ping"       GET "$BASE/ping"          '"ping":"pong"'
has_value "Health"     GET "$BASE/health"        '"status":"ok"'
has_key   "Health (microtimestamp)" GET "$BASE/health" "microtimestamp"
has_key   "Client IP"  GET "$BASE/client_ip"     "ip"
has_key   "User Agent" GET "$BASE/user_agent"    "user_agent"
has_value "IP Lookup"  GET "$BASE/ip_reverse_lookup/8.8.8.8" '"country":"United States"'
has_key   "Domain Lookup" GET "$BASE/domain_ip_lookup/example.com" "ip"
echo ""

# ── STORAGE ROUND TRIP ───────────────────────────────────────
echo -e "${YELLOW}🗄  Storage round trip${NC}"
MARKER="test-$(date +%s)-$$"
request POST "$BASE/storage" "{\"marker\":\"$MARKER\"}"
SID=$(echo "$BODY" | grep -o '"storage_id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$SID" ]; then
  ok "Storage (store)  → $SID"
  # The body is stored verbatim, so the marker must come back unwrapped.
  has_value "Storage (retrieve)" GET "$BASE/storage/$SID" "\"marker\":\"$MARKER\""
  has_value "Storage (unknown id)" GET "$BASE/storage/00000000-0000-4000-8000-000000000000" "Storage id unknown"
else
  bad "Storage (store)" "no storage_id in: $(echo "$BODY" | head -c 140)"
fi
echo ""

# ── URL SHORTENER ────────────────────────────────────────────
echo -e "${YELLOW}🔗  URL shortener${NC}"
has_key "URL Shortener" GET "$BASE/url_shortener/https://example.com/some/long/path" "short_url"
echo ""

# ── WEBHOOK CAPTURE ROUND TRIP ───────────────────────────────
echo -e "${YELLOW}📡  Webhook capture round trip${NC}"
request POST "$BASE/webhook_capture" '{}'
CID=$(echo "$BODY" | grep -o '"capture_id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$CID" ]; then
  ok "Webhook Capture (create)  → $CID"
  curl -s -m 30 -o /dev/null -X POST "$BASE/webhook_capture/$CID/update" \
    -H 'Content-Type: application/json' -d "{\"marker\":\"$MARKER\"}"
  # The captured body must actually contain what we sent.
  has_value "Webhook Capture (read back)" GET "$BASE/webhook_capture/$CID" "$MARKER"
else
  bad "Webhook Capture (create)" "no capture_id in: $(echo "$BODY" | head -c 140)"
fi
echo ""

# ── WEBHOOK ACTION ───────────────────────────────────────────
echo -e "${YELLOW}📝  Webhook action${NC}"
request POST "$BASE/webhook_action" \
  '{"title":"Smoke test","fields":[{"type":"radio","name":"c","label":"Pick","options":[{"value":"y","label":"Yes"}]}]}'
AID=$(echo "$BODY" | grep -o '"action_id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$AID" ]; then
  ok "Webhook Action (create)  → $AID"
  has_value "Webhook Action (pending)" GET "$BASE/webhook_action/$AID" '"status":"pending"'
  # The form is HTML, not JSON — the only endpoint here that is.
  FORM_TYPE=$(curl -s -m 30 -o /dev/null -w '%{content_type}' "$BASE/webhook_action/$AID/form")
  case "$FORM_TYPE" in
    text/html*) ok "Webhook Action (form is HTML)" ;;
    *) bad "Webhook Action (form)" "content-type was $FORM_TYPE" ;;
  esac
else
  bad "Webhook Action (create)" "no action_id in: $(echo "$BODY" | head -c 140)"
fi
echo ""

# ── CRYPTO ───────────────────────────────────────────────────
echo -e "${YELLOW}🪙  Crypto${NC}"
has_key   "Solana Wallet"   GET "$BASE/solana/generate_new_wallet"   "public_address"
has_key   "Bitcoin Wallet"  GET "$BASE/bitcoin/generate_new_wallet"  "private_key_wif"
has_value "Bitcoin Wallet (public_address, not address)" GET "$BASE/bitcoin/generate_new_wallet" '"public_address"'
has_key   "Ethereum Wallet" GET "$BASE/ethereum/generate_new_wallet" "public_address"
has_key   "Bitcoin Balance"  GET "$BASE/bitcoin/balance/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  "final_balance_btc"
has_key   "Solana Balance"   GET "$BASE/solana/balance/So11111111111111111111111111111111111111112" "balance_sol"
has_key   "Ethereum Balance" GET "$BASE/ethereum/balance/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" "balance_wei"
# Wei must be a string — a JSON number loses precision above 2^53 in JS clients.
has_value "Ethereum Balance (wei is a string)" GET "$BASE/ethereum/balance/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" '"balance_wei":"'
echo ""

# ── UTILITY ENDPOINTS (added 2026-08-17) ─────────────────────
echo -e "${YELLOW}🧰  Utility endpoints${NC}"

# timestamp_convert: fixed vector so a timezone or off-by-1000 regression is
# caught by value, not by shape. 1700000000 is 2023-11-14T22:13:20+00:00.
has_value "Timestamp convert (unix)" POST "$BASE/timestamp_convert" '"datetime":"2023-11-14T22:13:20+00:00"' '{"data":"1700000000"}'
has_value "Timestamp convert (detects milliseconds)" POST "$BASE/timestamp_convert" '"detected":"unix_ms"' '{"data":"1700000000123"}'
has_value "Timestamp convert (ms divides to seconds)" POST "$BASE/timestamp_convert" '"timestamp":1700000000' '{"data":"1700000000123"}'
has_value "Timestamp convert (ISO back to unix)" POST "$BASE/timestamp_convert" '"timestamp":1700000000' '{"data":"2023-11-14T22:13:20+00:00"}'
has_value "Timestamp convert (offset +0100)" POST "$BASE/timestamp_convert" '"datetime":"2023-11-14T23:13:20+01:00"' '{"data":"1700000000","offset":"+0100"}'
request POST "$BASE/timestamp_convert" '{"data":"not a date"}'
[ "$STATUS" = "400" ] && ok "Timestamp convert (bad input -> 400)" || bad "Timestamp convert (bad input)" "expected 400, got $STATUS"

# email_validate: a failing address is a result, not an error.
has_value "Email validate (gmail.com has MX)" POST "$BASE/email_validate" '"has_mx":true' '{"data":"test@gmail.com"}'
has_value "Email validate (bad syntax is a result)" POST "$BASE/email_validate" '"valid_syntax":false' '{"data":"not-an-email"}'

# hash_verify: the tampered vector differs from the real digest in its final
# character, which is exactly the kind of mismatch eyeballs skip.
has_value "Hash verify (sha256 match)" POST "$BASE/hash_verify" '"match":true' '{"data":"Hello","hash":"185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969"}'
has_value "Hash verify (tampered digest)" POST "$BASE/hash_verify" '"match":false' '{"data":"Hello","hash":"185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381970"}'
has_value "Hash verify (integer crc32)" POST "$BASE/hash_verify" '"algorithm":"crc32"' '{"data":"Hello","hash":4157704578}'
request POST "$BASE/hash_verify" '{"data":"Hello","hash":"abc123"}'
[ "$STATUS" = "400" ] && ok "Hash verify (unknown length -> 400)" || bad "Hash verify (unknown length)" "expected 400, got $STATUS"

# slugify: the Scandinavian vector is sent as explicit UTF-8 bytes from a
# file, because Windows shells mangle multibyte characters on the command
# line and the test must not depend on the terminal's encoding.
has_value "Slugify (ascii)" POST "$BASE/slugify" '"slug":"hello-world"' '{"data":"Hello World"}'
printf '{"data":"Bl\xc3\xa5b\xc3\xa6rsyltet\xc3\xb8y p\xc3\xa5 \xc3\x85s!"}' > /tmp/aisense-slug-test.json
SLUG_RAW=$(curl -s -m 30 -X POST "$BASE/slugify" -H 'Content-Type: application/json' --data-binary @/tmp/aisense-slug-test.json)
rm -f /tmp/aisense-slug-test.json
case "$SLUG_RAW" in
  *'"slug":"blabaersyltetoy-pa-as"'*) ok "Slugify (transliterates aa ae oe)" ;;
  *) bad "Slugify (transliterates aa ae oe)" "got: $(echo "$SLUG_RAW" | head -c 120)" ;;
esac
request POST "$BASE/slugify" '{"data":"!!! ???"}'
[ "$STATUS" = "400" ] && ok "Slugify (nothing sluggable -> 400)" || bad "Slugify (nothing sluggable)" "expected 400, got $STATUS"
echo ""

# ── WEBHOOK SCHEDULE + VALIDATE (added 2026-08-17) ───────────
echo -e "${YELLOW}⏰  Webhook schedule + validate${NC}"

# The full fire loop takes a cron cycle (~60s), too slow for this suite - it is
# verified separately. Here: creation returns a scheduled job, the status shape
# is right, and every SSRF and bounds guard refuses as designed. The guards are
# the part that matters; a scheduler that fires internal addresses is a weapon.
has_value "Webhook schedule (create)" POST "$BASE/webhook_schedule" '"status":"scheduled"' '{"url":"https://example.com/hook","delay_seconds":60}'
request POST "$BASE/webhook_schedule" '{"url":"http://169.254.169.254/latest/meta-data/","delay_seconds":60}'
[ "$STATUS" = "400" ] && ok "Webhook schedule refuses cloud metadata IP" || bad "Webhook schedule (metadata IP)" "expected 400, got $STATUS"
request POST "$BASE/webhook_schedule" '{"url":"http://127.0.0.1/","delay_seconds":60}'
[ "$STATUS" = "400" ] && ok "Webhook schedule refuses loopback" || bad "Webhook schedule (loopback)" "expected 400, got $STATUS"
request POST "$BASE/webhook_schedule" '{"url":"http://10.0.0.1/","delay_seconds":60}'
[ "$STATUS" = "400" ] && ok "Webhook schedule refuses private range" || bad "Webhook schedule (private range)" "expected 400, got $STATUS"
request POST "$BASE/webhook_schedule" '{"url":"http://user:pass@example.com/","delay_seconds":60}'
[ "$STATUS" = "400" ] && ok "Webhook schedule refuses URL credentials" || bad "Webhook schedule (userinfo)" "expected 400, got $STATUS"
request POST "$BASE/webhook_schedule" '{"url":"https://example.com/","delay_seconds":2}'
[ "$STATUS" = "400" ] && ok "Webhook schedule refuses sub-5s delay" || bad "Webhook schedule (too soon)" "expected 400, got $STATUS"
request POST "$BASE/webhook_schedule" '{"url":"https://example.com/","delay_seconds":90000}'
[ "$STATUS" = "400" ] && ok "Webhook schedule refuses beyond 24h" || bad "Webhook schedule (too far)" "expected 400, got $STATUS"

# validate: fixed vectors with genuine check digits.
has_value "Validate IBAN (valid NO)" POST "$BASE/validate/iban" '"valid":true' '{"data":"NO9386011117947"}'
has_value "Validate IBAN (bad checksum)" POST "$BASE/validate/iban" '"checksum_ok":false' '{"data":"NO9386011117940"}'
has_value "Validate card (Luhn ok)" POST "$BASE/validate/card" '"luhn_ok":true' '{"data":"4111111111111111"}'
has_value "Validate card (Luhn fail)" POST "$BASE/validate/card" '"valid":false' '{"data":"4111111111111112"}'
# The card endpoint must never reflect the number back.
request POST "$BASE/validate/card" '{"data":"4111111111111111"}'
case "$BODY" in *4111111111111111*) bad "Validate card (no echo)" "the card number was reflected in the response" ;; *) ok "Validate card (number never echoed)" ;; esac
has_value "Validate orgnr (AI SENSE, MOD11)" POST "$BASE/validate/orgnr" '"valid":true' '{"data":"NO 922 601 151 MVA"}'
has_value "Validate orgnr (bad check digit)" POST "$BASE/validate/orgnr" '"valid":false' '{"data":"922601152"}'
has_value "Validate kontonummer (MOD11)" POST "$BASE/validate/kontonummer" '"valid":true' '{"data":"1234.56.78903"}'
has_value "Validate phone (E.164 from 00)" POST "$BASE/validate/phone" '"e164":"+4740000000"' '{"data":"004740000000"}'
request POST "$BASE/validate/nonsense" '{"data":"x"}'
[ "$STATUS" = "400" ] && ok "Validate (unknown type -> 400)" || bad "Validate (unknown type)" "expected 400, got $STATUS"
echo ""

# ── MCP ──────────────────────────────────────────────────────
# The MCP server lives at /mcp, outside /services/v1, speaking JSON-RPC 2.0
# over POST. Documented in MCP.md and registered as
# io.github.aisenseapi/free-public-tools, so this section is what keeps those
# two documents honest the same way the sections above keep API.md honest.
echo -e "${YELLOW}🔌  MCP server${NC}"
MCP_BASE="${AISENSE_MCP_BASE:-https://aisenseapi.com/mcp}"

# mcp_post <json-body> [MCP-Protocol-Version] [accept] [mcp-method]
# "accept" as the third argument sends the streamable-http Accept header, and
# a fourth argument sends it as the MCP-Method header. 2026-07-28 requires
# both; the older protocol versions require neither.
mcp_post() {
  local body="$1" ver="$2" accept="$3" method="$4"
  local args=(-s -m 30 -w '\n%{http_code}' -X POST "$MCP_BASE" -H 'Content-Type: application/json')
  [ -n "$ver" ] && args+=(-H "MCP-Protocol-Version: $ver")
  [ "$accept" = "accept" ] && args+=(-H 'Accept: application/json, text/event-stream')
  [ -n "$method" ] && args+=(-H "MCP-Method: $method")
  RAW=$(curl "${args[@]}" -d "$body")
  STATUS="${RAW##*$'\n'}"
  BODY="${RAW%$'\n'*}"
}

mcp_expect() {
  local label="$1" want="$2"
  case "$BODY" in
    *"$want"*) ok "$label" ;;
    *) bad "$label" "expected [$want] in: $(echo "$BODY" | head -c 140)" ;;
  esac
}

mcp_post '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test.sh","version":"1.0"}}}'
mcp_expect "MCP initialize (2025-11-25)" '"serverInfo"'

# Nine tools, exactly. MCP.md and web/free-public-mcp-server.html both say
# nine, so a tenth tool must land in all three places in the same commit.
mcp_post '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' '2025-11-25'
MCP_TOOLS=$(echo "$BODY" | grep -o '"name":"[a-z_]*"' | sort -u | wc -l)
if [ "$MCP_TOOLS" -eq 9 ]; then
  ok "MCP tools/list (exactly 9 tools)"
else
  bad "MCP tools/list" "found $MCP_TOOLS tools, expected 9 - update MCP.md and the web page together with this number"
fi

# 2026-07-28 enforces three contracts, checked in a fixed order: the
# streamable-http Accept header must name both content types, the version in
# the header must agree with _meta in the body, and an MCP-Method header must
# match the JSON-RPC method. Each rung is asserted on its own, because each is
# a mistake a client can make in isolation and the error message differs.
mcp_post '{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}}' '2026-07-28'
mcp_expect "MCP 2026-07-28 without Accept -> -32020" '-32020'
mcp_post '{"jsonrpc":"2.0","id":4,"method":"tools/list","params":{}}' '2026-07-28' accept
mcp_expect "MCP 2026-07-28 without _meta -> -32022" '-32022'
mcp_post '{"jsonrpc":"2.0","id":5,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28"}}}' '2026-07-28' accept
mcp_expect "MCP 2026-07-28 without MCP-Method header" 'Mcp-Method does not match'
mcp_post '{"jsonrpc":"2.0","id":6,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28"}}}' '2026-07-28' accept 'tools/list'
mcp_expect "MCP tools/list (2026-07-28, all three)" '"get_current_time"'

mcp_post '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_current_time","arguments":{}}}' '2025-11-25'
mcp_expect "MCP call get_current_time" 'datetime'
mcp_post '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"generate_uuid","arguments":{}}}' '2025-11-25'
mcp_expect "MCP call generate_uuid" '"structuredContent"'

# Round trip through the storage tools: what goes in must come back out.
MCP_MARK="mcp-rt-$(date +%s)-$$"
mcp_post "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"store_temporary_data\",\"arguments\":{\"data\":\"$MCP_MARK\"}}}" '2025-11-25'
MCP_SID=$(echo "$BODY" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
if [ -n "$MCP_SID" ]; then
  ok "MCP store_temporary_data"
  mcp_post "{\"jsonrpc\":\"2.0\",\"id\":8,\"method\":\"tools/call\",\"params\":{\"name\":\"read_temporary_data\",\"arguments\":{\"storage_id\":\"$MCP_SID\"}}}" '2025-11-25'
  mcp_expect "MCP read_temporary_data (round trip)" "$MCP_MARK"
else
  bad "MCP store_temporary_data" "no storage_id in: $(echo "$BODY" | head -c 140)"
fi

# Error signalling: tool failures are results with isError, protocol failures
# are JSON-RPC errors. Implementations mix these up constantly; this one does
# not, and the distinction is load-bearing for clients.
mcp_post '{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"no_such_tool","arguments":{}}}' '2025-11-25'
mcp_expect "MCP unknown tool -> isError:true" '"isError":true'
mcp_post '{"jsonrpc":"2.0","id":10,"method":"no/such_method","params":{}}' '2025-11-25'
mcp_expect "MCP unknown method -> -32601" '-32601'

# Verbs: POST only, OPTIONS for CORS preflight.
MCP_GET=$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$MCP_BASE")
[ "$MCP_GET" = "405" ] && ok "MCP GET -> 405" || bad "MCP GET" "expected 405, got $MCP_GET"
MCP_OPT=$(curl -s -m 15 -o /dev/null -w '%{http_code}' -X OPTIONS "$MCP_BASE")
[ "$MCP_OPT" = "204" ] && ok "MCP OPTIONS -> 204" || bad "MCP OPTIONS" "expected 204, got $MCP_OPT"
echo ""

# ── SERVICE-WIDE CONTRACTS ───────────────────────────────────
echo -e "${YELLOW}📋  Service-wide contracts${NC}"
# Document the unknown-path behaviour rather than pretending it is a 404.
request GET "$BASE/this_endpoint_does_not_exist"
case "$BODY" in
  '["'*']["'*) expected "Unknown path returns 200 + debug echo instead of 404" ;;
  *) fixed "Unknown path no longer returns the debug echo" ;;
esac
echo ""

# ── SUMMARY ──────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo "============================================================"
echo -e " ${GREEN}$PASS passed${NC} / ${RED}$FAIL failed${NC} / $TOTAL asserted"
[ "$XFAIL" -gt 0 ] && echo -e " ${BLUE}$XFAIL known bug(s)${NC} reported, not counted as failures"
[ "$FIXED" -gt 0 ] && echo -e " ${GREEN}$FIXED known bug(s) now FIXED${NC} — promote them to real assertions"
echo "============================================================"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
