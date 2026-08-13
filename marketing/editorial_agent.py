from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.ai_router import AIRouterError, generate_text
from marketing.ops_agent import _extract_json, _provider


SENSITIVE_CLAIMS = re.compile(
    r"\b(pric(?:e|ing)|discount|sale|partnership|partnered|customer|testimonial|"
    r"incident|outage|breach|lawsuit|legal|policy|guarantee|best|first|only|"
    r"available now|launch(?:ed)?|release date|revenue|funding|investor)\b",
    re.IGNORECASE,
)
CONFIDENTIAL_TERMS = re.compile(r"\b(confidential|internal only|secret|nda|unannounced|private customer)\b", re.IGNORECASE)


@dataclass
class EditorialDraft:
    risk: str
    needs_approval: bool
    rationale: str
    title: str
    excerpt: str
    blog_body: str
    social: dict[str, str]
    provider: str = "local-editorial"
    input_tokens: int = 0
    output_tokens: int = 0
    provider_error: str = ""


def assess_brief(title: str, facts: str, content_type: str) -> tuple[str, bool, str]:
    text = f"{title}\n{facts}"
    if CONFIDENTIAL_TERMS.search(text):
        return "blocked", True, "The brief appears to contain confidential or unannounced material."
    if content_type != "education" or SENSITIVE_CLAIMS.search(text):
        return "review", True, "Product, commercial, customer, incident, partnership, or policy claims require factual approval."
    return "low", False, "Routine educational material may be prepared from this approved factual brief."


def local_draft(title: str, facts: str, audience: str, goal: str, call_to_action: str, content_type: str) -> EditorialDraft:
    risk, needs_approval, rationale = assess_brief(title, facts, content_type)
    clean_facts = [line.strip(" -•\t") for line in facts.splitlines() if line.strip()]
    fact_paragraph = " ".join(clean_facts)
    excerpt = (fact_paragraph[:280].rsplit(" ", 1)[0] + "…") if len(fact_paragraph) > 280 else fact_paragraph
    body = f"{fact_paragraph}\n\n## Why it matters\n\n{goal.strip()}\n\n## For creators\n\nThis work is intended for {audience.strip()}. {call_to_action.strip()}"
    social = {
        "x": f"{title}\n\n{excerpt}\n\n{call_to_action}"[:280],
        "linkedin": f"{title}\n\n{fact_paragraph}\n\nWhy it matters: {goal}\n\n{call_to_action}"[:3000],
        "instagram": f"{title}\n\n{excerpt}\n\n{call_to_action}\n\n#Kizuna #Storytelling #AnimeProduction"[:2200],
        "tiktok": f"{title}\n\n{excerpt}\n\n{call_to_action}"[:2200],
        "youtube": f"{title}\n\n{fact_paragraph}\n\n{call_to_action}"[:5000],
    }
    return EditorialDraft(risk, needs_approval, rationale, title.strip(), excerpt, body, social)


def create_editorial_draft(title: str, facts: str, audience: str, goal: str, call_to_action: str, content_type: str) -> EditorialDraft:
    fallback = local_draft(title, facts, audience, goal, call_to_action, content_type)
    provider = _provider()
    if provider is None or fallback.risk == "blocked":
        return fallback
    system = (
        "You are Kizuna's editorial agent. Return one JSON object only with title, excerpt, blog_body, and social. "
        "social must contain x, linkedin, instagram, tiktok, and youtube strings. Use only facts in the approved brief. "
        "Do not add dates, availability, performance claims, customer claims, prices, partnerships, comparisons, or guarantees. "
        "Kizuna is an AI-assisted storytelling platform and Anime Studio is its first suite. Preserve a thoughtful, clear, non-hype voice."
    )
    prompt = json.dumps({"title": title, "approved_facts": facts, "audience": audience, "goal": goal, "call_to_action": call_to_action, "content_type": content_type}, ensure_ascii=False)
    try:
        result = generate_text(provider, system=system, prompt=prompt)
        value = _extract_json(result.text)
        social = value.get("social") if isinstance(value.get("social"), dict) else {}
        required = {key: str(social.get(key, fallback.social[key])).strip() for key in fallback.social}
        combined = "\n".join([str(value.get("title", "")), str(value.get("excerpt", "")), str(value.get("blog_body", "")), *required.values()])
        # Generated copy cannot weaken the deterministic claim gate.
        generated_risk, generated_approval, generated_reason = assess_brief(title, f"{facts}\n{combined}", content_type)
        risk = "blocked" if generated_risk == "blocked" else "review" if fallback.needs_approval or generated_approval else "low"
        return EditorialDraft(
            risk,
            risk != "low",
            generated_reason if risk != "low" else fallback.rationale,
            str(value.get("title", fallback.title))[:180],
            str(value.get("excerpt", fallback.excerpt))[:500],
            str(value.get("blog_body", fallback.blog_body))[:100000],
            required,
            provider=f"{provider.protocol}:{provider.model}",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    except (AIRouterError, ValueError, TypeError, json.JSONDecodeError) as exc:
        fallback.provider_error = str(exc)[:500]
        return fallback
