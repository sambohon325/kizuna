from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import (
    AnimaticRender,
    AssetResidency,
    AssetRightsRecord,
    AuditLedgerEvent,
    AudioCue,
    AudioTrack,
    ComplianceClearance,
    ComplianceFindingResolution,
    CompliancePolicy,
    ComplianceProviderResult,
    ComplianceScan,
    CompositeRender,
    MasterExportJob,
    Project,
    ProfessionalIdentity,
    ProfessionalWorkClaim,
    Scene,
    Shot,
    ShotComposition,
    ShotMotionRender,
    StyleProfile,
    Timeline,
    TimelineClip,
    WorldLocation,
    Character,
    IntegrationProfile,
)


COMPLIANCE_STAGES = ["story", "style", "characters", "worlds", "shots", "timeline", "audio", "composite", "render"]
TERMS_VERSION = "2026-08-09"
SCANNER_VERSION = "kizuna-local-v1"
STAGE_CATEGORIES = {
    "story": ["text", "trademark"],
    "style": ["text", "trademark", "visual"],
    "characters": ["text", "visual"],
    "worlds": ["text", "visual"],
    "shots": ["text", "visual"],
    "timeline": ["text"],
    "audio": ["text", "audio"],
    "composite": ["visual"],
    "render": ["trademark", "visual", "audio"],
}
IMITATION_PATTERNS = [
    (r"\bin the (?:exact )?style of\b", "Replace artist/title imitation with transferable craft traits."),
    (r"\b(?:copy|clone|replicate|reproduce) (?:the |this )?(?:story|plot|character|art|design|scene|shot|song|music|melody|voice)\b", "Describe an original dramatic or craft goal instead of requesting a copy."),
    (r"\b(?:exactly|identical|indistinguishable) (?:like|to|from)\b", "Specify original differences in structure, silhouette, palette, staging, rhythm, or melody."),
    (r"\b(?:use|sample|lift) (?:the )?(?:melody|recording|dialogue|scene|character) from\b", "Use licensed material with documented rights or create a new source element."),
    (r"\b(?:official|authorized) (?:sequel|adaptation|version|soundtrack)\b", "Remove affiliation claims unless written authorization is documented."),
]
FAN_FICTION_PATTERNS = [
    (r"\b(?:write|make|create|generate|develop|produce)\s+(?:a\s+|an\s+|some\s+)?(?:fan\s*fiction|fanfic)\b", "Kizuna does not create fan fiction. Start from original characters, settings, and story premises."),
    (r"\b(?:fan\s*fiction|fanfic)\s+(?:of|about|for|based\s+on)\b", "Kizuna does not create fan fiction based on known properties."),
    (r"\b(?:unofficial|unauthorized)\s+(?:sequel|prequel|spin[ -]?off|adaptation|crossover)\b", "Kizuna cannot develop an unofficial derivative production."),
    (r"\b(?:use|include|bring\s+back)\s+(?:the\s+)?(?:characters?|world|universe)\s+from\b", "Create original characters and worlds instead of reusing a known property."),
    (r"\bcrossover\s+(?:with|between)\b", "Kizuna cannot create crossovers from known properties."),
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode()).hexdigest()


def fan_fiction_violation(value: Any) -> dict[str, str] | None:
    for text in _all_strings(value):
        normalized = " ".join(text.split())
        for pattern, guidance in FAN_FICTION_PATTERNS:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                return {"evidence": normalized[max(0, match.start() - 55):match.end() + 90], "guidance": guidance}
    return None


def verified_professional_claims(db: Session) -> list[ProfessionalWorkClaim]:
    identity = db.scalar(select(ProfessionalIdentity).where(ProfessionalIdentity.verification_status == "verified").order_by(ProfessionalIdentity.id).limit(1))
    if identity is None:
        return []
    return db.scalars(select(ProfessionalWorkClaim).where(ProfessionalWorkClaim.identity_id == identity.id, ProfessionalWorkClaim.verification_status == "verified").order_by(ProfessionalWorkClaim.id)).all()


