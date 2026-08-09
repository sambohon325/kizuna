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


class WriterProposalRequest(StoryBriefInput):
    objective: str = "Develop a production-ready story foundation."
    provider: str = Field(default="simulation", pattern="^(simulation|openai)$")


class WriterProposal(BaseModel):
    premise: str
    format: str
    target_duration_minutes: int = Field(ge=1, le=240)
    audience: str
    genre: str
    themes: list[str]
    synopsis: str
    beats: list[dict[str, Any]]
    rationale: str
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DirectorProposalRequest(BaseModel):
    objective: str = "Create a clear, emotionally specific coverage plan."
    shots_per_beat: int = Field(default=3, ge=1, le=6)
    pacing: str = Field(default="balanced", pattern="^(restrained|balanced|kinetic)$")
    provider: str = Field(default="simulation", pattern="^(simulation|openai)$")


class DirectorShotProposal(BaseModel):
    position: int = Field(ge=1)
    title: str
    description: str
    duration_seconds: float = Field(gt=0, le=3600)
    shot_size: str
    angle: str
    lens: str
    movement: str
    composition: str
    focus: str
    action: str
    dialogue: str = ""
    lighting: str
    continuity_notes: str
    performance_intent: str
    character_names: list[str] = Field(default_factory=list)
    location_name: str = ""


class DirectorSceneProposal(BaseModel):
    position: int = Field(ge=1)
    title: str
    summary: str
    dramatic_goal: str
    shots: list[DirectorShotProposal] = Field(min_length=1)


class DirectorProposal(BaseModel):
    approach: str
    estimated_duration_seconds: float = Field(ge=0)
    scenes: list[DirectorSceneProposal] = Field(min_length=1)
    continuity_rules: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnimatorProposalRequest(BaseModel):
    objective: str = "Create an economical, performance-led motion pass that preserves continuity."
    provider: str = Field(default="simulation", pattern="^(simulation|openai)$")
    render_preview: bool = False
    quality: str = Field(default="proxy", pattern="^(proxy|full)$")
    fps: int | None = Field(default=None, ge=1, le=60)


class AnimatorCameraProposal(BaseModel):
    move: str
    start_scale: float = Field(default=1, ge=1, le=5)
    end_scale: float = Field(default=1, ge=1, le=5)
    pan_x: float = Field(default=0, ge=-0.5, le=0.5)
    pan_y: float = Field(default=0, ge=-0.5, le=0.5)
    easing: str = Field(default="ease-in-out", pattern="^(linear|ease-in|ease-out|ease-in-out)$")
    intent: str = ""


class AnimatorLayerProposal(BaseModel):
    layer_id: int | None = None
    layer_name: str
    kind: str
    intent: str
    easing: str = Field(default="ease-in-out", pattern="^(linear|ease-in|ease-out|ease-in-out)$")
    end_x: float = Field(ge=-1, le=2)
    end_y: float = Field(ge=-1, le=2)
    end_scale: float = Field(ge=0.05, le=5)
    end_rotation: float = Field(ge=-360, le=360)
    end_opacity: float = Field(ge=0, le=1)


class AnimatorProposal(BaseModel):
    approach: str
    camera: AnimatorCameraProposal
    layer_motions: list[AnimatorLayerProposal] = Field(min_length=1)
    acting_beats: list[str] = Field(default_factory=list)
    timing_notes: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EditorProposalRequest(BaseModel):
    objective: str = "Shape a clear, emotionally paced assembly while preserving story continuity."
    pacing: str = Field(default="balanced", pattern="^(restrained|balanced|kinetic)$")
    provider: str = Field(default="simulation", pattern="^(simulation|openai)$")
    render_review: bool = False
    review_profile: str = Field(default="preview", pattern="^(preview|1080p|4k)$")


class EditorClipProposal(BaseModel):
    clip_id: int | None = None
    shot_id: int
    shot_title: str
    position: int = Field(ge=1)
    duration_seconds: float = Field(gt=0, le=3600)
    transition: str = Field(default="cut", pattern="^(cut|dissolve|fade)$")
    transition_duration: float = Field(default=0, ge=0, le=10)
    rationale: str


class EditorProposal(BaseModel):
    approach: str
    clips: list[EditorClipProposal] = Field(min_length=1)
    estimated_runtime_seconds: float = Field(ge=0)
    rhythm_notes: list[str] = Field(default_factory=list)
    continuity_checks: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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


class CharacterStoryProfileInput(BaseModel):
    history: str = ""
    formative_event: str = ""
    secret: str = ""
    fear: str = ""
    misbelief: str = ""
    arc_start: str = ""
    arc_turn: str = ""
    arc_end: str = ""
    stakes: str = ""


