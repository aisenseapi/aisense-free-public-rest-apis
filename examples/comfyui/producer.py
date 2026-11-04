"""Producer: put render jobs on an Agent Queue, one Webhook capture per job for the result.

    python producer.py --jobs 3 --prompt "a lighthouse at dusk, oil painting"

The first run creates a queue and keeps its id and tokens in the private state directory;
later runs reuse the queue until it expires, 24 hours after creation. Each job carries the
inputs a worker applies to its ComfyUI workflow and the update URL of a capture the worker
posts the result to. Nothing is printed that would let another process read the queue.

Requests per run: one queue creation on the first run, then two per job, one capture and
one enqueue. The queue takes 100 jobs over its lifetime and 16 KiB per payload."""

import argparse
import json
import time

from common import BASE, ApiError, call, read_json, say, state_directory, write_json


def queue_handle(state):
    kept = read_json(state / "queue.json")
    if kept and kept.get("expire_timestamp", 0) > time.time() + 600:
        return kept
    made = call("POST", BASE + "/queue", {})
    handle = {key: made[key] for key in ("queue_id", "expire_timestamp", "read_token", "write_token", "worker_token")}
    write_json(state / "queue.json", handle)
    say("created queue, expires", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(handle["expire_timestamp"])))
    return handle


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jobs", type=int, default=3, help="how many render jobs to enqueue (default 3)")
    parser.add_argument("--prompt", default="a lighthouse at dusk, oil painting", help="the positive prompt")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1000, help="seed of the first job; each job adds one")
    parser.add_argument("--downloads", type=int, default=3, help="how many times the result may be downloaded, 1 to 100")
    parser.add_argument("--state-dir", help="private directory for the queue handle and the manifest")
    args = parser.parse_args()
    if not 1 <= args.downloads <= 100:
        parser.error("--downloads must be 1 to 100")

    state = state_directory(args.state_dir)
    queue = queue_handle(state)
    manifest = read_json(state / "manifest.json", {"queue_id": queue["queue_id"], "jobs": []})
    if manifest.get("queue_id") != queue["queue_id"]:
        manifest = {"queue_id": queue["queue_id"], "jobs": []}

    for n in range(args.jobs):
        seed = args.seed + n
        job_key = "render:%d" % seed
        capture = call("POST", BASE + "/webhook_capture", {})
        payload = {
            "workflow": "txt2img",
            # Paths into the worker's API-format workflow: node id, "inputs", input name.
            "inputs": {"6.inputs.text": args.prompt, "3.inputs.seed": seed, "3.inputs.steps": args.steps},
            "output": {"format": "png", "max_downloads": args.downloads},
            "result_url": capture["update_url"],
        }
        encoded = json.dumps(payload)
        if len(encoded.encode("utf-8")) > 16384:
            raise SystemExit("payload over 16 KiB; carry a reference to the workflow, not the workflow")
        try:
            job = call("POST", BASE + "/queue/%s/jobs" % queue["queue_id"], {"job_key": job_key, "payload": payload},
                       headers={"Authorization": "Bearer " + queue["write_token"]}, expect=(200, 201))
        except ApiError as error:
            if error.status == 409:
                say(job_key, "already queued with another payload; skipped")
                continue
            raise
        manifest["jobs"].append({"job_key": job_key, "job_id": job["job"]["job_id"] if "job" in job else job.get("job_id"),
                                 "capture_id": capture["capture_id"], "read_url": capture["read_url"],
                                 "wait_url": capture["wait_url"], "seed": seed})
        say("enqueued", job_key, "deduplicated" if job.get("deduplicated") else "new")

    write_json(state / "manifest.json", manifest)
    print(json.dumps({"queue_id": queue["queue_id"], "jobs": len(manifest["jobs"]),
                      "queue_expires": queue["expire_timestamp"], "state_dir": str(state)}))


if __name__ == "__main__":
    main()
