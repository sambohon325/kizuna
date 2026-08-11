from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(32), default="creator")
    account_tier: Mapped[str] = mapped_column(String(32), default="collaborator")
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    failed_sign_in_count: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sign_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AccountToken(Base):
    __tablename__ = "account_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    purpose: Mapped[str] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AccountSecurityEvent(Base):
    __tablename__ = "account_security_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64))
    network_hash: Mapped[str] = mapped_column(String(64), default="")
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SignupAttempt(Base):
    __tablename__ = "signup_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    network_hash: Mapped[str] = mapped_column(String(64))
    email_hash: Mapped[str] = mapped_column(String(64))
    accepted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    provider: Mapped[str] = mapped_column(String(32), default="stripe")
    customer_id: Mapped[str] = mapped_column(String(160), unique=True)
    subscription_id: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    plan_key: Mapped[str] = mapped_column(String(64), default="creator")
    status: Mapped[str] = mapped_column(String(32), default="incomplete")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="stripe")
    event_id: Mapped[str] = mapped_column(String(160), unique=True)
    event_type: Mapped[str] = mapped_column(String(100))
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(32), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StudioInvitation(Base):
    __tablename__ = "studio_invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(160), default="")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    project_roles: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    logline: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="development")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    style_profile: Mapped[StyleProfile | None] = relationship(back_populates="project", cascade="all, delete-orphan", uselist=False)
    story_brief: Mapped[StoryBrief | None] = relationship(back_populates="project", cascade="all, delete-orphan", uselist=False)
    characters: Mapped[list[Character]] = relationship(back_populates="project", cascade="all, delete-orphan", order_by="Character.id")
    locations: Mapped[list[WorldLocation]] = relationship(back_populates="project", cascade="all, delete-orphan", order_by="WorldLocation.id")
    scenes: Mapped[list[Scene]] = relationship(back_populates="project", cascade="all, delete-orphan", order_by="Scene.position")
    timeline: Mapped[Timeline | None] = relationship(back_populates="project", cascade="all, delete-orphan", uselist=False)
    scope: Mapped[ProductionScope | None] = relationship(back_populates="project", cascade="all, delete-orphan", uselist=False)
    assistant_messages: Mapped[list[AssistantMessage]] = relationship(back_populates="project", cascade="all, delete-orphan", order_by="AssistantMessage.id")
    source_notes: Mapped[list[ProductionSourceNote]] = relationship(back_populates="project", cascade="all, delete-orphan", order_by="ProductionSourceNote.id")
    media_assets: Mapped[list[MediaAsset]] = relationship(back_populates="project", cascade="all, delete-orphan")
    library_assets: Mapped[list[LibraryAsset]] = relationship(back_populates="project", cascade="all, delete-orphan")
    asset_reviews: Mapped[list[AssetReview]] = relationship(back_populates="project", cascade="all, delete-orphan")


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    era_primary: Mapped[str] = mapped_column(String(64), default="1990s")
    era_secondary: Mapped[str] = mapped_column(String(64), default="2020s")
    visual: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    direction: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    narrative: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    archetypes: Mapped[list[str]] = mapped_column(JSON, default=list)
    craft: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    project: Mapped[Project] = relationship(back_populates="style_profile")


class ProductionScope(Base):
    __tablename__ = "production_scopes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    distribution_channel: Mapped[str] = mapped_column(String(80), default="web")
    release_format: Mapped[str] = mapped_column(String(40), default="one_off")
    aspect_ratio: Mapped[str] = mapped_column(String(20), default="16:9")
    width: Mapped[int] = mapped_column(default=1920)
    height: Mapped[int] = mapped_column(default=1080)
    target_duration_seconds: Mapped[int] = mapped_column(default=300)
    installment_count: Mapped[int] = mapped_column(default=1)
    season_count: Mapped[int] = mapped_column(default=1)
    story_status: Mapped[str] = mapped_column(String(32), default="not_started")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project: Mapped[Project] = relationship(back_populates="scope")


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    page: Mapped[str] = mapped_column(String(80), default="productions")
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="assistant_messages")


class StoryBrief(Base):
    __tablename__ = "story_briefs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    premise: Mapped[str] = mapped_column(Text, default="")
    format: Mapped[str] = mapped_column(String(32), default="short film")
    target_duration_minutes: Mapped[int] = mapped_column(default=5)
    audience: Mapped[str] = mapped_column(String(80), default="general")
    genre: Mapped[str] = mapped_column(String(80), default="science fantasy")
    themes: Mapped[list[str]] = mapped_column(JSON, default=list)
    synopsis: Mapped[str] = mapped_column(Text, default="")
    beats: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    project: Mapped[Project] = relationship(back_populates="story_brief")


