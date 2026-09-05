"""
aisense_api.py — Python client for the AI SENSE AS Free Public REST APIs
https://aisenseapi.com

No dependencies beyond the standard library (uses urllib).

Usage:
    from aisense_api import AISenseAPI
    api = AISenseAPI()
    print(api.get_uuid()["uuid"])
    print(api.hash_sha256("Hello")["sha256_hash"])

Every method returns the parsed JSON response as a dict, and each docstring
names the exact response key. The upstream API is not consistent about
naming — /md5_hash returns "md5_hash", /ping returns "ping", /random_color
returns "random_color" — so do not guess the key.

Two endpoints return raw bytes instead of JSON (base64_decode and
base32_decode). Those methods return str when the payload is valid UTF-8,
and bytes otherwise.

Known upstream bugs, verified against production:
  * /base58_decode always fails with "Invalid Base32 input." — it cannot
    decode the output of /base58_encode. base58_decode() raises
    AISenseAPIError until the server is fixed.
  * /qrcode_encode prepends a PHP warning to its JSON body. This client
    strips it and records it in `last_server_notice`.
  * /ethereum/balance returns "Failed to retrieve balance data."
  * Unknown paths return HTTP 200 with a debug echo instead of 404. This
    client detects that and raises AISenseAPIError.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Optional, Union

BASE_URL = "https://aisenseapi.com/services/v1"

# Unknown paths do not 404 — they return HTTP 200 with a body shaped like
#   ["<your-ip>",1786873281]["\/services\/v1\/random","1","random"]
# Detecting it turns a confusing JSON parse error into a clear message.
_DEBUG_ECHO_PREFIX = '["'
_DEBUG_ECHO_MARKER = '"]["'


class AISenseAPIError(RuntimeError):
    """Raised when the API reports an error or returns an unusable response."""

    def __init__(self, message: str, *, status: Optional[int] = None, body: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.body = body


class AISenseAPI:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        #: Set when the server prepends a PHP warning to a JSON response
        #: (currently /qrcode_encode). None when the last call was clean.
        self.last_server_notice: Optional[str] = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _read(self, path: str, method: str, payload: Any = None, content_type: str = "application/json"):
        url = f"{self.base_url}{path}"
        data = None
        headers = {}
        if method == "POST":
            data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            headers["Content-Type"] = content_type

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.headers.get("Content-Type", ""), resp.read()
        except urllib.error.HTTPError as err:
            # The API returns 400 with a JSON error body for some endpoints —
            # read it rather than letting urllib swallow the reason.
            return err.code, err.headers.get("Content-Type", ""), err.read()

    def _request(self, path: str, method: str = "GET", payload: Any = None) -> dict:
        status, _content_type, raw = self._read(path, method, payload)
        text = raw.decode("utf-8", "replace")

        if text.startswith(_DEBUG_ECHO_PREFIX) and _DEBUG_ECHO_MARKER in text:
            raise AISenseAPIError(
                f"{method} {path} is not a known endpoint — the API answered with its "
                f"debug echo instead of a 404. Check the path against API.md.",
                status=status,
                body=text[:200],
            )

        body, self.last_server_notice = _strip_server_notice(text)

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as err:
            raise AISenseAPIError(
                f"{method} {path} returned a body that is not JSON: {body[:200]!r}",
                status=status,
                body=text[:500],
            ) from err

        if isinstance(parsed, dict) and "error" in parsed:
            raise AISenseAPIError(
                f"{method} {path} failed: {parsed['error']}", status=status, body=text[:500]
            )
        if status >= 400:
            raise AISenseAPIError(f"{method} {path} failed with HTTP {status}", status=status, body=text[:500])

        return parsed

    def _request_binary(self, path: str, payload: Any) -> Union[str, bytes]:
        """For endpoints that answer with application/octet-stream, not JSON."""
        status, _content_type, raw = self._read(path, "POST", payload)
        text = raw.decode("utf-8", "replace")

        if text.startswith(_DEBUG_ECHO_PREFIX) and _DEBUG_ECHO_MARKER in text:
            raise AISenseAPIError(f"POST {path} is not a known endpoint.", status=status, body=text[:200])

        # Errors still come back as JSON even though success is raw bytes.
        if text.lstrip().startswith("{"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict) and "error" in parsed:
                raise AISenseAPIError(f"POST {path} failed: {parsed['error']}", status=status, body=text[:500])

        if status >= 400:
            raise AISenseAPIError(f"POST {path} failed with HTTP {status}", status=status, body=text[:500])

        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw

    def _get(self, path: str) -> dict:
        return self._request(path, "GET")

    def _post(self, path: str, payload: Any) -> dict:
        return self._request(path, "POST", payload)

    def _delete(self, path: str) -> dict:
        return self._request(path, "DELETE")

    # ── Time ──────────────────────────────────────────────────────────────────

    def get_datetime(self, offset: Optional[str] = None) -> dict:
        """Current datetime in ISO 8601. Response key: ``datetime``.

        ``offset`` must be a four-digit UTC offset such as ``"+0200"``,
        ``"-0530"`` or ``"0100"``. Hour-only values like ``"1"`` are NOT
        accepted by the API and resolve to an unknown path.
        """
        path = f"/datetime/{offset}" if offset is not None else "/datetime"
        return self._get(path)

    def get_timestamp(self) -> dict:
        """Current Unix timestamp in seconds. Response key: ``timestamp``."""
        return self._get("/timestamp")

    def get_microtimestamp(self) -> dict:
        """Unix timestamp with microsecond precision. Response key: ``microtimestamp``."""
        return self._get("/microtimestamp")

    def get_timezones(self, offset: Optional[str] = None) -> dict:
        """All timezones, optionally filtered by a four-digit offset (``"+0200"``).

        Response key: ``timezones`` — a list of ``{"timezone": ..., "offset": ...}``
        objects, not a list of strings.
        """
        path = f"/timezones/{offset}" if offset is not None else "/timezones"
        return self._get(path)

    def get_swatch_time(self) -> dict:
        """Swatch Internet Time. Response keys: ``beat`` (e.g. ``"@444"``) and ``date``."""
        return self._get("/swatchinternettime")

    # ── Random ────────────────────────────────────────────────────────────────

    def get_random_number(self, from_: Optional[int] = None, to: Optional[int] = None) -> dict:
        """Random integer. Response keys: ``random_number`` and ``range``.

        No arguments defaults to 1–6. A single argument is treated by the API
        as the upper bound, with the lower bound fixed at 1.
        """
        if from_ is None:
            path = "/random_number"
        elif to is None:
            path = f"/random_number/{from_}"
        else:
            path = f"/random_number/{from_}/{to}"
        return self._get(path)

    def get_random_color(self) -> dict:
        """Random hex colour. Response key: ``random_color``."""
        return self._get("/random_color")

    def get_uuid(self) -> dict:
        """Generate a UUID v4. Response key: ``uuid``."""
        return self._get("/uuid")

    def get_guid(self) -> dict:
        """Generate a GUID. Response key: ``guid``."""
        return self._get("/guid")

    def get_password(self, length: Optional[int] = None) -> dict:
        """Random password, 12 characters by default.

        Response keys: ``password`` and ``password_length``.
        """
        path = f"/password/{length}" if length is not None else "/password"
        return self._get(path)

    # ── Transform ─────────────────────────────────────────────────────────────

    def base64_encode(self, data: str) -> dict:
        """Response key: ``base64_encoded_data``."""
        return self._post("/base64_encode", {"data": data})

    def base64_decode(self, data: str) -> Union[str, bytes]:
        """Decode Base64, returning the payload directly as ``str`` or ``bytes``.

        This client deliberately sends no ``Accept`` header, which makes the
        endpoint answer with ``application/octet-stream`` — the decoded bytes
        and nothing else. Send ``Accept: application/json`` instead and the same
        endpoint wraps the result as ``{"type": "json"|"binary", "decoded_data": ...}``,
        base64-re-encoding the payload in the binary case. Raw is the more
        useful default; use the JSON form when you need the type tag.
        """
        return self._request_binary("/base64_decode", {"data": data})

    def base58_encode(self, data: str) -> dict:
        """Response key: ``base58_encoded_data``."""
        return self._post("/base58_encode", {"data": data})

    def base58_decode(self, data: str) -> Union[str, bytes]:
        """Decode Base58.

        BROKEN UPSTREAM: the server validates the input with its Base32 decoder
        and rejects everything with "Invalid Base32 input." — including strings
        produced by :meth:`base58_encode`. This will raise ``AISenseAPIError``
        until the server is fixed. Kept here so the bug stays visible.
        """
        return self._request_binary("/base58_decode", {"data": data})

    def base32_encode(self, data: str) -> dict:
        """Response key: ``base32_encoded_data``."""
        return self._post("/base32_encode", {"data": data})

    def base32_decode(self, data: str) -> Union[str, bytes]:
        """Decode Base32. Answers with raw bytes, not JSON — see :meth:`base64_decode`."""
        return self._request_binary("/base32_decode", {"data": data})

    def jwt_encode(self, payload: Union[dict, str], secret: str) -> dict:
        """Encode a payload into an HS256 JWT. Response key: ``jwt``.

        The API requires ``data`` to be a *string*. A dict is serialised to
        JSON here; passing a dict straight through returns
        "Invalid data provided. Expected a string."
        """
        data = payload if isinstance(payload, str) else json.dumps(payload)
        return self._post("/jwt_encode", {"data": data, "secret": secret})

    def jwt_decode(self, token: str, secret: str) -> dict:
        """Decode a JWT. Response key: ``decoded_payload``."""
        return self._post("/jwt_decode", {"data": token, "secret": secret})

    def qrcode_encode(self, payload: str) -> dict:
        """Generate a QR code. Response keys: ``qrcode_image`` (Base64 PNG) and ``image_type``.

        The request field is ``payload``, not ``data``.

        The server currently prepends a PHP warning to the JSON body because it
        cannot write a temp file. This client strips it; inspect
        ``last_server_notice`` to see whether it fired.
        """
        return self._post("/qrcode_encode", {"payload": payload})

    def qrcode_decode(self, image_base64: str) -> dict:
        """Decode a Base64-encoded QR code image. Response key: ``qrcode_content``.

        The request field is ``payload``, not ``data``.
        """
        return self._post("/qrcode_decode", {"payload": image_base64})

    # ── Hash ──────────────────────────────────────────────────────────────────

    def hash_md5(self, data: str) -> dict:
        """Response key: ``md5_hash``."""
        return self._post("/md5_hash", {"data": data})

    def hash_sha1(self, data: str) -> dict:
        """Response key: ``sha1_hash``."""
        return self._post("/sha1_hash", {"data": data})

    def hash_sha256(self, data: str) -> dict:
        """Response key: ``sha256_hash``."""
        return self._post("/sha256_hash", {"data": data})

    def hash_sha512(self, data: str) -> dict:
        """Response key: ``sha512_hash``."""
        return self._post("/sha512_hash", {"data": data})

    def crc32_checksum(self, data: str) -> dict:
        """CRC32 checksum. Response key: ``crc32_checksum`` — an integer, not a hex string."""
        return self._post("/crc32_checksum", {"data": data})

    # ── Web ───────────────────────────────────────────────────────────────────

    def ping(self) -> dict:
        """Connectivity check. Response key: ``ping`` (value ``"pong"``)."""
        return self._get("/ping")

    def health(self) -> dict:
        """Health check. Response keys: ``status`` and ``microtimestamp``."""
        return self._get("/health")

    def get_client_ip(self) -> dict:
        """Your public IP address. Response key: ``ip``."""
        return self._get("/client_ip")

    def get_user_agent(self) -> dict:
        """The User-Agent string the API saw. Response key: ``user_agent``."""
        return self._get("/user_agent")

    def ip_reverse_lookup(self, ip: str) -> dict:
        """Reverse IP lookup.

        Response keys: ``ip``, ``country``, ``city``, ``location`` (``lat``/``lng``),
        ``place``, ``timezone``. ``city`` and ``place`` are often ``null``.
        """
        return self._get(f"/ip_reverse_lookup/{ip}")

    def domain_ip_lookup(self, domain: str) -> dict:
        """Resolve a domain to an IP. Response keys: ``domain`` and ``ip``."""
        return self._get(f"/domain_ip_lookup/{domain}")

    def storage_set(self, data: Any) -> dict:
        """Store data for 24 hours. Response keys: ``storage_id`` and ``expire_timestamp``.

        The request body is stored verbatim, so whatever you pass here is
        exactly what :meth:`storage_get` gives back — no ``data`` wrapper is
        added or removed.
        """
        return self._post("/storage", data)

    def storage_get(self, storage_id: str) -> dict:
        """Retrieve stored data by its ``storage_id``, returned verbatim."""
        return self._get(f"/storage/{storage_id}")

    def shorten_url(self, url: str) -> dict:
        """Shorten a URL for 24 hours. Response keys: ``short_url`` and ``expire_timestamp``.

        This is a GET with the target URL inline in the path — not a POST.
        """
        return self._get(f"/url_shortener/{url}")

    def webhook_capture_create(self, notify_url: Optional[str] = None) -> dict:
        """Open a capture session.

        Response keys: ``ok``, ``capture_id``, ``update_url``, ``read_url``,
        ``expire_timestamp``. Point any HTTP client at ``update_url``, then read
        it back with :meth:`webhook_capture_read`.
        """
        body = {}
        if notify_url is not None:
            body["notify_url"] = notify_url
        return self._post("/webhook_capture", body)

    def webhook_capture_read(self, capture_id: str, wait_seconds: Optional[int] = None) -> dict:
        """Read a captured request.

        Response keys: ``ok``, ``capture_id``, ``captured_at_timestamp``,
        ``captured_at_datetime``, ``request``.
        """
        suffix = "" if wait_seconds is None else f"/wait/{wait_seconds}"
        return self._get(f"/webhook_capture/{capture_id}{suffix}")

    def webhook_action_create(
        self,
        title: str,
        fields: list,
        description: Optional[str] = None,
        respondents: Optional[int] = None,
        notify_url: Optional[str] = None,
    ) -> dict:
        """Create a human-in-the-loop action form.

        Response keys: ``ok``, ``action_id``, ``form_url``, ``result_url``,
        ``expire_timestamp``, ``expire_datetime``.

        ``fields`` example — ``options`` accepts either plain strings or
        ``{"value": ..., "label": ...}`` objects::

            [{"type": "radio", "name": "decision", "label": "Approve?",
              "required": True,
              "options": [{"value": "yes", "label": "Yes"},
                          {"value": "no", "label": "No"}]}]

        Field types: radio, select, text, textarea, checkbox.
        """
        body: dict = {"title": title, "fields": fields}
        if description is not None:
            body["description"] = description
        if respondents is not None:
            body["respondents"] = respondents
        if notify_url is not None:
            body["notify_url"] = notify_url
        return self._post("/webhook_action", body)

    def webhook_action_result(self, action_id: str, wait_seconds: Optional[int] = None) -> dict:
        """Poll for the answer to an action.

        Response keys: ``ok``, ``action_id``, ``status`` (``"pending"`` or
        ``"answered"``), ``created_at_timestamp``, ``created_at_datetime``,
        ``expire_timestamp``, ``expire_datetime``, ``answered_at_timestamp``,
        ``answered_at_datetime``, ``response``.
        """
        suffix = "" if wait_seconds is None else f"/wait/{wait_seconds}"
        return self._get(f"/webhook_action/{action_id}{suffix}")

    def webhook_schedule_create(
        self,
        url: str,
        *,
        delay_seconds: Optional[int] = None,
        fire_at: Optional[int] = None,
        payload: Any = None,
        every: Optional[int] = None,
    ) -> dict:
        """Create a one-shot or recurring webhook schedule."""
        body: dict = {"url": url}
        if delay_seconds is not None:
            body["delay_seconds"] = delay_seconds
        if fire_at is not None:
            body["fire_at"] = fire_at
        if payload is not None:
            body["payload"] = payload
        if every is not None:
            body["every"] = every
        return self._post("/webhook_schedule", body)

    def webhook_schedule_read(self, schedule_id: str, wait_seconds: Optional[int] = None) -> dict:
        """Read a schedule, or wait up to 25 seconds for a state change."""
        suffix = "" if wait_seconds is None else f"/wait/{wait_seconds}"
        return self._get(f"/webhook_schedule/{schedule_id}{suffix}")

    def webhook_schedule_cancel(self, schedule_id: str) -> dict:
        """Cancel a schedule that has not reached a terminal state."""
        return self._delete(f"/webhook_schedule/{schedule_id}")

    def agent_wake_create(self, event_type: str, **options: Any) -> dict:
        """Create a durable webhook, human or time Agent Wake task."""
        return self._post("/agent_wake", {"event_type": event_type, **options})

    def agent_wake_read(self, task_id: str, wait_seconds: Optional[int] = None) -> dict:
        """Read an Agent Wake task, or wait up to 25 seconds for completion."""
        suffix = "" if wait_seconds is None else f"/wait/{wait_seconds}"
        return self._get(f"/agent_wake/{task_id}{suffix}")

    def agent_wake_cancel(self, task_id: str) -> dict:
        """Cancel a waiting Agent Wake task."""
        return self._delete(f"/agent_wake/{task_id}")

    def heartbeat_create(
        self,
        expect_every_seconds: int,
        on_miss: dict,
        grace_seconds: int = 0,
    ) -> dict:
        """Create a Heartbeat that fires once when check-ins stop."""
        return self._post(
            "/heartbeat",
            {
                "expect_every_seconds": expect_every_seconds,
                "grace_seconds": grace_seconds,
                "on_miss": on_miss,
            },
        )

    def heartbeat_read(self, heartbeat_id: str) -> dict:
        """Read Heartbeat state."""
        return self._get(f"/heartbeat/{heartbeat_id}")

    def heartbeat_ping(self, heartbeat_id: str) -> dict:
        """Check in with a Heartbeat."""
        return self._post(f"/heartbeat/{heartbeat_id}/ping", {})

    def lease_create_namespace(self) -> dict:
        """Mint a bearer namespace for readable lease keys."""
        return self._post("/lease/namespace", {})

    def lease_acquire(self, **options: Any) -> dict:
        """Acquire a lease. The returned owner token is needed for owner actions."""
        return self._post("/lease/acquire", options)

    def lease_renew(
        self,
        namespace: str,
        key: str,
        owner_token: str,
        ttl_seconds: int,
    ) -> dict:
        return self._post(
            "/lease/renew",
            {
                "namespace": namespace,
                "key": key,
                "owner_token": owner_token,
                "ttl_seconds": ttl_seconds,
            },
        )

    def lease_release(self, namespace: str, key: str, owner_token: str) -> dict:
        return self._post(
            "/lease/release",
            {"namespace": namespace, "key": key, "owner_token": owner_token},
        )

    def lease_complete(self, namespace: str, key: str, owner_token: str, result: Any) -> dict:
        return self._post(
            "/lease/complete",
            {
                "namespace": namespace,
                "key": key,
                "owner_token": owner_token,
                "result": result,
            },
        )

    # ── Crypto ────────────────────────────────────────────────────────────────

    def generate_solana_wallet(self) -> dict:
        """New Solana wallet. Response keys: ``private_key``, ``public_address``.

        FOR DEVELOPMENT ONLY — never fund a wallet generated over a public API.
        """
        return self._get("/solana/generate_new_wallet")

    def generate_bitcoin_wallet(self) -> dict:
        """New Bitcoin wallet. Response keys: ``private_key``, ``private_key_wif``, ``public_address``.

        FOR DEVELOPMENT ONLY.
        """
        return self._get("/bitcoin/generate_new_wallet")

    def generate_ethereum_wallet(self) -> dict:
        """New Ethereum wallet. Response keys: ``private_key``, ``public_address``.

        FOR DEVELOPMENT ONLY.
        """
        return self._get("/ethereum/generate_new_wallet")

    def solana_balance(self, address: str) -> dict:
        """Response keys: ``wallet``, ``balance_sol``, ``balance_lamports``."""
        return self._get(f"/solana/balance/{address}")

    def bitcoin_balance(self, address: str) -> dict:
        """Response keys: ``wallet``, ``final_balance_btc``, ``final_balance_sats``."""
        return self._get(f"/bitcoin/balance/{address}")

    def ethereum_balance(self, address: str) -> dict:
        """Ethereum balance.

        BROKEN UPSTREAM: currently answers "Failed to retrieve balance data."
        for every address, so this raises ``AISenseAPIError``.
        """
        return self._get(f"/ethereum/balance/{address}")


def _strip_server_notice(text: str):
    """Split a leading PHP warning off a JSON body.

    /qrcode_encode emits a ``Warning: file_put_contents(...)`` line before its
    JSON because the QR library cannot write its temp file. Returns
    ``(json_text, notice_or_None)``.
    """
    stripped = text.lstrip()
    if stripped[:1] in "{[":
        return stripped, None
    brace = text.find("{")
    if brace == -1:
        return stripped, None
    return text[brace:], text[:brace].strip()


# ── Example usage ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    api = AISenseAPI()

    print("=== Time ===")
    print(api.get_datetime(offset="+0200")["datetime"])
    print(api.get_timestamp()["timestamp"])

    print("\n=== Random ===")
    print(api.get_uuid()["uuid"])
    print(api.get_random_color()["random_color"])
    print(api.get_random_number(1, 100)["random_number"])
    print(api.get_password(16)["password"])

    print("\n=== Transform ===")
    encoded = api.base64_encode("Hello, world!")["base64_encoded_data"]
    print("Base64 encoded:", encoded)
    print("Base64 decoded:", api.base64_decode(encoded))

    token = api.jwt_encode({"user": "alice"}, secret="my-secret")["jwt"]
    print("JWT:", token)
    print("JWT decoded:", api.jwt_decode(token, secret="my-secret")["decoded_payload"])

    print("\n=== Hash ===")
    print(api.hash_sha256("Hello")["sha256_hash"])
    print(api.crc32_checksum("Hello")["crc32_checksum"])

    print("\n=== Web ===")
    print(api.ping()["ping"])
    print(api.get_client_ip()["ip"])
    print(api.ip_reverse_lookup("8.8.8.8")["country"])

    stored = api.storage_set({"hello": "world"})
    print("Stored:", stored["storage_id"])
    print("Retrieved:", api.storage_get(stored["storage_id"]))

    print("\n=== Crypto (dev only) ===")
    print(api.generate_ethereum_wallet()["public_address"])

    print("\n=== Known upstream bugs ===")
    try:
        api.base58_decode(api.base58_encode("Hello")["base58_encoded_data"])
    except AISenseAPIError as err:
        print("base58_decode still broken:", err)

    api.qrcode_encode("https://aisenseapi.com/")
    if api.last_server_notice:
        print("qrcode_encode still leaking a PHP warning:", api.last_server_notice[:80], "...")