def professional_context(db: Session) -> list[dict[str, Any]]:
    return [{"claim_id": item.id, "title": item.title, "work_type": item.work_type, "credited_role": item.credited_role, "release_year": item.release_year, "external_ids": item.external_ids, "authorization_scope": item.authorization_scope} for item in verified_professional_claims(db)]


def _verified_self_match(match: dict[str, Any], claims: list[ProfessionalWorkClaim]) -> dict[str, Any]:
    source_id = str(match.get("source_id", "")).strip().casefold()
    source_title = re.sub(r"\W+", " ", str(match.get("source", "")).casefold()).strip()
    for claim in claims:
        identifiers = {str(item).strip().casefold() for item in claim.external_ids}
        claim_title = re.sub(r"\W+", " ", claim.title.casefold()).strip()
        if (source_id and source_id in identifiers) or (source_title and claim_title and source_title == claim_title):
            return {**match, "category": "verified_prior_work", "severity": "warning", "message": "Match aligns with a verified professional work claim.", "suggestion": "Confirm this production stays within the verified authorization scope and retain the supporting evidence.", "verified_claim_id": claim.id, "authorization_scope": claim.authorization_scope}
    return match


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


def _provider_categories(profile: IntegrationProfile) -> list[str]:
    configured = profile.configuration.get("categories", []) if isinstance(profile.configuration, dict) else []
    if not configured and isinstance(profile.configuration, dict):
        configured = [item for item in profile.configuration.get("capabilities", []) if str(item).lower() in {"text", "trademark", "visual", "audio"}]
    if configured:
        return [str(item).lower() for item in configured]
    if profile.key == "kizuna-reference-scanner":
        return ["text", "trademark", "visual", "audio"]
    suffix = profile.key.removeprefix("compliance-")
    return [suffix] if suffix in {"text", "trademark", "visual", "audio"} else []


def configured_scanners(db: Session, stage: str | None = None) -> list[IntegrationProfile]:
    profiles = db.scalars(select(IntegrationProfile).where(IntegrationProfile.category == "compliance", IntegrationProfile.mode == "api", IntegrationProfile.endpoint != "").order_by(IntegrationProfile.key)).all()
    if stage is None:
        return profiles
    required = set(STAGE_CATEGORIES.get(stage, []))
    return [profile for profile in profiles if required.intersection(_provider_categories(profile))]


def _safe_match(provider_key: str, category: str, value: Any, position: int) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    severity = str(raw.get("severity", "review")).lower()
    if severity not in {"warning", "review", "block"}:
        severity = "review"
    try:
        score = max(0.0, min(1.0, float(raw.get("score", 0))))
    except (TypeError, ValueError):
        score = 0.0
    evidence = str(raw.get("evidence", raw.get("excerpt", "")))[:1000]
    source = str(raw.get("source", raw.get("title", "External corpus match")))[:300]
    source_url = str(raw.get("url", ""))[:1000]
    return {
        "id": canonical_hash([provider_key, category, position, source, evidence])[:16],
        "category": category,
        "severity": severity,
        "message": str(raw.get("message", f"{category.title()} scanner reported a possible match."))[:500],
        "evidence": evidence or source,
        "suggestion": str(raw.get("suggestion", "Review the source match, revise the material, or document applicable rights."))[:1000],
        "provider_key": provider_key,
        "source": source,
        "source_id": str(raw.get("source_id", raw.get("external_id", "")))[:300],
        "source_url": source_url,
        "score": score,
        "resolvable": True,
    }


