"""Shared pieces for the ComfyUI render farm example: one small HTTP client over the
standard library, the private state directory, and a PNG writer for the fake renderer.

Python 3.9 or newer, no third-party packages. Nothing here prints a token."""

import hashlib
import json
import os
import pathlib
import stat
import struct
import sys
import urllib.error
import urllib.request
import uuid
import zlib

BASE = "https://aisenseapi.com/services/v1"
USER_AGENT = "aisense-comfyui-example/1.0"


class ApiError(Exception):
    """An HTTP answer that is not the one the step needs. `status` is the HTTP code."""

    def __init__(self, status, body, where):
        self.status = status
        self.body = body
        self.where = where
        text = body.get("error") if isinstance(body, dict) else body
        super().__init__("%s answered %s: %s" % (where, status, text))


def _request(method, url, body=None, headers=None, timeout=60):
    data = None
    sent = dict(headers or {})
    sent.setdefault("User-Agent", USER_AGENT)
    sent.setdefault("Accept", "application/json")
    if isinstance(body, (dict, list)):
        data = json.dumps(body).encode("utf-8")
        sent.setdefault("Content-Type", "application/json")
    elif isinstance(body, bytes):
        data = body
    request = urllib.request.Request(url, data=data, method=method, headers=sent)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            raw = reply.read()
            return reply.status, dict(reply.headers), raw
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def call(method, url, body=None, headers=None, timeout=60, expect=(200, 201)):
    """One JSON call. Returns the parsed body; raises ApiError on any other status."""
    status, _, raw = _request(method, url, body, headers, timeout)
    try:
        parsed = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        parsed = {"raw": raw[:200].decode("utf-8", "replace")}
    if status not in expect:
        raise ApiError(status, parsed, method + " " + url.replace(BASE, ""))
    return parsed


def download(url, timeout=120):
    """GET raw bytes. Returns (status, headers, bytes)."""
    return _request("GET", url, None, None, timeout)


def upload_file(url, name, data, content_type="image/png", timeout=120):
    """POST one file as the `file` field of a multipart form, the shape the Storage endpoint takes."""
    boundary = "----aisense" + uuid.uuid4().hex
    head = ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
            "Content-Type: %s\r\n\r\n" % (boundary, name, content_type)).encode("utf-8")
    tail = ("\r\n--%s--\r\n" % boundary).encode("utf-8")
    headers = {"Content-Type": "multipart/form-data; boundary=" + boundary}
    status, _, raw = _request("POST", url, head + data + tail, headers, timeout)
    parsed = json.loads(raw.decode("utf-8")) if raw else {}
    if status not in (200, 201):
        raise ApiError(status, parsed, "POST " + url.replace(BASE, ""))
    return parsed


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def state_directory(override=None):
    """A private directory for queue ids, tokens and the job manifest. Never commit it."""
    if override:
        path = pathlib.Path(override)
    elif os.name == "nt":
        path = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home())) / "aisense" / "comfyui-example"
    else:
        path = pathlib.Path(os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local" / "state")) / "aisense" / "comfyui-example"
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(path, stat.S_IRWXU)
    return path


def read_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path, value):
    path = pathlib.Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    if os.name != "nt":
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(temporary, path)


def fake_png(seed_text, size=256):
    """A valid PNG without any imaging library: a two-colour gradient derived from the text,
    so two different prompts give two different images and the same prompt gives the same one."""
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    top = digest[0:3]
    bottom = digest[3:6]
    rows = []
    for y in range(size):
        t = y / (size - 1)
        colour = bytes(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        rows.append(b"\x00" + colour * size)
    raw = b"".join(rows)

    def chunk(kind, payload):
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def say(*parts):
    print(*parts, file=sys.stderr, flush=True)