class ProductionSourceNote(Base):
    __tablename__ = "production_source_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    stage: Mapped[str] = mapped_column(String(32))
    source_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(160))
    note: Mapped[str] = mapped_column(Text)
    application: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, default="")
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project: Mapped[Project] = relationship(back_populates="source_notes")


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80), default="protagonist")
    want: Mapped[str] = mapped_column(Text, default="")
    need: Mapped[str] = mapped_column(Text, default="")
    contradiction: Mapped[str] = mapped_column(Text, default="")

    project: Mapped[Project] = relationship(back_populates="characters")
    design: Mapped[CharacterDesign | None] = relationship(back_populates="character", cascade="all, delete-orphan", uselist=False)
    voice_profile: Mapped[VoiceProfile | None] = relationship(back_populates="character", cascade="all, delete-orphan", uselist=False)
    story_profile: Mapped[CharacterStoryProfile | None] = relationship(back_populates="character", cascade="all, delete-orphan", uselist=False)
    relationships: Mapped[list[CharacterRelationship]] = relationship(back_populates="character", cascade="all, delete-orphan", foreign_keys="CharacterRelationship.character_id")


class CharacterDesign(Base):
    __tablename__ = "character_designs"

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), unique=True)
    appearance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    palette: Mapped[list[str]] = mapped_column(JSON, default=list)
    wardrobe: Mapped[list[str]] = mapped_column(JSON, default=list)
    consistency_anchors: Mapped[list[str]] = mapped_column(JSON, default=list)
    reference_brief: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(default=1)

    character: Mapped[Character] = relationship(back_populates="design")


class CharacterStoryProfile(Base):
    __tablename__ = "character_story_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), unique=True)
    history: Mapped[str] = mapped_column(Text, default="")
    formative_event: Mapped[str] = mapped_column(Text, default="")
    secret: Mapped[str] = mapped_column(Text, default="")
    fear: Mapped[str] = mapped_column(Text, default="")
    misbelief: Mapped[str] = mapped_column(Text, default="")
    arc_start: Mapped[str] = mapped_column(Text, default="")
    arc_turn: Mapped[str] = mapped_column(Text, default="")
    arc_end: Mapped[str] = mapped_column(Text, default="")
    stakes: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(default=1)

    character: Mapped[Character] = relationship(back_populates="story_profile")


