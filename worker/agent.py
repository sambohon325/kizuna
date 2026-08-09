"""Kizuna render worker agent.

Register once to receive a worker ID and token, then run the agent beside a
private ComfyUI instance. Credentials are read from environment variables so
tokens do not need to be committed or placed in command history.
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

from app.generation import ComfyUIProvider, ProviderError


def hardware_capabilities() -> dict:
    capabilities = {"os": platform.system(), "architecture": platform.machine(), "cpu_threads": os.cpu_count() or 1}
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=True)
        gpus = []
        for line in result.stdout.strip().splitlines():
            name, memory = [part.strip() for part in line.rsplit(",", 1)]
            gpus.append({"name": name, "vram_mb": int(memory)})
        capabilities["gpus"] = gpus
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        capabilities["gpus"] = []
    return capabilities


class KizunaWorker:
    def __init__(self, args):
        self.server = args.server.rstrip("/")
        self.worker_id = args.worker_id
        self.token = args.token
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.poll_seconds = args.poll_seconds
        self.provider = ComfyUIProvider(args.comfyui_url, args.workflow, args.positive_node, args.negative_node, args.sampler_node)

    def heartbeat(self, status: str = "online"):
        response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/heartbeat", headers=self.headers, json={"status": status, "capabilities": hardware_capabilities()}, timeout=30)
        response.raise_for_status()

    def claim(self):
        response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/claim", headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json() if response.content else None

    def fail(self, job_id: int, error: str, retryable: bool = True):
        response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/jobs/{job_id}/fail", headers=self.headers, json={"error": error[:4000], "retryable": retryable}, timeout=30)
        response.raise_for_status()

    def process(self, job: dict):
        job_id = job["id"]
        try:
            self.heartbeat("busy")
            submitted = self.provider.submit(job_id, f"character-{job['character_id']}", job["prompt"], negative_prompt=job["negative_prompt"])
            while True:
                time.sleep(self.poll_seconds)
                self.heartbeat("busy")
                result = self.provider.poll(submitted.external_id)
                if result.status == "running":
                    continue
                if result.status != "completed":
                    raise ProviderError("ComfyUI finished without a usable output")
                break
            with tempfile.TemporaryDirectory(prefix=f"kizuna-job-{job_id}-") as temp_dir:
                outputs = self.provider.materialize(result.outputs, Path(temp_dir), job_id)
                for output in outputs:
                    content = Path(output["path"]).read_bytes()
                    response = httpx.put(f"{self.server}/api/workers/{self.worker_id}/jobs/{job_id}/artifacts/{output['filename']}", headers={**self.headers, "Content-Type": output["mime_type"]}, content=content, timeout=120)
                    response.raise_for_status()
            response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/jobs/{job_id}/complete", headers=self.headers, json={"result_data": {"comfyui_prompt_id": submitted.external_id}}, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            self.fail(job_id, str(exc), retryable=True)

    def run(self, once: bool = False):
        while True:
            self.heartbeat()
            job = self.claim()
            if job:
                self.process(job)
            if once:
                return
            time.sleep(self.poll_seconds)


def register(args):
    response = httpx.post(f"{args.server.rstrip('/')}/api/workers/register", headers={"X-Enrollment-Secret": args.enrollment_secret}, json={"name": args.name, "hostname": platform.node() or args.name, "capabilities": hardware_capabilities(), "supported_tasks": ["character_reference"]}, timeout=30)
    response.raise_for_status()
    worker = response.json()
    print("Worker enrolled. Store these values securely on this render machine:")
    print(f"KIZUNA_WORKER_ID={worker['id']}")
    print(f"KIZUNA_WORKER_TOKEN={worker['token']}")


def parser():
    root = argparse.ArgumentParser(description="Kizuna network render worker")
    subparsers = root.add_subparsers(dest="command", required=True)
    enroll = subparsers.add_parser("register", help="Enroll this machine and receive its token")
    enroll.add_argument("--server", default=os.getenv("KIZUNA_SERVER_URL", "http://127.0.0.1:8000"))
    enroll.add_argument("--name", default=platform.node() or "render-worker")
    enroll.add_argument("--enrollment-secret", default=os.getenv("KIZUNA_WORKER_ENROLLMENT_SECRET"), required=not bool(os.getenv("KIZUNA_WORKER_ENROLLMENT_SECRET")))
    run = subparsers.add_parser("run", help="Heartbeat, claim, and render jobs")
    run.add_argument("--server", default=os.getenv("KIZUNA_SERVER_URL", "http://127.0.0.1:8000"))
    run.add_argument("--worker-id", type=int, default=os.getenv("KIZUNA_WORKER_ID"), required=not bool(os.getenv("KIZUNA_WORKER_ID")))
    run.add_argument("--token", default=os.getenv("KIZUNA_WORKER_TOKEN"), required=not bool(os.getenv("KIZUNA_WORKER_TOKEN")))
    run.add_argument("--comfyui-url", default=os.getenv("KIZUNA_COMFYUI_URL", "http://127.0.0.1:8188"))
    run.add_argument("--workflow", default=os.getenv("KIZUNA_COMFYUI_WORKFLOW_PATH"), required=not bool(os.getenv("KIZUNA_COMFYUI_WORKFLOW_PATH")))
    run.add_argument("--positive-node", default=os.getenv("KIZUNA_COMFYUI_POSITIVE_NODE", "6"))
    run.add_argument("--negative-node", default=os.getenv("KIZUNA_COMFYUI_NEGATIVE_NODE", "7"))
    run.add_argument("--sampler-node", default=os.getenv("KIZUNA_COMFYUI_SAMPLER_NODE", "3"))
    run.add_argument("--poll-seconds", type=float, default=3.0)
    run.add_argument("--once", action="store_true")
    return root


def main():
    args = parser().parse_args()
    if args.command == "register":
        register(args)
    else:
        KizunaWorker(args).run(once=args.once)


if __name__ == "__main__":
    main()
