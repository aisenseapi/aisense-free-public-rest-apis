# AI SENSE Agent Quickstart

Use this guide for one complete Queue workflow. See [AGENT-GUIDE.md](AGENT-GUIDE.md)
for the compact 28-tool catalog, [MCP.md](MCP.md) for protocol details, and
[API.md](API.md#agent-queue---temporary-work-for-multiple-workers) for response
fields and limits.

On 9 September 2026, the deployed Queue REST smoke test passed 21 checks and
production MCP discovery returned all 28 tools. This verifies the Queue
deployment and discovery, not deployment of the refreshed embedded agent
guide. Check `resources/read` before relying on its contents.

## Choose the right primitive

| Need | Choose | Important boundary |
| --- | --- | --- |
| Give several workers a backlog of JSON jobs | Queue | Workers pull jobs and perform the work. The service does not run code |
| Prevent cooperating workers from owning the same named work at once | Lease | Use the fencing token downstream. A Lease does not distribute a backlog |
| Resume after a webhook, human answer or chosen time | Agent Wake | Waits for an event. It is not a job queue or a background worker |

Use the [agent guide](AGENT-GUIDE.md) for Heartbeat, Inbox, human approval,
webhook capture and the other tool families.

## Run one Queue job

Running this example creates one temporary queue and one job on the public
service. Use only non-sensitive example data and run it intentionally from a
trusted local terminal. Python 3.9+ and a checkout of this repository are required.

The example keeps the three role tokens in process memory. It passes only the
Queue ID and worker token to the child worker through environment variables,
not command-line arguments. It does not print tokens, receipts or payloads.
Do not enable shell tracing or put credentials in URLs, shared logs or prompts
sent to unrelated services.

The setup requests and worker use the User-Agent
`aisense-agent-queue-example/1` so example traffic can be recognized in logs.

Run this Python code from the repository root:

```python
import json
import os
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

API = "https://aisenseapi.com/services/v1"


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


http = build_opener(NoRedirects())


def request(method, route, body=None, token=None):
    headers = {
        "Accept": "application/json",
        "User-Agent": "aisense-agent-queue-example/1",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    call = Request(API + route, data=data, headers=headers, method=method)
    try:
        with http.open(call, timeout=15) as response:
            result = json.load(response)
    except HTTPError as error:
        raise SystemExit("HTTP " + str(error.code) + ". Stop and use the retry table.")
    except (URLError, TimeoutError, ValueError):
        raise SystemExit("Uncertain response. Stop without blindly retrying the operation.")
    if result.get("error"):
        raise SystemExit("API error. Stop and inspect the operation before retrying.")
    return result


queue = request("POST", "/queue", {})
queue_path = "/queue/" + queue["queue_id"]
created = request(
    "POST",
    queue_path + "/jobs",
    {"job_key": "quickstart:1", "payload": {"message": "hello"}},
    queue["write_token"],
)
job_id = created["job"]["job_id"]

worker_env = dict(os.environ)
worker_env["AISENSE_QUEUE_ID"] = queue["queue_id"]
worker_env["AISENSE_QUEUE_WORKER_TOKEN"] = queue["worker_token"]
worker_env["AISENSE_QUEUE_API_BASE"] = API
subprocess.run(
    [sys.executable, "examples/agent_queue_worker.py", "--max-jobs", "1"],
    env=worker_env,
    check=True,
)

job = request("GET", queue_path + "/jobs/" + job_id, token=queue["read_token"])
summary = request("GET", queue_path, token=queue["read_token"])
if job["job"]["status"] != "completed":
    raise SystemExit("The job is not completed. Do not repeat its effect blindly.")
print(json.dumps({"status": job["job"]["status"], "counts": summary["counts"]}))
```

The [example worker](examples/agent_queue_worker.py) claims the job, writes a
deterministic payload summary to its private local SQLite state, and then
acknowledges with the current receipt. It does not execute payloads or follow
URLs. The local journal deduplicates this sample effect by job identity.
Replacing that effect with an external action requires idempotency at the
external destination as well.

The expected final status is `completed`, with one completed job in `counts`.
Queue does not store the worker's output. The example worker keeps its sample
output locally. After this process exits, its role tokens are not recoverable
from the API. A real producer should save creation credentials once in a
private credential store and share only the role each participant needs.

The worker is bounded by job count, polls and elapsed time. Run
`python3 examples/agent_queue_worker.py --help` for its limits and local state
options. It does not create queues or enqueue work.

## Handle retries deliberately

For MCP, inspect `isError` and the structured `status_code`. A tool failure can
arrive in an HTTP 200 JSON-RPC response. The statuses below describe the Queue
operation, not necessarily the MCP transport.

| Result | Next action |
| --- | --- |
| Claim returns `job: null` | No work is available now. Wait with bounded backoff, then poll within a request budget and the queue expiry |
| `401` or `403` | Stop and fix the missing, malformed or wrong-role credential. Repeating it does not help |
| `409` on enqueue | Inspect whether the key has a different payload or the 100-job lifetime capacity is full. Do not change keys merely to hide a conflict |
| `409` on ack, release or renew | The receipt is stale or ownership is lost. Stop using that claim and do not repeat the external effect |
| `404` or `410` | Stop using the missing or expired resource. Expiry cannot be extended or reversed. Recreating work needs an explicit recovery plan |
| `429` | Back off within a bounded budget. Respect `Retry-After` if provided and account for the separate queue-creation quota |
| `503` | Stop on a claim response and treat its outcome as uncertain. For repeat-safe operations use bounded backoff. Stop when the retry budget or queue lifetime ends |
| Enqueue response is uncertain | Retry the same queue, job key and unchanged payload. Do not generate a fresh key |
| Ack response is uncertain | The same winning receipt can be acknowledged again. Do not repeat the effect just because the ack reply was lost |
| Create response is uncertain | Do not blindly create again. The queue may exist but its creation-only tokens may be lost. There is no listing or token-recovery operation |
| Claim response is uncertain | Do not blindly claim again. A retry may take another job while the first remains claimed. Stop, allow the unknown claim's visibility window to end, and resume only under a bounded recovery plan |

Renew before a known claim's visibility expires when work needs more time.
Renewal keeps the same attempt and cannot extend the queue's lifetime. Release
only when another attempt is appropriate. After five unsuccessful claims a
job becomes `failed`.

All Queue state expires 86400 seconds after queue creation, including payloads,
completed jobs, failed jobs and deduplication state. There is no guaranteed
initial delivery or exactly-once execution. Keep an independent record of work
that must survive expiry and make external effects idempotent.