def run_external_scanner(profile: IntegrationProfile, project_id: int, stage: str, snapshot: dict[str, Any], scan: ComplianceScan, db: Session) -> tuple[list[dict[str, Any]], bool]:
    categories = [item for item in _provider_categories(profile) if item in STAGE_CATEGORIES.get(stage, [])]
    request_body = {"protocol_version": "kizuna-compliance-v1", "project_id": project_id, "stage": stage, "categories": categories, "subject_hash": scan.subject_hash, "content": snapshot, "verified_professional_works": professional_context(db)}
    request_bytes = json.dumps(request_body, ensure_ascii=False, default=str).encode()
    request_hash = hashlib.sha256(request_bytes).hexdigest()
    result = ComplianceProviderResult(scan_id=scan.id, provider_key=profile.key, category=",".join(categories), status="running", request_hash=request_hash)
    db.add(result); db.flush()
    endpoint = profile.endpoint.strip()
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        error = "Scanner endpoint must use http or https"
        result.status, result.error = "failed", error
        return [{"id": canonical_hash([profile.key, error])[:16], "category": "scanner_unavailable", "severity": "block", "message": f"{profile.display_name or profile.key} could not run.", "evidence": error, "suggestion": "Correct or disable this scanner connection, then run the stage again.", "provider_key": profile.key, "resolvable": False}], False
    configuration = profile.configuration if isinstance(profile.configuration, dict) else {}
    path = str(configuration.get("scan_path", "/scan"))
    target = urljoin(endpoint.rstrip("/") + "/", path.lstrip("/"))
    headers = {"Content-Type": "application/json", "Accept": "application/json", "X-Kizuna-Protocol": "kizuna-compliance-v1"}
    secret = os.getenv(profile.secret_env_var, "") if profile.secret_env_var else ""
    if secret:
        headers[str(configuration.get("auth_header", "Authorization"))] = f"{configuration.get('auth_scheme', 'Bearer')} {secret}".strip()
    timeout = max(1, min(120, int(configuration.get("timeout_seconds", 30))))
    try:
        with urlopen(Request(target, data=request_bytes, headers=headers, method="POST"), timeout=timeout) as response:
            response_bytes = response.read(1_048_577)
        if len(response_bytes) > 1_048_576:
            raise ValueError("Scanner response exceeded 1 MB")
        body = json.loads(response_bytes.decode())
        if not isinstance(body, dict):
            raise ValueError("Scanner response must be a JSON object")
        raw_matches = body.get("matches", [])
        if not isinstance(raw_matches, list):
            raise ValueError("Scanner matches must be a list")
        claims = verified_professional_claims(db)
        matches = [_verified_self_match(_safe_match(profile.key, categories[0] if len(categories) == 1 else "external_similarity", item, index), claims) for index, item in enumerate(raw_matches[:100])]
        provider_status = str(body.get("status", "pass")).lower()
        if provider_status in {"review", "blocked"} and not matches:
            matches.append(_safe_match(profile.key, categories[0] if categories else "external_similarity", {"severity": "review" if provider_status == "review" else "block", "message": str(body.get("summary", "External scanner requires review.")), "evidence": str(body.get("evidence", "No match details supplied."))}, 0))
        result.status, result.response_hash, result.matches = "completed", hashlib.sha256(response_bytes).hexdigest(), matches
        return matches, True
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
        error = str(exc)[:2000]
        result.status, result.error = "failed", error
        finding = {"id": canonical_hash([profile.key, scan.subject_hash, error])[:16], "category": "scanner_unavailable", "severity": "block", "message": f"{profile.display_name or profile.key} could not complete this scan.", "evidence": error, "suggestion": "Restore or disable this scanner connection, then run the stage again.", "provider_key": profile.key, "resolvable": False}
        return [finding], False


