from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any

from app.ai_router import AIRouterError, ResolvedProvider, generate_text


OPS_MODE = os.getenv("KIZUNA_OPS_AUTOMATION_MODE", "assist").strip().lower()
OPS_PROTOCOL = os.getenv("KIZUNA_OPS_AI_PROTOCOL", "local").strip().lower()
OPS_ENDPOINT = os.getenv("KIZUNA_OPS_AI_ENDPOINT", "").strip().rstrip("/")
OPS_MODEL = os.getenv("KIZUNA_OPS_AI_MODEL", "").strip()
OPS_API_KEY = os.getenv("KIZUNA_OPS_AI_API_KEY", "").strip()
OPS_CONFIDENCE = max(50, min(95, int(os.getenv("KIZUNA_OPS_AUTO_CONFIDENCE", "85"))))

ALLOWED_RISKS = {"low", "medium", "high", "critical"}
ESCALATION_TERMS = re.compile(
    r"\b(refund|chargeback|lawsuit|lawyer|legal action|subpoena|copyright claim|"
    r"trademark claim|hacked|breach|security incident|stolen account|unauthori[sz]ed|"
    r"delete my account|data loss|lost all|harassment|self-harm)\b",
    re.IGNORECASE,
)
KNOWN_PROPERTY_TERMS = re.compile(
    r"\b(fan[ -]?fiction|fanfic|existing franchise|known character|copyrighted character|"
    r"make (?:it|this) (?:exactly )?like|copy (?:the|a) story)\b",
    re.IGNORECASE,
)
UNSAFE_RESPONSE_TERMS = re.compile(
    r"\b(we (?:will|can) refund|refund approved|guarantee|we accept liability|"
    r"legal advice|your account has been restored|ownership has been changed|"
    r"your data (?:was|has been) deleted)\b",
    re.IGNORECASE,
)


@dataclass
class OpsDecision:
    agent: str
    classification: str
    risk: str
    confidence: int
    summary: str
    recommended_action: str
    draft_response: str
    actions: list[str]
    needs_human: bool
    provider: str = "local-policy"
    input_tokens: int = 0
    output_tokens: int = 0
    provider_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def provider_status() -> dict[str, Any]:
    configured = OPS_PROTOCOL != "local" and bool(OPS_MODEL) and (OPS_PROTOCOL == "openai" or bool(OPS_ENDPOINT))
    return {
        "mode": OPS_MODE if OPS_MODE in {"off", "assist", "autopilot"} else "assist",
        "protocol": OPS_PROTOCOL,
        "model": OPS_MODEL,
        "provider_ready": configured,
        "auto_confidence": OPS_CONFIDENCE,
    }


def _provider() -> ResolvedProvider | None:
    if not provider_status()["provider_ready"]:
        return None
    return ResolvedProvider(
        key="marketing-ops",
        name="Marketing operations AI",
        endpoint=OPS_ENDPOINT,
        model=OPS_MODEL,
        api_key=OPS_API_KEY,
        protocol=OPS_PROTOCOL,
    )


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("AI response did not contain a JSON object")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("AI response was not an object")
    return value


