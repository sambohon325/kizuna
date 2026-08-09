from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.integration_catalog import INTEGRATION_CATALOG
from app.models import AIProviderRoute, IntegrationProfile


AI_TASKS: dict[str, dict[str, str]] = {
    "assistant": {"label": "Studio Assistant", "description": "Page-aware help, co-writing, co-directing, and workflow guidance."},
    "writer": {"label": "Writer", "description": "Premise, structure, scenes, dialogue, and story adaptation."},
    "director": {"label": "Director", "description": "Coverage, staging, performance, lenses, and continuity."},
    "character_designer": {"label": "Character Designer", "description": "Original character bibles, silhouettes, costumes, and consistency locks."},
    "background_artist": {"label": "Background Artist", "description": "World geography, reusable layers, lighting, and staging."},
    "animator": {"label": "Animator", "description": "Motion plans, acting beats, camera movement, and timing."},
    "editor": {"label": "Editor", "description": "Pacing, continuity, assembly decisions, and missing-work flags."},
    "sound_producer": {"label": "Sound Producer", "description": "Dialogue, music, ambience, effects, and mix direction."},
    "producer": {"label": "Producer", "description": "Cross-department coordination and next-step planning."},
}


class AIRouterError(RuntimeError):
    pass


@dataclass
class ResolvedProvider:
    key: str
    name: str
    endpoint: str
    model: str
    api_key: str
    protocol: str


def _profile_values(key: str, profile: IntegrationProfile | None) -> tuple[str, str, str]:
    definition = INTEGRATION_CATALOG.get(key, {})
    endpoint = profile.endpoint if profile and profile.endpoint else definition.get("default_endpoint", "")
    model = profile.model if profile and profile.model else definition.get("default_model", "")
    secret_env_var = profile.secret_env_var if profile else definition.get("secret_env_var", "")
    return endpoint.rstrip("/"), model, secret_env_var


def provider_readiness(key: str, profile: IntegrationProfile | None, model_override: str = "") -> tuple[bool, str]:
    if key == "local":
        return True, "Built-in private guidance"
    if not profile or profile.mode != "api":
        return False, "Connect this engine first"
    endpoint, model, secret_env_var = _profile_values(key, profile)
    if not endpoint:
        return False, "Endpoint required"
    if not (model_override or model):
        return False, "Model required"
    if key in {"openai", "anthropic", "google"} and not ((key == "openai" and settings.openai_api_key) or (secret_env_var and os.getenv(secret_env_var))):
        return False, "Server secret required"
    return True, "Ready"


def resolve_provider(db: Session, task: str) -> ResolvedProvider | None:
    route = db.scalar(select(AIProviderRoute).where(AIProviderRoute.task == task))
    if route is None or route.provider_key == "local":
        return None
    profile = db.scalar(select(IntegrationProfile).where(IntegrationProfile.key == route.provider_key))
    ready, note = provider_readiness(route.provider_key, profile, route.model_override)
    if not ready:
        raise AIRouterError(note)
    endpoint, model, secret_env_var = _profile_values(route.provider_key, profile)
    if urlparse(endpoint).scheme not in {"http", "https"}:
        raise AIRouterError("Provider endpoint must use http or https")
    api_key = settings.openai_api_key if route.provider_key == "openai" and settings.openai_api_key else os.getenv(secret_env_var, "")
    protocol = (profile.configuration or {}).get("protocol", "openai-compatible") if profile else "openai-compatible"
    if route.provider_key in {"openai", "anthropic", "google", "ollama"}:
        protocol = route.provider_key
    return ResolvedProvider(route.provider_key, profile.display_name or INTEGRATION_CATALOG.get(route.provider_key, {}).get("name", route.provider_key), endpoint, route.model_override or model, api_key, protocol)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 90) -> dict[str, Any]:
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise AIRouterError(f"Provider returned {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AIRouterError(f"Could not reach provider: {exc}") from exc


def generate_text(provider: ResolvedProvider, *, system: str, prompt: str) -> str:
    try:
        if provider.protocol == "openai":
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise AIRouterError("The OpenAI client is not installed on this server") from exc
            client = OpenAI(api_key=provider.api_key or "not-required", base_url=provider.endpoint or None, timeout=90)
            response = client.responses.create(model=provider.model, instructions=system, input=prompt)
            text = response.output_text
        elif provider.protocol == "anthropic":
            data = _post_json(f"{provider.endpoint}/v1/messages", {"model": provider.model, "max_tokens": 1800, "system": system, "messages": [{"role": "user", "content": prompt}]}, {"x-api-key": provider.api_key, "anthropic-version": "2023-06-01"})
            text = "\n".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        elif provider.protocol == "google":
            model = provider.model.removeprefix("models/")
            data = _post_json(f"{provider.endpoint}/v1beta/models/{quote(model, safe='')}:generateContent", {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": prompt}]}]}, {"x-goog-api-key": provider.api_key})
            text = "\n".join(part.get("text", "") for candidate in data.get("candidates", []) for part in candidate.get("content", {}).get("parts", []))
        elif provider.protocol == "ollama":
            data = _post_json(f"{provider.endpoint}/api/generate", {"model": provider.model, "system": system, "prompt": prompt, "stream": False}, {})
            text = data.get("response", "")
        else:
            headers = {"Authorization": f"Bearer {provider.api_key}"} if provider.api_key else {}
            data = _post_json(f"{provider.endpoint}/chat/completions", {"model": provider.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "stream": False}, headers)
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except AIRouterError:
        raise
    except Exception as exc:
        raise AIRouterError(str(exc)) from exc
    if not text or not text.strip():
        raise AIRouterError("Provider returned an empty response")
    return text.strip()