def run_stage_scan(project_id: int, stage: str, db: Session) -> ComplianceScan:
    snapshot = stage_snapshot(project_id, stage, db)
    subject_hash = canonical_hash(snapshot)
    findings: list[dict[str, Any]] = []
    suggestions: list[str] = []
    violation = fan_fiction_violation(snapshot)
    if violation:
        findings.append({"id": canonical_hash([stage, "fan_fiction", violation["evidence"]])[:12], "category": "fan_fiction", "severity": "block", "message": "Fan-fiction and known-property derivative requests are not supported.", "evidence": violation["evidence"], "suggestion": violation["guidance"], "provider_key": "kizuna-policy", "resolvable": False})
        suggestions.append(violation["guidance"])
    for text in _all_strings(snapshot):
        normalized = " ".join(text.split())
        if len(normalized) < 8:
            continue
        for pattern, suggestion in IMITATION_PATTERNS:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            finding = {"id": canonical_hash([stage, pattern, normalized])[:12], "category": "originality", "severity": "block", "message": "Direct-copy or affiliation language needs revision.", "evidence": normalized[max(0, match.start() - 55):match.end() + 90], "suggestion": suggestion, "provider_key": "kizuna-local", "resolvable": True}
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
            findings.append({"id": canonical_hash(duplicates)[:12], "category": "asset_provenance", "severity": "warning", "message": "Identical full-resolution files appear under multiple asset records.", "evidence": f"{sum(len(items) for items in duplicates)} records share file checksums.", "suggestion": suggestions[-1], "provider_key": "kizuna-local", "resolvable": True})
    scan = ComplianceScan(
        project_id=project_id,
        stage=stage,
        subject_hash=subject_hash,
        status="running",
        coverage="preliminary",
        risk_score=0,
        scanner_version=SCANNER_VERSION,
        summary="Scan in progress.",
        findings=findings,
        suggestions=list(dict.fromkeys(suggestions)),
        input_manifest={"stage": stage, "subject_hash": subject_hash, "text_items": len(_all_strings(snapshot)), "scope": "Local pattern and internal checksum checks; not a comprehensive external copyright or trademark search."},
    )
    db.add(scan)
    db.flush()
    providers = configured_scanners(db, stage)
    provider_successes = 0
    for profile in providers:
        matches, succeeded = run_external_scanner(profile, project_id, stage, snapshot, scan, db)
        findings.extend(matches)
        suggestions.extend(item.get("suggestion", "") for item in matches if item.get("suggestion"))
        provider_successes += int(succeeded)
    # Assign fresh containers so SQLAlchemy's JSON change tracking persists
    # provider results added after the initial flush.
    scan.findings = list(findings)
    scan.suggestions = list(dict.fromkeys(suggestions))
    flag_modified(scan, "findings")
    flag_modified(scan, "suggestions")
    scan.status = "blocked" if any(item["severity"] in {"block", "review"} for item in findings) else "pass"
    scan.coverage = "external" if providers and provider_successes == len(providers) else "partial" if providers else "preliminary"
    scan.risk_score = min(100, sum(35 if item["severity"] == "block" else 20 if item["severity"] == "review" else 5 for item in findings))
    scan.summary = "No blocking originality or rights indicators were found." if scan.status == "pass" else f"{sum(item['severity'] in {'block', 'review'} for item in findings)} issue(s) require revision or documented rights."
    status = scan.status
    append_audit_event(db, project_id, "compliance", "scan_completed", subject_type="production_stage", subject_key=stage, details={"scan_id": scan.id, "status": status, "subject_hash": subject_hash, "risk_score": scan.risk_score, "scanner_version": SCANNER_VERSION})
    return scan


def latest_current_scan(project_id: int, stage: str, db: Session) -> ComplianceScan | None:
    current_hash = snapshot_hash(project_id, stage, db)
    return db.scalar(select(ComplianceScan).where(ComplianceScan.project_id == project_id, ComplianceScan.stage == stage, ComplianceScan.subject_hash == current_hash).order_by(ComplianceScan.id.desc()).limit(1))


def scan_passes(scan: ComplianceScan | None) -> bool:
    return bool(scan and scan.status in {"pass", "pass_with_resolution"})


