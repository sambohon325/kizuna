from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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

    project: Mapped[Project] = relationship(back_populates="style_profile")


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
    background_job_id: Mapped[int] = mapped_column(ForeignKey("background_jobs.id"))
    filename: Mapped[str] = mapped_column(String(255))
    uri: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(80), default="image/png")
    asset_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


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


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(default=1)

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
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CrewAction(Base):
    __tablename__ = "crew_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
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
    profile: Mapped[str] = mapped_column(String(32), default="preview")
    fps: Mapped[int] = mapped_column(default=24)
    width: Mapped[int] = mapped_column(default=1280)
    height: Mapped[int] = mapped_column(default=720)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    final_filename: Mapped[str] = mapped_column(String(255), default="")
    final_uri: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
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
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(Text)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(default=0)
    asset_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(32), default="completed")
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
