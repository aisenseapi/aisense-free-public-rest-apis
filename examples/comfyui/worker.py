"""Worker: claim render jobs, run them through ComfyUI, hand the image to Storage and post the result.

    python worker.py --fake                      # no ComfyUI needed: renders a gradient PNG locally
    python worker.py --comfyui http://127.0.0.1:8188 --workflow workflow_api.json

The queue id and worker token come from the producer's state directory (--state-dir) or from the
environment, AISENSE_QUEUE_ID and AISENSE_QUEUE_WORKER_TOKEN. A job holds `inputs`, a map of
"node.inputs.name" paths applied to your API-format workflow, and `result_url`, the capture the
result is posted to.

Order per job: render, upload to Storage with the download limit the job asks for, post the result
to the job's capture, acknowledge the claim. A capture keeps the first request only, so a redelivered
job that posts again does not overwrite the result. Requests per job: one claim, one upload, one
result post, one ack, plus one renew for every long render. Between jobs the worker sleeps
--poll-seconds (default 20); a worker that polls all day spends about 4,300 of the 5,000 requests
an address has per day, so run it while jobs are expected, not forever."""

import argparse
import json
import os
import time
import urllib.parse
import uuid

from common import BASE, ApiError, call, download, fake_png, read_json, say, sha256, state_directory, upload_file


def credentials(args):
    if args.state_dir or not (os.environ.get("AISENSE_QUEUE_ID") and os.environ.get("AISENSE_QUEUE_WORKER_TOKEN")):
        kept = read_json(state_directory(args.state_dir) / "queue.json")
        if kept:
            return kept["queue_id"], kept["worker_token"]
    queue_id = os.environ.get("AISENSE_QUEUE_ID")
    token = os.environ.get("AISENSE_QUEUE_WORKER_TOKEN")
    if not (queue_id and token):
        raise SystemExit("no queue: run producer.py first, or set AISENSE_QUEUE_ID and AISENSE_QUEUE_WORKER_TOKEN")
    return queue_id, token


def apply_inputs(workflow, inputs):
    """Set "node.inputs.name" paths in a copy of the API-format workflow."""
    graph = json.loads(json.dumps(workflow))
    for path, value in inputs.items():
        node, _, name = path.partition(".inputs.")
        if node not in graph or not name:
            raise ValueError("input path %r is not in the workflow" % path)
        graph[node].setdefault("inputs", {})[name] = value
    return graph


def render_with_comfyui(base, workflow, inputs, timeout):
    """POST the graph to /prompt, poll /history until the first image, fetch it from /view."""
    graph = apply_inputs(workflow, inputs)
    client = uuid.uuid4().hex
    queued = call("POST", base.rstrip("/") + "/prompt", {"prompt": graph, "client_id": client}, expect=(200,))
    prompt_id = queued["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        history = call("GET", base.rstrip("/") + "/history/" + prompt_id, expect=(200,))
        entry = history.get(prompt_id)
        if entry and entry.get("outputs"):
            for output in entry["outputs"].values():
                for image in output.get("images", []):
                    query = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""),
                                                    "type": image.get("type", "output")})
                    status, _, data = download(base.rstrip("/") + "/view?" + query)
                    if status == 200:
                        return data
            raise RuntimeError("ComfyUI finished without an image")
        time.sleep(2)
    raise TimeoutError("ComfyUI did not finish within %d seconds" % timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fake", action="store_true", help="render locally without ComfyUI")
    parser.add_argument("--comfyui", default="http://127.0.0.1:8188", help="ComfyUI base URL")
    parser.add_argument("--workflow", help="an API-format workflow JSON exported from ComfyUI")
    parser.add_argument("--render-timeout", type=int, default=600, help="seconds to wait for one render")
    parser.add_argument("--visibility", type=int, default=300, help="claim window in seconds, 30 to 900")
    parser.add_argument("--poll-seconds", type=int, default=20, help="sleep between empty claims")
    parser.add_argument("--max-seconds", type=int, default=600, help="stop after this long with nothing to do")
    parser.add_argument("--max-jobs", type=int, default=100)
    parser.add_argument("--state-dir")
    args = parser.parse_args()
    if not args.fake and not args.workflow:
        parser.error("give --workflow (an API-format JSON) or use --fake")
    workflow = None if args.fake else json.load(open(args.workflow, encoding="utf-8"))

    queue_id, token = credentials(args)
    auth = {"Authorization": "Bearer " + token}
    done = 0
    idle_since = time.time()
    while done < args.max_jobs:
        claimed = call("POST", BASE + "/queue/%s/claim" % queue_id, {"visibility_timeout": args.visibility}, headers=auth, expect=(200,))
        job = claimed.get("job")
        if not job:
            if time.time() - idle_since > args.max_seconds:
                say("nothing to do for %d seconds; stopping" % args.max_seconds)
                break
            time.sleep(args.poll_seconds)
            continue
        idle_since = time.time()
        payload = job.get("payload") or {}
        receipt = job["receipt"]
        job_path = BASE + "/queue/%s/jobs/%s" % (queue_id, job["job_id"])
        say("claimed", job.get("job_key"), "attempt", job.get("attempts"))
        try:
            inputs = payload.get("inputs") or {}
            started = time.time()
            if args.fake:
                image = fake_png(json.dumps(inputs, sort_keys=True))
            else:
                image = render_with_comfyui(args.comfyui, workflow, inputs, args.render_timeout)
            if time.time() - started > args.visibility / 2:
                call("POST", job_path + "/renew", {"receipt": receipt, "visibility_timeout": args.visibility}, headers=auth, expect=(200,))
            limit = int((payload.get("output") or {}).get("max_downloads") or 0)
            where = BASE + "/storage" + ("/max_downloads/%d" % limit if limit else "")
            stored = upload_file(where, "%s.png" % job.get("job_key", "render").replace(":", "-"), image)
            if stored.get("sha256_hash") != sha256(image):
                raise RuntimeError("stored hash differs from the rendered image")
            result = {"job_key": job.get("job_key"), "job_id": job["job_id"], "storage_url": stored["storage_url"],
                      "sha256": stored["sha256_hash"], "bytes": stored["bytes"], "downloads_left": stored.get("downloads_left"),
                      "expire_timestamp": stored.get("expire_timestamp"), "rendered_in_seconds": round(time.time() - started, 1)}
            if payload.get("result_url"):
                call("POST", payload["result_url"], result, expect=(200, 201))
            call("POST", job_path + "/ack", {"receipt": receipt}, headers=auth, expect=(200,))
            done += 1
            say("done", job.get("job_key"), stored["bytes"], "bytes")
        except (ApiError, RuntimeError, TimeoutError, ValueError) as error:
            say("failed", job.get("job_key"), str(error))
            try:
                call("POST", job_path + "/release", {"receipt": receipt}, headers=auth, expect=(200,))
            except ApiError as release_error:
                say("release failed too", str(release_error))
            if isinstance(error, ApiError) and error.status in (401, 403, 404, 410, 429):
                break
    print(json.dumps({"queue_id": queue_id, "completed": done}))


if __name__ == "__main__":
    main()
