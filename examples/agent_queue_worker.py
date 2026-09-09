#!/usr/bin/env python3
"""Bounded, standard-library worker for an existing AI SENSE Agent Queue.

Credentials come only from AISENSE_QUEUE_ID and AISENSE_QUEUE_WORKER_TOKEN.
The sample effect is one durable SQLite row containing a payload hash and size,
never the payload itself. No payload instructions, paths or URLs are executed.
"""

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


DEFAULT_BASE = "https://aisenseapi.com/services/v1"
ID_PATTERN = re.compile(r"[a-f0-9]{32}\Z")
TOKEN_PATTERN = re.compile(r"[a-f0-9]{64}\Z")
KEY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}\Z")


class AmbiguousReply(Exception):
    """The request might have succeeded, but its response cannot be trusted."""


class StopWorker(Exception):
    def __init__(self, reason, exit_code=1):
        super().__init__(reason)
        self.reason = reason
        self.exit_code = exit_code


@dataclass
class Reply:
    status: int
    body: object = None


@dataclass
class Settings:
    queue_id: str
    worker_token: str
    base_url: str = DEFAULT_BASE
    max_jobs: int = 1
    max_polls: int = 5
    poll_seconds: float = 2
    max_seconds: float = 120
    visibility_timeout: int = 60
    max_retries: int = 3


@dataclass
class Result:
    reason: str
    acknowledged: int
    local_effects: int
    polls: int
    exit_code: int = 0


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the capability to a redirect target.
        return None


def reject_json_constant(value):
    raise ValueError("Non-JSON number")


class HTTPTransport:
    def __init__(self, base_url, worker_token):
        self.base_url = base_url.rstrip("/")
        self.worker_token = worker_token
        self.opener = urllib.request.build_opener(NoRedirect())

    def post(self, path, arguments, timeout):
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(arguments, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": "Bearer " + self.worker_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "aisense-agent-queue-example/1",
            },
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read(65537)
                if len(raw) > 65536:
                    raise AmbiguousReply()
                body = json.loads(raw, parse_constant=reject_json_constant)
                return Reply(response.status, body)
        except urllib.error.HTTPError as error:
            # Error bodies may contain private data; do not decode or print them.
            status_code = error.code
            error.close()
            return Reply(status_code)
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError, UnicodeError, RecursionError):
            raise AmbiguousReply() from None


