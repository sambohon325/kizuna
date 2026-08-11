# Durable jobs

Kizuna's long-running work uses a database ledger as its source of truth. Redis carries lightweight wake-up notifications so workers can respond quickly, but workers also poll the ledger. A Redis restart or missed notification therefore does not lose accepted work.

Each job records its kind, project, payload, priority, progress, attempts, result, error, cancellation state, lease owner, lease expiry, and append-only progress events. An idempotency key prevents the same requested output from being queued twice. A worker claims a job for a bounded lease; if that lease expires, Kizuna returns the job to the queue until its retry limit is reached.

Working-media proxy generation is the first workload on this contract. More production workloads will move onto the same state machine without changing their creator-facing APIs.

## Local development

The default `KIZUNA_JOB_INLINE_FALLBACK=true` keeps one-command development simple. Jobs are still recorded with their complete lifecycle, but the web process performs them immediately. Redis is optional.

## Production

Docker Compose starts Redis and the `job-worker` service. The web service uses `KIZUNA_JOB_INLINE_FALLBACK=false`, so it can return without blocking while the worker processes queued media jobs. Both services must share the database, render volume, and storage volume.

The worker records a persistent service heartbeat and emits structured JSON events when it starts, claims a job, completes a job, or records a failure. Studio administrators can see stale worker heartbeats and job recovery guidance in **Settings → Operations**; Coolify Logs retains the corresponding detailed event stream.

Operators can inspect `GET /api/jobs`, filter by project, status, or kind, open `GET /api/jobs/{id}` for event history, request cancellation, and retry failed or cancelled work.
