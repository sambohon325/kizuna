from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnimaticRender,
    AssetResidency,
    AuditLedgerEvent,
    AudioCue,
    AudioTrack,
    ComplianceClearance,
    CompliancePolicy,
    ComplianceScan,
    CompositeRender,
    MasterExportJob,
    Project,
    Scene,
    Shot,
    ShotComposition,
    ShotMotionRender,
    StyleProfile,
    Timeline,
    TimelineClip,
    WorldLocation,
    Character,
)


COMPLIANCE_STAGES = ["story", "style", "characters", "worlds", "shots", "timeline", "audio", "composite", "render"]
TERMS_VERSION = "2026-08-09"
SCANNER_VERSION = "kizuna-local-v1"
IMITATION_PATTERNS = [
    (r"\bin the (?:exact )?style of\b", "Replace artist/title imitation with transferable craft traits."),
    (r"\b(?:copy|clone|replicate|reproduce) (?:the |this )?(?:story|plot|character|art|design|scene|shot|song|music|melody|voice)\b", "Describe an original dramatic or craft goal instead of requesting a copy."),
    (r"\b(?:exactly|identical|indistinguishable) (?:like|to|from)\b", "Specify original differences in structure, silhouette, palette, staging, rhythm, or melody."),
    (r"\b(?:use|sample|lift) (?:the )?(?:melody|recording|dialogue|scene|character) from\b", "Use licensed material with documented rights or create a new source element."),
    (r"\b(?:official|authorized) (?:sequel|adaptation|version|soundtrack)\b", "Remove affiliation claims unless written authorization is documented."),
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode()).hexdigest()


def policy_for(project_id: int, db: Session) -> CompliancePolicy:
    policy = db.scalar(select(CompliancePolicy).where(CompliancePolicy.project_id == project_id))
    if policy is None:
        policy = CompliancePolicy(project_id=project_id, terms_version=TERMS_VERSION)
        db.add(policy)
        db.flush()
    return policy


def append_audit_event(
    db: Session,
    project_id: int,
    category: str,
    action: str,
    *,
    actor_type: str = "system",
    subject_type: str = "",
    subject_key: str = "",
    details: dict[str, Any] | None = None,
) -> AuditLedgerEvent:
    previous = db.scalar(select(AuditLedgerEvent).where(AuditLedgerEvent.project_id == project_id).order_by(AuditLedgerEvent.sequence.desc()).limit(1))
    sequence = (previous.sequence + 1) if previous else 1
    previous_hash = previous.event_hash if previous else ""
    payload = {"project_id": project_id, "sequence": sequence, "previous_hash": previous_hash, "category": category, "action": action, "actor_type": actor_type, "subject_type": subject_type, "subject_key": subject_key, "details": details or {}}
    event = AuditLedgerEvent(
        project_id=project_id,
        sequence=sequence,
        previous_hash=previous_hash,
        event_hash=canonical_hash(payload),
        category=category,
        action=action,
        actor_type=actor_type,
        subject_type=subject_type,
        subject_key=subject_key,
        details=details or {},
    )
    db.add(event)
    db.flush()
    return event


def _rows(rows: list[Any], fields: list[str]) -> list[dict[str, Any]]:
    return [{field: getattr(row, field, None) for field in fields} for row in rows]


