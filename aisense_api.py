"""
aisense_api.py — Python client for the AI SENSE AS Free Public REST APIs
https://www.aisense.no

No dependencies beyond the standard library (uses urllib).
Optionally install `requests` for the requests-based version below.

Usage:
    from aisense_api import AISenseAPI
    api = AISenseAPI()
    print(api.get_uuid())
    print(api.hash_sha256("Hello"))
"""

import json
import urllib.request
import urllib.error
from typing import Any, Optional

BASE_URL = "https://aisenseapi.com/services/v1"


class AISenseAPI:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def _post(self, path: str, payload: Any) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    # ── Time ──────────────────────────────────────────────────────────────────

    def get_datetime(self, offset: Optional[int] = None) -> dict:
        """Current datetime in ISO 8601. Optional UTC offset (e.g. 1 for UTC+1)."""
        path = f"/time/datetime/{offset}" if offset is not None else "/time/datetime"
        return self._get(path)

    def get_timestamp(self) -> dict:
        """Current Unix timestamp (seconds)."""
        return self._get("/time/timestamp")

    def get_microtimestamp(self) -> dict:
        """Current Unix timestamp with microsecond precision."""
        return self._get("/time/microtimestamp")

    def get_timezones(self, offset: Optional[int] = None) -> dict:
        """All timezones, optionally filtered by UTC offset."""
        path = f"/time/timezones/{offset}" if offset is not None else "/time/timezones"
        return self._get(path)

    def get_swatch_time(self) -> dict:
        """Current time in Swatch Internet Time (.beats)."""
        return self._get("/time/swatchinternettime")

    # ── Random ────────────────────────────────────────────────────────────────

    def get_random_number(self, from_: int = 1, to: int = 6) -> dict:
        """Random integer in range [from_, to]. Defaults to 1–6."""
        return self._get(f"/random/number/{from_}/{to}")

    def get_random_color(self) -> dict:
        """Random hex color code."""
        return self._get("/random/color")

    def get_uuid(self) -> dict:
        """Generate a UUID v4."""
        return self._get("/random/uuid")

    def get_guid(self) -> dict:
        """Generate a GUID."""
        return self._get("/random/guid")

    # ── Transform ─────────────────────────────────────────────────────────────

    def base64_encode(self, data: str) -> dict:
        return self._post("/transform/base64_encode", {"data": data})

    def base64_decode(self, data: str) -> dict:
        return self._post("/transform/base64_decode", {"data": data})

    def base58_encode(self, data: str) -> dict:
        return self._post("/transform/base58_encode", {"data": data})

    def base58_decode(self, data: str) -> dict:
        return self._post("/transform/base58_decode", {"data": data})

    def base32_encode(self, data: str) -> dict:
        return self._post("/transform/base32_encode", {"data": data})

    def base32_decode(self, data: str) -> dict:
        return self._post("/transform/base32_decode", {"data": data})

    def jwt_encode(self, payload: dict, secret: str) -> dict:
        """Encode a JSON payload into a JWT (HS256)."""
        return self._post("/transform/jwt_encode", {"data": payload, "secret": secret})

    def jwt_decode(self, token: str, secret: str) -> dict:
        """Decode a JWT and return its payload."""
        return self._post("/transform/jwt_decode", {"data": token, "secret": secret})

    def qrcode_encode(self, data: str) -> dict:
        """Generate a QR code from text. Returns Base64-encoded PNG."""
        return self._post("/transform/qrcode_encode", {"data": data})

    def qrcode_decode(self, image_base64: str) -> dict:
        """Decode a Base64-encoded QR code image."""
        return self._post("/transform/qrcode_decode", {"data": image_base64})

    # ── Hash ──────────────────────────────────────────────────────────────────

    def hash_md5(self, data: str) -> dict:
        return self._post("/hash/md5", {"data": data})

    def hash_sha1(self, data: str) -> dict:
        return self._post("/hash/sha1", {"data": data})

    def hash_sha256(self, data: str) -> dict:
        return self._post("/hash/sha256", {"data": data})

    def hash_sha512(self, data: str) -> dict:
        return self._post("/hash/sha512", {"data": data})

    # ── Web ───────────────────────────────────────────────────────────────────

    def ping(self) -> dict:
        """Verify API connectivity."""
        return self._get("/web/ping")

    def health(self) -> dict:
        """API health check with microsecond timestamp."""
        return self._get("/web/health")

    def get_client_ip(self) -> dict:
        """Returns your public IP address."""
        return self._get("/web/ip")

    def ip_lookup(self, ip: str) -> dict:
        """Reverse IP lookup: country, city, coordinates, timezone."""
        return self._get(f"/web/ip_reverse_lookup/{ip}")

    def storage_set(self, data: Any) -> dict:
        """Store data temporarily (24h TTL). Returns a UUID."""
        return self._post("/web/storage", {"data": data})

    def storage_get(self, uuid: str) -> dict:
        """Retrieve stored data by UUID."""
        return self._get(f"/web/storage/{uuid}")

    def shorten_url(self, url: str) -> dict:
        """Shorten a URL (24h TTL)."""
        return self._post("/web/url_shortener", {"url": url})

    def webhook_capture(self, body: Optional[dict] = None) -> dict:
        """Capture and return the full incoming HTTP request (24h TTL)."""
        return self._post("/web/webhook_capture", body or {})

    def webhook_action(self, title: str, fields: list) -> dict:
        """
        Create a human-in-the-loop action form (24h TTL).

        fields example:
        [
            {"type": "radio", "name": "approval", "label": "Approve?", "options": ["Yes", "No"]}
        ]
        Returns: { action_id, form_url, result_url }
        """
        return self._post("/web/webhook_action", {"title": title, "fields": fields})

    # ── Crypto ────────────────────────────────────────────────────────────────

    def generate_solana_wallet(self) -> dict:
        """Generate a new Solana wallet. FOR DEVELOPMENT ONLY."""
        return self._get("/crypto/solana/generate_new_wallet")

    def generate_bitcoin_wallet(self) -> dict:
        """Generate a new Bitcoin wallet. FOR DEVELOPMENT ONLY."""
        return self._get("/crypto/bitcoin/generate_new_wallet")

    def generate_ethereum_wallet(self) -> dict:
        """Generate a new Ethereum wallet. FOR DEVELOPMENT ONLY."""
        return self._get("/crypto/ethereum/generate_new_wallet")


# ── Example usage ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    api = AISenseAPI()

    print("=== Time ===")
    print(api.get_datetime(offset=1))
    print(api.get_timestamp())

    print("\n=== Random ===")
    print(api.get_uuid())
    print(api.get_random_color())
    print(api.get_random_number(1, 100))

    print("\n=== Transform ===")
    encoded = api.base64_encode("Hello, world!")
    print("Base64 encoded:", encoded)
    print("Base64 decoded:", api.base64_decode(encoded["base64_encoded_data"]))

    token = api.jwt_encode({"user": "alice"}, secret="my-secret")
    print("JWT:", token)
    print("JWT decoded:", api.jwt_decode(token["jwt"], secret="my-secret"))

    print("\n=== Hash ===")
    print(api.hash_sha256("Hello"))

    print("\n=== Web ===")
    print(api.ping())
    print(api.get_client_ip())
    print(api.ip_lookup("8.8.8.8"))

    stored = api.storage_set({"hello": "world"})
    print("Stored, UUID:", stored)
    print("Retrieved:", api.storage_get(stored["uuid"]))

    print("\n=== Crypto (dev only) ===")
    print(api.generate_ethereum_wallet())