class CharacterRelationship(Base):
    __tablename__ = "character_relationships"
    __table_args__ = (UniqueConstraint("character_id", "target_character_id", name="uq_character_relationship_target"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    target_character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    relationship_type: Mapped[str] = mapped_column(String(80), default="ally")
    public_dynamic: Mapped[str] = mapped_column(Text, default="")
    private_truth: Mapped[str] = mapped_column(Text, default="")
    tension: Mapped[str] = mapped_column(Text, default="")
    arc: Mapped[str] = mapped_column(Text, default="")

    character: Mapped[Character] = relationship(back_populates="relationships", foreign_keys=[character_id])


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    prompt: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    external_id: Mapped[str] = mapped_column(String(160), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    request_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    character_id: Mapped[int | None] = mapped_column(ForeignKey("characters.id"), nullable=True)
    generation_job_id: Mapped[int | None] = mapped_column(ForeignKey("generation_jobs.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(48), default="character_reference")
    filename: Mapped[str] = mapped_column(String(255))
    uri: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(80), default="image/png")
    asset_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="media_assets")


class LibraryAsset(Base):
    __tablename__ = "library_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    group_key: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(48), default="reference")
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    filename: Mapped[str] = mapped_column(String(255))
    uri: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(80), default="application/octet-stream")
    rights_status: Mapped[str] = mapped_column(String(32), default="pending")
    rights_notes: Mapped[str] = mapped_column(Text, default="")
    source_tool: Mapped[str] = mapped_column(String(80), default="creator upload")
    asset_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="library_assets")


class AssetReview(Base):
    __tablename__ = "asset_reviews"
    __table_args__ = (UniqueConstraint("asset_type", "asset_id", name="uq_asset_review_target"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    asset_type: Mapped[str] = mapped_column(String(32))
    asset_id: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(24), default="pending")
    notes: Mapped[str] = mapped_column(Text, default="")
    selected: Mapped[bool] = mapped_column(default=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="asset_reviews")


class RenderWorker(Base):
    __tablename__ = "render_workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    hostname: Mapped[str] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="offline")
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    supported_tasks: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WorkerAssignment(Base):
    __tablename__ = "worker_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    generation_job_id: Mapped[int] = mapped_column(ForeignKey("generation_jobs.id"), unique=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("render_workers.id"))
    status: Mapped[str] = mapped_column(String(32), default="leased")
    attempts: Mapped[int] = mapped_column(default=1)
    leased_until: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WorldLocation(Base):
    __tablename__ = "world_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(160))
    narrative_function: Mapped[str] = mapped_column(String(160), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    geography: Mapped[str] = mapped_column(String(160), default="")
    time_period: Mapped[str] = mapped_column(String(120), default="")

    project: Mapped[Project] = relationship(back_populates="locations")
    design: Mapped[LocationDesign | None] = relationship(back_populates="location", cascade="all, delete-orphan", uselist=False)
    background_assets: Mapped[list[BackgroundAsset]] = relationship(back_populates="location", cascade="all, delete-orphan")


class LocationDesign(Base):
    __tablename__ = "location_designs"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("world_locations.id"), unique=True)
    appearance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    palette: Mapped[list[str]] = mapped_column(JSON, default=list)
    layers: Mapped[list[str]] = mapped_column(JSON, default=list)
    lighting_variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    continuity_anchors: Mapped[list[str]] = mapped_column(JSON, default=list)
    reference_brief: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(default=1)

    location: Mapped[WorldLocation] = relationship(back_populates="design")


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("world_locations.id"))
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    prompt: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    external_id: Mapped[str] = mapped_column(String(160), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BackgroundAsset(Base):
    __tablename__ = "background_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("world_locations.id"))
    background_job_id: Mapped[int | None] = mapped_column(ForeignKey("background_jobs.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    uri: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(80), default="image/png")
    asset_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    location: Mapped[WorldLocation] = relationship(back_populates="background_assets")


class StoryboardJob(Base):
    __tablename__ = "storyboard_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"))
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    prompt: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    external_id: Mapped[str] = mapped_column(String(160), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StoryboardAsset(Base):
    __tablename__ = "storyboard_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"))
    storyboard_job_id: Mapped[int] = mapped_column(ForeignKey("storyboard_jobs.id"))
    filename: Mapped[str] = mapped_column(String(255))
    uri: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(80), default="image/png")
    asset_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    shot: Mapped[Shot] = relationship(back_populates="storyboard_assets")


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(default=1)
    slugline: Mapped[str] = mapped_column(String(255), default="")
    script: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    draft_status: Mapped[str] = mapped_column(String(32), default="outline")

    project: Mapped[Project] = relationship(back_populates="scenes")
    shots: Mapped[list[Shot]] = relationship(back_populates="scene", cascade="all, delete-orphan", order_by="Shot.position")


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(primary_key=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(default=1)
    duration_seconds: Mapped[float] = mapped_column(default=4.0)
    status: Mapped[str] = mapped_column(String(32), default="draft")

    scene: Mapped[Scene] = relationship(back_populates="shots")
    plan: Mapped[ShotPlan | None] = relationship(back_populates="shot", cascade="all, delete-orphan", uselist=False)
    composition: Mapped[ShotComposition | None] = relationship(back_populates="shot", cascade="all, delete-orphan", uselist=False)
    storyboard_assets: Mapped[list[StoryboardAsset]] = relationship(back_populates="shot", cascade="all, delete-orphan")


class ShotPlan(Base):
    __tablename__ = "shot_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"), unique=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("world_locations.id"), nullable=True)
    character_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    action: Mapped[str] = mapped_column(Text, default="")
    dialogue: Mapped[str] = mapped_column(Text, default="")
    camera: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    lighting: Mapped[str] = mapped_column(String(160), default="")
    continuity_notes: Mapped[str] = mapped_column(Text, default="")
    storyboard_prompt: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(default=1)

    shot: Mapped[Shot] = relationship(back_populates="plan")


class Timeline(Base):
    __tablename__ = "timelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    fps: Mapped[int] = mapped_column(default=24)
    width: Mapped[int] = mapped_column(default=1920)
    height: Mapped[int] = mapped_column(default=1080)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="timeline")
    clips: Mapped[list[TimelineClip]] = relationship(back_populates="timeline", cascade="all, delete-orphan", order_by="TimelineClip.position")
    renders: Mapped[list[AnimaticRender]] = relationship(back_populates="timeline", cascade="all, delete-orphan")
    audio_tracks: Mapped[list[AudioTrack]] = relationship(back_populates="timeline", cascade="all, delete-orphan", order_by="AudioTrack.position")


