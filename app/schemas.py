from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StyleProfileInput(BaseModel):
    era_primary: str = "1990s"
    era_secondary: str = "2020s"
    visual: dict[str, Any] = Field(default_factory=dict)
    direction: dict[str, Any] = Field(default_factory=dict)
    narrative: dict[str, Any] = Field(default_factory=dict)
    archetypes: list[str] = Field(default_factory=list)


class StyleProfileRead(StyleProfileInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int


class StoryBriefInput(BaseModel):
    premise: str = ""
    format: str = "short film"
    target_duration_minutes: int = Field(default=5, ge=1, le=240)
    audience: str = "general"
    genre: str = "science fantasy"
    themes: list[str] = Field(default_factory=list)


class StoryBriefRead(StoryBriefInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    synopsis: str
    beats: list[dict[str, Any]] = Field(default_factory=list)


class StoryOutlineUpdate(BaseModel):
    synopsis: str
    beats: list[dict[str, Any]]


class CharacterInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = "protagonist"
    want: str = ""
    need: str = ""
    contradiction: str = ""


class CharacterDesignInput(BaseModel):
    appearance: dict[str, Any] = Field(default_factory=dict)
    palette: list[str] = Field(default_factory=list)
    wardrobe: list[str] = Field(default_factory=list)
    consistency_anchors: list[str] = Field(default_factory=list)


class CharacterDesignRead(CharacterDesignInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    character_id: int
    reference_brief: str
    version: int


class GenerationRequest(BaseModel):
    provider: str | None = None
    negative_prompt: str = "copyrighted character, logo, watermark, inconsistent face, extra limbs, text"
    seed: int | None = None


class MediaAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    character_id: int | None
    generation_job_id: int | None
    kind: str
    filename: str
    uri: str
    mime_type: str
    asset_metadata: dict[str, Any]
    version: int


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    character_id: int
    provider: str
    status: str
    prompt: str
    negative_prompt: str
    external_id: str
    error: str
    result_data: dict[str, Any]
    assets: list[MediaAssetRead] = Field(default_factory=list)


class CharacterRead(CharacterInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    design: CharacterDesignRead | None = None


class ShotCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = ""
    position: int = Field(default=1, ge=1)
    duration_seconds: float = Field(default=4.0, gt=0, le=3600)


class ShotRead(ShotCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scene_id: int
    status: str


class SceneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str = ""
    position: int = Field(default=1, ge=1)


class SceneRead(SceneCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    shots: list[ShotRead] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    logline: str = ""


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    created_at: datetime
    style_profile: StyleProfileRead | None = None
    story_brief: StoryBriefRead | None = None
    characters: list[CharacterRead] = Field(default_factory=list)
    scenes: list[SceneRead] = Field(default_factory=list)
