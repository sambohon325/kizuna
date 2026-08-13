from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DigestDraft:
    subject: str
    body: str
    snapshot: dict


def _line(label: str, value: int) -> str:
    return f"- {label}: {value}"


def build_digest(
    *,
    period_start: datetime,
    period_end: datetime,
    tickets: list[dict],
    beta: list[dict],
    ops: list[dict],
    campaigns: list[dict],
) -> DigestDraft:
    urgent = [item for item in ops if item.get("needs_human") and item.get("status") == "needs_review"]
    blocked_customers = [item for item in tickets if item.get("status") in {"open", "investigating"} and item.get("severity") in {"high", "blocking"}]
    active_tickets = [item for item in tickets if item.get("status") in {"open", "investigating"}]
    issue_counts = Counter(item.get("category") or "other" for item in active_tickets)
    top_issues = [{"category": name, "count": count} for name, count in issue_counts.most_common(3)]
    beta_counts = Counter(item.get("status") or "unknown" for item in beta)
    editorial_review = [item for item in campaigns if item.get("status") in {"needs_review", "blocked"}]
    editorial_ready = [item for item in campaigns if item.get("status") in {"prepared", "approved", "ready"}]
    completed = [item for item in ops if item.get("status") in {"completed", "auto_completed"}]
    automated = [item for item in completed if item.get("auto_executed")]
    ops_tokens = sum(int(item.get("input_tokens") or 0) + int(item.get("output_tokens") or 0) for item in ops)
    editorial_tokens = sum(int(item.get("input_tokens") or 0) + int(item.get("output_tokens") or 0) for item in campaigns)

    snapshot = {
        "urgent_decisions": len(urgent),
        "blocked_customers": len(blocked_customers),
        "active_tickets": len(active_tickets),
        "top_issues": top_issues,
        "beta": dict(beta_counts),
        "editorial_review": len(editorial_review),
        "editorial_ready": len(editorial_ready),
        "automatic_actions": len(automated),
        "completed_actions": len(completed),
        "ai_tokens": ops_tokens + editorial_tokens,
    }

    issue_text = ", ".join(f"{item['category']} ({item['count']})" for item in top_issues) or "None"
    body = "\n".join(
        [
            "Kizuna daily operations digest",
            f"{period_start:%B %d, %Y %H:%M} to {period_end:%B %d, %Y %H:%M} UTC",
            "",
            "NEEDS YOU",
            _line("Urgent decisions", snapshot["urgent_decisions"]),
            _line("Customers blocked or at risk", snapshot["blocked_customers"]),
            _line("Editorial items requiring review", snapshot["editorial_review"]),
            "",
            "OPERATIONS",
            _line("Active support tickets", snapshot["active_tickets"]),
            f"- Most common support areas: {issue_text}",
            _line("Completed actions", snapshot["completed_actions"]),
            _line("Automatic actions", snapshot["automatic_actions"]),
            "",
            "BETA",
            _line("New applications", beta_counts.get("new", 0)),
            _line("Reviewing", beta_counts.get("reviewing", 0)),
            _line("Invited", beta_counts.get("invited", 0)),
            "",
            "EDITORIAL",
            _line("Ready or prepared", snapshot["editorial_ready"]),
            _line("Awaiting review", snapshot["editorial_review"]),
            "",
            "USAGE",
            _line("Recorded AI tokens", snapshot["ai_tokens"]),
            "",
            "Open the Kizuna website administrator to review details. This digest intentionally excludes customer contact information and private request text.",
        ]
    )
    return DigestDraft(subject=f"Kizuna daily digest · {period_end:%B %d, %Y}", body=body, snapshot=snapshot)
