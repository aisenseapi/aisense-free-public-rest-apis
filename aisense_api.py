"""
aisense_api.py: Python client for the AI SENSE AS Free Public REST APIs
https://aisenseapi.com

No dependencies beyond the standard library (uses urllib). There is no account.
Most requests need nothing beyond the path and, for POST endpoints, the body.
Agent Queue calls also carry the queue's role token, which this client sends as
an Authorization header and never puts in a URL.

Usage:
    from aisense_api import AISenseAPI
    api = AISenseAPI()
    print(api.get_uuid()["uuid"])
    print(api.hash_sha256("Hello")["sha256_hash"])

Every method returns the parsed JSON response as a dict, and each docstring
names the exact response key. The upstream API is not consistent about
naming. /md5_hash returns "md5_hash", /ping returns "ping" and /random_color
returns "random_color", so do not guess the key.

Three endpoints return raw bytes instead of JSON (base64_decode, base58_decode
and base32_decode). Those methods return str when the payload is valid UTF-8,
and bytes otherwise.

Failures arrive as {"error": "message"} with a real HTTP status, and this client
raises AISenseAPIError carrying both.

Older deployments answered differently, and this client still handles two of
those shapes so that the same code works against either:
  * a plain-text warning line in front of a JSON body, which it strips and
    records in `last_server_notice`;
  * an unknown path answering HTTP 200 with a debug echo instead of a 404,
    which it turns into a clear AISenseAPIError.
Neither shape appeared when this client was last checked against production, on
2026-09-06.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Optional, Union

BASE_URL = "https://aisenseapi.com/services/v1"

# An unknown path answers a real 404 with the usual {"error": ...} body.
# Older deployments answered HTTP 200 with a body shaped like
#   ["<your-ip>",1786873281]["\/services\/v1\/random","1","random"]
# Detecting that turns a confusing JSON parse error into a clear message.
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
        #: Set when the server prepends a plain-text warning line to a JSON
        #: response, which an older deployment of /qrcode_encode did. None when
        #: the last call was clean, which is every call against production today.
        self.last_server_notice: Optional[str] = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _read(
        self,
        path: str,
        method: str,
        payload: Any = None,
        content_type: str = "application/json",
        token: Optional[str] = None,
    ):
        url = f"{self.base_url}{path}"
        data = None
        headers = {}
        if method == "POST":
            data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            headers["Content-Type"] = content_type
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.headers.get("Content-Type", ""), resp.read()
        except urllib.error.HTTPError as err:
            # The API returns a JSON error body with the failing status, so
            # read it rather than letting urllib swallow the reason.
            return err.code, err.headers.get("Content-Type", ""), err.read()

    def _request(self, path: str, method: str = "GET", payload: Any = None, token: Optional[str] = None) -> dict:
        status, _content_type, raw = self._read(path, method, payload, token=token)
        text = raw.decode("utf-8", "replace")

        if text.startswith(_DEBUG_ECHO_PREFIX) and _DEBUG_ECHO_MARKER in text:
            raise AISenseAPIError(
                f"{method} {path} is not a known endpoint. The API answered with the "
                f"debug echo an older deployment sent instead of a 404. Check the "
                f"path against API.md.",
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

    def _get(self, path: str, token: Optional[str] = None) -> dict:
        return self._request(path, "GET", token=token)

    def _post(self, path: str, payload: Any, token: Optional[str] = None) -> dict:
        return self._request(path, "POST", payload, token=token)

    def _delete(self, path: str) -> dict:
        return self._request(path, "DELETE")

    # ── Time ──────────────────────────────────────────────────────────────────

    def get_datetime(self, offset: Optional[str] = None) -> dict:
        """Current datetime in ISO 8601. Response key: ``datetime``.

        ``offset`` must be a four-digit UTC offset such as ``"+0200"``,
        ``"-0530"`` or ``"0100"``. Hour-only values like ``"1"`` are NOT
        accepted by the API: they form a path that matches no route, so they
        answer 404.
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

        Response key: ``timezones``, a list of ``{"timezone": ..., "offset": ...}``
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

        No arguments defaults to 1 to 6. A single argument is treated by the API
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

        This client sends no ``Accept`` of its own, so the endpoint answers with
        ``application/octet-stream``: the decoded bytes and nothing else. Send
        ``Accept: application/json`` instead and the same endpoint wraps the
        result as ``{"type": ..., "decoded_data": ...}``. ``type`` is ``"json"``
        when the decoded bytes themselves parse as JSON, and ``"binary"``
        otherwise, which adds ``"encoding": "base64"`` and re-encodes
        ``decoded_data``. Plain text that is not JSON therefore comes back
        tagged ``"binary"``. Raw is the more useful default; use the JSON form
        when you need the tag.

        /base64_decode is the only decoder that reads ``Accept``. Its Base58 and
        Base32 siblings always answer raw bytes.
        """
        return self._request_binary("/base64_decode", {"data": data})

    def base58_encode(self, data: str) -> dict:
        """Response key: ``base58_encoded_data``."""
        return self._post("/base58_encode", {"data": data})

    def base58_decode(self, data: str) -> Union[str, bytes]:
        """Decode Base58. Answers with raw bytes, not JSON, and ignores ``Accept``.

        This endpoint used to validate its input with the Base32 decoder and
        reject everything with "Invalid Base32 input.", including strings
        produced by :meth:`base58_encode`. It round-trips against
        :meth:`base58_encode` as of 2026-09-06; bad input now answers 400 with
        "Invalid Base58 input."
        """
        return self._request_binary("/base58_decode", {"data": data})

    def base32_encode(self, data: str) -> dict:
        """Response key: ``base32_encoded_data``."""
        return self._post("/base32_encode", {"data": data})

    def base32_decode(self, data: str) -> Union[str, bytes]:
        """Decode Base32. Answers with raw bytes, not JSON, and ignores ``Accept``."""
        return self._request_binary("/base32_decode", {"data": data})

    def jwt_encode(self, payload: Union[dict, str], secret: str) -> dict:
        """Encode a payload into an HS256 JWT. Response key: ``jwt``.

        The API takes ``data`` as either a JSON object or a string containing
        JSON, and both produce the same token. A dict is serialised here so the
        behaviour is the same whichever deployment answers. An empty ``data`` or
        an empty ``secret`` answers 400.
        """
        data = payload if isinstance(payload, str) else json.dumps(payload)
        return self._post("/jwt_encode", {"data": data, "secret": secret})

    def jwt_decode(self, token: str, secret: str) -> dict:
        """Decode a JWT. Response key: ``decoded_payload``."""
        return self._post("/jwt_decode", {"data": token, "secret": secret})

    def qrcode_encode(self, payload: str) -> dict:
        """Generate a QR code. Response keys: ``qrcode_image`` (Base64 PNG) and ``image_type``.

        The request field is ``payload``. ``data`` is accepted as well, so the
        QR pair is no longer the one endpoint with a field name of its own.
        """
        return self._post("/qrcode_encode", {"payload": payload})

    def qrcode_decode(self, image_base64: str) -> dict:
        """Decode a Base64-encoded QR code image. Response key: ``qrcode_content``.

        The request field is ``payload``, and ``data`` is accepted as well.
        Anything the decoder cannot read as a QR code answers 400.
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
        """CRC32 checksum. Response key: ``crc32_checksum``, an integer, not a hex string."""
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
        """Store data for 24 hours.

        Response keys: ``storage_id``, ``expire_timestamp`` and
        ``expire_datetime``.

        The request body is stored verbatim, so whatever you pass here is
        exactly what :meth:`storage_get` gives back. No ``data`` wrapper is
        added or removed.
        """
        return self._post("/storage", data)

    def storage_get(self, storage_id: str) -> dict:
        """Retrieve stored data by its ``storage_id``, returned verbatim."""
        return self._get(f"/storage/{storage_id}")

    def shorten_url(self, url: str) -> dict:
        """Shorten a URL for 24 hours.

        Response keys: ``short_url``, ``expire_timestamp`` and
        ``expire_datetime``. This is a GET with the target URL inline in the
        path, not a POST.
        """
        return self._get(f"/url_shortener/{url}")

    def webhook_capture_create(self, notify_url: Optional[str] = None) -> dict:
        """Create a URL that records the next request sent to it.

        Response keys: ``ok``, ``capture_id``, ``status``, ``update_url``,
        ``read_url``, ``wait_url``, ``expire_timestamp``, ``expire_datetime``.
        Point any HTTP client at ``update_url``, then read it back with
        :meth:`webhook_capture_read`.
        """
        body = {}
        if notify_url is not None:
            body["notify_url"] = notify_url
        return self._post("/webhook_capture", body)

    def webhook_capture_read(self, capture_id: str, wait_seconds: Optional[int] = None) -> dict:
        """Read a captured request.

        Response keys: ``ok``, ``capture_id``, ``status`` (``"pending"`` or
        ``"captured"``), ``created_at_timestamp``, ``created_at_datetime``,
        ``expire_timestamp``, ``expire_datetime``. Once something has arrived it
        also carries ``captured_at_timestamp``, ``captured_at_datetime`` and
        ``request``. Branch on ``status``, not on the presence of ``request``.
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
        ``wait_url``, ``expire_timestamp``, ``expire_datetime``.

        With ``respondents`` above 1 the shape changes: there is no
        ``form_url``, and ``form_urls`` carries one link per respondent,
        alongside ``respondents``, ``answered``, ``tally`` and ``responses``.
        Hand each respondent their own link.

        ``fields`` example, where ``options`` accepts either plain strings or
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

        Response keys: ``ok``, ``action_id``, ``status``,
        ``created_at_timestamp``, ``created_at_datetime``,
        ``expire_timestamp``, ``expire_datetime``, ``answered_at_timestamp``,
        ``answered_at_datetime``, ``response``.

        ``status`` is ``"pending"``, ``"answered"``, or ``"partial"`` when an
        action with several respondents has some answers but not all. A
        multi-respondent action also returns ``respondents``, ``answered``,
        ``tally`` and ``responses``.
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

    def agent_inbox_create(self) -> dict:
        """Create a disposable mail inbox that lives at most 24 hours.

        For a verification code, a confirmation link or a sign-up mail. Takes no
        arguments. Response keys: ``ok``, ``inbox_id``, ``slug``, ``address``,
        ``read_url``, ``wait_url``, ``expire_timestamp``.

        The two identifiers are not interchangeable. ``slug`` is the seven
        characters ``[a-z0-9]`` inside ``address``, and it is public by
        construction: it travels in mail headers, bounces and sender logs.
        Knowing it lets anyone send mail to the inbox, and nothing else; it
        never appears in a URL. ``inbox_id`` is the only credential that reads
        the inbox. It is a bearer secret, anyone holding it reads the mail, and
        it is returned once, here. Guessing the address does not read the inbox.
        A wrong ``inbox_id`` and a missing inbox both answer 404, and nothing
        here answers 403, so the two cannot be told apart. An inbox that has
        passed its expiry answers 410 until the pruner removes it, and 404 after
        that.

        Caps: 20 messages per inbox, 64 KiB of cleaned text per message, 256 KiB
        per inbox, 50 inboxes per client per UTC day, 5000 active inboxes
        service wide. The 24 hour lifetime is fixed and cannot be extended.

        The routes are POST /inbox, GET /inbox/{inbox_id} and
        GET /inbox/{inbox_id}/wait/{0..25}. A wait outside 0 to 25 answers 404,
        which is where this differs from the other long poll routes.
        """
        return self._post("/inbox", {})

    def agent_inbox_read(self, inbox_id: str, wait_seconds: Optional[int] = None) -> dict:
        """Read an inbox, or wait up to 25 seconds for it to change.

        Response keys: ``ok``, ``slug``, ``address``, ``received``,
        ``truncated``, ``messages``, ``created_at_timestamp``,
        ``expire_timestamp``. The wait form adds ``waited_seconds`` and
        ``wait_reason``. ``inbox_id`` is not echoed back; the credential never
        travels in a response.

        Each entry in ``messages`` has ``from``, ``subject``, ``date``, ``text``,
        ``codes`` and ``links``. ``date`` is when the service received the
        message, not the sender's Date header, because that header is sender
        controlled. ``codes`` are standalone 4 to 8 digit numbers. ``links`` are
        public http(s) links only: private-IP and localhost links are dropped.
        Attachments, raw MIME, arbitrary headers, scripts and styles are
        stripped before storage.

        ``truncated`` is true once at least one message has been refused, either
        by the 20 message cap or by the 256 KiB total. A full inbox refuses new
        mail rather than evicting old mail, so without the flag a reader would
        see a full inbox, no code and no reason. It carries no count, and it
        says nothing about text cut short inside a message at the 64 KiB
        per-message cap, which the parser does silently.

        The wait watches ``truncated`` as well as ``received``, so a message
        the cap turns away ends the wait instead of leaving the caller to run
        out the clock on one that will never arrive.
        """
        suffix = "" if wait_seconds is None else f"/wait/{wait_seconds}"
        return self._get(f"/inbox/{inbox_id}{suffix}")

    def create_agent_queue(self) -> dict:
        """Create a pull queue that cooperating agents share for at most 24 hours.

        Takes no arguments. Response keys: ``ok``, ``queue_id``,
        ``created_at_timestamp``, ``expire_timestamp``, ``counts``,
        ``read_token``, ``write_token``, ``worker_token``.

        The three tokens are separate capabilities, and each is returned once,
        here. ``read_token`` reads counts and single jobs, ``write_token`` adds
        jobs, and ``worker_token`` claims, acknowledges, releases and renews
        them. A token used for another role answers 403, so each agent can be
        given only the token its role needs. Every queue method below takes the
        queue ID first, then the token, then the job details, and sends the
        token as an Authorization header.

        The whole queue expires 24 hours after creation, and activity never
        extends it. Caps: 100 jobs over the queue's lifetime, 16 KiB of encoded
        JSON per payload, 5 claims per job and 20 new queues per client IP per
        24 hours. The service stores jobs and hands them out; it never runs
        them.
        """
        return self._post("/queue", {})

    def read_agent_queue(self, queue_id: str, read_token: str) -> dict:
        """Read queue counts with the read token.

        Response keys: ``ok``, ``queue_id``, ``created_at_timestamp``,
        ``expire_timestamp``, ``counts``. ``counts`` has ``pending``,
        ``claimed``, ``completed``, ``failed`` and ``total``. Payloads and
        tokens are never listed.
        """
        return self._get(f"/queue/{queue_id}", token=read_token)

    def enqueue_agent_queue_job(self, queue_id: str, write_token: str, job_key: str, payload: Any) -> dict:
        """Add a job with the write token.

        Response keys: ``ok``, ``queue_id``, ``expire_timestamp``, ``job``,
        ``deduplicated``. ``job`` has ``job_id``, ``job_key``, ``payload``,
        ``status``, ``attempts``, ``created_at_timestamp``,
        ``expire_timestamp`` and ``claimed_until_timestamp``.

        ``job_key`` makes a resend harmless. The same key with the same payload
        returns the existing job with ``deduplicated`` true. The same key with a
        different payload answers 409, so a retry can never quietly change a
        job. A key is 1 to 64 characters of ``[A-Za-z0-9._:-]`` and starts
        with a letter or digit.

        ``payload`` is any JSON value, ``None`` included, up to 16 KiB encoded.
        """
        body = {"job_key": job_key, "payload": payload}
        return self._post(f"/queue/{queue_id}/jobs", body, token=write_token)

    def read_agent_queue_job(self, queue_id: str, read_token: str, job_id: str) -> dict:
        """Read one job with the read token.

        Response keys: ``ok``, ``queue_id``, ``expire_timestamp``, ``job``,
        with the same ``job`` fields as :meth:`enqueue_agent_queue_job`. A
        claim receipt is never shown here. The server keeps only its hash, so
        the worker that claimed the job is the one party that holds it.
        """
        return self._get(f"/queue/{queue_id}/jobs/{job_id}", token=read_token)

    def claim_agent_queue_job(
        self,
        queue_id: str,
        worker_token: str,
        visibility_timeout: Optional[int] = None,
    ) -> dict:
        """Claim the next pending job with the worker token.

        Response keys: ``ok``, ``queue_id``, ``expire_timestamp``, ``job``.
        ``job`` is ``None`` when nothing is waiting, which is the normal answer
        from an idle queue and not an error. Otherwise it is the job with
        ``status`` ``"claimed"``, a ``claimed_until_timestamp`` and a secret
        ``receipt``. Keep the receipt: acknowledging, releasing and renewing
        all need it.

        ``visibility_timeout`` is how long the claim holds, 30 to 900 seconds,
        60 by default, and never past the queue's expiry. A job whose claim
        runs out goes back to pending for another worker. Each claim counts one
        attempt, and a job fails after 5 unsuccessful ones.

        A job can be handed out more than once, so make the work itself
        idempotent. A claim reply that is lost can still have reserved a job;
        the Agent Queue section of API.md describes how to recover without
        taking a second job.
        """
        body = {} if visibility_timeout is None else {"visibility_timeout": visibility_timeout}
        return self._post(f"/queue/{queue_id}/claim", body, token=worker_token)

    def ack_agent_queue_job(self, queue_id: str, worker_token: str, job_id: str, receipt: str) -> dict:
        """Mark a claimed job completed with the worker token and its receipt.

        Response keys: ``ok``, ``queue_id``, ``expire_timestamp``, ``job``,
        with ``status`` ``"completed"``. Repeating the acknowledgement with the
        same receipt succeeds again, so a worker whose reply was lost can
        retry it. A receipt from an earlier claim of the same job answers 409.
        Completing a job does not free room under the 100 job cap.
        """
        path = f"/queue/{queue_id}/jobs/{job_id}/ack"
        return self._post(path, {"receipt": receipt}, token=worker_token)

    def release_agent_queue_job(self, queue_id: str, worker_token: str, job_id: str, receipt: str) -> dict:
        """Give a claimed job back to the queue with the worker token and its receipt.

        Response keys: ``ok``, ``queue_id``, ``expire_timestamp``, ``job``,
        with ``status`` ``"pending"`` again. The attempt the claim used still
        counts toward the limit of 5.
        """
        path = f"/queue/{queue_id}/jobs/{job_id}/release"
        return self._post(path, {"receipt": receipt}, token=worker_token)

    def renew_agent_queue_job(
        self,
        queue_id: str,
        worker_token: str,
        job_id: str,
        receipt: str,
        visibility_timeout: Optional[int] = None,
    ) -> dict:
        """Extend a claim with the worker token and its receipt.

        Response keys: ``ok``, ``queue_id``, ``expire_timestamp``, ``job``,
        with a later ``claimed_until_timestamp``. No new receipt is issued, and
        the one from the claim stays valid. Renewing adds no attempt.
        ``visibility_timeout`` is 30 to 900 seconds, 60 by default, and never
        past the queue's expiry.
        """
        body = {"receipt": receipt}
        if visibility_timeout is not None:
            body["visibility_timeout"] = visibility_timeout
        return self._post(f"/queue/{queue_id}/jobs/{job_id}/renew", body, token=worker_token)

    # ── Crypto ────────────────────────────────────────────────────────────────

    def generate_solana_wallet(self) -> dict:
        """New Solana wallet. Response keys: ``private_key``, ``public_address``.

        FOR DEVELOPMENT ONLY. Do not fund a wallet whose private key was
        generated on a server and sent back over the wire.
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

        Response keys: ``wallet``, ``balance_eth``, ``balance_wei``.

        This used to answer "Failed to retrieve balance data." for every
        address. It returns a balance as of 2026-09-06.
        """
        return self._get(f"/ethereum/balance/{address}")


def _strip_server_notice(text: str):
    """Split a leading plain-text warning line off a JSON body.

    An older deployment of /qrcode_encode emitted one in front of its JSON.
    Production does not, so this is a guard for callers pointed at an older
    deployment rather than a workaround for current behaviour. Returns
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

    print("\n=== Base58, which used to reject its own encoder's output ===")
    encoded_58 = api.base58_encode("Hello")["base58_encoded_data"]
    print(encoded_58, "->", api.base58_decode(encoded_58))

    print("\n=== An unknown path raises with the server's own message ===")
    try:
        api.get_datetime(offset="1")
    except AISenseAPIError as err:
        print(err)

    api.qrcode_encode("https://aisenseapi.com/")
    if api.last_server_notice:
        print("Server sent a warning line before its JSON:", api.last_server_notice[:80], "...")