class TimelineClip(Base):
    __tablename__ = "timeline_clips"

    id: Mapped[int] = mapped_column(primary_key=True)
    timeline_id: Mapped[int] = mapped_column(ForeignKey("timelines.id"))
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"), unique=True)
    position: Mapped[int] = mapped_column(default=1)
    duration_seconds: Mapped[float] = mapped_column(default=4.0)
    transition: Mapped[str] = mapped_column(String(32), default="cut")
    transition_duration: Mapped[float] = mapped_column(default=0.0)
    audio_cue: Mapped[str] = mapped_column(Text, default="")

    timeline: Mapped[Timeline] = relationship(back_populates="clips")
    shot: Mapped[Shot] = relationship()


class AnimaticRender(Base):
    __tablename__ = "animatic_renders"

    id: Mapped[int] = mapped_column(primary_key=True)
    timeline_id: Mapped[int] = mapped_column(ForeignKey("timelines.id"))
    durable_job_id: Mapped[int | None] = mapped_column(ForeignKey("durable_jobs.id"), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    filename: Mapped[str] = mapped_column(String(255), default="")
    uri: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    render_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    timeline: Mapped[Timeline] = relationship(back_populates="renders")


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), unique=True)
    vocal_age: Mapped[str] = mapped_column(String(80), default="young adult")
    texture: Mapped[str] = mapped_column(String(120), default="clear and grounded")
    energy: Mapped[str] = mapped_column(String(120), default="restrained")
    accent: Mapped[str] = mapped_column(String(120), default="neutral")
    language: Mapped[str] = mapped_column(String(40), default="English")
    pace: Mapped[float] = mapped_column(default=1.0)
    pitch: Mapped[float] = mapped_column(default=0.0)
    provider: Mapped[str] = mapped_column(String(40), default="simulation")
    provider_voice_id: Mapped[str] = mapped_column(String(160), default="")
    direction_notes: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(default=1)

    character: Mapped[Character] = relationship(back_populates="voice_profile")


class AudioTrack(Base):
    __tablename__ = "audio_tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    timeline_id: Mapped[int] = mapped_column(ForeignKey("timelines.id"))
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(32), default="dialogue")
    position: Mapped[int] = mapped_column(default=1)
    volume: Mapped[float] = mapped_column(default=1.0)
    muted: Mapped[bool] = mapped_column(default=False)

    timeline: Mapped[Timeline] = relationship(back_populates="audio_tracks")
    cues: Mapped[list[AudioCue]] = relationship(back_populates="track", cascade="all, delete-orphan", order_by="AudioCue.start_seconds")


class AudioCue(Base):
    __tablename__ = "audio_cues"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("audio_tracks.id"))
    clip_id: Mapped[int | None] = mapped_column(ForeignKey("timeline_clips.id"), nullable=True)
    character_id: Mapped[int | None] = mapped_column(ForeignKey("characters.id"), nullable=True)
    start_seconds: Mapped[float] = mapped_column(default=0.0)
    duration_seconds: Mapped[float] = mapped_column(default=2.0)
    text: Mapped[str] = mapped_column(Text, default="")
    direction: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="planned")
    filename: Mapped[str] = mapped_column(String(255), default="")
    uri: Mapped[str] = mapped_column(Text, default="")
    mime_type: Mapped[str] = mapped_column(String(80), default="")

    track: Mapped[AudioTrack] = relationship(back_populates="cues")


