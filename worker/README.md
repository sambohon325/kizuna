# Kizuna render worker

Run this agent on each private-network render computer. A worker can render ComfyUI character references, FFmpeg master-export segments, or both.

## Enroll once

Choose the work this computer should accept:

```powershell
$env:KIZUNA_SERVER_URL="http://KIZUNA-SERVER:8000"
$env:KIZUNA_WORKER_ENROLLMENT_SECRET="your-enrollment-secret"
$env:KIZUNA_WORKER_TASKS="master_segment"
python -m worker.agent register --name "studio-render-01"
```

Valid task selections are `character_reference`, `master_segment`, or `character_reference,master_segment`. The command prints a worker ID and token. Store both securely as environment variables; the token is shown only at enrollment.

## Run an FFmpeg master worker

```powershell
$env:KIZUNA_WORKER_ID="1"
$env:KIZUNA_WORKER_TOKEN="the-issued-token"
$env:KIZUNA_WORKER_TASKS="master_segment"
$env:KIZUNA_WORKER_CONCURRENCY="2"
python -m worker.agent run
```

This mode does not require ComfyUI. The agent downloads the frozen segment manifest, renders locally, renews its lease during long renders, uploads the MP4, and reports retryable failures.

## Run a ComfyUI character worker

```powershell
$env:KIZUNA_WORKER_ID="2"
$env:KIZUNA_WORKER_TOKEN="the-issued-token"
$env:KIZUNA_WORKER_TASKS="character_reference"
$env:KIZUNA_COMFYUI_URL="http://127.0.0.1:8188"
$env:KIZUNA_COMFYUI_WORKFLOW_PATH="C:\workflows\character-sheet-api.json"
python -m worker.agent run
```

Use the same task selection at registration and runtime. Keep concurrency at `1` until the machine's GPU memory and ComfyUI workflow have been tested under parallel load.

Use Tailscale, WireGuard, or another private network between Kizuna and its workers. Change the development enrollment secret before connecting another computer.
