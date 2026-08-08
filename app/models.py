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