class CharacterStoryProfileRead(CharacterStoryProfileInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    character_id: int
    version: int


class CharacterRelationshipInput(BaseModel):
    target_character_id: int
    relationship_type: str = "ally"
    public_dynamic: str = ""
    private_truth: str = ""
    tension: str = ""
    arc: str = ""


class CharacterRelationshipRead(CharacterRelationshipInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    character_id: int
    target_name: str = ""


class CharacterDesignerRequest(BaseModel):
    objective: str = "Create an original, animation-ready identity with strong consistency locks."
    provider: str = Field(default="simulation", pattern="^(simulation|openai)$")
    queue_generation: bool = False
    generation_provider: str = Field(default="mock", pattern="^(mock|farm|comfyui)$")


class CharacterDesignProposal(CharacterDesignInput):
    rationale: str
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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


class AssetReviewUpdate(BaseModel):
    status: str = Field(default="pending", pattern="^(pending|approved|rejected)$")
    notes: str = Field(default="", max_length=2000)
    selected: bool = False


class AssetReviewRead(BaseModel):
    id: int | None = None
    project_id: int
    asset_type: str
    asset_id: int
    status: str
    notes: str
    selected: bool
    active: bool = False
    affected_compositions: list[int] = Field(default_factory=list)


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


class BackgroundArtistRequest(BaseModel):
    objective: str = "Create a reusable, camera-ready environment system with clear staging and continuity."
    provider: str = Field(default="simulation", pattern="^(simulation|openai)$")
    queue_generation: bool = False
    generation_provider: str = Field(default="mock", pattern="^(mock|comfyui)$")


class BackgroundDesignProposal(LocationDesignInput):
    rationale: str
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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
    motion_uri: str = ""


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


class MasterRenderRequest(BaseModel):
    profile: str = Field(default="preview", pattern="^(preview|1080p|4k)$")
    fps: int | None = Field(default=None, ge=1, le=60)


class SegmentedExportRequest(MasterRenderRequest):
    segment_size: int = Field(default=4, ge=1, le=20)


class MasterSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    export_id: int
    position: int
    status: str
    attempts: int
    worker_id: int | None
    filename: str
    uri: str
    checksum_sha256: str
    manifest: dict[str, Any]
    error: str


class MasterExportRead(BaseModel):
    id: int
    timeline_id: int
    profile: str
    fps: int
    width: int
    height: int
    status: str
    final_filename: str
    final_uri: str
    error: str
    completed_segments: int
    total_segments: int
    progress_percent: float
    segments: list[MasterSegmentRead] = Field(default_factory=list)


class VoiceProfileInput(BaseModel):
    vocal_age: str = "young adult"
    texture: str = "clear and grounded"
    energy: str = "restrained"
    accent: str = "neutral"
    language: str = "English"
    pace: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=0.0, ge=-12, le=12)
    provider: str = "simulation"
    provider_voice_id: str = ""
    direction_notes: str = ""


class VoiceProfileRead(VoiceProfileInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    character_id: int
    version: int


class AudioCueInput(BaseModel):
    clip_id: int | None = None
    character_id: int | None = None
    start_seconds: float = Field(default=0, ge=0, le=86400)
    duration_seconds: float = Field(default=2, gt=0, le=3600)
    text: str = ""
    direction: str = ""


class AudioCueRead(AudioCueInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    track_id: int
    status: str
    filename: str
    uri: str
    mime_type: str


class AudioCueSplitRequest(BaseModel):
    split_seconds: float = Field(gt=0, le=3600)


class AudioCueDuplicateRequest(BaseModel):
    offset_seconds: float = Field(default=.25, ge=0, le=3600)


class AudioTrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timeline_id: int
    name: str
    kind: str
    position: int
    volume: float
    muted: bool
    cues: list[AudioCueRead] = Field(default_factory=list)


class AudioStudioRead(BaseModel):
    timeline_id: int
    project_id: int
    total_duration_seconds: float
    voice_profiles: list[VoiceProfileRead] = Field(default_factory=list)
    tracks: list[AudioTrackRead] = Field(default_factory=list)


class CrewDeployRequest(BaseModel):
    roles: list[str] = Field(default_factory=list)
    autonomy: str = Field(default="propose", pattern="^(assist|propose|execute)$")


class ProducerWorkflowRequest(BaseModel):
    objective: str = "Guide this production from its current state to a reviewable master."
    provider: str = Field(default="simulation", pattern="^(simulation|openai)$")
    render_motion_previews: bool = True
    render_final_review: bool = True
    review_profile: str = Field(default="preview", pattern="^(preview|1080p|4k)$")


class ProducerWorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    objective: str
    status: str
    current_stage: str
    stages: list[dict[str, Any]] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
    last_action_id: int | None = None
    created_at: datetime
    updated_at: datetime


class CrewAssignmentUpdate(BaseModel):
    enabled: bool = True
    autonomy: str = Field(default="propose", pattern="^(assist|propose|execute)$")
    instructions: str = ""


class CrewAssignmentRead(CrewAssignmentUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    role: str
    name: str
    capabilities: list[str] = Field(default_factory=list)


class CrewActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    assignment_id: int | None
    role: str
    action_type: str
    title: str
    summary: str
    status: str
    requires_approval: bool
    payload: dict[str, Any]
    result: dict[str, Any]
    error: str
    created_at: datetime
    reviewed_at: datetime | None


class VoiceConsentInput(BaseModel):
    source_type: str = Field(default="built_in_ai", pattern="^(built_in_ai|licensed|creator_owned|uploaded_performance)$")
    subject_name: str = ""
    consent_confirmed: bool = False
    disclosure_required: bool = True
    notes: str = ""


class VoiceConsentRead(VoiceConsentInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    character_id: int


class PronunciationInput(BaseModel):
    character_id: int | None = None
    term: str = Field(min_length=1, max_length=160)
    pronunciation: str = Field(min_length=1, max_length=240)
    language: str = "English"
    notes: str = ""


class PronunciationRead(PronunciationInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int


class CrewVoiceRequest(BaseModel):
    provider: str | None = None
    voice: str | None = None


class CompositionInput(BaseModel):
    camera: dict[str, Any] = Field(default_factory=dict)
    color_grade: dict[str, Any] = Field(default_factory=dict)


class CompositionLayerInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(default="character", pattern="^(background|character|prop|effect|reference|custom)$")
    source_kind: str = "custom"
    source_asset_id: int | None = None
    source_uri: str = ""
    z_index: int = Field(default=1, ge=-100, le=100)
    visible: bool = True
    opacity: float = Field(default=1, ge=0, le=1)
    blend_mode: str = Field(default="normal", pattern="^(normal|multiply|screen|overlay)$")
    transform: dict[str, Any] = Field(default_factory=dict)
    animation: dict[str, Any] = Field(default_factory=dict)


class CompositionLayerRead(CompositionLayerInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    composition_id: int


class ShotCompositionRead(CompositionInput):
    id: int
    shot_id: int
    width: int
    height: int
    status: str
    version: int
    shot_title: str = ""
    scene_title: str = ""
    layers: list[CompositionLayerRead] = Field(default_factory=list)
    latest_render_uri: str = ""
    latest_motion_uri: str = ""


class CompositeRenderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    composition_id: int
    status: str
    filename: str
    uri: str
    mime_type: str
    error: str
    render_settings: dict[str, Any]


class MotionRenderRequest(BaseModel):
    quality: str = Field(default="proxy", pattern="^(proxy|full)$")
    fps: int | None = Field(default=None, ge=1, le=60)


class ShotMotionRenderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    composition_id: int
    status: str
    filename: str
    uri: str
    mime_type: str
    error: str
    render_settings: dict[str, Any]


class CompositorStudioRead(BaseModel):
    project_id: int
    shots: list[dict[str, Any]] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)


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


class ProductionStageRead(BaseModel):
    key: str
    label: str
    state: str
    summary: str
    nav: str


class ProductionStatusRead(BaseModel):
    project_id: int
    complete_count: int
    total_count: int
    next_key: str | None = None
    stages: list[ProductionStageRead] = Field(default_factory=list)


class StoragePolicyUpdate(BaseModel):
    retention_days: int = Field(default=30, ge=1, le=3650)
    max_backups: int = Field(default=10, ge=1, le=100)
    include_media: bool = True


class StoragePolicyRead(StoragePolicyUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int | None = None
    project_id: int
    backend: str


class ProjectBackupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    filename: str
    checksum_sha256: str
    size_bytes: int
    asset_count: int
    status: str
    download_url: str = ""
    created_at: datetime


class DeliveryLinkCreate(BaseModel):
    asset_uri: str = Field(min_length=1, max_length=2000)
    label: str = Field(default="Review delivery", max_length=160)
    expires_hours: int = Field(default=72, ge=1, le=720)
    max_downloads: int = Field(default=10, ge=1, le=10000)


class DeliveryLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    asset_uri: str
    label: str
    expires_at: datetime
    max_downloads: int
    download_count: int
    revoked: bool
    url: str = ""
    created_at: datetime