def stage_snapshot(project_id: int, stage: str, db: Session) -> dict[str, Any]:
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError("Project not found")
    scenes = db.scalars(select(Scene).where(Scene.project_id == project_id).order_by(Scene.position)).all()
    scene_ids = [item.id for item in scenes]
    shots = db.scalars(select(Shot).where(Shot.scene_id.in_(scene_ids)).order_by(Shot.scene_id, Shot.position)).all() if scene_ids else []
    timeline = db.scalar(select(Timeline).where(Timeline.project_id == project_id))
    if stage == "story":
        brief = project.story_brief
        return {"project": {"title": project.title, "logline": project.logline}, "story": {"premise": brief.premise, "synopsis": brief.synopsis, "beats": brief.beats, "themes": brief.themes} if brief else {}}
    if stage == "style":
        profile = db.scalar(select(StyleProfile).where(StyleProfile.project_id == project_id))
        return {"style": {"era_primary": profile.era_primary, "era_secondary": profile.era_secondary, "visual": profile.visual, "direction": profile.direction, "narrative": profile.narrative, "archetypes": profile.archetypes} if profile else {}}
    if stage == "characters":
        characters = db.scalars(select(Character).where(Character.project_id == project_id).order_by(Character.id)).all()
        return {"characters": [{**_rows([item], ["id", "name", "role", "want", "need", "contradiction"])[0], "design": {"appearance": item.design.appearance, "palette": item.design.palette, "wardrobe": item.design.wardrobe, "anchors": item.design.consistency_anchors, "reference_brief": item.design.reference_brief} if item.design else {}} for item in characters]}
    if stage == "worlds":
        worlds = db.scalars(select(WorldLocation).where(WorldLocation.project_id == project_id).order_by(WorldLocation.id)).all()
        return {"worlds": [{**_rows([item], ["id", "name", "description", "narrative_function", "geography", "time_period"])[0], "design": {"appearance": item.design.appearance, "palette": item.design.palette, "layers": item.design.layers, "lighting": item.design.lighting_variants, "anchors": item.design.continuity_anchors, "reference_brief": item.design.reference_brief} if item.design else {}} for item in worlds]}
    if stage == "shots":
        return {"scenes": _rows(scenes, ["id", "title", "summary", "position"]), "shots": [{**_rows([item], ["id", "title", "description", "position", "duration_seconds"])[0], "plan": {"action": item.plan.action, "dialogue": item.plan.dialogue, "camera": item.plan.camera, "lighting": item.plan.lighting, "continuity": item.plan.continuity_notes, "prompt": item.plan.storyboard_prompt} if item.plan else {}} for item in shots]}
    if stage == "timeline":
        clips = db.scalars(select(TimelineClip).where(TimelineClip.timeline_id == timeline.id).order_by(TimelineClip.position)).all() if timeline else []
        return {"timeline": _rows([timeline], ["id", "fps", "width", "height", "status"])[0] if timeline else {}, "clips": _rows(clips, ["id", "shot_id", "position", "duration_seconds", "transition", "transition_duration", "audio_cue"])}
    if stage == "audio":
        tracks = db.scalars(select(AudioTrack).where(AudioTrack.timeline_id == timeline.id).order_by(AudioTrack.position)).all() if timeline else []
        track_ids = [item.id for item in tracks]
        cues = db.scalars(select(AudioCue).where(AudioCue.track_id.in_(track_ids)).order_by(AudioCue.start_seconds)).all() if track_ids else []
        return {"tracks": _rows(tracks, ["id", "name", "kind", "position", "volume", "muted"]), "cues": _rows(cues, ["id", "track_id", "character_id", "start_seconds", "duration_seconds", "text", "direction", "status", "uri"])}
    if stage == "composite":
        shot_ids = [item.id for item in shots]
        compositions = db.scalars(select(ShotComposition).where(ShotComposition.shot_id.in_(shot_ids)).order_by(ShotComposition.id)).all() if shot_ids else []
        comp_ids = [item.id for item in compositions]
        stills = db.scalars(select(CompositeRender).where(CompositeRender.composition_id.in_(comp_ids)).order_by(CompositeRender.id)).all() if comp_ids else []
        motion = db.scalars(select(ShotMotionRender).where(ShotMotionRender.composition_id.in_(comp_ids)).order_by(ShotMotionRender.id)).all() if comp_ids else []
        return {"compositions": _rows(compositions, ["id", "shot_id", "width", "height", "camera", "color_grade", "status", "version"]), "renders": _rows(stills + motion, ["id", "composition_id", "status", "uri", "render_settings"])}
    renders = db.scalars(select(AnimaticRender).where(AnimaticRender.timeline_id == timeline.id).order_by(AnimaticRender.id)).all() if timeline else []
    exports = db.scalars(select(MasterExportJob).where(MasterExportJob.timeline_id == timeline.id).order_by(MasterExportJob.id)).all() if timeline else []
    return {"masters": _rows(renders, ["id", "status", "uri", "render_settings"]), "exports": _rows(exports, ["id", "profile", "status", "final_uri"])}


def snapshot_hash(project_id: int, stage: str, db: Session) -> str:
    return canonical_hash(stage_snapshot(project_id, stage, db))


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _all_strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in _all_strings(item)]
    return []


