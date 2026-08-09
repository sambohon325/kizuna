from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
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
