# Kizuna render worker

Run this agent on each private-network render computer beside ComfyUI.

## Enroll once

```powershell
$env:KIZUNA_SERVER_URL="http://KIZUNA-SERVER:8000"
$env:KIZUNA_WORKER_ENROLLMENT_SECRET="your-enrollment-secret"
python -m worker.agent register --name "studio-gpu-01"
```

The command prints a worker ID and token. Store both as environment variables on that render computer; the token is shown only at enrollment.

## Run

```powershell
$env:KIZUNA_WORKER_ID="1"
$env:KIZUNA_WORKER_TOKEN="the-issued-token"
$env:KIZUNA_COMFYUI_URL="http://127.0.0.1:8188"
$env:KIZUNA_COMFYUI_WORKFLOW_PATH="C:\workflows\character-sheet-api.json"
python -m worker.agent run
```

The worker reports its GPU and CPU capabilities, renews its job lease through heartbeats, renders claimed jobs through local ComfyUI, uploads finished artifacts to Kizuna, and reports completion or retryable failure.

Use Tailscale, WireGuard, or another private network between Kizuna and its workers. Change the development enrollment secret before connecting another computer.