def resolve_finding(scan: ComplianceScan, finding_id: str, status: str, reviewer: str, rationale: str, evidence_refs: list[str], db: Session) -> ComplianceFindingResolution:
    finding = next((item for item in scan.findings if item.get("id") == finding_id), None)
    if finding is None:
        raise ValueError("Finding not found in this scan")
    if not finding.get("resolvable", True):
        if finding.get("category") == "fan_fiction":
            raise PermissionError("Kizuna's no-fan-fiction policy cannot be overridden. Rework the production around original characters, worlds, and story material")
        raise PermissionError("Scanner availability failures cannot be overridden; restore or disable the scanner and run again")
    resolution = db.scalar(select(ComplianceFindingResolution).where(ComplianceFindingResolution.scan_id == scan.id, ComplianceFindingResolution.finding_id == finding_id))
    if resolution is None:
        resolution = ComplianceFindingResolution(scan_id=scan.id, finding_id=finding_id, status=status, reviewer=reviewer, rationale=rationale, evidence_refs=evidence_refs)
        db.add(resolution)
    else:
        resolution.status, resolution.reviewer, resolution.rationale, resolution.evidence_refs = status, reviewer, rationale, evidence_refs
    db.flush()
    blocking_ids = {item["id"] for item in scan.findings if item.get("severity") in {"block", "review"}}
    resolved_ids = set(db.scalars(select(ComplianceFindingResolution.finding_id).where(ComplianceFindingResolution.scan_id == scan.id)).all())
    if blocking_ids and blocking_ids.issubset(resolved_ids):
        scan.status = "pass_with_resolution"
        scan.summary = "All blocking findings have evidence-backed reviewer resolutions."
    append_audit_event(db, scan.project_id, "compliance", "finding_resolved", actor_type="rights_reviewer", subject_type="scan_finding", subject_key=f"{scan.id}:{finding_id}", details={"status": status, "reviewer": reviewer, "rationale_hash": hashlib.sha256(rationale.encode()).hexdigest(), "evidence_refs": evidence_refs})
    return resolution


def save_asset_rights(project_id: int, asset_key: str, values: dict[str, Any], reviewer: str, db: Session) -> AssetRightsRecord:
    exists = db.scalar(select(AssetResidency.id).where(AssetResidency.project_id == project_id, AssetResidency.asset_key == asset_key, AssetResidency.representation == "original").limit(1))
    if not exists:
        raise ValueError("Choose an indexed original asset from this production")
    record = db.scalar(select(AssetRightsRecord).where(AssetRightsRecord.project_id == project_id, AssetRightsRecord.asset_key == asset_key))
    if record is None:
        record = AssetRightsRecord(project_id=project_id, asset_key=asset_key)
        db.add(record)
    for key, value in values.items():
        if key != "asset_key":
            setattr(record, key, value)
    db.flush()
    append_audit_event(db, project_id, "rights", "asset_rights_recorded", actor_type="rights_reviewer", subject_type="asset", subject_key=asset_key, details={"source_type": record.source_type, "rights_holder": record.rights_holder, "license_name": record.license_name, "evidence_refs": record.evidence_refs, "reviewer": reviewer})
    return record


