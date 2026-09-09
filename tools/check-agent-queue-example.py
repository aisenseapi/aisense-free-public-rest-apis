#!/usr/bin/env python3
"""Offline fault-injection checks; no server, account or network is used."""

import contextlib
import copy
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
MODULE_FILE = Path(__file__).resolve().parents[1] / "examples" / "agent_queue_worker.py"
SPEC = importlib.util.spec_from_file_location("agent_queue_worker_example", MODULE_FILE)
worker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = worker
SPEC.loader.exec_module(worker)

QUEUE = "a" * 32
JOB = "b" * 32
TOKEN = "c" * 64
RECEIPT = "d" * 64
START = 1800000000
EXPIRY = START + 86400


class Clock:
    def __init__(self):
        self.elapsed = 0
        self.sleeps = []

    def now(self):
        return START + self.elapsed

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.elapsed += seconds


class ScriptedTransport:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def post(self, path, arguments, timeout):
        self.calls.append((path, copy.deepcopy(arguments), timeout))
        if not self.replies:
            raise AssertionError("Unexpected additional request")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return copy.deepcopy(reply)


def claim(*, receipt=RECEIPT, until=START + 60, expiry=EXPIRY, payload=None):
    return worker.Reply(200, {
        "queue_id": QUEUE, "expire_timestamp": expiry,
        "job": {
            "job_id": JOB, "job_key": "safe-example", "receipt": receipt,
            "status": "claimed", "attempts": 1, "created_at_timestamp": START,
            "expire_timestamp": expiry, "claimed_until_timestamp": until,
            "payload": {"message": "offline test"} if payload is None else payload,
        },
    })


def empty(expiry=EXPIRY):
    return worker.Reply(200, {"queue_id": QUEUE, "expire_timestamp": expiry, "job": None})


def completed(expiry=EXPIRY):
    return worker.Reply(200, {"queue_id": QUEUE, "expire_timestamp": expiry,
                              "job": {"job_id": JOB, "status": "completed"}})


class QueueWorkerChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aisense-queue-example-check-")
        self.directory = Path(self.temporary.name) / "state"
        self.store = worker.EffectStore(self.directory)
        self.clock = Clock()

    def tearDown(self):
        self.store.close()
        self.temporary.cleanup()

    def run_worker(self, replies, **settings):
        transport = ScriptedTransport(replies)
        config = worker.Settings(QUEUE, TOKEN, **settings)
        result = worker.Worker(config, transport, self.store, now=self.clock.now,
                               monotonic=self.clock.monotonic, sleep=self.clock.sleep).run()
        return result, transport

    def rows(self):
        return self.store.connection.execute("SELECT * FROM jobs").fetchall()

    def test_empty_queue_is_bounded(self):
        result, transport = self.run_worker([empty(), empty(), empty()], max_polls=3)
        self.assertEqual(result.reason, "poll_limit_reached")
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(self.clock.sleeps, [2, 2])
        self.assertEqual(self.rows(), [])

    def test_safe_effect_is_only_a_deterministic_hash_summary(self):
        payload = {"command": "must never execute", "url": "https://never-fetch.invalid/secret"}
        result, transport = self.run_worker([claim(payload=payload), completed()])
        self.assertEqual((result.acknowledged, result.local_effects, result.exit_code), (1, 1, 0))
        self.assertEqual([call[0] for call in transport.calls], [
            "/queue/" + QUEUE + "/claim", "/queue/" + QUEUE + "/jobs/" + JOB + "/ack",
        ])
        row = self.rows()[0]
        self.assertEqual(row[:2], (QUEUE, JOB))
        self.assertEqual(len(row[2]), 64)
        raw = (self.directory / "jobs.sqlite3").read_bytes()
        for private_value in (TOKEN, RECEIPT, "never-fetch.invalid", "must never execute"):
            self.assertNotIn(private_value.encode(), raw)

    def test_timed_out_claim_is_not_retried(self):
        result, transport = self.run_worker([worker.AmbiguousReply()])
        self.assertEqual(result.reason, "claim_reply_uncertain")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(self.rows(), [])

    def test_malformed_claim_success_is_not_retried(self):
        bad = claim()
        del bad.body["job"]["receipt"]
        result, transport = self.run_worker([bad])
        self.assertEqual(result.reason, "claim_reply_uncertain")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(self.rows(), [])

    def test_claim_503_may_have_reserved_work_and_is_not_replayed(self):
        result, transport = self.run_worker([worker.Reply(503)])
        self.assertEqual(result.reason, "claim_reply_uncertain")
        self.assertEqual(len(transport.calls), 1)

    def test_ack_transport_failure_retries_the_same_receipt_after_effect(self):
        result, transport = self.run_worker([claim(), worker.AmbiguousReply(), completed()])
        self.assertEqual((result.acknowledged, result.local_effects), (1, 1))
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(transport.calls[1][:2], transport.calls[2][:2])
        self.assertEqual(transport.calls[2][1], {"receipt": RECEIPT})
        self.assertEqual(self.clock.sleeps, [1])

    def test_ack_429_and_503_have_bounded_backoff(self):
        result, transport = self.run_worker([
            claim(), worker.Reply(429), worker.Reply(503), worker.Reply(503), worker.Reply(503),
        ])
        self.assertEqual(result.reason, "retry_limit_reached")
        self.assertEqual(len(transport.calls), 5)
        self.assertEqual(self.clock.sleeps, [1, 2, 4])
        self.assertEqual(len(self.rows()), 1)
        self.assertTrue(all(call[1] == {"receipt": RECEIPT} for call in transport.calls[1:]))

    def test_claim_429_uses_bounded_backoff(self):
        result, transport = self.run_worker([worker.Reply(429)] * 4)
        self.assertEqual(result.reason, "retry_limit_reached")
        self.assertEqual(len(transport.calls), 4)
        self.assertEqual(self.clock.sleeps, [1, 2, 4])
        self.assertEqual(self.rows(), [])

    def test_auth_and_gone_statuses_stop_immediately(self):
        for status_code in (401, 403, 404, 410):
            with self.subTest(status=status_code):
                result, transport = self.run_worker([worker.Reply(status_code)])
                self.assertEqual(len(transport.calls), 1)
                self.assertEqual(result.exit_code, 1)
        self.assertEqual(self.rows(), [])

    def test_409_after_effect_means_receipt_lost(self):
        result, transport = self.run_worker([claim(), worker.Reply(409)])
        self.assertEqual(result.reason, "receipt_lost")
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(len(self.rows()), 1)

    def test_409_claim_does_not_become_an_enqueue_retry(self):
        result, transport = self.run_worker([worker.Reply(409)])
        self.assertEqual(result.reason, "unexpected_claim_conflict")
        self.assertEqual(len(transport.calls), 1)

    def test_restart_redelivery_uses_durable_job_id_dedup(self):
        self.run_worker([claim(), worker.Reply(409)])
        self.store.close()
        self.store = worker.EffectStore(self.directory)
        result, transport = self.run_worker([claim(receipt="e" * 64), completed()])
        self.assertEqual((result.acknowledged, result.local_effects), (1, 0))
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(transport.calls[-1][1], {"receipt": "e" * 64})

    def test_redelivered_job_cannot_silently_change_payload(self):
        self.run_worker([claim(), worker.Reply(409)])
        result, transport = self.run_worker([claim(receipt="e" * 64, payload={"different": True})])
        self.assertEqual(result.reason, "job_changed_since_local_effect")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(len(self.rows()), 1)

    def test_expired_claim_never_performs_effect(self):
        result, transport = self.run_worker([claim(until=START)])
        self.assertEqual(result.reason, "receipt_lost")
        self.assertEqual(self.rows(), [])
        self.assertEqual(len(transport.calls), 1)

    def test_queue_deadline_stops_ack_backoff_exactly(self):
        result, transport = self.run_worker([
            claim(until=START + 1, expiry=START + 1), worker.Reply(503),
        ])
        self.assertEqual(result.reason, "deadline_reached")
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(self.clock.sleeps, [])
        self.assertEqual(len(self.rows()), 1)

    def test_queue_expiry_cannot_move_between_claim_responses(self):
        result, transport = self.run_worker([empty(), empty(EXPIRY + 1)], max_polls=2)
        self.assertEqual(result.reason, "claim_reply_uncertain")
        self.assertEqual(len(transport.calls), 2)

    def test_overall_time_budget_bounds_empty_waits(self):
        result, transport = self.run_worker([empty()], max_seconds=1)
        self.assertEqual(result.reason, "deadline_reached")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(self.clock.sleeps, [])

    def test_integer_receipt_is_not_accepted_as_string(self):
        invalid = claim()
        invalid.body["job"]["receipt"] = int("1" * 64)
        result, _ = self.run_worker([invalid])
        self.assertEqual(result.reason, "claim_reply_uncertain")
        self.assertEqual(self.rows(), [])

    @unittest.skipIf(os.name == "nt", "Windows ACLs are account-managed, not POSIX modes")
    def test_private_directory_and_database_modes(self):
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.directory / "jobs.sqlite3").stat().st_mode), 0o600)

    def test_symlinked_database_is_refused(self):
        link_dir = Path(self.temporary.name) / "links"
        link_dir.mkdir()
        target = Path(self.temporary.name) / "untouched"
        target.write_text("do not change", encoding="utf-8")
        try:
            (link_dir / "jobs.sqlite3").symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this host")
        with self.assertRaises(worker.StopWorker):
            worker.EffectStore(link_dir)
        self.assertEqual(target.read_text(encoding="utf-8"), "do not change")

    def test_configuration_uses_environment_not_secret_arguments(self):
        settings, _ = worker.configuration([], {"AISENSE_QUEUE_ID": QUEUE, "AISENSE_QUEUE_WORKER_TOKEN": TOKEN})
        self.assertEqual(settings.worker_token, TOKEN)
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
            worker.configuration(["--worker-token", TOKEN], {})
        self.assertNotIn(TOKEN, output.getvalue())

    def test_unsafe_base_url_is_rejected_before_network(self):
        for base in ("http://example.com/services/v1", "https://user:pass@example.com/services/v1",
                     "https://example.com/services/v1?token=secret", "https://example.com/elsewhere"):
            with self.subTest(base=base), self.assertRaises(worker.StopWorker):
                worker.configuration([], {"AISENSE_QUEUE_ID": QUEUE,
                    "AISENSE_QUEUE_WORKER_TOKEN": TOKEN, "AISENSE_QUEUE_API_BASE": base})

    def test_redirect_handler_never_forwards_credentials(self):
        self.assertIsNone(worker.NoRedirect().redirect_request(None, None, 302, None, None,
                                                              "https://other.invalid/"))

    def test_truncated_http_reply_is_ambiguous_without_private_error_output(self):
        transport = worker.HTTPTransport(worker.DEFAULT_BASE, TOKEN)
        transport.opener = mock.Mock()
        transport.opener.open.side_effect = http.client.IncompleteRead(RECEIPT.encode())
        with self.assertRaises(worker.AmbiguousReply) as captured:
            transport.post("/queue/" + QUEUE + "/claim", {}, 1)
        self.assertNotIn(RECEIPT, str(captured.exception))

    def test_cli_never_prints_credentials_or_receipts(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        scripted = ScriptedTransport([claim(), completed()])
        with mock.patch.dict(os.environ, {"AISENSE_QUEUE_ID": QUEUE, "AISENSE_QUEUE_WORKER_TOKEN": TOKEN}), \
                mock.patch.object(worker, "HTTPTransport", return_value=scripted), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            # Worker default callables are bound at import, so use a future real-time deadline.
            current = int(worker.time.time())
            scripted.replies[0].body["expire_timestamp"] = current + 86400
            scripted.replies[0].body["job"]["expire_timestamp"] = current + 86400
            scripted.replies[0].body["job"]["claimed_until_timestamp"] = current + 900
            scripted.replies[1].body["expire_timestamp"] = current + 86400
            code = worker.main(["--state-dir", str(Path(self.temporary.name) / "cli")])
        self.assertEqual(code, 0)
        for secret in (TOKEN, RECEIPT):
            self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
