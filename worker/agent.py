"""Kizuna render worker for ComfyUI jobs and distributed master segments."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import tempfile
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.animatic import ffmpeg_executable
from app.generation import ComfyUIProvider, ProviderError
from app.mastering import render_timeline_master


def parse_tasks(value: str) -> set[str]:
    tasks = {item.strip() for item in value.split(",") if item.strip()}
    allowed = {"character_reference", "master_segment"}
    unknown = tasks - allowed
    if not tasks or unknown:
        raise ValueError(f"Tasks must be a comma-separated selection of: {', '.join(sorted(allowed))}")
    return tasks


def hardware_capabilities() -> dict:
    capabilities = {
        "os": platform.system(),
        "architecture": platform.machine(),
        "cpu_threads": os.cpu_count() or 1,
        "ffmpeg": False,
    }
    try:
        capabilities["ffmpeg"] = Path(ffmpeg_executable()).exists()
    except Exception:
        pass
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=True)
        capabilities["gpus"] = [
            {"name": name.strip(), "vram_mb": int(memory.strip())}
            for name, memory in (line.rsplit(",", 1) for line in result.stdout.strip().splitlines())
        ]
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        capabilities["gpus"] = []
    return capabilities


class KizunaWorker:
    def __init__(self, args):
        self.server = args.server.rstrip("/")
        self.worker_id = args.worker_id
        self.token = args.token
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.poll_seconds = max(1.0, args.poll_seconds)
        self.concurrency = max(1, args.concurrency)
        self.tasks = parse_tasks(args.tasks)
        self.provider = None
        if "character_reference" in self.tasks:
            if not args.workflow:
                raise SystemExit("Character-reference workers require --workflow or KIZUNA_COMFYUI_WORKFLOW_PATH")
            self.provider = ComfyUIProvider(args.comfyui_url, args.workflow, args.positive_node, args.negative_node, args.sampler_node)

    def heartbeat(self, status: str = "online"):
        response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/heartbeat", headers=self.headers, json={"status": status, "capabilities": hardware_capabilities()}, timeout=30)
        response.raise_for_status()

    def claim(self):
        if "master_segment" in self.tasks:
            response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/master-segments/claim", headers=self.headers, timeout=30)
            response.raise_for_status()
            if response.content:
                return {"kind": "master_segment", "payload": response.json()}
        if "character_reference" in self.tasks:
            response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/claim", headers=self.headers, timeout=30)
            response.raise_for_status()
            if response.content and response.json() is not None:
                return {"kind": "character_reference", "payload": response.json()}
        return None

    def fail_character(self, job_id: int, error: str, retryable: bool = True):
        response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/jobs/{job_id}/fail", headers=self.headers, json={"error": error[:4000], "retryable": retryable}, timeout=30)
        response.raise_for_status()

    def process_character(self, job: dict):
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
                    response = httpx.put(f"{self.server}/api/workers/{self.worker_id}/jobs/{job_id}/artifacts/{output['filename']}", headers={**self.headers, "Content-Type": output["mime_type"]}, content=Path(output["path"]).read_bytes(), timeout=120)
                    response.raise_for_status()
            response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/jobs/{job_id}/complete", headers=self.headers, json={"result_data": {"comfyui_prompt_id": submitted.external_id}}, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            self.fail_character(job_id, str(exc), retryable=True)

    def segment_heartbeat(self, segment_id: int):
        response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/master-segments/{segment_id}/heartbeat", headers=self.headers, timeout=30)
        response.raise_for_status()

    def fail_segment(self, segment_id: int, error: str, retryable: bool = True):
        response = httpx.post(f"{self.server}/api/workers/{self.worker_id}/master-segments/{segment_id}/fail", headers=self.headers, json={"error": error[:4000], "retryable": retryable}, timeout=30)
        response.raise_for_status()

    def download_asset(self, uri: str, destination: Path):
        parsed = urlparse(uri)
        url = uri if parsed.scheme in {"http", "https"} else f"{self.server}/{uri.lstrip('/')}"
        with httpx.stream("GET", url, headers=self.headers, timeout=120) as response:
            response.raise_for_status()
            with destination.open("wb") as output:
                for chunk in response.iter_bytes():
                    output.write(chunk)

    def process_segment(self, claim: dict):
        segment, export = claim["segment"], claim["export"]
        segment_id = segment["id"]
        try:
            with tempfile.TemporaryDirectory(prefix=f"kizuna-segment-{segment_id}-") as temp_dir:
                root = Path(temp_dir)
                downloaded: dict[str, Path] = {}

                def local_asset(uri: str) -> Path | None:
                    if not uri:
                        return None
                    if uri not in downloaded:
                        suffix = Path(urlparse(uri).path).suffix or ".bin"
                        target = root / f"asset-{len(downloaded):04d}{suffix}"
                        self.download_asset(uri, target)
                        downloaded[uri] = target
                    return downloaded[uri]

                clips = [{
                    "motion_source": local_asset(clip.get("motion_uri", "")),
                    "still_source": local_asset(clip.get("still_uri", "")),
                    "title": clip.get("title", ""),
                    "subtitle": clip.get("subtitle", ""),
                    "duration": float(clip["duration"]),
                    "transition": clip.get("transition", "cut"),
                    "transition_duration": float(clip.get("transition_duration", 0)),
                } for clip in segment["manifest"]["clips"]]
                audio = [{
                    "source": local_asset(cue.get("uri", "")),
                    "start": float(cue.get("start", 0)),
                    "duration": float(cue.get("duration", 0)),
                    "volume": float(cue.get("volume", 1)),
                } for cue in segment["manifest"].get("audio", [])]
                output = root / "segment.mp4"
                with ThreadPoolExecutor(max_workers=1) as renderer:
                    future = renderer.submit(render_timeline_master, clips, audio, output, root / "work", int(export["fps"]), int(export["width"]), int(export["height"]))
                    while not future.done():
                        time.sleep(self.poll_seconds)
                        self.segment_heartbeat(segment_id)
                    future.result()
                with output.open("rb") as artifact:
                    response = httpx.put(f"{self.server}/api/workers/{self.worker_id}/master-segments/{segment_id}/artifact", headers={**self.headers, "Content-Type": "video/mp4"}, content=artifact, timeout=600)
                    response.raise_for_status()
        except Exception as exc:
            try:
                self.fail_segment(segment_id, str(exc), retryable=True)
            except Exception as reporting_error:
                print(f"Segment {segment_id} failed and could not report retry state: {reporting_error}")

    def process(self, claim: dict):
        if claim["kind"] == "master_segment":
            self.process_segment(claim["payload"])
        else:
            self.process_character(claim["payload"])

    def run(self, once: bool = False):
        if once:
            self.heartbeat()
            claim = self.claim()
            if claim:
                self.process(claim)
            return
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            active: set[Future] = set()
            while True:
                active = {future for future in active if not future.done()}
                self.heartbeat("busy" if active else "online")
                while len(active) < self.concurrency:
                    claim = self.claim()
                    if not claim:
                        break
                    active.add(pool.submit(self.process, claim))
                time.sleep(self.poll_seconds)


def register(args):
    tasks = sorted(parse_tasks(args.tasks))
    response = httpx.post(f"{args.server.rstrip('/')}/api/workers/register", headers={"X-Enrollment-Secret": args.enrollment_secret}, json={"name": args.name, "hostname": platform.node() or args.name, "capabilities": hardware_capabilities(), "supported_tasks": tasks}, timeout=30)
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
    enroll.add_argument("--tasks", default=os.getenv("KIZUNA_WORKER_TASKS", "character_reference"))
    run = subparsers.add_parser("run", help="Heartbeat, claim, and render jobs")
    run.add_argument("--server", default=os.getenv("KIZUNA_SERVER_URL", "http://127.0.0.1:8000"))
    run.add_argument("--worker-id", type=int, default=os.getenv("KIZUNA_WORKER_ID"), required=not bool(os.getenv("KIZUNA_WORKER_ID")))
    run.add_argument("--token", default=os.getenv("KIZUNA_WORKER_TOKEN"), required=not bool(os.getenv("KIZUNA_WORKER_TOKEN")))
    run.add_argument("--tasks", default=os.getenv("KIZUNA_WORKER_TASKS", "character_reference"))
    run.add_argument("--concurrency", type=int, default=int(os.getenv("KIZUNA_WORKER_CONCURRENCY", "1")))
    run.add_argument("--comfyui-url", default=os.getenv("KIZUNA_COMFYUI_URL", "http://127.0.0.1:8188"))
    run.add_argument("--workflow", default=os.getenv("KIZUNA_COMFYUI_WORKFLOW_PATH"))
    run.add_argument("--positive-node", default=os.getenv("KIZUNA_COMFYUI_POSITIVE_NODE", "6"))
    run.add_argument("--negative-node", default=os.getenv("KIZUNA_COMFYUI_NEGATIVE_NODE", "7"))
    run.add_argument("--sampler-node", default=os.getenv("KIZUNA_COMFYUI_SAMPLER_NODE", "3"))
    run.add_argument("--poll-seconds", type=float, default=3.0)
    run.add_argument("--once", action="store_true")
    return root


def main():
    args = parser().parse_args()
    try:
        register(args) if args.command == "register" else KizunaWorker(args).run(once=args.once)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
