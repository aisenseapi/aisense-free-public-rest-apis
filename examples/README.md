# Agent Queue worker

`agent_queue_worker.py` uses Python 3.9+ and its standard library. It consumes an
existing queue. It does not create queues, enqueue jobs, execute commands from
payloads, or fetch payload URLs. See [the quickstart](../AGENT-QUICKSTART.md) for
private credential setup and producer/reader examples.

Set `AISENSE_QUEUE_ID` and `AISENSE_QUEUE_WORKER_TOKEN` in the worker's environment.
Keep credentials out of command arguments, shell history, shared logs and source
control. Only give this process its worker capability. It does not need the read
or write capabilities. Then run:

```sh
python3 examples/agent_queue_worker.py --max-jobs 1
```

The defaults stop after one acknowledged job, five polls, or 120 seconds.
`--max-jobs`, `--max-polls`, `--poll-seconds`, `--max-seconds` and
`--visibility-timeout` provide explicit bounds. Visibility defaults to 60 seconds
and accepts 30-900 seconds. The server's fixed queue expiry always takes priority.
There is no queue-lifetime argument and this example does not renew claims.

The sample effect is a durable local SQLite row containing the queue ID, job ID,
payload SHA-256 and encoded byte count. It stores neither payloads nor credentials.
The row and its deduplication key commit together before acknowledgement. When
a job is delivered again, the same local database prevents applying this sample
effect twice. The worker acknowledges with the new claim's receipt. A different
payload for an existing job ID stops the worker.

State defaults to `$LOCALAPPDATA/aisense/agent-queue-worker` on Windows, or
`~/.local/state/aisense/agent-queue-worker` otherwise. Override it with
`--state-dir /your/private/queue-worker-state`. Keep the same state directory
across retries. On POSIX the directory and database use modes 0700 and 0600.
Windows uses your account's directory ACLs. Local hash summaries persist after
server queue expiry and can be removed separately when you no longer need them.
Different machines or different state directories do not share deduplication.

The worker stops on 401/403, 404/410 and lost-receipt 409 responses. A producer's
409 for a changed payload under the same `job_key` is a different error: inspect
the producer input rather than retrying it. This worker has no enqueue path.

Claim throttling (429) uses at most three retries with 1, 2 and 4 second waits.
A lost or invalid claim reply, including a 503 which might follow a successful
reservation, stops the worker. It cannot recover an unknown receipt. Let that
claim's visibility window pass before starting another run. The example never
replays queue creation or claims after an ambiguous reply.

After the local effect commits, acknowledgements may safely retry the same job
and receipt on transport failure, 429 or 503, with the same bounded backoff.
Retries stop before claim expiry, queue expiry or the overall time limit. Receipts
remain in memory. Exit code 0 means a configured bound was reached normally.
1 means an operation stopped and needs inspection. 2 means invalid configuration.
The summary distinguishes acknowledged jobs from newly committed local effects.

This deduplication covers the SQLite sample only. If you replace it with an
external effect, that destination needs its own idempotency key or transactional
deduplication. A local record written separately from an external action cannot
make both atomic.

Run the fault-injection checks without contacting the API:

```sh
python3 -B tools/check-agent-queue-example.py
```