def compliance_overview(project_id: int, db: Session) -> dict[str, Any]:
    policy = policy_for(project_id, db)
    stages = []
    current_scan_rows: list[ComplianceScan] = []
    for stage in COMPLIANCE_STAGES:
        current_hash = snapshot_hash(project_id, stage, db)
        latest = db.scalar(select(ComplianceScan).where(ComplianceScan.project_id == project_id, ComplianceScan.stage == stage).order_by(ComplianceScan.id.desc()).limit(1))
        current = latest if latest and latest.subject_hash == current_hash else None
        if current:
            current_scan_rows.append(current)
        resolutions = db.scalars(select(ComplianceFindingResolution).where(ComplianceFindingResolution.scan_id == current.id)).all() if current else []
        resolution_map = {item.finding_id: {"status": item.status, "reviewer": item.reviewer, "rationale": item.rationale, "evidence_refs": item.evidence_refs, "created_at": item.created_at} for item in resolutions}
        findings = [{**item, "resolution": resolution_map.get(item.get("id"))} for item in current.findings] if current else []
        provider_runs = db.scalars(select(ComplianceProviderResult).where(ComplianceProviderResult.scan_id == current.id).order_by(ComplianceProviderResult.id)).all() if current else []
        stages.append({"stage": stage, "status": current.status if current else "scan_required", "stale": bool(latest and not current), "scan_id": current.id if current else None, "summary": current.summary if current else "Run a scan for the current version.", "findings": findings, "suggestions": current.suggestions if current else [], "coverage": current.coverage if current else "none", "provider_runs": [{"provider_key": item.provider_key, "category": item.category, "status": item.status, "matches": len(item.matches), "error": item.error} for item in provider_runs]})
    clearance = db.scalar(select(ComplianceClearance).where(ComplianceClearance.project_id == project_id, ComplianceClearance.scope == "release").order_by(ComplianceClearance.id.desc()).limit(1))
    rights = db.scalars(select(AssetRightsRecord).where(AssetRightsRecord.project_id == project_id).order_by(AssetRightsRecord.asset_key)).all()
    assets = db.scalars(select(AssetResidency).where(AssetResidency.project_id == project_id, AssetResidency.representation == "original").order_by(AssetResidency.asset_key, AssetResidency.id)).all()
    asset_candidates = []
    seen_assets = set()
    for item in assets:
        if item.asset_key in seen_assets:
            continue
        seen_assets.add(item.asset_key)
        asset_candidates.append({"asset_key": item.asset_key, "uri": item.uri, "checksum_sha256": item.checksum_sha256})
    scanner_profiles = configured_scanners(db)
    audit_head = db.scalar(select(AuditLedgerEvent).where(AuditLedgerEvent.project_id == project_id).order_by(AuditLedgerEvent.sequence.desc()).limit(1))
    scans_pass = all(item["status"] in {"pass", "pass_with_resolution"} for item in stages)
    rights_event = db.scalar(select(AuditLedgerEvent).where(AuditLedgerEvent.project_id == project_id, AuditLedgerEvent.category == "rights").order_by(AuditLedgerEvent.id.desc()).limit(1))
    resolution_event = db.scalar(select(AuditLedgerEvent).where(AuditLedgerEvent.project_id == project_id, AuditLedgerEvent.action == "finding_resolved").order_by(AuditLedgerEvent.id.desc()).limit(1))
    newest_review_input = max([item.created_at for item in current_scan_rows] + [item.updated_at for item in rights] + ([rights_event.created_at] if rights_event else []) + ([resolution_event.created_at] if resolution_event else []), default=None)
    clearance_current = bool(clearance and (newest_review_input is None or clearance.created_at >= newest_review_input))
    release_ready = bool(policy.accepted_at and scans_pass and (clearance_current or not policy.external_clearance_required))
    return {
        "project_id": project_id,
        "policy": {"enabled": policy.enabled, "strict_gates": policy.strict_gates, "external_clearance_required": policy.external_clearance_required, "terms_version": policy.terms_version, "accepted_by": policy.accepted_by, "accepted_at": policy.accepted_at},
        "stages": stages,
        "release_clearance": {"confirmed_by": clearance.confirmed_by, "notes": clearance.notes, "evidence_refs": clearance.evidence_refs, "created_at": clearance.created_at, "current": clearance_current} if clearance else None,
        "rights_records": [{"asset_key": item.asset_key, "source_type": item.source_type, "rights_holder": item.rights_holder, "license_name": item.license_name, "permitted_uses": item.permitted_uses, "territories": item.territories, "expires_at": item.expires_at, "evidence_refs": item.evidence_refs, "notes": item.notes, "updated_at": item.updated_at} for item in rights],
        "asset_candidates": asset_candidates,
        "scanners": [{"key": item.key, "name": item.display_name or item.key, "categories": _provider_categories(item), "ready": bool(item.endpoint)} for item in scanner_profiles],
        "release_ready": release_ready,
        "audit": {"events": audit_head.sequence if audit_head else 0, "head_hash": audit_head.event_hash if audit_head else ""},
        "legal_notice": "Kizuna provides risk-screening and records, not legal advice or a guarantee of non-infringement. The creator remains responsible for rights, licenses, clearances, disclosures, and released content. Automated checks can miss matches and should be supplemented by qualified legal review before commercial release.",
    }


def require_release_clearance(project_id: int, db: Session) -> None:
    overview = compliance_overview(project_id, db)
    if overview["policy"]["strict_gates"] and not overview["release_ready"]:
        blockers = [item["stage"] for item in overview["stages"] if item["status"] not in {"pass", "pass_with_resolution"}]
        reason = f"Current compliance scans required for: {', '.join(blockers)}." if blockers else "Creator terms and qualified release clearance are required."
        raise PermissionError(reason)