def private_state_directory(directory):
    path = Path(os.path.abspath(os.path.expanduser(str(directory))))
    broad = {Path(path.anchor), Path.home(), Path.cwd(), Path(tempfile.gettempdir())}
    if path in broad:
        raise StopWorker("unsafe_state_directory")
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            raise StopWorker("unsafe_state_directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    details = path.stat()
    if not stat.S_ISDIR(details.st_mode):
        raise StopWorker("unsafe_state_directory")
    if hasattr(os, "geteuid") and details.st_uid != os.geteuid():
        raise StopWorker("unsafe_state_directory")
    os.chmod(path, 0o700)
    return path


class EffectStore:
    """The committed row is the sample effect and its durable deduplication record."""

    def __init__(self, directory):
        root = private_state_directory(directory)
        database = root / "jobs.sqlite3"
        for candidate in (database, Path(str(database) + "-journal"),
                          Path(str(database) + "-wal"), Path(str(database) + "-shm")):
            if candidate.is_symlink():
                raise StopWorker("unsafe_state_file")
            if candidate.exists():
                details = candidate.stat()
                if (not stat.S_ISREG(details.st_mode) or details.st_nlink != 1
                        or (hasattr(os, "geteuid") and details.st_uid != os.geteuid())):
                    raise StopWorker("unsafe_state_file")
                os.chmod(candidate, 0o600)
        descriptor = os.open(database, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(descriptor)
        os.chmod(database, 0o600)
        self.connection = sqlite3.connect(database, timeout=2)
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS jobs ("
            "queue_id TEXT NOT NULL, job_id TEXT NOT NULL, "
            "payload_sha256 TEXT NOT NULL, payload_bytes INTEGER NOT NULL, "
            "PRIMARY KEY (queue_id, job_id))"
        )
        self.connection.commit()

    def apply(self, queue_id, job):
        encoded = json.dumps(job["payload"], ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        with self.connection:
            inserted = self.connection.execute(
                "INSERT OR IGNORE INTO jobs VALUES (?, ?, ?, ?)",
                (queue_id, job["job_id"], digest, len(encoded)),
            ).rowcount
            existing = self.connection.execute(
                "SELECT payload_sha256, payload_bytes FROM jobs WHERE queue_id=? AND job_id=?",
                (queue_id, job["job_id"]),
            ).fetchone()
            if existing != (digest, len(encoded)):
                raise StopWorker("job_changed_since_local_effect")
        return inserted == 1

    def close(self):
        self.connection.close()


class Worker:
    def __init__(self, settings, transport, store, *, now=time.time,
                 monotonic=time.monotonic, sleep=time.sleep):
        self.settings = settings
        self.transport = transport
        self.store = store
        self.now = now
        self.monotonic = monotonic
        self.sleep = sleep
        self.deadline = monotonic() + settings.max_seconds
        self.queue_expiry = None
        self.acknowledged = 0
        self.local_effects = 0
        self.polls = 0

    def remaining(self, claim_deadline=None):
        remaining = self.deadline - self.monotonic()
        if self.queue_expiry is not None:
            remaining = min(remaining, self.queue_expiry - self.now())
        if claim_deadline is not None:
            remaining = min(remaining, claim_deadline - self.now())
        return remaining

    def pause(self, seconds, claim_deadline=None):
        if self.remaining(claim_deadline) <= seconds:
            raise StopWorker("deadline_reached", 0)
        self.sleep(seconds)

    def request(self, operation, path, arguments, claim_deadline=None):
        for attempt in range(self.settings.max_retries + 1):
            remaining = self.remaining(claim_deadline)
            if remaining <= 0:
                raise StopWorker("deadline_reached", 0)
            try:
                reply = self.transport.post(path, arguments, min(10, remaining))
            except AmbiguousReply:
                if operation == "claim":
                    raise StopWorker("claim_reply_uncertain") from None
                # Ack is idempotent: retry only the same job and receipt.
                reply = Reply(503)
            if reply.status == 200:
                return reply.body
            if reply.status in (401, 403):
                raise StopWorker("authorization_refused")
            if reply.status in (404, 410):
                raise StopWorker("queue_missing_or_expired")
            if reply.status == 409:
                # This worker never enqueues. Here 409 means receipt loss, not
                # the separate producer error for a conflicting job_key.
                raise StopWorker("receipt_lost" if operation == "ack" else "unexpected_claim_conflict")
            if operation == "claim" and reply.status == 503:
                # A storage failure can occur after reserving a job. Its receipt
                # is unknown, so even this explicit error must not be replayed.
                raise StopWorker("claim_reply_uncertain")
            if reply.status not in (429, 503):
                raise StopWorker("unexpected_http_status")
            if attempt == self.settings.max_retries:
                raise StopWorker("retry_limit_reached")
            self.pause(2 ** attempt, claim_deadline)
        raise StopWorker("retry_limit_reached")

    def validate_claim(self, body):
        if not isinstance(body, dict) or body.get("queue_id") != self.settings.queue_id:
            raise StopWorker("claim_reply_uncertain")
        expiry = body.get("expire_timestamp")
        if (type(expiry) is not int or expiry <= 0
                or (self.queue_expiry is not None and expiry != self.queue_expiry)):
            raise StopWorker("claim_reply_uncertain")
        self.queue_expiry = expiry
        if "job" not in body:
            raise StopWorker("claim_reply_uncertain")
        job = body["job"]
        if job is None:
            return None
        if (not isinstance(job, dict)
                or not isinstance(job.get("job_id"), str) or not ID_PATTERN.fullmatch(job["job_id"])
                or not isinstance(job.get("receipt"), str) or not TOKEN_PATTERN.fullmatch(job["receipt"])
                or not isinstance(job.get("job_key"), str) or not KEY_PATTERN.fullmatch(job["job_key"])
                or job.get("status") != "claimed"
                or job.get("expire_timestamp") != expiry
                or type(job.get("attempts")) is not int or not 1 <= job["attempts"] <= 5
                or type(job.get("claimed_until_timestamp")) is not int
                or not 0 < job["claimed_until_timestamp"] <= expiry
                or "payload" not in job):
            raise StopWorker("claim_reply_uncertain")
        return job

    def run(self):
        reason = "job_limit_reached"
        exit_code = 0
        try:
            while self.acknowledged < self.settings.max_jobs:
                if self.polls >= self.settings.max_polls:
                    reason = "poll_limit_reached"
                    break
                self.polls += 1
                path = "/queue/" + self.settings.queue_id
                body = self.request("claim", path + "/claim", {
                    "visibility_timeout": self.settings.visibility_timeout,
                })
                job = self.validate_claim(body)
                if job is None:
                    if self.polls < self.settings.max_polls:
                        self.pause(self.settings.poll_seconds)
                    continue
                claim_deadline = job["claimed_until_timestamp"]
                if self.remaining(claim_deadline) <= 0:
                    raise StopWorker("receipt_lost")
                self.local_effects += int(self.store.apply(self.settings.queue_id, job))
                acknowledgement = self.request(
                    "ack", path + "/jobs/" + job["job_id"] + "/ack",
                    {"receipt": job["receipt"]}, claim_deadline,
                )
                if (not isinstance(acknowledgement, dict)
                        or acknowledgement.get("queue_id") != self.settings.queue_id
                        or acknowledgement.get("expire_timestamp") != self.queue_expiry
                        or not isinstance(acknowledgement.get("job"), dict)
                        or acknowledgement["job"].get("job_id") != job["job_id"]
                        or acknowledgement["job"].get("status") != "completed"):
                    raise StopWorker("ack_reply_invalid_local_effect_preserved")
                self.acknowledged += 1
                # Neither receipts nor role capabilities enter the local database.
                del job
        except StopWorker as error:
            reason, exit_code = error.reason, error.exit_code
        return Result(reason, self.acknowledged, self.local_effects, self.polls, exit_code)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes bad argv values; a mistakenly supplied token
        # must not be printed by this example's argument-error path.
        self.exit(2, "Invalid arguments. Use --help; credentials belong in environment variables.\n")


def configuration(argv=None, environ=None):
    environ = os.environ if environ is None else environ
    parser = SafeParser(description=__doc__)
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--max-polls", type=int, default=5)
    parser.add_argument("--poll-seconds", type=float, default=2)
    parser.add_argument("--max-seconds", type=float, default=120)
    parser.add_argument("--visibility-timeout", type=int, default=60)
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args(argv)
    queue_id = environ.get("AISENSE_QUEUE_ID", "")
    token = environ.get("AISENSE_QUEUE_WORKER_TOKEN", "")
    base = environ.get("AISENSE_QUEUE_API_BASE", DEFAULT_BASE).rstrip("/")
    url = urllib.parse.urlsplit(base)
    if (not ID_PATTERN.fullmatch(queue_id) or not TOKEN_PATTERN.fullmatch(token)
            or url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.path != "/services/v1"
            or not 1 <= args.max_jobs <= 100 or not 1 <= args.max_polls <= 100
            or not 0 <= args.poll_seconds <= 60 or not 1 <= args.max_seconds <= 86400
            or not 30 <= args.visibility_timeout <= 900):
        raise StopWorker("invalid_configuration", 2)
    settings = Settings(queue_id, token, base, args.max_jobs, args.max_polls,
                        args.poll_seconds, args.max_seconds, args.visibility_timeout)
    default_root = Path(environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "state")))
    state_dir = args.state_dir or default_root / "aisense" / "agent-queue-worker"
    return settings, state_dir


def main(argv=None):
    store = None
    try:
        settings, directory = configuration(argv)
        store = EffectStore(directory)
        result = Worker(settings, HTTPTransport(settings.base_url, settings.worker_token), store).run()
        print(f"Worker stopped: {result.reason}, acknowledged={result.acknowledged}, "
              f"new_local_effects={result.local_effects}, polls={result.polls}.")
        return result.exit_code
    except StopWorker as error:
        print("Worker stopped: " + error.reason + ".", file=sys.stderr)
        return error.exit_code
    except (OSError, sqlite3.Error, ValueError, TypeError):
        print("Worker stopped: local_state_or_response_unavailable.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Worker interrupted; local effects remain durable.", file=sys.stderr)
        return 130
    finally:
        if store is not None:
            store.close()


if __name__ == "__main__":
    sys.exit(main())
