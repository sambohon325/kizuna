# Network render farm

Kizuna render workers make outbound requests to the Kizuna server, so worker database and queue ports never need to be public.

## Server configuration

Set a strong enrollment secret and use the farm provider:

```env
KIZUNA_GENERATION_PROVIDER=farm
KIZUNA_WORKER_ENROLLMENT_SECRET=a-long-random-secret
KIZUNA_WORKER_LEASE_SECONDS=300
KIZUNA_MAX_ARTIFACT_BYTES=67108864
```

The enrollment secret is only used to add a new computer. Each enrolled worker receives its own bearer token, stored as a SHA-256 hash by Kizuna.

## Add a computer

Install this repository and its Python dependencies on the render computer, make sure its local ComfyUI workflow works, then follow [the worker instructions](../worker/README.md).

Workers report operating system, CPU threads, NVIDIA GPU names, and VRAM. The scheduler only gives character-reference work to workers advertising that capability.

## Job safety

- Claims are leases, not permanent ownership.
- Heartbeats extend active leases.
- Abandoned leases return their jobs to the queue.
- Retryable failures return jobs to the queue.
- Workers may only upload to jobs leased to their token.
- A job cannot complete until at least one artifact has been uploaded.
- Filenames are replaced with server-generated names before storage.
- Upload size is bounded by `KIZUNA_MAX_ARTIFACT_BYTES`.

Use TLS and a private overlay network such as Tailscale or WireGuard. Do not expose worker tokens, the enrollment secret, ComfyUI, PostgreSQL, or Redis to the public internet.

## Master export segments

Workers may opt into the `master_segment` capability. The authenticated contract is:

- `POST /api/workers/{worker_id}/master-segments/claim` leases one queued segment and returns its frozen clip/audio manifest plus output settings.
- `POST /api/workers/{worker_id}/master-segments/{segment_id}/heartbeat` renews the lease while FFmpeg is rendering.
- `POST /api/workers/{worker_id}/master-segments/{segment_id}/fail` reports a retryable or terminal failure.
- The worker downloads the manifest assets, renders with matching FPS and dimensions, then uploads an MP4 to `PUT /api/workers/{worker_id}/master-segments/{segment_id}/artifact`.
- The server stores a SHA-256 checksum and marks the segment complete. Missing or altered files are detected by the resume audit and queued again.

The bundled agent supports both ComfyUI character jobs and FFmpeg master segments. Tasks are selected per machine, and concurrency is bounded with `KIZUNA_WORKER_CONCURRENCY` or `--concurrency`.