def run_stage_scan(project_id: int, stage: str, db: Session) -> ComplianceScan:
    snapshot = stage_snapshot(project_id, stage, db)
    subject_hash = canonical_hash(snapshot)
    findings: list[dict[str, Any]] = []
    suggestions: list[str] = []
    for text in _all_strings(snapshot):
        normalized = " ".join(text.split())
        if len(normalized) < 8:
            continue
        for pattern, suggestion in IMITATION_PATTERNS:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            finding = {"id": canonical_hash([stage, pattern, normalized])[:12], "category": "originality", "severity": "block", "message": "Direct-copy or affiliation language needs revision.", "evidence": normalized[max(0, match.start() - 55):match.end() + 90], "suggestion": suggestion}
            if finding["id"] not in {item["id"] for item in findings}:
                findings.append(finding)
                suggestions.append(suggestion)
    if stage in {"characters", "worlds", "shots", "composite", "render", "audio"}:
        residencies = db.scalars(select(AssetResidency).where(AssetResidency.project_id == project_id, AssetResidency.representation == "original", AssetResidency.checksum_sha256 != "")).all()
        by_checksum: dict[str, set[str]] = {}
        for item in residencies:
            by_checksum.setdefault(item.checksum_sha256, set()).add(item.asset_key)
        duplicates = [keys for keys in by_checksum.values() if len(keys) > 1]
        if duplicates:
            suggestions.append("Review identical source files and document their license or remove unintended copies.")
            findings.append({"id": canonical_hash(duplicates)[:12], "category": "asset_provenance", "severity": "warning", "message": "Identical full-resolution files appear under multiple asset records.", "evidence": f"{sum(len(items) for items in duplicates)} records share file checksums.", "suggestion": suggestions[-1]})
    status = "blocked" if any(item["severity"] in {"block", "review"} for item in findings) else "pass"
    scan = ComplianceScan(
        project_id=project_id,
        stage=stage,
        subject_hash=subject_hash,
        status=status,
        coverage="preliminary",
        risk_score=min(100, sum(35 if item["severity"] == "block" else 20 for item in findings)),
        scanner_version=SCANNER_VERSION,
        summary="No direct-copy indicators found by Kizuna's preliminary scanner." if status == "pass" else f"{len(findings)} issue(s) require revision or documented rights.",
        findings=findings,
        suggestions=list(dict.fromkeys(suggestions)),
        input_manifest={"stage": stage, "subject_hash": subject_hash, "text_items": len(_all_strings(snapshot)), "scope": "Local pattern and internal checksum checks; not a comprehensive external copyright or trademark search."},
    )
    db.add(scan)
    db.flush()
    append_audit_event(db, project_id, "compliance", "scan_completed", subject_type="production_stage", subject_key=stage, details={"scan_id": scan.id, "status": status, "subject_hash": subject_hash, "risk_score": scan.risk_score, "scanner_version": SCANNER_VERSION})
    return scan


def latest_current_scan(project_id: int, stage: str, db: Session) -> ComplianceScan | None:
    current_hash = snapshot_hash(project_id, stage, db)
    return db.scalar(select(ComplianceScan).where(ComplianceScan.project_id == project_id, ComplianceScan.stage == stage, ComplianceScan.subject_hash == current_hash).order_by(ComplianceScan.id.desc()).limit(1))


def compliance_overview(project_id: int, db: Session) -> dict[str, Any]:
    policy = policy_for(project_id, db)
    stages = []
    for stage in COMPLIANCE_STAGES:
        current_hash = snapshot_hash(project_id, stage, db)
        latest = db.scalar(select(ComplianceScan).where(ComplianceScan.project_id == project_id, ComplianceScan.stage == stage).order_by(ComplianceScan.id.desc()).limit(1))
        current = latest if latest and latest.subject_hash == current_hash else None
        stages.append({"stage": stage, "status": current.status if current else "scan_required", "stale": bool(latest and not current), "scan_id": current.id if current else None, "summary": current.summary if current else "Run a scan for the current version.", "findings": current.findings if current else [], "suggestions": current.suggestions if current else [], "coverage": current.coverage if current else "none"})
    clearance = db.scalar(select(ComplianceClearance).where(ComplianceClearance.project_id == project_id, ComplianceClearance.scope == "release").order_by(ComplianceClearance.id.desc()).limit(1))
    audit_head = db.scalar(select(AuditLedgerEvent).where(AuditLedgerEvent.project_id == project_id).order_by(AuditLedgerEvent.sequence.desc()).limit(1))
    scans_pass = all(item["status"] == "pass" for item in stages)
    release_ready = bool(policy.accepted_at and scans_pass and (clearance or not policy.external_clearance_required))
    return {
        "project_id": project_id,
        "policy": {"enabled": policy.enabled, "strict_gates": policy.strict_gates, "external_clearance_required": policy.external_clearance_required, "terms_version": policy.terms_version, "accepted_by": policy.accepted_by, "accepted_at": policy.accepted_at},
        "stages": stages,
        "release_clearance": {"confirmed_by": clearance.confirmed_by, "notes": clearance.notes, "evidence_refs": clearance.evidence_refs, "created_at": clearance.created_at} if clearance else None,
        "release_ready": release_ready,
        "audit": {"events": audit_head.sequence if audit_head else 0, "head_hash": audit_head.event_hash if audit_head else ""},
        "legal_notice": "Kizuna provides risk-screening and records, not legal advice or a guarantee of non-infringement. The creator remains responsible for rights, licenses, clearances, disclosures, and released content. Automated checks can miss matches and should be supplemented by qualified legal review before commercial release.",
    }


def require_release_clearance(project_id: int, db: Session) -> None:
    overview = compliance_overview(project_id, db)
    if overview["policy"]["strict_gates"] and not overview["release_ready"]:
        blockers = [item["stage"] for item in overview["stages"] if item["status"] != "pass"]
        reason = f"Current compliance scans required for: {', '.join(blockers)}." if blockers else "Creator terms and qualified release clearance are required."
        raise PermissionError(reason)
