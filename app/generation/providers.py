from __future__ import annotations

import html
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import httpx


class ProviderError(RuntimeError):
    pass


@dataclass
class ProviderResult:
    status: str
    external_id: str = ""
    outputs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MockProvider:
    name = "mock"

    def __init__(self, render_directory: Path):
        self.render_directory = render_directory

    def submit(self, job_id: int, character_name: str, prompt: str, **_: Any) -> ProviderResult:
        self.render_directory.mkdir(parents=True, exist_ok=True)
        filename = f"character-reference-{job_id}.svg"
        destination = self.render_directory / filename
        short_prompt = html.escape(prompt[:460])
        name = html.escape(character_name)
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720"><defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#191521"/><stop offset="1" stop-color="#5d3d68"/></linearGradient></defs><rect width="1280" height="720" fill="#f4f1ea"/><rect x="40" y="40" width="1200" height="640" rx="28" fill="url(#g)"/><circle cx="260" cy="330" r="140" fill="#e98b76" opacity=".75"/><circle cx="260" cy="265" r="60" fill="#f5d1c8"/><path d="M145 530 Q260 350 375 530" fill="#30253c"/><text x="460" y="160" fill="#f39c87" font-family="Arial" font-size="22" letter-spacing="4">REFERENCE SHEET SIMULATION</text><text x="460" y="225" fill="white" font-family="Arial" font-weight="bold" font-size="52">{name}</text><foreignObject x="460" y="270" width="690" height="280"><div xmlns="http://www.w3.org/1999/xhtml" style="font:22px/1.5 Arial;color:#ddd2ea">{short_prompt}</div></foreignObject><text x="460" y="620" fill="#b8adc3" font-family="Arial" font-size="18">Mock provider · connect ComfyUI for rendered artwork</text></svg>'''
        destination.write_text(svg, encoding="utf-8")
        return ProviderResult(status="completed", external_id=f"mock-{uuid4()}", outputs=[{"filename": filename, "mime_type": "image/svg+xml", "path": str(destination)}], metadata={"simulation": True})


class ComfyUIProvider:
    name = "comfyui"

    def __init__(self, base_url: str, workflow_path: str, positive_node: str, negative_node: str, sampler_node: str):
        self.base_url = base_url.rstrip("/")
        self.workflow_path = Path(workflow_path) if workflow_path else None
        self.positive_node = positive_node
        self.negative_node = negative_node
        self.sampler_node = sampler_node

    def _workflow(self, prompt: str, negative_prompt: str, seed: int | None) -> dict[str, Any]:
        if not self.workflow_path or not self.workflow_path.exists():
            raise ProviderError("Set KIZUNA_COMFYUI_WORKFLOW_PATH to a ComfyUI workflow exported in API format")
        workflow = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        try:
            workflow[self.positive_node]["inputs"]["text"] = prompt
            workflow[self.negative_node]["inputs"]["text"] = negative_prompt
            workflow[self.sampler_node]["inputs"]["seed"] = seed if seed is not None else random.randint(0, 2**32 - 1)
        except KeyError as exc:
            raise ProviderError(f"Configured ComfyUI node is missing: {exc}") from exc
        return workflow

    def submit(self, job_id: int, character_name: str, prompt: str, negative_prompt: str, seed: int | None = None) -> ProviderResult:
        workflow = self._workflow(prompt, negative_prompt, seed)
        try:
            response = httpx.post(f"{self.base_url}/prompt", json={"prompt": workflow, "client_id": f"kizuna-{job_id}"}, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"ComfyUI submission failed: {exc}") from exc
        data = response.json()
        if "prompt_id" not in data:
            raise ProviderError(f"ComfyUI rejected the workflow: {data}")
        return ProviderResult(status="submitted", external_id=data["prompt_id"], metadata={"queue_number": data.get("number")})

    def poll(self, external_id: str) -> ProviderResult:
        try:
            response = httpx.get(f"{self.base_url}/history/{external_id}", timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"ComfyUI status check failed: {exc}") from exc
        history = response.json().get(external_id)
        if not history:
            return ProviderResult(status="running", external_id=external_id)
        outputs = []
        for node_output in history.get("outputs", {}).values():
            for image in node_output.get("images", []):
                query = urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")})
                outputs.append({**image, "url": f"{self.base_url}/view?{query}"})
        status = "completed" if outputs else "failed"
        return ProviderResult(status=status, external_id=external_id, outputs=outputs, metadata={"history": history.get("status", {})})

    def materialize(self, outputs: list[dict[str, Any]], render_directory: Path, job_id: int) -> list[dict[str, Any]]:
        render_directory.mkdir(parents=True, exist_ok=True)
        local_outputs = []
        for index, output in enumerate(outputs, start=1):
            suffix = Path(output["filename"]).suffix.lower() or ".png"
            filename = f"comfyui-job-{job_id}-{index}{suffix}"
            destination = render_directory / filename
            try:
                response = httpx.get(output["url"], timeout=60)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ProviderError(f"Could not copy ComfyUI output into asset storage: {exc}") from exc
            destination.write_bytes(response.content)
            local_outputs.append({"filename": filename, "mime_type": response.headers.get("content-type", "image/png").split(";")[0], "path": str(destination), "source": output})
        return local_outputs
