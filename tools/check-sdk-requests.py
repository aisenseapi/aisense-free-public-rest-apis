"""The requests both SDKs send, checked against a local stub. No network.

python tools/check-sdk-requests.py

Runs the methods for the Convert, Images and Logic endpoints, PDF, DNS,
semantic search, validation and the time, passphrase, slug, hash and email helpers through
aisense_api.py and, when Node.js 18 or later is on the path, aisense-api.js,
against a server on 127.0.0.1. Each request is compared with what API.md
documents: method, path, content type, JSON body or multipart fields and file,
and the bearer token. The stub answers every call with {"ok": true}, and
/chaos/503/1500 with a 503 like the real one, to check simulate_failure.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import aisense_api  # noqa: E402

# A PNG signature and filler. The stub never decodes it.
IMAGE = bytes.fromhex("89504e470d0a1a0a") + b"synthetic image bytes \x00\xff\r\n end"
RECORDED = []

DECIDE_QUESTIONS = {"urgent": {"type": "noul", "instructions": "Is this urgent?", "criteria": {"true": "Yes.", "false": "No."}}}
JSON_POSTS = [
    ("/timestamp_convert", {"data": "now", "offset": "+0200"}),
    ("/slugify", {"data": "Blåbær på Ås"}),
    ("/hash_verify", {"data": "Hello", "hash": 4157704578, "algorithm": "crc32"}),
    ("/email_validate", {"data": "post@example.com"}),
    ("/validate/iban", {"data": "NO9386011117947"}),
]
# method, path, kind, expected body or fields, file name, token
EXPECTED = [("GET", "/passphrase/5", None, None, None, None)]
EXPECTED += [("POST", path, "json", body, None, None) for path, body in JSON_POSTS]
EXPECTED += [
    ("GET", "/dns/198.51.100.7", None, None, None, None),
    ("GET", "/dns/abcdefg", None, None, None, None),
    ("POST", "/dns/abcdefg/update/198.51.100.8", "json", {}, None, "dns-token-1"),
    ("POST", "/dns/abcdefg/delete", "json", {}, None, "dns-token-1"),
    ("POST", "/semantic_search", "json", {"model": "qwen3-embedding-4b"}, None, None),
    ("GET", "/semantic_search/" + "c" * 32, None, None, None, "read-token-1"),
    ("POST", "/semantic_search/" + "c" * 32 + "/notes", "json", {"notes": [{"text": "Refund ORD-4410", "key": "job:4410"}]}, None, "write-token-1"),
    ("POST", "/semantic_search/" + "c" * 32 + "/search", "json", {"query": "refund", "limit": 2}, None, "read-token-1"),
    ("POST", "/semantic_search/" + "c" * 32 + "/notes/" + "d" * 32 + "/delete", "json", {}, None, "write-token-1"),
    ("POST", "/html2pdf", "json", {"html": "<h1>4817</h1>", "options": {"page-size": "A5"}}, None, None),
    ("POST", "/json_to_csv", "json", {"columns": ["id"], "rows": [{"id": "1"}], "delimiter": ";", "spreadsheet_safe": True}, None, None),
    ("POST", "/csv_to_json", "json", {"data": "id\n1\n", "delimiter": "\t"}, None, None),
    ("POST", "/table_match", "json", {"left": [{"id": "1"}], "right": [{"id": "1"}], "keys": [{"left": "id", "right": "id"}]}, None, None),
    ("POST", "/json_format", "json", {"data": "{\"a\":1}", "mode": "compact", "indent": 4}, None, None),
    ("POST", "/json_validate", "json", {"data": "{"}, None, None),
    ("POST", "/image_convert", "form", {"format": "webp", "quality": "80", "lossless": "true"}, "image", None),
    ("POST", "/image_compress", "form", {"quality": "70"}, "image", None),
    ("POST", "/image_resize", "form", {"width": "800", "height": "600", "fit": "cover", "upscale": "false"}, "image", None),
    ("POST", "/image_metadata", "form", {}, "photo.png", None),
    ("POST", "/image_strip", "form", {}, "image", None),
    ("POST", "/image_colors", "form", {"count": "6"}, "image", None),
    ("POST", "/image_favicon", "form", {"crop": "trim", "name": "Example site"}, "image", None),
    ("POST", "/decide", "json", {"state": {"amount": 30}, "questions": DECIDE_QUESTIONS, "model": "nimble"}, None, None),
    ("GET", "/chaos/503/1500", None, None, None, None),
]
FAILURE = {"status": 503, "retry_after": "2", "chaos": "503/1500"}

JS_CALLS = r"""
import { AISenseAPI } from '__SDK__'
const { File } = globalThis.File ? globalThis : await import('node:buffer')
const api = new AISenseAPI(process.argv[2])
const image = Uint8Array.from(Buffer.from(process.argv[3], 'hex'))
const questions = JSON.parse(process.argv[4])
await api.getPassphrase(5)
await api.timestampConvert('now', '+0200')
await api.slugify('Blåbær på Ås')
await api.hashVerify('Hello', 4157704578, 'crc32')
await api.emailValidate('post@example.com')
await api.validate('iban', 'NO9386011117947')
await api.dnsCreate('198.51.100.7')
await api.dnsRead('abcdefg')
await api.dnsUpdate('abcdefg', '198.51.100.8', 'dns-token-1')
await api.dnsDelete('abcdefg', 'dns-token-1')
await api.createSemanticSearch('qwen3-embedding-4b')
await api.readSemanticSearch('cccccccccccccccccccccccccccccccc', 'read-token-1')
await api.addSemanticSearchNotes('cccccccccccccccccccccccccccccccc', 'write-token-1', [{ text: 'Refund ORD-4410', key: 'job:4410' }])
await api.querySemanticSearch('cccccccccccccccccccccccccccccccc', 'read-token-1', 'refund', 2)
await api.deleteSemanticSearchNote('cccccccccccccccccccccccccccccccc', 'write-token-1', 'dddddddddddddddddddddddddddddddd')
await api.htmlToPdf('<h1>4817</h1>', { 'page-size': 'A5' })
await api.jsonToCsv(['id'], [{ id: '1' }], { delimiter: ';', spreadsheetSafe: true })
await api.csvToJson('id\n1\n', '\t')
await api.tableMatch([{ id: '1' }], [{ id: '1' }], [{ left: 'id', right: 'id' }])
await api.jsonFormat('{"a":1}', 'compact', 4)
await api.jsonValidate('{')
await api.imageConvert(image, 'webp', { quality: 80, lossless: true })
await api.imageCompress(image, 70)
await api.imageResize(image, { width: 800, height: 600, fit: 'cover', upscale: false })
await api.imageMetadata(new File([image], 'photo.png'))
await api.imageStrip(image)
await api.imageColors(image, 6)
await api.imageFavicon(image, { crop: 'trim', name: 'Example site' })
await api.decide({ amount: 30 }, questions, 'nimble')
const failure = await api.simulateFailure(503, 1500)
console.log(JSON.stringify({ status: failure.status, retry_after: failure.retryAfter, chaos: failure.chaos, body: failure.body }))
"""


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _body(self) -> bytes:
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            data = b""
            while True:
                size = int(self.rfile.readline().strip() or b"0", 16)
                if size == 0:
                    self.rfile.readline()
                    return data
                data += self.rfile.read(size)
                self.rfile.readline()
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def _answer(self):
        RECORDED.append({
            "method": self.command, "path": self.path, "type": self.headers.get("Content-Type") or "",
            "auth": self.headers.get("Authorization"), "body": self._body(),
        })
        status, payload, extra = 200, b'{"ok":true}', {}
        if self.path.startswith("/services/v1/chaos/"):
            status, payload = 503, b'{"error":"Service Unavailable","chaos":{"status":503,"delay_ms":1500}}'
            extra = {"Retry-After": "2", "X-Chaos": "503/1500"}
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for key, value in extra.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = _answer


def multipart(record: dict) -> tuple:
    """The text fields and the file parts of a multipart/form-data body."""
    boundary = record["type"].split("boundary=", 1)[1].strip('"').encode()
    fields, files = {}, {}
    for part in record["body"].split(b"--" + boundary)[1:]:
        if part.startswith(b"--"):
            break
        head, _, content = part[2:].partition(b"\r\n\r\n")
        content = content[:-2] if content.endswith(b"\r\n") else content
        disposition = next(l for l in head.decode().split("\r\n") if l.lower().startswith("content-disposition"))
        params = dict(p.strip().split("=", 1) for p in disposition.split(";")[1:])
        name = params["name"].strip('"')
        if "filename" in params:
            files[name] = (params["filename"].strip('"'), content)
        else:
            fields[name] = content.decode()
    return fields, files


def compare(client: str, records: list, failure: dict) -> list:
    problems = []
    if len(records) != len(EXPECTED):
        return [f"{client}: {len(records)} requests, expected {len(EXPECTED)}"]
    for record, (method, path, kind, body, filename, token) in zip(records, EXPECTED):
        where = f"{client} {method} {path}"
        if (record["method"], record["path"]) != (method, "/services/v1" + path):
            problems.append(f"{where}: sent {record['method']} {record['path']}")
            continue
        if record["auth"] != (f"Bearer {token}" if token else None):
            problems.append(f"{where}: Authorization {record['auth']!r}")
        if kind == "json":
            if not record["type"].startswith("application/json"):
                problems.append(f"{where}: Content-Type {record['type']!r}")
            elif json.loads(record["body"] or b"null") != body:
                problems.append(f"{where}: body {record['body'][:200]!r}")
        elif kind == "form":
            if not record["type"].startswith("multipart/form-data"):
                problems.append(f"{where}: Content-Type {record['type']!r}")
                continue
            fields, files = multipart(record)
            if fields != body:
                problems.append(f"{where}: fields {fields!r}")
            if list(files) != ["file"] or files["file"] != (filename, IMAGE):
                problems.append(f"{where}: file part {[(k, v[0], len(v[1])) for k, v in files.items()]!r}")
        elif record["body"]:
            problems.append(f"{where}: unexpected body {record['body'][:80]!r}")
    if {k: failure.get(k) for k in FAILURE} != FAILURE or "Service Unavailable" not in str(failure.get("body")):
        problems.append(f"{client} simulate_failure returned {failure!r}")
    return problems


def run_python(base: str, folder: pathlib.Path) -> dict:
    api = aisense_api.AISenseAPI(base_url=base)
    photo = folder / "photo.png"
    photo.write_bytes(IMAGE)
    api.get_passphrase(5)
    api.timestamp_convert("now", "+0200")
    api.slugify("Blåbær på Ås")
    api.hash_verify("Hello", 4157704578, "crc32")
    api.email_validate("post@example.com")
    api.validate("iban", "NO9386011117947")
    api.dns_create("198.51.100.7")
    api.dns_read("abcdefg")
    api.dns_update("abcdefg", "198.51.100.8", "dns-token-1")
    api.dns_delete("abcdefg", "dns-token-1")
    api.create_semantic_search("qwen3-embedding-4b")
    api.read_semantic_search("c" * 32, "read-token-1")
    api.add_semantic_search_notes("c" * 32, "write-token-1", [{"text": "Refund ORD-4410", "key": "job:4410"}])
    api.query_semantic_search("c" * 32, "read-token-1", "refund", 2)
    api.delete_semantic_search_note("c" * 32, "write-token-1", "d" * 32)
    api.html_to_pdf("<h1>4817</h1>", {"page-size": "A5"})
    api.json_to_csv(["id"], [{"id": "1"}], delimiter=";", spreadsheet_safe=True)
    api.csv_to_json("id\n1\n", "\t")
    api.table_match([{"id": "1"}], [{"id": "1"}], [{"left": "id", "right": "id"}])
    api.json_format('{"a":1}', "compact", 4)
    api.json_validate("{")
    api.image_convert(IMAGE, "webp", quality=80, lossless=True)
    api.image_compress(IMAGE, 70)
    api.image_resize(IMAGE, width=800, height=600, fit="cover", upscale=False)
    api.image_metadata(str(photo))
    api.image_strip(IMAGE)
    api.image_colors(IMAGE, 6)
    api.image_favicon(IMAGE, crop="trim", name="Example site")
    api.decide({"amount": 30}, DECIDE_QUESTIONS, "nimble")
    return api.simulate_failure(503, 1500)


def run_node(base: str, folder: pathlib.Path):
    node = shutil.which("node")
    if node is None:
        return None
    script = folder / "calls.mjs"
    script.write_text(JS_CALLS.replace("__SDK__", (ROOT / "aisense-api.js").as_uri()), encoding="utf-8")
    done = subprocess.run([node, str(script), base, IMAGE.hex(), json.dumps(DECIDE_QUESTIONS)],
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    if done.returncode != 0:
        raise RuntimeError("node failed: " + done.stderr.strip()[-500:])
    return json.loads(done.stdout.strip().splitlines()[-1])


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/services/v1"
    problems = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            failure = run_python(base, folder)
            problems += compare("aisense_api.py", RECORDED[:], failure)
            RECORDED.clear()
            js = run_node(base, folder)
            if js is None:
                print("  skip  aisense-api.js: no node on the path")
            else:
                problems += compare("aisense-api.js", RECORDED[:], js)
    finally:
        server.shutdown()
    for line in problems:
        print("  FAIL  " + line)
    print(f"check-sdk-requests: {len(EXPECTED)} requests per client, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
