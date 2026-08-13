from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AnimaticRender, AudioCue, AudioTrack, BackgroundAsset, BackgroundJob, Character,
    CharacterRelationship, CompositionLayer, CompositeRender, CrewAction, CrewAssignment,
    DeliveryLink, DurableJob, GenerationJob, MasterExportJob, MediaAsset, MediaTransferJob,
    ProductionWorkflow, ProjectBackup, ProjectMembership, Scene, Shot, ShotComposition,
    ShotMotionRender, StoryboardAsset, StoryboardJob, Timeline, TimelineClip, User,
    UserSession, WorldLocation,
)

SESSION_COOKIE = "kizuna_session"
CSRF_COOKIE = "kizuna_csrf"
PASSWORD_ITERATIONS = 600_000
PUBLIC_PREFIXES = ("/static/", "/api/workers/", "/api/nodes/", "/api/internal/")
PUBLIC_EXACT = {"/api/health", "/api/auth/status", "/api/auth/setup", "/api/auth/login", "/api/auth/trial", "/api/auth/password/forgot", "/api/auth/verification/resend", "/api/billing/stripe/webhook", "/login", "/signup", "/forgot-password", "/setup"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
        return secrets.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_session(user: User, db: Session) -> tuple[str, str, UserSession]:
    session_token, csrf_token = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    session = UserSession(user_id=user.id, token_hash=token_hash(session_token), csrf_hash=token_hash(csrf_token), expires_at=utcnow() + timedelta(days=max(1, settings.session_days)))
    db.add(session)
    db.flush()
    return session_token, csrf_token, session


def request_identity(request: Request, db: Session) -> tuple[User | None, UserSession | None]:
    raw = request.cookies.get(SESSION_COOKIE, "")
    if not raw:
        return None, None
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash(raw)))
    if not session or session.expires_at <= utcnow():
        if session:
            db.delete(session); db.commit()
        return None, None
    user = db.get(User, session.user_id)
    if not user or not user.active:
        return None, None
    if session.last_seen_at < utcnow() - timedelta(hours=1):
        session.last_seen_at = utcnow(); db.commit()
    return user, session


def public_path(path: str) -> bool:
    return path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIXES) or path.startswith(("/delivery/", "/invite/", "/beta-invite/", "/reset-password/", "/verify-email/", "/api/auth/invitations/", "/api/auth/beta-invitations/", "/api/auth/password/reset/", "/api/auth/verify/", "/api/internal/account-steward/"))


def has_membership(db: Session, user_id: int, project_id: int) -> bool:
    return db.scalar(select(ProjectMembership.id).where(ProjectMembership.user_id == user_id, ProjectMembership.project_id == project_id)) is not None


def project_membership(db: Session, user_id: int, project_id: int) -> ProjectMembership | None:
    return db.scalar(select(ProjectMembership).where(ProjectMembership.user_id == user_id, ProjectMembership.project_id == project_id))


def user_project_ids(db: Session, user_id: int) -> list[int]:
    return list(db.scalars(select(ProjectMembership.project_id).where(ProjectMembership.user_id == user_id)).all())


def _id(path: str, pattern: str) -> int | None:
    match = re.match(pattern, path)
    return int(match.group(1)) if match else None


def _project_from_shot(db: Session, shot_id: int) -> int | None:
    return db.scalar(select(Scene.project_id).join(Shot, Shot.scene_id == Scene.id).where(Shot.id == shot_id))


def _project_from_timeline(db: Session, timeline_id: int) -> int | None:
    return db.scalar(select(Timeline.project_id).where(Timeline.id == timeline_id))