class CrewAssignment(Base):
    __tablename__ = "crew_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    role: Mapped[str] = mapped_column(String(48))
    name: Mapped[str] = mapped_column(String(120))
    enabled: Mapped[bool] = mapped_column(default=True)
    autonomy: Mapped[str] = mapped_column(String(24), default="propose")
    instructions: Mapped[str] = mapped_column(Text, default="")
    traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    provider_key: Mapped[str] = mapped_column(String(120), default="auto")
    model_override: Mapped[str] = mapped_column(String(255), default="")
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CrewAction(Base):
    __tablename__ = "crew_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    durable_job_id: Mapped[int | None] = mapped_column(ForeignKey("durable_jobs.id"), nullable=True, unique=True)
    assignment_id: Mapped[int | None] = mapped_column(ForeignKey("crew_assignments.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(48))
    action_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    requires_approval: Mapped[bool] = mapped_column(default=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProductionWorkflow(Base):
    __tablename__ = "production_workflows"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    objective: Mapped[str] = mapped_column(Text, default="Guide this production from its current state to a reviewable master.")
    status: Mapped[str] = mapped_column(String(32), default="active")
    current_stage: Mapped[str] = mapped_column(String(48), default="story")
    stages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_action_id: Mapped[int | None] = mapped_column(ForeignKey("crew_actions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_project_milestone_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    key: Mapped[str] = mapped_column(String(48))
    completed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VoiceConsent(Base):
    __tablename__ = "voice_consents"

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    source_type: Mapped[str] = mapped_column(String(48), default="built_in_ai")
    subject_name: Mapped[str] = mapped_column(String(160), default="")
    consent_confirmed: Mapped[bool] = mapped_column(default=False)
    disclosure_required: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PronunciationEntry(Base):
    __tablename__ = "pronunciation_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    character_id: Mapped[int | None] = mapped_column(ForeignKey("characters.id"), nullable=True)
    term: Mapped[str] = mapped_column(String(160))
    pronunciation: Mapped[str] = mapped_column(String(240))
    language: Mapped[str] = mapped_column(String(40), default="English")
    notes: Mapped[str] = mapped_column(Text, default="")


class ShotComposition(Base):
    __tablename__ = "shot_compositions"

    id: Mapped[int] = mapped_column(primary_key=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id"), unique=True)
    width: Mapped[int] = mapped_column(default=1920)
    height: Mapped[int] = mapped_column(default=1080)
    camera: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    color_grade: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    version: Mapped[int] = mapped_column(default=1)

    shot: Mapped[Shot] = relationship(back_populates="composition")
    layers: Mapped[list[CompositionLayer]] = relationship(back_populates="composition", cascade="all, delete-orphan", order_by="CompositionLayer.z_index")
    renders: Mapped[list[CompositeRender]] = relationship(back_populates="composition", cascade="all, delete-orphan")
    motion_renders: Mapped[list[ShotMotionRender]] = relationship(back_populates="composition", cascade="all, delete-orphan")


class CompositionLayer(Base):
    __tablename__ = "composition_layers"

    id: Mapped[int] = mapped_column(primary_key=True)
    composition_id: Mapped[int] = mapped_column(ForeignKey("shot_compositions.id"))
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(32), default="character")
    source_kind: Mapped[str] = mapped_column(String(48), default="custom")
    source_asset_id: Mapped[int | None] = mapped_column(nullable=True)
    source_uri: Mapped[str] = mapped_column(Text, default="")
    z_index: Mapped[int] = mapped_column(default=1)
    visible: Mapped[bool] = mapped_column(default=True)
    opacity: Mapped[float] = mapped_column(default=1.0)
    blend_mode: Mapped[str] = mapped_column(String(32), default="normal")
    transform: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    animation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    composition: Mapped[ShotComposition] = relationship(back_populates="layers")


class CompositeRender(Base):
    __tablename__ = "composite_renders"

    id: Mapped[int] = mapped_column(primary_key=True)
    composition_id: Mapped[int] = mapped_column(ForeignKey("shot_compositions.id"))
    durable_job_id: Mapped[int | None] = mapped_column(ForeignKey("durable_jobs.id"), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    filename: Mapped[str] = mapped_column(String(255), default="")
    uri: Mapped[str] = mapped_column(Text, default="")
    mime_type: Mapped[str] = mapped_column(String(80), default="image/png")
    error: Mapped[str] = mapped_column(Text, default="")
    render_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    composition: Mapped[ShotComposition] = relationship(back_populates="renders")


class ShotMotionRender(Base):
    __tablename__ = "shot_motion_renders"

    id: Mapped[int] = mapped_column(primary_key=True)
    composition_id: Mapped[int] = mapped_column(ForeignKey("shot_compositions.id"))
    durable_job_id: Mapped[int | None] = mapped_column(ForeignKey("durable_jobs.id"), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    filename: Mapped[str] = mapped_column(String(255), default="")
    uri: Mapped[str] = mapped_column(Text, default="")
    mime_type: Mapped[str] = mapped_column(String(80), default="video/mp4")
    error: Mapped[str] = mapped_column(Text, default="")
    render_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    composition: Mapped[ShotComposition] = relationship(back_populates="motion_renders")


class MasterExportJob(Base):
    __tablename__ = "master_export_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timeline_id: Mapped[int] = mapped_column(ForeignKey("timelines.id"))
    durable_job_id: Mapped[int | None] = mapped_column(ForeignKey("durable_jobs.id"), nullable=True, unique=True)
    profile: Mapped[str] = mapped_column(String(32), default="preview")
    fps: Mapped[int] = mapped_column(default=24)
    width: Mapped[int] = mapped_column(default=1280)
    height: Mapped[int] = mapped_column(default=720)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    final_filename: Mapped[str] = mapped_column(String(255), default="")
    final_uri: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    watermarked: Mapped[bool] = mapped_column(default=False)
    max_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    segments: Mapped[list[MasterSegment]] = relationship(back_populates="export", cascade="all, delete-orphan", order_by="MasterSegment.position")


class MasterSegment(Base):
    __tablename__ = "master_segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    export_id: Mapped[int] = mapped_column(ForeignKey("master_export_jobs.id"))
    position: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    attempts: Mapped[int] = mapped_column(default=0)
    worker_id: Mapped[int | None] = mapped_column(ForeignKey("render_workers.id"), nullable=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), default="")
    uri: Mapped[str] = mapped_column(Text, default="")
    checksum_sha256: Mapped[str] = mapped_column(String(64), default="")
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    export: Mapped[MasterExportJob] = relationship(back_populates="segments")


class StoragePolicy(Base):
    __tablename__ = "storage_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    backend: Mapped[str] = mapped_column(String(32), default="local")
    retention_days: Mapped[int] = mapped_column(default=30)
    max_backups: Mapped[int] = mapped_column(default=10)
    include_media: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ProjectBackup(Base):
    __tablename__ = "project_backups"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    durable_job_id: Mapped[int | None] = mapped_column(ForeignKey("durable_jobs.id"), nullable=True, unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(Text)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(default=0)
    asset_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BackupSchedule(Base):
    __tablename__ = "backup_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    enabled: Mapped[bool] = mapped_column(default=False)
    interval_hours: Mapped[int] = mapped_column(default=24)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str] = mapped_column(String(32), default="never")
    last_error: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MediaStoragePolicy(Base):
    __tablename__ = "media_storage_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    original_strategy: Mapped[str] = mapped_column(String(32), default="server")
    preferred_node_key: Mapped[str] = mapped_column(String(64), default="")
    keep_server_proxies: Mapped[bool] = mapped_column(default=True)
    thumbnail_width: Mapped[int] = mapped_column(default=480)
    proxy_width: Mapped[int] = mapped_column(default=1280)
    minimum_replicas: Mapped[int] = mapped_column(default=1)
    evict_server_originals: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AssetResidency(Base):
    __tablename__ = "asset_residencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    residency_key: Mapped[str] = mapped_column(String(64), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    asset_key: Mapped[str] = mapped_column(String(160))
    representation: Mapped[str] = mapped_column(String(24), default="original")
    backend: Mapped[str] = mapped_column(String(24), default="server")
    node_key: Mapped[str] = mapped_column(String(64), default="")
    object_ref: Mapped[str] = mapped_column(Text, default="")
    uri: Mapped[str] = mapped_column(Text, default="")
    checksum_sha256: Mapped[str] = mapped_column(String(64), default="")
    size_bytes: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(24), default="available")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MediaTransferJob(Base):
    __tablename__ = "media_transfer_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    durable_job_id: Mapped[int | None] = mapped_column(ForeignKey("durable_jobs.id"), nullable=True, unique=True)
    job_key: Mapped[str] = mapped_column(String(64), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    asset_key: Mapped[str] = mapped_column(String(160))
    source_residency_id: Mapped[int] = mapped_column(ForeignKey("asset_residencies.id"))
    target_node_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    expected_checksum_sha256: Mapped[str] = mapped_column(String(64))
    expected_size_bytes: Mapped[int] = mapped_column(default=0)
    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=5)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    object_ref: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MediaCleanupReview(Base):
    __tablename__ = "media_cleanup_reviews"
    __table_args__ = (UniqueConstraint("project_id", "asset_key", name="uq_media_cleanup_review"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    asset_key: Mapped[str] = mapped_column(String(160))
    source_residency_id: Mapped[int] = mapped_column(ForeignKey("asset_residencies.id"))
    status: Mapped[str] = mapped_column(String(24), default="review")
    checksum_sha256: Mapped[str] = mapped_column(String(64), default="")
    required_replicas: Mapped[int] = mapped_column(default=1)
    verified_replicas: Mapped[int] = mapped_column(default=0)
    verification_cutoff: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DurableJob(Base):
    __tablename__ = "durable_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_key: Mapped[str] = mapped_column(String(64), unique=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(80))
    queue: Mapped[str] = mapped_column(String(48), default="default")
    status: Mapped[str] = mapped_column(String(24), default="queued")
    priority: Mapped[int] = mapped_column(default=50)
    progress_percent: Mapped[int] = mapped_column(default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=5)
    lease_owner: Mapped[str] = mapped_column(String(120), default="")
    leased_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancellation_requested: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DurableJobEvent(Base):
    __tablename__ = "durable_job_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("durable_jobs.id"))
    status: Mapped[str] = mapped_column(String(24))
    progress_percent: Mapped[int] = mapped_column(default=0)
    message: Mapped[str] = mapped_column(String(500), default="")
    event_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeats"
    __table_args__ = (UniqueConstraint("service_key", "instance_id", name="uq_service_heartbeat_instance"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_key: Mapped[str] = mapped_column(String(64))
    instance_id: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), default="ready")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CompliancePolicy(Base):
    __tablename__ = "compliance_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    strict_gates: Mapped[bool] = mapped_column(default=True)
    external_clearance_required: Mapped[bool] = mapped_column(default=True)
    terms_version: Mapped[str] = mapped_column(String(32), default="2026-08-09")
    accepted_by: Mapped[str] = mapped_column(String(160), default="")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ComplianceScan(Base):
    __tablename__ = "compliance_scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    stage: Mapped[str] = mapped_column(String(48))
    subject_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="blocked")
    coverage: Mapped[str] = mapped_column(String(32), default="preliminary")
    risk_score: Mapped[int] = mapped_column(default=0)
    scanner_version: Mapped[str] = mapped_column(String(32), default="kizuna-local-v1")
    summary: Mapped[str] = mapped_column(Text, default="")
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    suggestions: Mapped[list[str]] = mapped_column(JSON, default=list)
    input_manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ComplianceProviderResult(Base):
    __tablename__ = "compliance_provider_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("compliance_scans.id"))
    provider_key: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(24), default="completed")
    request_hash: Mapped[str] = mapped_column(String(64))
    response_hash: Mapped[str] = mapped_column(String(64), default="")
    matches: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ComplianceFindingResolution(Base):
    __tablename__ = "compliance_finding_resolutions"
    __table_args__ = (UniqueConstraint("scan_id", "finding_id", name="uq_compliance_scan_finding_resolution"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("compliance_scans.id"))
    finding_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    reviewer: Mapped[str] = mapped_column(String(160))
    rationale: Mapped[str] = mapped_column(Text)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AssetRightsRecord(Base):
    __tablename__ = "asset_rights_records"
    __table_args__ = (UniqueConstraint("project_id", "asset_key", name="uq_asset_rights_project_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    asset_key: Mapped[str] = mapped_column(String(160))
    source_type: Mapped[str] = mapped_column(String(48))
    rights_holder: Mapped[str] = mapped_column(String(200), default="")
    license_name: Mapped[str] = mapped_column(String(200), default="")
    permitted_uses: Mapped[list[str]] = mapped_column(JSON, default=list)
    territories: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ProfessionalIdentity(Base):
    __tablename__ = "professional_identities"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(160), default="")
    legal_name: Mapped[str] = mapped_column(String(200), default="")
    identity_type: Mapped[str] = mapped_column(String(48), default="individual")
    professional_role: Mapped[str] = mapped_column(String(160), default="")
    website: Mapped[str] = mapped_column(String(1000), default="")
    biography: Mapped[str] = mapped_column(Text, default="")
    verification_status: Mapped[str] = mapped_column(String(32), default="unsubmitted")
    verification_evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    reviewed_by: Mapped[str] = mapped_column(String(160), default="")
    review_notes: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ProfessionalWorkClaim(Base):
    __tablename__ = "professional_work_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    identity_id: Mapped[int] = mapped_column(ForeignKey("professional_identities.id"))
    title: Mapped[str] = mapped_column(String(300))
    work_type: Mapped[str] = mapped_column(String(48))
    credited_role: Mapped[str] = mapped_column(String(160))
    release_year: Mapped[int | None] = mapped_column(nullable=True)
    external_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    authorization_scope: Mapped[str] = mapped_column(Text, default="")
    verification_status: Mapped[str] = mapped_column(String(32), default="pending")
    reviewed_by: Mapped[str] = mapped_column(String(160), default="")
    review_notes: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ProfessionalVerificationEvent(Base):
    __tablename__ = "professional_verification_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    identity_id: Mapped[int] = mapped_column(ForeignKey("professional_identities.id"))
    work_claim_id: Mapped[int | None] = mapped_column(ForeignKey("professional_work_claims.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(160), default="creator")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ComplianceClearance(Base):
    __tablename__ = "compliance_clearances"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    scope: Mapped[str] = mapped_column(String(48), default="release")
    confirmed_by: Mapped[str] = mapped_column(String(160))
    notes: Mapped[str] = mapped_column(Text, default="")
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLedgerEvent(Base):
    __tablename__ = "audit_ledger_events"
    __table_args__ = (UniqueConstraint("project_id", "sequence", name="uq_audit_project_sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    sequence: Mapped[int] = mapped_column()
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str] = mapped_column(String(48))
    action: Mapped[str] = mapped_column(String(80))
    actor_type: Mapped[str] = mapped_column(String(32), default="system")
    subject_type: Mapped[str] = mapped_column(String(80), default="")
    subject_key: Mapped[str] = mapped_column(String(180), default="")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DeliveryLink(Base):
    __tablename__ = "delivery_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    asset_uri: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(String(160), default="Review delivery")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    max_downloads: Mapped[int] = mapped_column(default=10)
    download_count: Mapped[int] = mapped_column(default=0)
    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class IntegrationProfile(Base):
    __tablename__ = "integration_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)
    display_name: Mapped[str] = mapped_column(String(160), default="")
    category: Mapped[str] = mapped_column(String(40), default="ai")
    mode: Mapped[str] = mapped_column(String(32), default="disabled")
    endpoint: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(255), default="")
    secret_env_var: Mapped[str] = mapped_column(String(160), default="")
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AIProviderRoute(Base):
    __tablename__ = "ai_provider_routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    task: Mapped[str] = mapped_column(String(80), unique=True)
    provider_key: Mapped[str] = mapped_column(String(120), default="local")
    model_override: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class NodeEnrollment(Base):
    __tablename__ = "node_enrollments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KizunaNode(Base):
    __tablename__ = "kizuna_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    os_name: Mapped[str] = mapped_column(String(80), default="")
    os_version: Mapped[str] = mapped_column(String(160), default="")
    architecture: Mapped[str] = mapped_column(String(40), default="")
    cpu_name: Mapped[str] = mapped_column(String(255), default="")
    logical_cores: Mapped[int] = mapped_column(default=1)
    ram_gb: Mapped[float] = mapped_column(Float, default=0)
    gpu: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    software: Mapped[list[str]] = mapped_column(JSON, default=list)
    benchmark_score: Mapped[float] = mapped_column(Float, default=0)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    choices: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="online")
    token_hash: Mapped[str] = mapped_column(String(64))
    last_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WorkloadPolicy(Base):
    __tablename__ = "workload_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    task: Mapped[str] = mapped_column(String(80), unique=True)
    placement: Mapped[str] = mapped_column(String(24), default="auto")
    node_key: Mapped[str] = mapped_column(String(64), default="")
    cloud_provider: Mapped[str] = mapped_column(String(120), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AIModelRate(Base):
    __tablename__ = "ai_model_rates"
    __table_args__ = (UniqueConstraint("provider_key", "model", name="uq_ai_model_rate"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_key: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(255))
    input_per_million: Mapped[float] = mapped_column(Float, default=0)
    cached_input_per_million: Mapped[float] = mapped_column(Float, default=0)
    output_per_million: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    source_url: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AIUsageEvent(Base):
    __tablename__ = "ai_usage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    provider_key: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(255))
    task: Mapped[str] = mapped_column(String(80))
    input_tokens: Mapped[int] = mapped_column(default=0)
    cached_input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    pricing_known: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StudioSpendSettings(Base):
    __tablename__ = "studio_spend_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(40), unique=True, default="studio")
    monthly_budget: Mapped[float] = mapped_column(Float, default=0)
    warning_percent: Mapped[int] = mapped_column(default=80)
    hard_stop: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class HiveNodeControl(Base):
    __tablename__ = "hive_node_controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_key: Mapped[str] = mapped_column(String(64), unique=True)
    render_worker_id: Mapped[int | None] = mapped_column(ForeignKey("render_workers.id"), unique=True, nullable=True)
    paused: Mapped[bool] = mapped_column(default=False)
    drain: Mapped[bool] = mapped_column(default=False)
    max_concurrency: Mapped[int] = mapped_column(default=1)
    cpu_limit_percent: Mapped[int] = mapped_column(default=75)
    gpu_limit_percent: Mapped[int] = mapped_column(default=90)
    memory_limit_gb: Mapped[float] = mapped_column(Float, default=0)
    available_days: Mapped[list[int]] = mapped_column(JSON, default=lambda: [0, 1, 2, 3, 4, 5, 6])
    start_hour: Mapped[int] = mapped_column(default=0)
    end_hour: Mapped[int] = mapped_column(default=24)
    timezone_offset_minutes: Mapped[int] = mapped_column(default=0)
    priority: Mapped[int] = mapped_column(default=50)
    allowed_tasks: Mapped[list[str]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
