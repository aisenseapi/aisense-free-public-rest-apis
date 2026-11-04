"""Collector: wait for each job's result, download the image once and check its SHA-256.

    python collector.py --out ./renders

Reads the manifest the producer wrote. For every job it calls the capture's wait URL, which holds
the connection for up to 25 seconds and returns as soon as the worker has posted the result, then
downloads the image from Storage and compares the digest with the one in the result. Each wait
call is one request; a job that takes ten minutes costs about 24 of them, so for long renders set
--wait-rounds and come back, or let the producer give the capture a notify_url of your own."""

import argparse
import json
import pathlib
import time

from common import ApiError, call, download, read_json, say, sha256, state_directory, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="renders", help="directory for the downloaded images")
    parser.add_argument("--wait-rounds", type=int, default=24, help="wait calls of 25 seconds per job before giving up for now")
    parser.add_argument("--state-dir")
    args = parser.parse_args()

    state = state_directory(args.state_dir)
    manifest = read_json(state / "manifest.json")
    if not manifest or not manifest.get("jobs"):
        raise SystemExit("no manifest: run producer.py first")
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    collected = 0
    for job in manifest["jobs"]:
        if job.get("collected"):
            collected += 1
            continue
        result = None
        for _ in range(args.wait_rounds):
            try:
                answer = call("GET", job["wait_url"], expect=(200,))
            except ApiError as error:
                say(job["job_key"], "capture answered", error.status, "; giving up on it")
                break
            if "request" in answer:
                body = (answer["request"].get("body") or {}).get("json")
                if isinstance(body, dict) and body.get("storage_url"):
                    result = body
                else:
                    say(job["job_key"], "the capture holds something that is not a result; skipping")
                break
        if not result:
            say(job["job_key"], "not finished yet")
            continue
        status, headers, data = download(result["storage_url"])
        if status != 200:
            say(job["job_key"], "download answered", status, "; the object may have reached its download limit")
            continue
        digest = sha256(data)
        if digest != result.get("sha256"):
            say(job["job_key"], "digest mismatch; not saved")
            continue
        target = out / ("%s.png" % job["job_key"].replace(":", "-"))
        target.write_bytes(data)
        job["collected"] = {"path": str(target), "bytes": len(data), "sha256": digest,
                            "downloads_left": headers.get("Downloads-Left"), "at": int(time.time())}
        collected += 1
        say("saved", target.name, len(data), "bytes, downloads left:", headers.get("Downloads-Left"))

    write_json(state / "manifest.json", manifest)
    print(json.dumps({"collected": collected, "jobs": len(manifest["jobs"]), "out": str(out)}))


if __name__ == "__main__":
    main()