def project_for_path(db: Session, path: str) -> int | None:
    direct_project = _id(path, r"^/api/projects/(\d+)(?:/|$)") or _id(path, r"^/api/media/(?:thumbnails|proxies)/(\d+)(?:/|$)")
    if direct_project:
        return direct_project

    direct_models = (
        (r"^/api/backups/(\d+)", ProjectBackup), (r"^/api/delivery-links/(\d+)", DeliveryLink),
        (r"^/api/jobs/(\d+)", DurableJob), (r"^/api/media-transfers/(\d+)", MediaTransferJob),
        (r"^/api/crew-assignments/(\d+)", CrewAssignment), (r"^/api/crew-actions/(\d+)", CrewAction),
        (r"^/api/producer-workflows/(\d+)", ProductionWorkflow),
    )
    for pattern, model in direct_models:
        item_id = _id(path, pattern)
        if item_id:
            item = db.get(model, item_id)
            return item.project_id if item else None

    character_id = _id(path, r"^/api/characters/(\d+)")
    if character_id:
        item = db.get(Character, character_id); return item.project_id if item else None
    relationship_id = _id(path, r"^/api/character-relationships/(\d+)")
    if relationship_id:
        return db.scalar(select(Character.project_id).join(CharacterRelationship, CharacterRelationship.character_id == Character.id).where(CharacterRelationship.id == relationship_id))
    location_id = _id(path, r"^/api/locations/(\d+)")
    if location_id:
        item = db.get(WorldLocation, location_id); return item.project_id if item else None
    scene_id = _id(path, r"^/api/scenes/(\d+)")
    if scene_id:
        item = db.get(Scene, scene_id); return item.project_id if item else None
    shot_id = _id(path, r"^/api/shots/(\d+)")
    if shot_id:
        return _project_from_shot(db, shot_id)

    job_lookups = (
        (r"^/api/background-jobs/(\d+)", select(WorldLocation.project_id).join(BackgroundJob, BackgroundJob.location_id == WorldLocation.id).where),
        (r"^/api/generation-jobs/(\d+)", select(Character.project_id).join(GenerationJob, GenerationJob.character_id == Character.id).where),
        (r"^/api/storyboard-jobs/(\d+)", select(Scene.project_id).join(Shot, Shot.scene_id == Scene.id).join(StoryboardJob, StoryboardJob.shot_id == Shot.id).where),
    )
    for pattern, where_method in job_lookups:
        item_id = _id(path, pattern)
        if item_id:
            model = BackgroundJob if "background" in pattern else GenerationJob if "generation" in pattern else StoryboardJob
            return db.scalar(where_method(model.id == item_id))

    timeline_id = _id(path, r"^/api/timelines/(\d+)")
    if timeline_id:
        return _project_from_timeline(db, timeline_id)
    clip_id = _id(path, r"^/api/timeline-clips/(\d+)")
    if clip_id:
        return db.scalar(select(Timeline.project_id).join(TimelineClip, TimelineClip.timeline_id == Timeline.id).where(TimelineClip.id == clip_id))
    track_id = _id(path, r"^/api/audio-tracks/(\d+)")
    if track_id:
        return db.scalar(select(Timeline.project_id).join(AudioTrack, AudioTrack.timeline_id == Timeline.id).where(AudioTrack.id == track_id))
    cue_id = _id(path, r"^/api/audio-cues/(\d+)")
    if cue_id:
        return db.scalar(select(Timeline.project_id).join(AudioTrack, AudioTrack.timeline_id == Timeline.id).join(AudioCue, AudioCue.track_id == AudioTrack.id).where(AudioCue.id == cue_id))

    composition_id = _id(path, r"^/api/compositions/(\d+)")
    if composition_id:
        return db.scalar(select(Scene.project_id).join(Shot, Shot.scene_id == Scene.id).join(ShotComposition, ShotComposition.shot_id == Shot.id).where(ShotComposition.id == composition_id))
    layer_id = _id(path, r"^/api/composition-layers/(\d+)")
    if layer_id:
        return db.scalar(select(Scene.project_id).join(Shot, Shot.scene_id == Scene.id).join(ShotComposition, ShotComposition.shot_id == Shot.id).join(CompositionLayer, CompositionLayer.composition_id == ShotComposition.id).where(CompositionLayer.id == layer_id))
    export_id = _id(path, r"^/api/master-exports/(\d+)")
    if export_id:
        return db.scalar(select(Timeline.project_id).join(MasterExportJob, MasterExportJob.timeline_id == Timeline.id).where(MasterExportJob.id == export_id))

    asset_match = re.match(r"^/api/assets/(character|background|storyboard)/(\d+)", path)
    if asset_match:
        kind, asset_id = asset_match.group(1), int(asset_match.group(2))
        if kind == "character":
            item = db.get(MediaAsset, asset_id); return item.project_id if item else None
        if kind == "background":
            return db.scalar(select(WorldLocation.project_id).join(BackgroundAsset, BackgroundAsset.location_id == WorldLocation.id).where(BackgroundAsset.id == asset_id))
        return db.scalar(select(Scene.project_id).join(Shot, Shot.scene_id == Scene.id).join(StoryboardAsset, StoryboardAsset.shot_id == Shot.id).where(StoryboardAsset.id == asset_id))
    return None


def project_for_render_uri(db: Session, uri: str) -> int | None:
    project_id = db.scalar(select(MediaAsset.project_id).where(MediaAsset.uri == uri))
    if project_id:
        return project_id
    project_id = db.scalar(select(WorldLocation.project_id).join(BackgroundAsset, BackgroundAsset.location_id == WorldLocation.id).where(BackgroundAsset.uri == uri))
    if project_id:
        return project_id
    project_id = db.scalar(select(Scene.project_id).join(Shot, Shot.scene_id == Scene.id).join(StoryboardAsset, StoryboardAsset.shot_id == Shot.id).where(StoryboardAsset.uri == uri))
    if project_id:
        return project_id
    for model, uri_column, join_column in ((AnimaticRender, AnimaticRender.uri, AnimaticRender.timeline_id),):
        project_id = db.scalar(select(Timeline.project_id).join(model, join_column == Timeline.id).where(uri_column == uri))
        if project_id:
            return project_id
    project_id = db.scalar(select(Timeline.project_id).join(MasterExportJob, MasterExportJob.timeline_id == Timeline.id).where(MasterExportJob.final_uri == uri))
    if project_id:
        return project_id
    for model in (CompositeRender, ShotMotionRender):
        project_id = db.scalar(select(Scene.project_id).join(Shot, Shot.scene_id == Scene.id).join(ShotComposition, ShotComposition.shot_id == Shot.id).join(model, model.composition_id == ShotComposition.id).where(model.uri == uri))
        if project_id:
            return project_id
    project_id = db.scalar(select(Timeline.project_id).join(AudioTrack, AudioTrack.timeline_id == Timeline.id).join(AudioCue, AudioCue.track_id == AudioTrack.id).where(AudioCue.uri == uri))
    return project_id


def safe_render_path(request_path: str, render_root: Path) -> Path | None:
    relative = request_path.removeprefix("/renders/")
    candidate = (render_root / relative).resolve()
    return candidate if render_root in candidate.parents and candidate.is_file() else None
