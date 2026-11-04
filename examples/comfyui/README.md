# ComfyUI agents: a render farm on three free endpoints

Three small Python scripts, standard library only, that run image jobs through
ComfyUI from any number of machines without a server of your own:

| Script | Role | Endpoints it uses |
| --- | --- | --- |
| `producer.py` | Puts render jobs on a queue, one capture per job for the result | Agent Queue, Webhook capture |
| `worker.py` | Claims a job, renders it in ComfyUI, uploads the image, posts the result, acknowledges | Agent Queue, Storage, Webhook capture |
| `collector.py` | Waits for each result, downloads the image once, checks its SHA-256 | Webhook capture, Storage |

No account and no API key. The queue, the captures and the stored images all
expire by themselves within 24 hours. `worker.py --fake` renders a gradient PNG
locally, so the whole flow runs on a laptop without ComfyUI installed.

## Why a queue, a store and a capture

An agent that drives ComfyUI directly hits three walls. A render takes minutes,
longer than most HTTP clients and agent tool calls are willing to wait. The
image has to get from the GPU machine to whoever asked for it. And the asker
is usually gone by the time the image exists. The three endpoints take one wall
each:

- **Agent Queue** holds the job while nobody is connected. A worker claims it
  for a visibility window, renews the claim while the render runs, and
  acknowledges when done; an unacknowledged claim returns the job to the
  queue, so a worker that dies loses nothing but time.
- **Storage** takes the finished PNG as a plain multipart upload and answers a
  URL, the byte count and a SHA-256. With `max_downloads/{n}` the URL works
  exactly n times and then answers 410.
- **Webhook capture** gives every job a URL that remembers the first request
  posted to it. The worker posts the result there; the collector waits on it
  with a call that holds for up to 25 seconds and returns the moment the
  result lands. Nothing polls ComfyUI from outside.

## Run it in five minutes, without ComfyUI

```sh
cd examples/comfyui
python producer.py --jobs 3 --prompt "a lighthouse at dusk, oil painting"
python worker.py --fake --poll-seconds 5 --max-seconds 30
python collector.py --out ./renders
```

The producer creates a queue on its first run and keeps the id and the three
role tokens in a private state directory (`%LOCALAPPDATA%\aisense\comfyui-example`
on Windows, `~/.local/state/aisense/comfyui-example` elsewhere, or `--state-dir`).
The worker reads the worker token from there, or from `AISENSE_QUEUE_ID` and
`AISENSE_QUEUE_WORKER_TOKEN` on another machine. Give a render machine the
worker token only; it does not need the read or write token.

## Run it with ComfyUI

Export your workflow from ComfyUI in API format (Save (API Format) in the
developer menu). Node ids in that file are the keys a job's `inputs` address:

```json
"inputs": { "6.inputs.text": "a lighthouse at dusk", "3.inputs.seed": 1000, "3.inputs.steps": 20 }
```

Then, on each machine that has ComfyUI running:

```sh
python worker.py --comfyui http://127.0.0.1:8188 --workflow workflow_api.json --visibility 600
```

The worker posts the graph to ComfyUI's `/prompt`, polls `/history/{prompt_id}`
until the first image exists, fetches it from `/view`, and carries on as in
fake mode. A render that runs past half the visibility window renews the claim
once. Set `--visibility` to about twice your longest render, 30 to 900 seconds.

## What each side costs

Every address has 5,000 requests a day across all endpoints, so the scripts are
frugal and say what they spend:

| Step | Requests | Notes |
| --- | --- | --- |
| Producer, first run | 1 | Creates the queue; 100 jobs per queue over 24 hours |
| Producer, per job | 2 | One capture, one enqueue; payload at most 16 KiB |
| Worker, per empty poll | 1 | `--poll-seconds 20` all day is about 4,300 requests; run it while jobs are expected |
| Worker, per job | 4 to 5 | Claim, upload, result post, ack, and a renew for a long render |
| Collector, per job | 1 per 25 s of waiting | A ten minute render costs about 24; `--wait-rounds` bounds it |

Storage takes 80 MB per address per day in total and refuses executables.
Captured results are capped at 256 KB, which the result JSON never approaches.
A job's payload carries inputs and a result URL, not the workflow itself: an
API-format workflow is often larger than 16 KiB.

## What this does not do

- It does not move video. 80 MB a day is room for PNGs and thumbnails.
- It does not keep anything. Queue, captures and images are gone within 24
  hours; download what you need, or pass the storage URL on at once.
- It does not run ComfyUI for you, and it does not execute anything from a
  payload: the worker applies values to inputs of a workflow you exported.
- It does not retry forever. The worker releases a failed job for another
  attempt; after five attempts the queue marks the job failed.

## Order of operations in the worker, and why

Render, upload, post the result, acknowledge. If the worker dies after
posting but before acknowledging, the job is delivered again, rendered again
and uploaded again; the second result post is ignored because a capture keeps
the first request only, so the collector still sees one result. The price of
that order is one duplicate upload in a rare case, against the alternative of
acknowledging first and losing the result if the post fails.

## Where the pieces are documented

- [Agent Queue](https://aisense.no/free-public-api-agent-queue-api-endpoint):
  tokens, claim, renew, ack, release, limits.
- [Storage](https://aisense.no/free-public-api-storage-api-endpoint): upload
  shapes, `max_downloads`, `Downloads-Left`, the daily budget.
- [Webhook capture](https://aisense.no/free-public-api-webhook-capture-api-endpoint):
  the update URL, the wait route, `notify_url`.
- The same endpoints as MCP tools, for an agent that drives this without a
  script: [free MCP server](https://aisense.no/free-public-mcp-server).