def _ai_refine(kind: str, record: dict[str, Any], fallback: OpsDecision) -> OpsDecision:
    provider = _provider()
    if provider is None:
        return fallback
    system = (
        "You are Kizuna's customer-operations triage agent. Kizuna helps people create original stories. "
        "Return one JSON object only. Never request passwords, API keys, payment-card data, or confidential media. "
        "Never promise refunds, legal outcomes, account restoration, publication, invitations, or deadlines. "
        "Escalate security, legal, billing disputes, ownership, deletion, safety, harassment, and irreversible actions. "
        "Allowed keys: classification, risk, confidence, summary, recommended_action, draft_response, actions, needs_human. "
        "risk must be low, medium, high, or critical; confidence is 0-100; actions is a list of short internal actions."
    )
    prompt = json.dumps({"work_type": kind, "request": record, "policy_fallback": fallback.to_dict()}, ensure_ascii=False)
    try:
        result = generate_text(provider, system=system, prompt=prompt)
        raw = _extract_json(result.text)
        risk = str(raw.get("risk", fallback.risk)).lower()
        if risk not in ALLOWED_RISKS:
            risk = fallback.risk
        confidence = max(0, min(100, int(raw.get("confidence", fallback.confidence))))
        needs_human = fallback.needs_human or bool(raw.get("needs_human", False)) or risk in {"high", "critical"}
        if fallback.needs_human and risk not in {"high", "critical"}:
            risk = fallback.risk
        actions = [str(item)[:120] for item in raw.get("actions", fallback.actions) if str(item).strip()][:8]
        draft_response = str(raw.get("draft_response", fallback.draft_response))[:6000]
        if UNSAFE_RESPONSE_TERMS.search(draft_response):
            needs_human = True
            risk = "high"
        return OpsDecision(
            agent=fallback.agent,
            classification=str(raw.get("classification", fallback.classification))[:80],
            risk=risk,
            confidence=confidence,
            summary=str(raw.get("summary", fallback.summary))[:1000],
            recommended_action=str(raw.get("recommended_action", fallback.recommended_action))[:1000],
            draft_response=draft_response,
            actions=actions or fallback.actions,
            needs_human=needs_human,
            provider=f"{provider.protocol}:{provider.model}",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    except (AIRouterError, ValueError, TypeError, json.JSONDecodeError) as exc:
        fallback.provider_error = str(exc)[:500]
        return fallback


def decide_support(record: dict[str, Any]) -> OpsDecision:
    category = str(record.get("category", "other"))
    severity = str(record.get("severity", "normal"))
    subject = str(record.get("subject", "Support request"))
    description = str(record.get("description", ""))
    sensitive = bool(ESCALATION_TERMS.search(f"{subject}\n{description}"))
    needs_human = sensitive or category in {"billing", "account"} or severity in {"high", "blocking"}
    risk = "high" if needs_human else "low"
    classification = {
        "bug": "product bug",
        "feature": "feature request",
        "feedback": "product feedback",
        "billing": "billing decision",
        "account": "account access",
    }.get(category, "general support")
    response = (
        f"Thanks for reporting this. Your reference is {record.get('reference', '')}. "
        f"Kizuna has categorized it as {classification}. "
        "We have preserved the details for review; please do not send passwords, API keys, payment-card data, or confidential media."
    )
    if category == "bug" and not record.get("environment"):
        response += " If possible, reply with your operating system, browser, and the last action taken before the issue appeared."
    fallback = OpsDecision(
        agent="Support Concierge",
        classification=classification,
        risk=risk,
        confidence=95 if needs_human else 88,
        summary=f"{severity.title()}-impact {classification}: {subject}"[:1000],
        recommended_action="Escalate with a decision brief; do not change the account or promise an outcome." if needs_human else "Acknowledge, preserve context, and route to the appropriate product queue.",
        draft_response=response,
        actions=["send acknowledgement", "preserve request context", "create product follow-up"],
        needs_human=needs_human,
    )
    return _ai_refine("support", {key: value for key, value in record.items() if key != "email"}, fallback)


def decide_beta(record: dict[str, Any]) -> OpsDecision:
    summary = str(record.get("project_summary", ""))
    known_property = bool(KNOWN_PROPERTY_TERMS.search(summary))
    needs_human = known_property
    experience = str(record.get("experience", "beginner"))
    response = (
        "Thank you for applying to the Kizuna private beta. We received your project and workflow goals. "
        "Invitations are released in small cohorts so that every creator can receive meaningful support. "
        "This application does not create an account or guarantee access."
    )
    if known_property:
        response += " Kizuna supports original stories only and cannot support fan fiction or work based on known properties."
    fallback = OpsDecision(
        agent="Beta Coordinator",
        classification="originality review" if known_property else f"{experience} creator cohort",
        risk="high" if known_property else "low",
        confidence=96 if known_property else 84,
        summary="Possible known-property request requires review." if known_property else f"Candidate for a supported {experience} workflow cohort.",
        recommended_action="Decline or request an original-project application." if known_property else "Acknowledge and place in cohort review; do not create an account yet.",
        draft_response=response,
        actions=["send acknowledgement", "score cohort fit", "hold account provisioning until invitation approval"],
        needs_human=needs_human,
    )
    return _ai_refine("beta application", {key: value for key, value in record.items() if key not in {"email", "name"}}, fallback)


def may_auto_execute(decision: OpsDecision) -> bool:
    return (
        provider_status()["mode"] == "autopilot"
        and not decision.needs_human
        and decision.risk == "low"
        and decision.confidence >= OPS_CONFIDENCE
    )
