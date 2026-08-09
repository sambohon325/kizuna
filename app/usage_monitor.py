from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_router import GeneratedText, ResolvedProvider
from app.models import AIModelRate, AIUsageEvent


def record_ai_usage(db: Session, provider: ResolvedProvider, task: str, project_id: int | None, result: GeneratedText) -> AIUsageEvent:
    rate = db.scalar(select(AIModelRate).where(AIModelRate.provider_key == provider.key, AIModelRate.model == provider.model))
    cost = 0.0
    if rate:
        uncached = max(0, result.input_tokens - result.cached_input_tokens)
        cost = (uncached * rate.input_per_million + result.cached_input_tokens * rate.cached_input_per_million + result.output_tokens * rate.output_per_million) / 1_000_000
    event = AIUsageEvent(project_id=project_id, provider_key=provider.key, model=provider.model, task=task, input_tokens=result.input_tokens, cached_input_tokens=result.cached_input_tokens, output_tokens=result.output_tokens, estimated_cost=round(cost, 8), pricing_known=bool(rate))
    db.add(event)
    return event


def usage_savings_suggestions(nodes: list, policies: list, rates: list[AIModelRate], usage_rows: list[dict]) -> list[str]:
    suggestions: list[str] = []
    if any("local_ai" in (node.capabilities or []) for node in nodes):
        suggestions.append("Use the local AI node for brainstorming, summaries, and early drafts; reserve hosted models for final creative or continuity passes.")
    if any("gpu_render" in (node.capabilities or []) for node in nodes):
        suggestions.append("This studio has a local GPU node. Auto placement can keep previews and low-resolution generations local, then send only final work to cloud capacity.")
    if usage_rows and any(not row["pricing_known"] for row in usage_rows):
        suggestions.append("Add verified model rates for every active provider so budget totals and comparisons are complete.")
    if len(rates) > 1:
        cheapest = min(rates, key=lambda rate: rate.input_per_million + rate.output_per_million)
        suggestions.append(f"{cheapest.provider_key} / {cheapest.model} has the lowest configured text-token rate; consider it for routine high-volume work after a quality check.")
    if not suggestions:
        suggestions.append("Enroll a computer or add verified model rates to unlock workload-specific savings recommendations.")
    return suggestions
