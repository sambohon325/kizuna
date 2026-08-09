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


class WorkerRegistration(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    hostname: str = Field(min_length=1, max_length=255)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    supported_tasks: list[str] = Field(default_factory=lambda: ["character_reference"])


class WorkerRegistrationResult(BaseModel):
    id: int
    token: str
    name: str


class WorkerHeartbeat(BaseModel):
    status: str = "online"
    capabilities: dict[str, Any] | None = None


class RenderWorkerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    hostname: str
    status: str
    capabilities: dict[str, Any]
    supported_tasks: list[str]
    last_seen: datetime | None


class WorldLocationInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    narrative_function: str = ""
    description: str = ""
    geography: str = ""
    time_period: str = ""


class LocationDesignInput(BaseModel):
    appearance: dict[str, Any] = Field(default_factory=dict)
    palette: list[str] = Field(default_factory=list)
    layers: list[str] = Field(default_factory=list)
    lighting_variants: list[str] = Field(default_factory=list)
    continuity_anchors: list[str] = Field(default_factory=list)


class LocationDesignRead(LocationDesignInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    location_id: int
    reference_brief: str
    version: int


class WorldLocationRead(WorldLocationInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    design: LocationDesignRead | None = None


class BackgroundAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    location_id: int
    background_job_id: int
    filename: str
    uri: str
    mime_type: str
    asset_metadata: dict[str, Any]
    version: int


class BackgroundJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    location_id: int
    provider: str
    status: str
    prompt: str
    negative_prompt: str
    external_id: str
    error: str
    result_data: dict[str, Any]
    assets: list[BackgroundAssetRead] = Field(default_factory=list)


class StoryboardAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    shot_id: int
    storyboard_job_id: int
    filename: str
    uri: str
    mime_type: str
    asset_metadata: dict[str, Any]
    version: int


class StoryboardJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    shot_id: int
    provider: str
    status: str
    prompt: str
    negative_prompt: str
    external_id: str
    error: str
    result_data: dict[str, Any]
    assets: list[StoryboardAssetRead] = Field(default_factory=list)


class JobCompletion(BaseModel):
    result_data: dict[str, Any] = Field(default_factory=dict)


class JobFailure(BaseModel):
    error: str
    retryable: bool = True


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


class ShotPlanInput(BaseModel):
    location_id: int | None = None
    character_ids: list[int] = Field(default_factory=list)
    action: str = ""
    dialogue: str = ""
    camera: dict[str, Any] = Field(default_factory=dict)
    lighting: str = ""
    continuity_notes: str = ""


class ShotPlanRead(ShotPlanInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    shot_id: int
    storyboard_prompt: str
    version: int


class ShotRead(ShotCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scene_id: int
    status: str
    plan: ShotPlanRead | None = None


class StoryExpansionRequest(BaseModel):
    shots_per_beat: int = Field(default=2, ge=1, le=6)


class SceneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str = ""
    position: int = Field(default=1, ge=1)


class SceneRead(SceneCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    shots: list[ShotRead] = Field(default_factory=list)


class TimelineBuildRequest(BaseModel):
    fps: int = Field(default=24, ge=1, le=60)
    width: int = Field(default=1920, ge=160, le=7680)
    height: int = Field(default=1080, ge=90, le=4320)


class TimelineClipUpdate(BaseModel):
    duration_seconds: float = Field(gt=0, le=3600)
    transition: str = Field(default="cut", pattern="^(cut|dissolve|fade)$")
    transition_duration: float = Field(default=0, ge=0, le=10)
    audio_cue: str = ""


class TimelineClipRead(TimelineClipUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timeline_id: int
    shot_id: int
    position: int
    shot_title: str = ""
    scene_title: str = ""
    storyboard_uri: str = ""


class TimelineOrderUpdate(BaseModel):
    clip_ids: list[int] = Field(min_length=1)


class TimelineRead(BaseModel):
    id: int
    project_id: int
    fps: int
    width: int
    height: int
    status: str
    total_duration_seconds: float
    clips: list[TimelineClipRead] = Field(default_factory=list)


class AnimaticRenderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timeline_id: int
    status: str
    filename: str
    uri: str
    error: str
    render_settings: dict[str, Any]


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
    locations: list[WorldLocationRead] = Field(default_factory=list)
    scenes: list[SceneRead] = Field(default_factory=list)
