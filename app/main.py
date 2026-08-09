import hashlib
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.animatic import render_animatic
from app.audio import generate_timing_slate
from app.compositor import render_composite
from app.motion import render_motion_video
from app.mastering import render_timeline_master
from app.segmented_export import assemble_segments, clip_start_times, segment_clip_ranges, sha256_file
from app.database import Base, engine, get_db
from app.character_development import compile_reference_brief
from app.generation import ComfyUIProvider, MockProvider, ProviderError
from app.models import AnimaticRender, AudioCue, AudioTrack, BackgroundAsset, BackgroundJob, Character, CharacterDesign, CompositeRender, CompositionLayer, CrewAction, CrewAssignment, GenerationJob, LocationDesign, MasterExportJob, MasterSegment, MediaAsset, Project, PronunciationEntry, RenderWorker, Scene, Shot, ShotComposition, ShotMotionRender, ShotPlan, StoryboardAsset, StoryboardJob, StoryBrief, StyleProfile, Timeline, TimelineClip, VoiceConsent, VoiceProfile, WorkerAssignment, WorldLocation
from app.schemas import AnimaticRenderRead, AnimatorProposal, AnimatorProposalRequest, AudioCueInput, AudioCueRead, AudioStudioRead, BackgroundArtistRequest, BackgroundJobRead, CharacterDesignerRequest, CharacterDesignInput, CharacterDesignRead, CharacterInput, CharacterRead, CompositeRenderRead, CompositionInput, CompositionLayerInput, CompositionLayerRead, CompositorStudioRead, CrewActionRead, CrewAssignmentRead, CrewAssignmentUpdate, CrewDeployRequest, CrewVoiceRequest, DirectorProposalRequest, GenerationJobRead, GenerationRequest, JobCompletion, JobFailure, LocationDesignInput, LocationDesignRead, MasterExportRead, MasterRenderRequest, MasterSegmentRead, MotionRenderRequest, ProjectCreate, ProjectRead, PronunciationInput, PronunciationRead, RenderWorkerRead, SceneCreate, SceneRead, SegmentedExportRequest, ShotCompositionRead, ShotCreate, ShotMotionRenderRead, ShotPlanInput, ShotPlanRead, ShotRead, StoryboardJobRead, StoryBriefInput, StoryBriefRead, StoryExpansionRequest, StoryOutlineUpdate, StyleProfileInput, StyleProfileRead, TimelineBuildRequest, TimelineClipUpdate, TimelineOrderUpdate, TimelineRead, VoiceConsentInput, VoiceConsentRead, VoiceProfileInput, VoiceProfileRead, WorkerHeartbeat, WorkerRegistration, WorkerRegistrationResult, WorldLocationInput, WorldLocationRead, WriterProposalRequest
from app.shot_development import compile_storyboard_prompt
from app.style_catalog import STYLE_CATALOG
from app.story_development import develop_story
from app.world_development import compile_background_brief
from app.voice import VoiceProviderError, generate_voice
from app.writer_agent import WriterAgentError, create_writer_proposal
from app.director_agent import DirectorAgentError, create_director_proposal
from app.visual_agents import VisualAgentError, create_background_design_proposal, create_character_design_proposal
from app.animator_agent import AnimatorAgentError, create_animator_proposal

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name, version="0.1.0")
static_dir = Path(__file__).parent / "static"
render_dir = Path(settings.render_directory).resolve()
render_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/renders", StaticFiles(directory=render_dir), name="renders")

CREW_ROLES = {
    "writer": {"name": "Writer", "description": "Develops premise, structure, scenes, dialogue, and revisions.", "capabilities": ["story outline", "scene draft", "dialogue pass"]},
    "director": {"name": "Director", "description": "Translates story intent into staging, coverage, camera, and performance notes.", "capabilities": ["shot strategy", "performance direction", "continuity review"]},
    "character_designer": {"name": "Character Designer", "description": "Builds consistent visual identities, expressions, wardrobe, and model sheets.", "capabilities": ["character brief", "model sheet", "consistency review"]},
    "background_artist": {"name": "Background Artist", "description": "Designs locations, reusable layers, lighting variants, and world continuity.", "capabilities": ["location brief", "background plates", "lighting variants"]},
    "animator": {"name": "Animator", "description": "Plans motion, acting beats, camera moves, timing, and render-ready shot animation.", "capabilities": ["motion plan", "acting pass", "shot animation"]},
    "sound_producer": {"name": "Sound Producer", "description": "Directs voices, pronunciation, music, ambience, sound effects, and the final mix.", "capabilities": ["voice direction", "dialogue generation", "sound plan"]},
    "editor": {"name": "Editor", "description": "Shapes pacing, transitions, assembly, quality review, and master delivery.", "capabilities": ["timeline assembly", "pacing pass", "master review"]},
}


def project_query():
    return select(Project).options(selectinload(Project.style_profile), selectinload(Project.story_brief), selectinload(Project.characters).selectinload(Character.design), selectinload(Project.locations).selectinload(WorldLocation.design), selectinload(Project.scenes).selectinload(Scene.shots).selectinload(Shot.plan))


def timeline_response(timeline: Timeline, db: Session):
    clips = db.scalars(select(TimelineClip).where(TimelineClip.timeline_id == timeline.id).order_by(TimelineClip.position)).all()
    output = []
    for clip in clips:
        shot = db.get(Shot, clip.shot_id)
        scene = db.get(Scene, shot.scene_id)
        asset = db.scalar(select(StoryboardAsset).where(StoryboardAsset.shot_id == shot.id).order_by(StoryboardAsset.version.desc(), StoryboardAsset.id.desc()))
        composite = db.scalar(select(CompositeRender).join(ShotComposition).where(ShotComposition.shot_id == shot.id, CompositeRender.status == "completed").order_by(CompositeRender.id.desc()))
        shot_composition = db.scalar(select(ShotComposition).where(ShotComposition.shot_id == shot.id))
        if composite and shot_composition and composite.render_settings.get("version") != shot_composition.version:
            composite = None
        motion = db.scalar(select(ShotMotionRender).where(ShotMotionRender.composition_id == shot_composition.id, ShotMotionRender.status == "completed").order_by(ShotMotionRender.id.desc())) if shot_composition else None
        if motion and motion.render_settings.get("version") != shot_composition.version:
            motion = None
        output.append({
            "id": clip.id, "timeline_id": clip.timeline_id, "shot_id": clip.shot_id, "position": clip.position,
            "duration_seconds": clip.duration_seconds, "transition": clip.transition,
            "transition_duration": clip.transition_duration, "audio_cue": clip.audio_cue,
            "shot_title": shot.title, "scene_title": scene.title, "storyboard_uri": composite.uri if composite else (asset.uri if asset else ""), "motion_uri": motion.uri if motion else "",
        })
    total = sum(clip["duration_seconds"] for clip in output)
    total -= sum(min(clip["transition_duration"], clip["duration_seconds"] / 2) for clip in output[1:] if clip["transition"] != "cut")
    return {"id": timeline.id, "project_id": timeline.project_id, "fps": timeline.fps, "width": timeline.width, "height": timeline.height, "status": timeline.status, "total_duration_seconds": round(max(0, total), 3), "clips": output}


@app.get("/api/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/style-catalog")
def style_catalog():
    return STYLE_CATALOG


@app.get("/api/generation/providers")
def generation_providers():
    workflow_ready = bool(settings.comfyui_workflow_path and Path(settings.comfyui_workflow_path).exists())
    return {"active": settings.generation_provider, "providers": [{"id": "mock", "label": "Simulation", "ready": True}, {"id": "farm", "label": "Render farm", "ready": True}, {"id": "comfyui", "label": "Local ComfyUI", "ready": workflow_ready, "base_url": settings.comfyui_url}]}


@app.get("/api/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(project_query().order_by(Project.updated_at.desc())).unique().all()


@app.post("/api/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(title=payload.title, logline=payload.logline)
    project.style_profile = StyleProfile(
        era_secondary="2020s",
        visual={"linework": "bold variable ink", "palette": "controlled cinematic", "shading": "two-tone cel"},
        direction={"camera": "character-led", "motion": "selective fluidity"},
        narrative={"structure": "kishotenketsu", "tone": "hopeful"},
        archetypes=["reluctant protagonist", "ideological rival"],
    )
    db.add(project)
    db.commit()
    return db.scalars(project_query().where(Project.id == project.id)).one()


@app.get("/api/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.scalars(project_query().where(Project.id == project_id)).one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@app.put("/api/projects/{project_id}/style", response_model=StyleProfileRead)
def update_style(project_id: int, payload: StyleProfileInput, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = db.scalar(select(StyleProfile).where(StyleProfile.project_id == project_id))
    if profile is None:
        profile = StyleProfile(project_id=project_id)
        db.add(profile)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@app.put("/api/projects/{project_id}/story", response_model=StoryBriefRead)
def develop_project_story(project_id: int, payload: StoryBriefInput, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    brief = db.scalar(select(StoryBrief).where(StoryBrief.project_id == project_id))
    if brief is None:
        brief = StoryBrief(project_id=project_id)
        db.add(brief)
    synopsis, beats = develop_story(project.title, project.logline, payload)
    for key, value in payload.model_dump().items():
        setattr(brief, key, value)
    brief.synopsis = synopsis
    brief.beats = beats
    db.commit()
    db.refresh(brief)
    return brief


@app.patch("/api/projects/{project_id}/story/outline", response_model=StoryBriefRead)
def update_story_outline(project_id: int, payload: StoryOutlineUpdate, db: Session = Depends(get_db)):
    brief = db.scalar(select(StoryBrief).where(StoryBrief.project_id == project_id))
    if brief is None:
        raise HTTPException(404, "Develop the story before editing its outline")
    brief.synopsis = payload.synopsis
    brief.beats = payload.beats
    db.commit()
    db.refresh(brief)
    return brief


@app.post("/api/projects/{project_id}/characters", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
def create_character(project_id: int, payload: CharacterInput, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    character = Character(project_id=project_id, **payload.model_dump())
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@app.put("/api/characters/{character_id}", response_model=CharacterRead)
def update_character(character_id: int, payload: CharacterInput, db: Session = Depends(get_db)):
    character = db.get(Character, character_id)
    if not character:
        raise HTTPException(404, "Character not found")
    for key, value in payload.model_dump().items():
        setattr(character, key, value)
    db.commit()
    return db.scalars(select(Character).options(selectinload(Character.design)).where(Character.id == character_id)).one()


@app.put("/api/characters/{character_id}/design", response_model=CharacterDesignRead)
def update_character_design(character_id: int, payload: CharacterDesignInput, db: Session = Depends(get_db)):
    character = db.get(Character, character_id)
    if not character:
        raise HTTPException(404, "Character not found")
    style = db.scalar(select(StyleProfile).where(StyleProfile.project_id == character.project_id))
    design = db.scalar(select(CharacterDesign).where(CharacterDesign.character_id == character_id))
    if design is None:
        design = CharacterDesign(character_id=character_id)
        db.add(design)
    else:
        design.version += 1
    for key, value in payload.model_dump().items():
        setattr(design, key, value)
    design.reference_brief = compile_reference_brief(character, payload, style)
    db.commit()
    db.refresh(design)
    return design


@app.post("/api/projects/{project_id}/locations", response_model=WorldLocationRead, status_code=status.HTTP_201_CREATED)
def create_location(project_id: int, payload: WorldLocationInput, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    location = WorldLocation(project_id=project_id, **payload.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@app.put("/api/locations/{location_id}", response_model=WorldLocationRead)
def update_location(location_id: int, payload: WorldLocationInput, db: Session = Depends(get_db)):
    location = db.get(WorldLocation, location_id)
    if not location:
        raise HTTPException(404, "Location not found")
    for key, value in payload.model_dump().items():
        setattr(location, key, value)
    db.commit()
    return db.scalars(select(WorldLocation).options(selectinload(WorldLocation.design)).where(WorldLocation.id == location_id)).one()


@app.put("/api/locations/{location_id}/design", response_model=LocationDesignRead)
def update_location_design(location_id: int, payload: LocationDesignInput, db: Session = Depends(get_db)):
    location = db.get(WorldLocation, location_id)
    if not location:
        raise HTTPException(404, "Location not found")
    style = db.scalar(select(StyleProfile).where(StyleProfile.project_id == location.project_id))
    design = db.scalar(select(LocationDesign).where(LocationDesign.location_id == location_id))
    if design is None:
        design = LocationDesign(location_id=location_id)
        db.add(design)
    else:
        design.version += 1
    for key, value in payload.model_dump().items():
        setattr(design, key, value)
    design.reference_brief = compile_background_brief(location, payload, style)
    db.commit()
    db.refresh(design)
    return design


def background_job_response(job: BackgroundJob, db: Session):
    assets = db.scalars(select(BackgroundAsset).where(BackgroundAsset.background_job_id == job.id)).all()
    return {"id": job.id, "location_id": job.location_id, "provider": job.provider, "status": job.status, "prompt": job.prompt, "negative_prompt": job.negative_prompt, "external_id": job.external_id, "error": job.error, "result_data": job.result_data, "assets": assets}


def record_background_assets(job: BackgroundJob, outputs: list[dict], db: Session):
    existing = db.scalars(select(BackgroundAsset).where(BackgroundAsset.location_id == job.location_id)).all()
    version = len(existing) + 1
    for output in outputs:
        filename = output["filename"]
        uri = f"/renders/{filename}" if output.get("path") else output.get("url", "")
        db.add(BackgroundAsset(location_id=job.location_id, background_job_id=job.id, filename=filename, uri=uri, mime_type=output.get("mime_type", "image/png"), asset_metadata={key: value for key, value in output.items() if key != "path"}, version=version))


@app.post("/api/locations/{location_id}/generate", response_model=BackgroundJobRead, status_code=status.HTTP_201_CREATED)
def generate_background(location_id: int, payload: GenerationRequest, db: Session = Depends(get_db)):
    location = db.scalars(select(WorldLocation).options(selectinload(WorldLocation.design)).where(WorldLocation.id == location_id)).one_or_none()
    if not location:
        raise HTTPException(404, "Location not found")
    if not location.design or not location.design.reference_brief:
        raise HTTPException(409, "Create the background reference brief before generating artwork")
    provider_name = payload.provider or settings.generation_provider
    if provider_name == "farm":
        raise HTTPException(409, "Background farm scheduling is not enabled yet; choose Simulation or Local ComfyUI")
    job = BackgroundJob(location_id=location.id, provider=provider_name, prompt=location.design.reference_brief, negative_prompt=payload.negative_prompt)
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        result = provider_for(provider_name).submit(job.id, location.name, job.prompt, negative_prompt=job.negative_prompt, seed=payload.seed, asset_kind="background-concept")
        job.status = result.status
        job.external_id = result.external_id
        job.result_data = result.metadata
        if result.outputs:
            record_background_assets(job, result.outputs, db)
    except ProviderError as exc:
        job.status = "failed"
        job.error = str(exc)
    db.commit()
    return background_job_response(job, db)


@app.post("/api/background-jobs/{job_id}/sync", response_model=BackgroundJobRead)
def sync_background_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(BackgroundJob, job_id)
    if not job:
        raise HTTPException(404, "Background job not found")
    if job.provider != "comfyui" or job.status in {"completed", "failed"}:
        return background_job_response(job, db)
    try:
        provider = provider_for(job.provider)
        result = provider.poll(job.external_id)
        job.status = result.status
        job.result_data = result.metadata
        if result.outputs:
            local_outputs = provider.materialize(result.outputs, render_dir, job.id)
            record_background_assets(job, local_outputs, db)
    except ProviderError as exc:
        job.status = "failed"
        job.error = str(exc)
    db.commit()
    return background_job_response(job, db)


def provider_for(name: str):
    if name == "mock":
        return MockProvider(render_dir)
    if name == "comfyui":
        return ComfyUIProvider(settings.comfyui_url, settings.comfyui_workflow_path, settings.comfyui_positive_node, settings.comfyui_negative_node, settings.comfyui_sampler_node)
    raise ProviderError(f"Unknown generation provider: {name}")


def record_assets(job: GenerationJob, character: Character, outputs: list[dict], db: Session) -> list[MediaAsset]:
    existing = db.scalars(select(MediaAsset).where(MediaAsset.character_id == character.id, MediaAsset.kind == "character_reference")).all()
    version = len(existing) + 1
    assets = []
    for output in outputs:
        filename = output["filename"]
        uri = f"/renders/{filename}" if output.get("path") else output.get("url", "")
        asset = MediaAsset(project_id=character.project_id, character_id=character.id, generation_job_id=job.id, kind="character_reference", filename=filename, uri=uri, mime_type=output.get("mime_type", "image/png"), asset_metadata={key: value for key, value in output.items() if key not in {"path"}}, version=version)
        db.add(asset)
        assets.append(asset)
    return assets


def job_response(job: GenerationJob, db: Session):
    assets = db.scalars(select(MediaAsset).where(MediaAsset.generation_job_id == job.id)).all()
    return {"id": job.id, "character_id": job.character_id, "provider": job.provider, "status": job.status, "prompt": job.prompt, "negative_prompt": job.negative_prompt, "external_id": job.external_id, "error": job.error, "result_data": job.result_data, "assets": assets}


@app.post("/api/characters/{character_id}/generate", response_model=GenerationJobRead, status_code=status.HTTP_201_CREATED)
def generate_character_reference(character_id: int, payload: GenerationRequest, db: Session = Depends(get_db)):
    character = db.scalars(select(Character).options(selectinload(Character.design)).where(Character.id == character_id)).one_or_none()
    if not character:
        raise HTTPException(404, "Character not found")
    if not character.design or not character.design.reference_brief:
        raise HTTPException(409, "Create the character reference brief before generating artwork")
    provider_name = payload.provider or settings.generation_provider
    job = GenerationJob(character_id=character.id, provider=provider_name, prompt=character.design.reference_brief, negative_prompt=payload.negative_prompt, request_data=payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    if provider_name == "farm":
        return job_response(job, db)
    try:
        result = provider_for(provider_name).submit(job.id, character.name, job.prompt, negative_prompt=job.negative_prompt, seed=payload.seed)
        job.status = result.status
        job.external_id = result.external_id
        job.result_data = result.metadata
        if result.outputs:
            record_assets(job, character, result.outputs, db)
    except ProviderError as exc:
        job.status = "failed"
        job.error = str(exc)
    db.commit()
    db.refresh(job)
    return job_response(job, db)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def authenticate_worker(worker_id: int, authorization: str | None, db: Session) -> RenderWorker:
    worker = db.get(RenderWorker, worker_id)
    if not worker or not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid worker credentials")
    token_hash = hashlib.sha256(authorization.removeprefix("Bearer ").encode()).hexdigest()
    if not secrets.compare_digest(token_hash, worker.token_hash):
        raise HTTPException(401, "Invalid worker credentials")
    return worker


@app.post("/api/workers/register", response_model=WorkerRegistrationResult, status_code=status.HTTP_201_CREATED)
def register_worker(payload: WorkerRegistration, x_enrollment_secret: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not x_enrollment_secret or not secrets.compare_digest(x_enrollment_secret, settings.worker_enrollment_secret):
        raise HTTPException(403, "Invalid worker enrollment secret")
    token = secrets.token_urlsafe(32)
    worker = RenderWorker(name=payload.name, hostname=payload.hostname, token_hash=hashlib.sha256(token.encode()).hexdigest(), status="online", capabilities=payload.capabilities, supported_tasks=payload.supported_tasks, last_seen=utcnow())
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return {"id": worker.id, "token": token, "name": worker.name}


@app.post("/api/workers/{worker_id}/heartbeat", response_model=RenderWorkerRead)
def worker_heartbeat(worker_id: int, payload: WorkerHeartbeat, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    worker.status = payload.status
    worker.last_seen = utcnow()
    if payload.capabilities is not None:
        worker.capabilities = payload.capabilities
    for assignment in db.scalars(select(WorkerAssignment).where(WorkerAssignment.worker_id == worker.id, WorkerAssignment.status.in_(["leased", "running"]))).all():
        assignment.leased_until = utcnow() + timedelta(seconds=settings.worker_lease_seconds)
    db.commit()
    db.refresh(worker)
    return worker


def recover_expired_assignments(db: Session):
    expired = db.scalars(select(WorkerAssignment).where(WorkerAssignment.leased_until < utcnow(), WorkerAssignment.status.in_(["leased", "running"]))).all()
    for assignment in expired:
        assignment.status = "expired"
        job = db.get(GenerationJob, assignment.generation_job_id)
        if job and job.status == "running":
            job.status = "queued"


@app.post("/api/workers/{worker_id}/claim", response_model=GenerationJobRead | None)
def claim_worker_job(worker_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    recover_expired_assignments(db)
    active = db.scalar(select(WorkerAssignment).where(WorkerAssignment.worker_id == worker.id, WorkerAssignment.status.in_(["leased", "running"])))
    if active:
        return job_response(db.get(GenerationJob, active.generation_job_id), db)
    if "character_reference" not in worker.supported_tasks:
        db.commit()
        return None
    job = db.scalar(select(GenerationJob).where(GenerationJob.provider == "farm", GenerationJob.status == "queued").order_by(GenerationJob.id).with_for_update(skip_locked=True))
    if not job:
        db.commit()
        return None
    assignment = db.scalar(select(WorkerAssignment).where(WorkerAssignment.generation_job_id == job.id))
    if assignment:
        assignment.worker_id = worker.id
        assignment.status = "leased"
        assignment.attempts += 1
        assignment.leased_until = utcnow() + timedelta(seconds=settings.worker_lease_seconds)
    else:
        assignment = WorkerAssignment(generation_job_id=job.id, worker_id=worker.id, leased_until=utcnow() + timedelta(seconds=settings.worker_lease_seconds))
        db.add(assignment)
    job.status = "running"
    worker.status = "busy"
    worker.last_seen = utcnow()
    db.commit()
    return job_response(job, db)


def worker_assignment(worker: RenderWorker, job_id: int, db: Session) -> WorkerAssignment:
    assignment = db.scalar(select(WorkerAssignment).where(WorkerAssignment.worker_id == worker.id, WorkerAssignment.generation_job_id == job_id, WorkerAssignment.status.in_(["leased", "running"])))
    if not assignment:
        raise HTTPException(409, "Job is not leased to this worker")
    return assignment


@app.put("/api/workers/{worker_id}/jobs/{job_id}/artifacts/{filename}", status_code=status.HTTP_201_CREATED)
async def upload_worker_artifact(worker_id: int, job_id: int, filename: str, request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    assignment = worker_assignment(worker, job_id, db)
    content = await request.body()
    if not content or len(content) > settings.max_artifact_bytes:
        raise HTTPException(413, f"Artifact must be between 1 byte and {settings.max_artifact_bytes} bytes")
    job = db.get(GenerationJob, job_id)
    character = db.get(Character, job.character_id)
    safe_suffix = Path(Path(filename).name).suffix.lower()[:10] or ".bin"
    stored_name = f"farm-job-{job_id}-{uuid4().hex[:12]}{safe_suffix}"
    (render_dir / stored_name).write_bytes(content)
    existing = db.scalars(select(MediaAsset).where(MediaAsset.character_id == character.id, MediaAsset.kind == "character_reference")).all()
    asset = MediaAsset(project_id=character.project_id, character_id=character.id, generation_job_id=job.id, kind="character_reference", filename=stored_name, uri=f"/renders/{stored_name}", mime_type=request.headers.get("content-type", "application/octet-stream").split(";")[0], asset_metadata={"original_filename": Path(filename).name, "worker_id": worker.id}, version=len(existing) + 1)
    db.add(asset)
    assignment.status = "running"
    assignment.leased_until = utcnow() + timedelta(seconds=settings.worker_lease_seconds)
    db.commit()
    db.refresh(asset)
    return {"asset_id": asset.id, "uri": asset.uri, "version": asset.version}


@app.post("/api/workers/{worker_id}/jobs/{job_id}/complete", response_model=GenerationJobRead)
def complete_worker_job(worker_id: int, job_id: int, payload: JobCompletion, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    assignment = worker_assignment(worker, job_id, db)
    assets = db.scalars(select(MediaAsset).where(MediaAsset.generation_job_id == job_id)).all()
    if not assets:
        raise HTTPException(409, "Upload at least one artifact before completing the job")
    job = db.get(GenerationJob, job_id)
    job.status = "completed"
    job.result_data = {**job.result_data, **payload.result_data, "worker_id": worker.id}
    assignment.status = "completed"
    worker.status = "online"
    worker.last_seen = utcnow()
    db.commit()
    return job_response(job, db)


@app.post("/api/workers/{worker_id}/jobs/{job_id}/fail", response_model=GenerationJobRead)
def fail_worker_job(worker_id: int, job_id: int, payload: JobFailure, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    assignment = worker_assignment(worker, job_id, db)
    job = db.get(GenerationJob, job_id)
    job.error = payload.error
    job.status = "queued" if payload.retryable else "failed"
    assignment.status = "failed_retryable" if payload.retryable else "failed"
    worker.status = "online"
    worker.last_seen = utcnow()
    db.commit()
    return job_response(job, db)


@app.get("/api/render-farm/status")
def render_farm_status(db: Session = Depends(get_db)):
    recover_expired_assignments(db)
    stale_before = utcnow() - timedelta(seconds=settings.worker_lease_seconds * 2)
    workers = db.scalars(select(RenderWorker).order_by(RenderWorker.name)).all()
    for worker in workers:
        if not worker.last_seen or worker.last_seen < stale_before:
            worker.status = "offline"
    jobs = db.scalars(select(GenerationJob).where(GenerationJob.provider == "farm").order_by(GenerationJob.id.desc()).limit(20)).all()
    segments = db.scalars(select(MasterSegment).order_by(MasterSegment.id.desc()).limit(20)).all()
    db.commit()
    return {
        "workers": [RenderWorkerRead.model_validate(worker).model_dump() for worker in workers],
        "jobs": [{"id": job.id, "character_id": job.character_id, "status": job.status, "error": job.error, "assets": len(db.scalars(select(MediaAsset).where(MediaAsset.generation_job_id == job.id)).all())} for job in jobs],
        "master_segments": [{
            "id": segment.id,
            "export_id": segment.export_id,
            "position": segment.position,
            "status": segment.status,
            "attempts": segment.attempts,
            "worker_id": segment.worker_id,
            "error": segment.error,
        } for segment in segments],
    }


@app.post("/api/generation-jobs/{job_id}/sync", response_model=GenerationJobRead)
def sync_generation_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(404, "Generation job not found")
    if job.provider != "comfyui" or job.status in {"completed", "failed"}:
        return job_response(job, db)
    try:
        provider = provider_for(job.provider)
        result = provider.poll(job.external_id)
        job.status = result.status
        job.result_data = result.metadata
        if result.outputs:
            character = db.get(Character, job.character_id)
            local_outputs = provider.materialize(result.outputs, render_dir, job.id)
            record_assets(job, character, local_outputs, db)
    except ProviderError as exc:
        job.status = "failed"
        job.error = str(exc)
    db.commit()
    return job_response(job, db)


@app.post("/api/projects/{project_id}/scenes", response_model=SceneRead, status_code=status.HTTP_201_CREATED)
def create_scene(project_id: int, payload: SceneCreate, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    scene = Scene(project_id=project_id, **payload.model_dump())
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


@app.post("/api/scenes/{scene_id}/shots", response_model=ShotRead, status_code=status.HTTP_201_CREATED)
def create_shot(scene_id: int, payload: ShotCreate, db: Session = Depends(get_db)):
    if not db.get(Scene, scene_id):
        raise HTTPException(404, "Scene not found")
    shot = Shot(scene_id=scene_id, **payload.model_dump())
    db.add(shot)
    db.commit()
    db.refresh(shot)
    return shot


@app.put("/api/shots/{shot_id}", response_model=ShotRead)
def update_shot(shot_id: int, payload: ShotCreate, db: Session = Depends(get_db)):
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(404, "Shot not found")
    for key, value in payload.model_dump().items():
        setattr(shot, key, value)
    db.commit()
    return db.scalars(select(Shot).options(selectinload(Shot.plan)).where(Shot.id == shot_id)).one()


def shot_context(shot: Shot, payload: ShotPlanInput, db: Session):
    scene = db.get(Scene, shot.scene_id)
    style = db.scalar(select(StyleProfile).where(StyleProfile.project_id == scene.project_id))
    location = db.scalars(select(WorldLocation).options(selectinload(WorldLocation.design)).where(WorldLocation.id == payload.location_id, WorldLocation.project_id == scene.project_id)).one_or_none() if payload.location_id else None
    if payload.location_id and not location:
        raise HTTPException(422, "Location does not belong to this project")
    characters = db.scalars(select(Character).options(selectinload(Character.design)).where(Character.project_id == scene.project_id, Character.id.in_(payload.character_ids))).unique().all() if payload.character_ids else []
    if len(characters) != len(set(payload.character_ids)):
        raise HTTPException(422, "One or more characters do not belong to this project")
    return style, location, characters


@app.put("/api/shots/{shot_id}/plan", response_model=ShotPlanRead)
def update_shot_plan(shot_id: int, payload: ShotPlanInput, db: Session = Depends(get_db)):
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(404, "Shot not found")
    style, location, characters = shot_context(shot, payload, db)
    plan = db.scalar(select(ShotPlan).where(ShotPlan.shot_id == shot_id))
    if plan is None:
        plan = ShotPlan(shot_id=shot_id)
        db.add(plan)
    else:
        plan.version += 1
    for key, value in payload.model_dump().items():
        setattr(plan, key, value)
    plan.storyboard_prompt = compile_storyboard_prompt(shot, payload, style, location, characters)
    db.commit()
    db.refresh(plan)
    return plan


@app.post("/api/projects/{project_id}/expand-story", response_model=ProjectRead)
def expand_story_to_shots(project_id: int, payload: StoryExpansionRequest, db: Session = Depends(get_db)):
    project = db.scalars(project_query().where(Project.id == project_id)).one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.story_brief or not project.story_brief.beats:
        raise HTTPException(409, "Develop the story in Writer's Room first")
    if project.scenes:
        raise HTTPException(409, "This project already has scenes; expansion will not overwrite them")
    shot_labels = ["Establish", "Action", "Reaction", "Detail", "Reversal", "Exit"]
    camera_sizes = ["wide", "medium", "close-up", "insert", "medium close-up", "wide"]
    style = project.style_profile
    for scene_position, beat in enumerate(project.story_brief.beats, start=1):
        scene = Scene(project_id=project.id, title=beat["name"], summary=beat["summary"], position=scene_position)
        db.add(scene)
        db.flush()
        for shot_position in range(1, payload.shots_per_beat + 1):
            label = shot_labels[shot_position - 1]
            shot = Shot(scene_id=scene.id, title=f"{beat['name']} — {label}", description=beat["summary"], position=shot_position, duration_seconds=4.0 if shot_position == 1 else 3.0)
            db.add(shot)
            db.flush()
            plan_payload = ShotPlanInput(action=beat["summary"], camera={"shot_size": camera_sizes[shot_position - 1], "angle": "eye level", "lens": "35mm", "movement": "locked"}, continuity_notes=f"Carry the emotional turn of {beat['name']} into the next shot.")
            prompt = compile_storyboard_prompt(shot, plan_payload, style, None, [])
            db.add(ShotPlan(shot_id=shot.id, **plan_payload.model_dump(), storyboard_prompt=prompt))
    db.commit()
    db.expire_all()
    return db.scalars(project_query().where(Project.id == project_id)).one()


def storyboard_job_response(job: StoryboardJob, db: Session):
    assets = db.scalars(select(StoryboardAsset).where(StoryboardAsset.storyboard_job_id == job.id)).all()
    return {"id": job.id, "shot_id": job.shot_id, "provider": job.provider, "status": job.status, "prompt": job.prompt, "negative_prompt": job.negative_prompt, "external_id": job.external_id, "error": job.error, "result_data": job.result_data, "assets": assets}


def record_storyboard_assets(job: StoryboardJob, outputs: list[dict], db: Session):
    existing = db.scalars(select(StoryboardAsset).where(StoryboardAsset.shot_id == job.shot_id)).all()
    version = len(existing) + 1
    for output in outputs:
        filename = output["filename"]
        uri = f"/renders/{filename}" if output.get("path") else output.get("url", "")
        db.add(StoryboardAsset(shot_id=job.shot_id, storyboard_job_id=job.id, filename=filename, uri=uri, mime_type=output.get("mime_type", "image/png"), asset_metadata={key: value for key, value in output.items() if key != "path"}, version=version))


@app.post("/api/shots/{shot_id}/storyboard", response_model=StoryboardJobRead, status_code=status.HTTP_201_CREATED)
def generate_storyboard(shot_id: int, payload: GenerationRequest, db: Session = Depends(get_db)):
    shot = db.scalars(select(Shot).options(selectinload(Shot.plan)).where(Shot.id == shot_id)).one_or_none()
    if not shot:
        raise HTTPException(404, "Shot not found")
    if not shot.plan or not shot.plan.storyboard_prompt:
        raise HTTPException(409, "Save the shot plan before generating a storyboard")
    provider_name = payload.provider or settings.generation_provider
    if provider_name == "farm":
        raise HTTPException(409, "Storyboard farm scheduling is not enabled yet; choose Simulation or Local ComfyUI")
    job = StoryboardJob(shot_id=shot.id, provider=provider_name, prompt=shot.plan.storyboard_prompt, negative_prompt=payload.negative_prompt)
    db.add(job); db.commit(); db.refresh(job)
    try:
        result = provider_for(provider_name).submit(job.id, shot.title, job.prompt, negative_prompt=job.negative_prompt, seed=payload.seed, asset_kind="storyboard-frame")
        job.status, job.external_id, job.result_data = result.status, result.external_id, result.metadata
        if result.outputs:
            record_storyboard_assets(job, result.outputs, db)
    except ProviderError as exc:
        job.status, job.error = "failed", str(exc)
    db.commit()
    return storyboard_job_response(job, db)


@app.post("/api/storyboard-jobs/{job_id}/sync", response_model=StoryboardJobRead)
def sync_storyboard_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(StoryboardJob, job_id)
    if not job:
        raise HTTPException(404, "Storyboard job not found")
    if job.provider != "comfyui" or job.status in {"completed", "failed"}:
        return storyboard_job_response(job, db)
    try:
        provider = provider_for(job.provider); result = provider.poll(job.external_id)
        job.status, job.result_data = result.status, result.metadata
        if result.outputs:
            record_storyboard_assets(job, provider.materialize(result.outputs, render_dir, job.id), db)
    except ProviderError as exc:
        job.status, job.error = "failed", str(exc)
    db.commit()
    return storyboard_job_response(job, db)


@app.post("/api/projects/{project_id}/timeline/build", response_model=TimelineRead)
def build_timeline(project_id: int, payload: TimelineBuildRequest, db: Session = Depends(get_db)):
    project = db.scalars(project_query().where(Project.id == project_id)).one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    shots = [shot for scene in project.scenes for shot in scene.shots]
    if not shots:
        raise HTTPException(409, "Build shots in the Storyboard & Shot Planner first")
    timeline = db.scalar(select(Timeline).where(Timeline.project_id == project_id))
    if timeline is None:
        timeline = Timeline(project_id=project_id, fps=payload.fps, width=payload.width, height=payload.height)
        db.add(timeline)
        db.flush()
        for position, shot in enumerate(shots, start=1):
            db.add(TimelineClip(timeline_id=timeline.id, shot_id=shot.id, position=position, duration_seconds=shot.duration_seconds))
    else:
        timeline.fps, timeline.width, timeline.height = payload.fps, payload.width, payload.height
        existing = {clip.shot_id for clip in db.scalars(select(TimelineClip).where(TimelineClip.timeline_id == timeline.id)).all()}
        next_position = len(existing) + 1
        for shot in shots:
            if shot.id not in existing:
                db.add(TimelineClip(timeline_id=timeline.id, shot_id=shot.id, position=next_position, duration_seconds=shot.duration_seconds))
                next_position += 1
    timeline.status = "draft"
    db.commit()
    return timeline_response(timeline, db)


@app.get("/api/projects/{project_id}/timeline", response_model=TimelineRead)
def get_timeline(project_id: int, db: Session = Depends(get_db)):
    timeline = db.scalar(select(Timeline).where(Timeline.project_id == project_id))
    if timeline is None:
        raise HTTPException(404, "Timeline not built")
    return timeline_response(timeline, db)


@app.put("/api/timeline-clips/{clip_id}", response_model=TimelineRead)
def update_timeline_clip(clip_id: int, payload: TimelineClipUpdate, db: Session = Depends(get_db)):
    clip = db.get(TimelineClip, clip_id)
    if not clip:
        raise HTTPException(404, "Timeline clip not found")
    for key, value in payload.model_dump().items():
        setattr(clip, key, value)
    db.commit()
    return timeline_response(db.get(Timeline, clip.timeline_id), db)


@app.put("/api/timelines/{timeline_id}/clips/order", response_model=TimelineRead)
def reorder_timeline(timeline_id: int, payload: TimelineOrderUpdate, db: Session = Depends(get_db)):
    timeline = db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(404, "Timeline not found")
    clips = db.scalars(select(TimelineClip).where(TimelineClip.timeline_id == timeline_id)).all()
    by_id = {clip.id: clip for clip in clips}
    if set(payload.clip_ids) != set(by_id):
        raise HTTPException(422, "The order must contain every timeline clip exactly once")
    for position, clip_id in enumerate(payload.clip_ids, start=1):
        by_id[clip_id].position = position
    db.commit()
    return timeline_response(timeline, db)


def composition_response(composition: ShotComposition, db: Session):
    shot = db.get(Shot, composition.shot_id)
    scene = db.get(Scene, shot.scene_id)
    layers = db.scalars(select(CompositionLayer).where(CompositionLayer.composition_id == composition.id).order_by(CompositionLayer.z_index)).all()
    latest = db.scalar(select(CompositeRender).where(CompositeRender.composition_id == composition.id, CompositeRender.status == "completed").order_by(CompositeRender.id.desc()))
    if latest and latest.render_settings.get("version") != composition.version:
        latest = None
    motion = db.scalar(select(ShotMotionRender).where(ShotMotionRender.composition_id == composition.id, ShotMotionRender.status == "completed").order_by(ShotMotionRender.id.desc()))
    if motion and motion.render_settings.get("version") != composition.version:
        motion = None
    return {"id": composition.id, "shot_id": composition.shot_id, "width": composition.width, "height": composition.height, "camera": composition.camera, "color_grade": composition.color_grade, "status": composition.status, "version": composition.version, "shot_title": shot.title, "scene_title": scene.title, "layers": layers, "latest_render_uri": latest.uri if latest else "", "latest_motion_uri": motion.uri if motion else ""}


def project_asset_library(project_id: int, db: Session):
    assets = []
    backgrounds = db.execute(select(BackgroundAsset, WorldLocation).join(WorldLocation, BackgroundAsset.location_id == WorldLocation.id).where(WorldLocation.project_id == project_id).order_by(BackgroundAsset.id.desc())).all()
    for asset, location in backgrounds:
        assets.append({"id": asset.id, "source_kind": "background_asset", "kind": "background", "name": location.name, "uri": asset.uri, "version": asset.version})
    characters = {character.id: character for character in db.scalars(select(Character).where(Character.project_id == project_id)).all()}
    for asset in db.scalars(select(MediaAsset).where(MediaAsset.project_id == project_id, MediaAsset.character_id.is_not(None)).order_by(MediaAsset.id.desc())).all():
        assets.append({"id": asset.id, "source_kind": "media_asset", "kind": "character", "name": characters[asset.character_id].name, "uri": asset.uri, "version": asset.version})
    storyboard_rows = db.execute(select(StoryboardAsset, Shot).join(Shot, StoryboardAsset.shot_id == Shot.id).join(Scene, Shot.scene_id == Scene.id).where(Scene.project_id == project_id).order_by(StoryboardAsset.id.desc())).all()
    for asset, shot in storyboard_rows:
        assets.append({"id": asset.id, "source_kind": "storyboard_asset", "kind": "reference", "name": f"Storyboard · {shot.title}", "uri": asset.uri, "version": asset.version})
    return assets


@app.get("/api/projects/{project_id}/compositor", response_model=CompositorStudioRead)
def get_compositor_studio(project_id: int, db: Session = Depends(get_db)):
    project = db.scalars(project_query().where(Project.id == project_id)).one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    compositions = {item.shot_id: item for item in db.scalars(select(ShotComposition).join(Shot).join(Scene).where(Scene.project_id == project_id)).all()}
    shots = [{"id": shot.id, "title": shot.title, "scene_title": scene.title, "duration_seconds": shot.duration_seconds, "composition_id": compositions[shot.id].id if shot.id in compositions else None, "composition_status": compositions[shot.id].status if shot.id in compositions else "unbuilt"} for scene in project.scenes for shot in scene.shots]
    return {"project_id": project_id, "shots": shots, "assets": project_asset_library(project_id, db)}


@app.post("/api/shots/{shot_id}/composition/build", response_model=ShotCompositionRead)
def build_shot_composition(shot_id: int, db: Session = Depends(get_db)):
    shot = db.scalars(select(Shot).options(selectinload(Shot.plan)).where(Shot.id == shot_id)).one_or_none()
    if not shot:
        raise HTTPException(404, "Shot not found")
    existing = db.scalar(select(ShotComposition).where(ShotComposition.shot_id == shot_id))
    if existing:
        return composition_response(existing, db)
    scene = db.get(Scene, shot.scene_id)
    timeline = db.scalar(select(Timeline).where(Timeline.project_id == scene.project_id))
    camera_plan = shot.plan.camera if shot.plan else {}
    composition = ShotComposition(shot_id=shot.id, width=timeline.width if timeline else 1920, height=timeline.height if timeline else 1080, camera={"move": camera_plan.get("movement", "locked"), "start_scale": 1, "end_scale": 1.08 if "push" in camera_plan.get("movement", "") else 1, "pan_x": 0, "pan_y": 0}, color_grade={"exposure": 1, "contrast": 1, "saturation": 1})
    db.add(composition); db.flush()
    z_index = 0
    location = db.get(WorldLocation, shot.plan.location_id) if shot.plan and shot.plan.location_id else None
    background = db.scalar(select(BackgroundAsset).where(BackgroundAsset.location_id == location.id).order_by(BackgroundAsset.version.desc(), BackgroundAsset.id.desc())) if location else None
    db.add(CompositionLayer(composition_id=composition.id, name=location.name if location else "Background plate", kind="background", source_kind="background_asset" if background else "placeholder", source_asset_id=background.id if background else None, source_uri=background.uri if background else "", z_index=z_index, transform={"x": .5, "y": .5, "scale": 1, "rotation": 0}))
    z_index += 10
    for character_id in (shot.plan.character_ids if shot.plan else []):
        character = db.get(Character, character_id)
        asset = db.scalar(select(MediaAsset).where(MediaAsset.character_id == character_id).order_by(MediaAsset.version.desc(), MediaAsset.id.desc()))
        db.add(CompositionLayer(composition_id=composition.id, name=character.name, kind="character", source_kind="media_asset" if asset else "placeholder", source_asset_id=asset.id if asset else None, source_uri=asset.uri if asset else "", z_index=z_index, transform={"x": .5, "y": .58, "scale": 1, "rotation": 0}, animation={"entrance": "hold", "exit": "hold"}))
        z_index += 10
    db.commit()
    return composition_response(composition, db)


@app.get("/api/shots/{shot_id}/composition", response_model=ShotCompositionRead)
def get_shot_composition(shot_id: int, db: Session = Depends(get_db)):
    composition = db.scalar(select(ShotComposition).where(ShotComposition.shot_id == shot_id))
    if not composition:
        raise HTTPException(404, "Composition not built")
    return composition_response(composition, db)


@app.put("/api/compositions/{composition_id}", response_model=ShotCompositionRead)
def update_composition(composition_id: int, payload: CompositionInput, db: Session = Depends(get_db)):
    composition = db.get(ShotComposition, composition_id)
    if not composition:
        raise HTTPException(404, "Composition not found")
    composition.camera, composition.color_grade = payload.camera, payload.color_grade
    composition.version += 1
    db.commit()
    return composition_response(composition, db)


@app.post("/api/compositions/{composition_id}/layers", response_model=CompositionLayerRead, status_code=status.HTTP_201_CREATED)
def create_composition_layer(composition_id: int, payload: CompositionLayerInput, db: Session = Depends(get_db)):
    composition = db.get(ShotComposition, composition_id)
    if not composition:
        raise HTTPException(404, "Composition not found")
    layer = CompositionLayer(composition_id=composition_id, **payload.model_dump())
    composition.version += 1
    composition.status = "draft"
    db.add(layer); db.commit(); db.refresh(layer)
    return layer


@app.put("/api/composition-layers/{layer_id}", response_model=CompositionLayerRead)
def update_composition_layer(layer_id: int, payload: CompositionLayerInput, db: Session = Depends(get_db)):
    layer = db.get(CompositionLayer, layer_id)
    if not layer:
        raise HTTPException(404, "Composition layer not found")
    for key, value in payload.model_dump().items():
        setattr(layer, key, value)
    composition = db.get(ShotComposition, layer.composition_id)
    composition.version += 1
    composition.status = "draft"
    db.commit(); db.refresh(layer)
    return layer


@app.post("/api/compositions/{composition_id}/render", response_model=CompositeRenderRead, status_code=status.HTTP_201_CREATED)
def render_shot_composition(composition_id: int, db: Session = Depends(get_db)):
    composition = db.get(ShotComposition, composition_id)
    if not composition:
        raise HTTPException(404, "Composition not found")
    render = CompositeRender(composition_id=composition_id, status="rendering", render_settings={"width": composition.width, "height": composition.height, "version": composition.version})
    db.add(render); db.commit(); db.refresh(render)
    try:
        layers = db.scalars(select(CompositionLayer).where(CompositionLayer.composition_id == composition_id).order_by(CompositionLayer.z_index)).all()
        prepared = [{"name": layer.name, "kind": layer.kind, "source": render_dir / Path(layer.source_uri).name if layer.source_uri else None, "z_index": layer.z_index, "visible": layer.visible, "opacity": layer.opacity, "blend_mode": layer.blend_mode, "transform": layer.transform} for layer in layers]
        render.filename = f"composite-{composition.id}-v{composition.version}-{render.id}.png"
        render_composite(prepared, render_dir / render.filename, composition.width, composition.height, composition.color_grade)
        render.uri, render.status = f"/renders/{render.filename}", "completed"
        composition.status = "preview-ready"
    except Exception as exc:
        render.status, render.error = "failed", str(exc)
    db.commit(); db.refresh(render)
    return render


@app.post("/api/compositions/{composition_id}/render-video", response_model=ShotMotionRenderRead, status_code=status.HTTP_201_CREATED)
def render_shot_motion(composition_id: int, payload: MotionRenderRequest, db: Session = Depends(get_db)):
    composition = db.get(ShotComposition, composition_id)
    if not composition:
        raise HTTPException(404, "Composition not found")
    shot = db.get(Shot, composition.shot_id)
    scene = db.get(Scene, shot.scene_id)
    timeline = db.scalar(select(Timeline).where(Timeline.project_id == scene.project_id))
    fps = payload.fps or (timeline.fps if timeline else 24)
    scale = min(1, 1280 / composition.width, 720 / composition.height) if payload.quality == "proxy" else 1
    width = max(2, int(composition.width * scale) // 2 * 2)
    height = max(2, int(composition.height * scale) // 2 * 2)
    settings_data = {"quality": payload.quality, "fps": fps, "width": width, "height": height, "duration_seconds": shot.duration_seconds, "version": composition.version}
    render = ShotMotionRender(composition_id=composition.id, status="rendering", render_settings=settings_data)
    db.add(render); db.commit(); db.refresh(render)
    try:
        layers = db.scalars(select(CompositionLayer).where(CompositionLayer.composition_id == composition_id).order_by(CompositionLayer.z_index)).all()
        prepared = [{"name": layer.name, "kind": layer.kind, "source": render_dir / Path(layer.source_uri).name if layer.source_uri else None, "z_index": layer.z_index, "visible": layer.visible, "opacity": layer.opacity, "blend_mode": layer.blend_mode, "transform": layer.transform, "animation": layer.animation} for layer in layers]
        render.filename = f"shot-{shot.id}-motion-v{composition.version}-{render.id}.mp4"
        frame_count = render_motion_video(prepared, render_dir / render.filename, width, height, fps, shot.duration_seconds, composition.color_grade, composition.camera)
        render.uri, render.status = f"/renders/{render.filename}", "completed"
        render.render_settings = {**settings_data, "frame_count": frame_count}
        composition.status = "motion-ready"
    except Exception as exc:
        render.status, render.error = "failed", str(exc)
    db.commit(); db.refresh(render)
    return render


def audio_studio_response(timeline: Timeline, db: Session):
    project = db.get(Project, timeline.project_id)
    tracks = db.scalars(select(AudioTrack).options(selectinload(AudioTrack.cues)).where(AudioTrack.timeline_id == timeline.id).order_by(AudioTrack.position)).unique().all()
    profiles = db.scalars(select(VoiceProfile).join(Character).where(Character.project_id == project.id).order_by(VoiceProfile.id)).all()
    return {"timeline_id": timeline.id, "project_id": project.id, "total_duration_seconds": timeline_response(timeline, db)["total_duration_seconds"], "voice_profiles": profiles, "tracks": tracks}


def cue_project_id(cue: AudioCue, db: Session) -> int:
    track = db.get(AudioTrack, cue.track_id)
    return db.get(Timeline, track.timeline_id).project_id


def perform_voice_action(action: CrewAction, db: Session) -> CrewAction:
    cue = db.get(AudioCue, int(action.payload.get("cue_id", 0)))
    if not cue:
        action.status, action.error = "failed", "Audio cue not found"
        db.commit()
        return action
    profile = db.scalar(select(VoiceProfile).where(VoiceProfile.character_id == cue.character_id)) if cue.character_id else None
    provider = action.payload.get("provider") or (profile.provider if profile else settings.voice_provider)
    if provider != "simulation":
        consent = db.scalar(select(VoiceConsent).where(VoiceConsent.character_id == cue.character_id, VoiceConsent.consent_confirmed.is_(True)).order_by(VoiceConsent.id.desc())) if cue.character_id else None
        if not consent:
            action.status, action.error = "failed", "Confirm voice rights and AI disclosure before generating a performance"
            db.commit()
            return action
    pronunciations = db.scalars(select(PronunciationEntry).where(PronunciationEntry.project_id == action.project_id)).all()
    dictionary = "; ".join(f"pronounce {entry.term} as {entry.pronunciation}" for entry in pronunciations if entry.character_id in (None, cue.character_id))
    instructions = ". ".join(part for part in [profile.direction_notes if profile else "", cue.direction, dictionary] if part)
    action.status = "running"
    db.commit()
    try:
        base = render_dir / f"audio-cue-{cue.id}-{uuid4().hex[:8]}"
        filename, mime_type = generate_voice(
            provider, base, cue.text, instructions, api_key=settings.openai_api_key,
            model=settings.openai_voice_model, voice=action.payload.get("voice") or (profile.provider_voice_id if profile and profile.provider_voice_id else settings.openai_voice),
            duration=cue.duration_seconds, pitch=profile.pitch if profile else 0, pace=profile.pace if profile else 1,
        )
        cue.filename, cue.uri, cue.mime_type, cue.status = filename, f"/renders/{filename}", mime_type, "voice-ready"
        action.status, action.error = "completed", ""
        action.result = {"cue_id": cue.id, "provider": provider, "uri": cue.uri, "mime_type": mime_type, "ai_generated": provider != "simulation", "disclosure_required": provider != "simulation"}
    except VoiceProviderError as exc:
        action.status, action.error = "failed", str(exc)
    db.commit(); db.refresh(action)
    return action


def writer_project_context(project: Project, db: Session) -> dict:
    style = db.scalar(select(StyleProfile).where(StyleProfile.project_id == project.id))
    brief = db.scalar(select(StoryBrief).where(StoryBrief.project_id == project.id))
    characters = db.scalars(select(Character).where(Character.project_id == project.id).order_by(Character.id)).all()
    return {
        "title": project.title,
        "logline": project.logline,
        "style": {"era_primary": style.era_primary, "era_secondary": style.era_secondary, "direction": style.direction, "narrative": style.narrative, "archetypes": style.archetypes} if style else {},
        "story_brief": {"premise": brief.premise, "format": brief.format, "target_duration_minutes": brief.target_duration_minutes, "audience": brief.audience, "genre": brief.genre, "themes": brief.themes, "synopsis": brief.synopsis, "beats": brief.beats} if brief else None,
        "characters": [{"name": character.name, "role": character.role, "want": character.want, "need": character.need, "contradiction": character.contradiction} for character in characters],
        "locations": [{"name": location.name, "narrative_function": location.narrative_function, "description": location.description} for location in db.scalars(select(WorldLocation).where(WorldLocation.project_id == project.id).order_by(WorldLocation.id)).all()],
    }


def perform_writer_action(action: CrewAction, db: Session) -> CrewAction:
    proposal = action.payload.get("proposal") or {}
    required = {"premise", "format", "target_duration_minutes", "audience", "genre", "themes", "synopsis", "beats"}
    if not required.issubset(proposal):
        action.status, action.error = "failed", "Writer proposal is incomplete"
        db.commit()
        return action
    brief = db.scalar(select(StoryBrief).where(StoryBrief.project_id == action.project_id))
    if brief is None:
        brief = StoryBrief(project_id=action.project_id)
        db.add(brief)
    for key in required:
        setattr(brief, key, proposal[key])
    action.status, action.error = "completed", ""
    action.result = {"story_brief_id": brief.id, "provider": action.payload.get("provider", "simulation"), "applied_fields": sorted(required), "changes": proposal.get("changes", [])}
    db.commit(); db.refresh(brief)
    action.result = {**action.result, "story_brief_id": brief.id}
    db.commit(); db.refresh(action)
    return action


def director_project_context(project: Project, db: Session) -> dict:
    context = writer_project_context(project, db)
    scenes = db.scalars(select(Scene).where(Scene.project_id == project.id).order_by(Scene.position)).all()
    context["existing_scenes"] = [{"position": scene.position, "title": scene.title, "summary": scene.summary, "shots": [{"position": shot.position, "title": shot.title, "description": shot.description, "duration_seconds": shot.duration_seconds} for shot in db.scalars(select(Shot).where(Shot.scene_id == scene.id).order_by(Shot.position)).all()]} for scene in scenes]
    return context


def perform_director_action(action: CrewAction, db: Session) -> CrewAction:
    proposal = action.payload.get("proposal") or {}
    if not proposal.get("scenes"):
        action.status, action.error = "failed", "Director proposal has no scenes"
        db.commit()
        return action
    style = db.scalar(select(StyleProfile).where(StyleProfile.project_id == action.project_id))
    created_scenes = updated_scenes = created_shots = updated_shots = 0
    try:
        for scene_data in proposal["scenes"]:
            scene = db.scalar(select(Scene).where(Scene.project_id == action.project_id, Scene.position == scene_data["position"]))
            if scene is None:
                scene = Scene(project_id=action.project_id, position=scene_data["position"], title=scene_data["title"], summary=scene_data["summary"])
                db.add(scene); db.flush(); created_scenes += 1
            else:
                scene.title, scene.summary = scene_data["title"], scene_data["summary"]
                updated_scenes += 1
            for shot_data in scene_data["shots"]:
                shot = db.scalar(select(Shot).where(Shot.scene_id == scene.id, Shot.position == shot_data["position"]))
                if shot is None:
                    shot = Shot(scene_id=scene.id, position=shot_data["position"], title=shot_data["title"], description=shot_data["description"], duration_seconds=shot_data["duration_seconds"], status="draft")
                    db.add(shot); db.flush(); created_shots += 1
                else:
                    shot.title, shot.description, shot.duration_seconds, shot.status = shot_data["title"], shot_data["description"], shot_data["duration_seconds"], "draft"
                    updated_shots += 1
                location = db.scalar(select(WorldLocation).where(WorldLocation.project_id == action.project_id, WorldLocation.name == shot_data.get("location_name", ""))) if shot_data.get("location_name") else None
                names = set(shot_data.get("character_names", []))
                characters = db.scalars(select(Character).where(Character.project_id == action.project_id, Character.name.in_(names))).all() if names else []
                camera = {key: shot_data.get(key, "") for key in ("shot_size", "angle", "lens", "movement", "composition", "focus")}
                payload = ShotPlanInput(location_id=location.id if location else None, character_ids=[character.id for character in characters], action=shot_data.get("action", ""), dialogue=shot_data.get("dialogue", ""), camera=camera, lighting=shot_data.get("lighting", ""), continuity_notes=" · ".join(part for part in [shot_data.get("continuity_notes", ""), f"Performance: {shot_data.get('performance_intent', '')}" if shot_data.get("performance_intent") else ""] if part))
                plan = db.scalar(select(ShotPlan).where(ShotPlan.shot_id == shot.id))
                if plan is None:
                    plan = ShotPlan(shot_id=shot.id)
                    db.add(plan)
                else:
                    plan.version += 1
                for key, value in payload.model_dump().items():
                    setattr(plan, key, value)
                plan.storyboard_prompt = compile_storyboard_prompt(shot, payload, style, location, list(characters))
        timeline = db.scalar(select(Timeline).where(Timeline.project_id == action.project_id))
        if timeline:
            timeline.status = "needs-rebuild"
        action.status, action.error = "completed", ""
        action.result = {"provider": action.payload.get("provider", "simulation"), "created_scenes": created_scenes, "updated_scenes": updated_scenes, "created_shots": created_shots, "updated_shots": updated_shots, "timeline_needs_rebuild": bool(timeline), "non_destructive": True}
    except Exception as exc:
        db.rollback()
        action = db.get(CrewAction, action.id)
        action.status, action.error = "failed", str(exc)
    db.commit(); db.refresh(action)
    return action


def character_design_context(character: Character, db: Session) -> dict:
    project = db.get(Project, character.project_id)
    context = writer_project_context(project, db)
    context["character"] = {"id": character.id, "name": character.name, "role": character.role, "want": character.want, "need": character.need, "contradiction": character.contradiction, "current_design": {"appearance": character.design.appearance, "palette": character.design.palette, "wardrobe": character.design.wardrobe, "consistency_anchors": character.design.consistency_anchors} if character.design else None}
    return context


def background_design_context(location: WorldLocation, db: Session) -> dict:
    project = db.get(Project, location.project_id)
    context = writer_project_context(project, db)
    context["location"] = {"id": location.id, "name": location.name, "narrative_function": location.narrative_function, "description": location.description, "geography": location.geography, "time_period": location.time_period, "current_design": {"appearance": location.design.appearance, "palette": location.design.palette, "layers": location.design.layers, "lighting_variants": location.design.lighting_variants, "continuity_anchors": location.design.continuity_anchors} if location.design else None}
    return context


def perform_character_design_action(action: CrewAction, db: Session) -> CrewAction:
    character = db.get(Character, int(action.payload.get("target_id", 0)))
    proposal = action.payload.get("proposal") or {}
    if not character or not all(key in proposal for key in ("appearance", "palette", "wardrobe", "consistency_anchors")):
        action.status, action.error = "failed", "Character design proposal is incomplete"
        db.commit()
        return action
    design_input = CharacterDesignInput(**{key: proposal[key] for key in ("appearance", "palette", "wardrobe", "consistency_anchors")})
    design = db.scalar(select(CharacterDesign).where(CharacterDesign.character_id == character.id))
    if design is None:
        design = CharacterDesign(character_id=character.id)
        db.add(design)
    else:
        design.version += 1
    for key, value in design_input.model_dump().items():
        setattr(design, key, value)
    style = db.scalar(select(StyleProfile).where(StyleProfile.project_id == character.project_id))
    design.reference_brief = compile_reference_brief(character, design_input, style)
    action.status, action.error = "completed", ""
    db.commit(); db.refresh(design)
    result = {"character_id": character.id, "design_id": design.id, "version": design.version, "generation_queued": False, "changes": proposal.get("changes", [])}
    request = action.payload.get("request", {})
    if request.get("queue_generation"):
        try:
            generation = generate_character_reference(character.id, GenerationRequest(provider=request.get("generation_provider", "mock")), db)
            result.update({
                "generation_queued": True,
                "generation_job_id": generation["id"],
                "generation_status": generation["status"],
                "generation_provider": generation["provider"],
                "generation_assets": [
                    {"id": asset.id, "uri": asset.uri, "mime_type": asset.mime_type, "version": asset.version}
                    for asset in generation.get("assets", [])
                ],
            })
        except Exception as exc:
            result["generation_error"] = str(getattr(exc, "detail", exc))
    action = db.get(CrewAction, action.id)
    action.status, action.result = "completed", result
    db.commit(); db.refresh(action)
    return action


def perform_background_design_action(action: CrewAction, db: Session) -> CrewAction:
    location = db.get(WorldLocation, int(action.payload.get("target_id", 0)))
    proposal = action.payload.get("proposal") or {}
    keys = ("appearance", "palette", "layers", "lighting_variants", "continuity_anchors")
    if not location or not all(key in proposal for key in keys):
        action.status, action.error = "failed", "Background design proposal is incomplete"
        db.commit()
        return action
    design_input = LocationDesignInput(**{key: proposal[key] for key in keys})
    design = db.scalar(select(LocationDesign).where(LocationDesign.location_id == location.id))
    if design is None:
        design = LocationDesign(location_id=location.id)
        db.add(design)
    else:
        design.version += 1
    for key, value in design_input.model_dump().items():
        setattr(design, key, value)
    style = db.scalar(select(StyleProfile).where(StyleProfile.project_id == location.project_id))
    design.reference_brief = compile_background_brief(location, design_input, style)
    action.status, action.error = "completed", ""
    db.commit(); db.refresh(design)
    result = {"location_id": location.id, "design_id": design.id, "version": design.version, "generation_queued": False, "changes": proposal.get("changes", [])}
    request = action.payload.get("request", {})
    if request.get("queue_generation"):
        try:
            generation = generate_background(location.id, GenerationRequest(provider=request.get("generation_provider", "mock")), db)
            result.update({
                "generation_queued": True,
                "generation_job_id": generation["id"],
                "generation_status": generation["status"],
                "generation_provider": generation["provider"],
                "generation_assets": [
                    {"id": asset.id, "uri": asset.uri, "mime_type": asset.mime_type, "version": asset.version}
                    for asset in generation.get("assets", [])
                ],
            })
        except Exception as exc:
            result["generation_error"] = str(getattr(exc, "detail", exc))
    action = db.get(CrewAction, action.id)
    action.status, action.result = "completed", result
    db.commit(); db.refresh(action)
    return action


def animator_shot_context(shot: Shot, db: Session) -> dict:
    scene = db.get(Scene, shot.scene_id)
    project = db.get(Project, scene.project_id)
    context = writer_project_context(project, db)
    plan = shot.plan
    composition = db.scalar(select(ShotComposition).where(ShotComposition.shot_id == shot.id))
    if composition:
        layers = db.scalars(select(CompositionLayer).where(CompositionLayer.composition_id == composition.id).order_by(CompositionLayer.z_index)).all()
        layer_context = [{"id": layer.id, "name": layer.name, "kind": layer.kind, "opacity": layer.opacity, "transform": layer.transform, "animation": layer.animation} for layer in layers]
    else:
        layer_context = []
        if plan and plan.location_id:
            location = db.get(WorldLocation, plan.location_id)
            if location:
                layer_context.append({"id": None, "name": location.name, "kind": "background", "opacity": 1, "transform": {"x": .5, "y": .5, "scale": 1, "rotation": 0}, "animation": {}})
        if plan:
            for character_id in plan.character_ids:
                character = db.get(Character, character_id)
                if character:
                    layer_context.append({"id": None, "name": character.name, "kind": "character", "opacity": 1, "transform": {"x": .5, "y": .58, "scale": 1, "rotation": 0}, "animation": {}})
        if not layer_context:
            layer_context.append({"id": None, "name": "Background plate", "kind": "background", "opacity": 1, "transform": {"x": .5, "y": .5, "scale": 1, "rotation": 0}, "animation": {}})
    context["shot"] = {"id": shot.id, "title": shot.title, "description": shot.description, "duration_seconds": shot.duration_seconds, "scene_title": scene.title, "plan": {"action": plan.action, "dialogue": plan.dialogue, "lighting": plan.lighting, "camera": plan.camera, "continuity_notes": plan.continuity_notes} if plan else None}
    context["composition"] = {"id": composition.id, "camera": composition.camera, "version": composition.version} if composition else None
    context["layers"] = layer_context
    return context


def perform_animator_action(action: CrewAction, db: Session) -> CrewAction:
    shot = db.scalars(select(Shot).options(selectinload(Shot.plan)).where(Shot.id == int(action.payload.get("target_id", 0)))).one_or_none()
    try:
        proposal = AnimatorProposal.model_validate(action.payload.get("proposal") or {})
    except Exception as exc:
        action.status, action.error = "failed", f"Animator proposal is incomplete: {exc}"
        db.commit()
        return action
    if not shot or not shot.plan:
        action.status, action.error = "failed", "Shot plan not found"
        db.commit()
        return action
    composition = db.scalar(select(ShotComposition).where(ShotComposition.shot_id == shot.id))
    if composition is None:
        build_shot_composition(shot.id, db)
        composition = db.scalar(select(ShotComposition).where(ShotComposition.shot_id == shot.id))
    layers = db.scalars(select(CompositionLayer).where(CompositionLayer.composition_id == composition.id).order_by(CompositionLayer.z_index)).all()
    by_id = {layer.id: layer for layer in layers}
    applied = []
    for motion in proposal.layer_motions:
        layer = by_id.get(motion.layer_id) if motion.layer_id else next((item for item in layers if item.name.casefold() == motion.layer_name.casefold() and item.kind == motion.kind), None)
        if not layer:
            continue
        layer.animation = {"intent": motion.intent, "easing": motion.easing, "end": {"x": motion.end_x, "y": motion.end_y, "scale": motion.end_scale, "rotation": motion.end_rotation, "opacity": motion.end_opacity}}
        applied.append({"layer_id": layer.id, "name": layer.name, "intent": motion.intent})
    if not applied:
        action.status, action.error = "failed", "No proposed motion matched the composition layers"
        db.commit()
        return action
    composition.camera = proposal.camera.model_dump()
    composition.version += 1
    composition.status = "draft"
    action.status, action.error = "completed", ""
    db.commit(); db.refresh(composition)
    result = {"shot_id": shot.id, "composition_id": composition.id, "composition_version": composition.version, "applied_layers": applied, "camera": proposal.camera.model_dump(), "acting_beats": proposal.acting_beats, "preview_queued": False}
    request = action.payload.get("request", {})
    if request.get("render_preview"):
        render = render_shot_motion(composition.id, MotionRenderRequest(quality=request.get("quality", "proxy"), fps=request.get("fps")), db)
        result.update({"preview_queued": True, "preview_render_id": render.id, "preview_status": render.status, "preview_uri": render.uri, "preview_error": render.error})
    action = db.get(CrewAction, action.id)
    action.status, action.result = "completed", result
    db.commit(); db.refresh(action)
    return action


@app.get("/api/crew/roles")
def crew_roles():
    return [{"id": role, **data} for role, data in CREW_ROLES.items()]


@app.get("/api/animation/providers")
def animation_providers():
    return {"active": settings.animator_provider, "providers": [{"id": "simulation", "label": "Local motion planner", "ready": True}, {"id": "openai", "label": "OpenAI Animator", "ready": bool(settings.openai_api_key)}]}


@app.get("/api/voice/providers")
def voice_providers():
    return {"active": settings.voice_provider, "providers": [
        {"id": "simulation", "label": "Timing slate", "ready": True, "ai_generated": False},
        {"id": "openai", "label": "OpenAI voices", "ready": bool(settings.openai_api_key), "ai_generated": True, "model": settings.openai_voice_model},
    ]}


@app.get("/api/writer/providers")
def writer_providers():
    return {"active": settings.writer_provider, "providers": [
        {"id": "simulation", "label": "Local story planner", "ready": True},
        {"id": "openai", "label": "OpenAI Writer", "ready": bool(settings.openai_api_key), "model": settings.openai_writer_model},
    ]}


@app.get("/api/director/providers")
def director_providers():
    return {"active": settings.director_provider, "providers": [
        {"id": "simulation", "label": "Local coverage planner", "ready": True},
        {"id": "openai", "label": "OpenAI Director", "ready": bool(settings.openai_api_key), "model": settings.openai_director_model},
    ]}


@app.get("/api/visual-development/providers")
def visual_development_providers():
    return {"active": settings.visual_agent_provider, "providers": [
        {"id": "simulation", "label": "Local design planner", "ready": True},
        {"id": "openai", "label": "OpenAI visual development", "ready": bool(settings.openai_api_key), "model": settings.openai_visual_agent_model},
    ]}


@app.get("/api/projects/{project_id}/crew")
def get_project_crew(project_id: int, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    assignments = db.scalars(select(CrewAssignment).where(CrewAssignment.project_id == project_id).order_by(CrewAssignment.id)).all()
    actions = db.scalars(select(CrewAction).where(CrewAction.project_id == project_id).order_by(CrewAction.id.desc()).limit(30)).all()
    return {"project_id": project_id, "assignments": [CrewAssignmentRead.model_validate(item) for item in assignments], "actions": [CrewActionRead.model_validate(item) for item in actions]}


@app.post("/api/projects/{project_id}/crew/deploy")
def deploy_crew(project_id: int, payload: CrewDeployRequest, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    invalid = [role for role in payload.roles if role not in CREW_ROLES]
    if invalid:
        raise HTTPException(422, f"Unknown crew roles: {', '.join(invalid)}")
    for role in payload.roles:
        assignment = db.scalar(select(CrewAssignment).where(CrewAssignment.project_id == project_id, CrewAssignment.role == role))
        if assignment:
            assignment.enabled, assignment.autonomy = True, payload.autonomy
        else:
            data = CREW_ROLES[role]
            db.add(CrewAssignment(project_id=project_id, role=role, name=data["name"], autonomy=payload.autonomy, capabilities=data["capabilities"]))
    db.commit()
    return get_project_crew(project_id, db)


@app.put("/api/crew-assignments/{assignment_id}", response_model=CrewAssignmentRead)
def update_crew_assignment(assignment_id: int, payload: CrewAssignmentUpdate, db: Session = Depends(get_db)):
    assignment = db.get(CrewAssignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Crew assignment not found")
    for key, value in payload.model_dump().items():
        setattr(assignment, key, value)
    db.commit(); db.refresh(assignment)
    return assignment


@app.get("/api/projects/{project_id}/crew/briefing")
def crew_briefing(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    suggestions = []
    if not db.scalar(select(StoryBrief).where(StoryBrief.project_id == project_id)):
        suggestions.append({"role": "writer", "title": "Develop the story brief", "reason": "The production does not have a structured story yet."})
    if not db.scalar(select(Character).where(Character.project_id == project_id)):
        suggestions.append({"role": "character_designer", "title": "Create the principal cast", "reason": "No character models are locked."})
    if not db.scalar(select(WorldLocation).where(WorldLocation.project_id == project_id)):
        suggestions.append({"role": "background_artist", "title": "Design the first location", "reason": "The world library is empty."})
    if not db.scalar(select(Scene).where(Scene.project_id == project_id)):
        suggestions.append({"role": "director", "title": "Break the story into shots", "reason": "No scenes or camera coverage are planned."})
    timeline = db.scalar(select(Timeline).where(Timeline.project_id == project_id))
    if not timeline:
        suggestions.append({"role": "editor", "title": "Build the working timeline", "reason": "Picture has not been assembled."})
    elif not db.scalar(select(AudioTrack).where(AudioTrack.timeline_id == timeline.id)):
        suggestions.append({"role": "sound_producer", "title": "Initialize sound production", "reason": "Dialogue, music, effects, and ambience tracks are not prepared."})
    return {"project_id": project_id, "headline": suggestions[0]["title"] if suggestions else "Production is ready for the next creative pass", "suggestions": suggestions}


@app.put("/api/characters/{character_id}/voice-consent", response_model=VoiceConsentRead)
def set_voice_consent(character_id: int, payload: VoiceConsentInput, db: Session = Depends(get_db)):
    if not db.get(Character, character_id):
        raise HTTPException(404, "Character not found")
    consent = db.scalar(select(VoiceConsent).where(VoiceConsent.character_id == character_id).order_by(VoiceConsent.id.desc()))
    if consent is None:
        consent = VoiceConsent(character_id=character_id)
        db.add(consent)
    for key, value in payload.model_dump().items():
        setattr(consent, key, value)
    db.commit(); db.refresh(consent)
    return consent


@app.post("/api/projects/{project_id}/pronunciations", response_model=PronunciationRead, status_code=status.HTTP_201_CREATED)
def add_pronunciation(project_id: int, payload: PronunciationInput, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    if payload.character_id:
        character = db.get(Character, payload.character_id)
        if not character or character.project_id != project_id:
            raise HTTPException(422, "Character does not belong to this production")
    entry = PronunciationEntry(project_id=project_id, **payload.model_dump())
    db.add(entry); db.commit(); db.refresh(entry)
    return entry


@app.post("/api/audio-cues/{cue_id}/crew/generate-voice", response_model=CrewActionRead, status_code=status.HTTP_201_CREATED)
def ask_sound_producer(cue_id: int, payload: CrewVoiceRequest, db: Session = Depends(get_db)):
    cue = db.get(AudioCue, cue_id)
    if not cue:
        raise HTTPException(404, "Audio cue not found")
    if not cue.text.strip():
        raise HTTPException(422, "Add dialogue before asking the Sound Producer")
    project_id = cue_project_id(cue, db)
    assignment = db.scalar(select(CrewAssignment).where(CrewAssignment.project_id == project_id, CrewAssignment.role == "sound_producer", CrewAssignment.enabled.is_(True)))
    if not assignment:
        raise HTTPException(409, "Deploy the Sound Producer bot first")
    action = CrewAction(project_id=project_id, assignment_id=assignment.id, role="sound_producer", action_type="generate_voice", title="Produce dialogue performance", summary=f"Generate and place: {cue.text[:120]}", status="proposed", requires_approval=assignment.autonomy != "execute", payload={"cue_id": cue.id, "provider": payload.provider, "voice": payload.voice})
    db.add(action); db.commit(); db.refresh(action)
    return perform_voice_action(action, db) if assignment.autonomy == "execute" else action


@app.post("/api/projects/{project_id}/crew/writer/propose", response_model=CrewActionRead, status_code=status.HTTP_201_CREATED)
def ask_writer(project_id: int, payload: WriterProposalRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    assignment = db.scalar(select(CrewAssignment).where(CrewAssignment.project_id == project_id, CrewAssignment.role == "writer", CrewAssignment.enabled.is_(True)))
    if not assignment:
        raise HTTPException(409, "Deploy the Writer bot first")
    provider = payload.provider or settings.writer_provider
    action = CrewAction(project_id=project_id, assignment_id=assignment.id, role="writer", action_type="develop_story", title="Develop story package", summary=f"{payload.objective[:180]}", status="running", requires_approval=assignment.autonomy != "execute", payload={"provider": provider, "request": payload.model_dump()})
    db.add(action); db.commit(); db.refresh(action)
    try:
        proposal = create_writer_proposal(writer_project_context(project, db), payload, provider=provider, api_key=settings.openai_api_key, model=settings.openai_writer_model, instructions=assignment.instructions)
        action.payload = {**action.payload, "proposal": proposal.model_dump()}
        action.summary = proposal.rationale
        action.status = "proposed"
        db.commit(); db.refresh(action)
    except WriterAgentError as exc:
        action.status, action.error = "failed", str(exc)
        db.commit(); db.refresh(action)
        return action
    return perform_writer_action(action, db) if assignment.autonomy == "execute" else action


@app.post("/api/projects/{project_id}/crew/director/propose", response_model=CrewActionRead, status_code=status.HTTP_201_CREATED)
def ask_director(project_id: int, payload: DirectorProposalRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    assignment = db.scalar(select(CrewAssignment).where(CrewAssignment.project_id == project_id, CrewAssignment.role == "director", CrewAssignment.enabled.is_(True)))
    if not assignment:
        raise HTTPException(409, "Deploy the Director bot first")
    provider = payload.provider or settings.director_provider
    action = CrewAction(project_id=project_id, assignment_id=assignment.id, role="director", action_type="direct_coverage", title="Direct scene and shot coverage", summary=payload.objective[:180], status="running", requires_approval=assignment.autonomy != "execute", payload={"provider": provider, "request": payload.model_dump()})
    db.add(action); db.commit(); db.refresh(action)
    try:
        proposal = create_director_proposal(director_project_context(project, db), payload, provider=provider, api_key=settings.openai_api_key, model=settings.openai_director_model, instructions=assignment.instructions)
        action.payload = {**action.payload, "proposal": proposal.model_dump()}
        action.summary, action.status = proposal.approach, "proposed"
        db.commit(); db.refresh(action)
    except DirectorAgentError as exc:
        action.status, action.error = "failed", str(exc)
        db.commit(); db.refresh(action)
        return action
    return perform_director_action(action, db) if assignment.autonomy == "execute" else action


@app.post("/api/shots/{shot_id}/crew/animate", response_model=CrewActionRead, status_code=status.HTTP_201_CREATED)
def ask_animator(shot_id: int, payload: AnimatorProposalRequest, db: Session = Depends(get_db)):
    shot = db.scalars(select(Shot).options(selectinload(Shot.plan)).where(Shot.id == shot_id)).one_or_none()
    if not shot:
        raise HTTPException(404, "Shot not found")
    if not shot.plan:
        raise HTTPException(409, "Save the shot plan before asking the Animator")
    scene = db.get(Scene, shot.scene_id)
    assignment = db.scalar(select(CrewAssignment).where(CrewAssignment.project_id == scene.project_id, CrewAssignment.role == "animator", CrewAssignment.enabled.is_(True)))
    if not assignment:
        raise HTTPException(409, "Deploy the Animator bot first")
    provider = payload.provider or settings.animator_provider
    action = CrewAction(project_id=scene.project_id, assignment_id=assignment.id, role="animator", action_type="animate_shot", title=f"Animate {shot.title}", summary=payload.objective[:180], status="running", requires_approval=assignment.autonomy != "execute", payload={"provider": provider, "target_id": shot.id, "request": payload.model_dump()})
    db.add(action); db.commit(); db.refresh(action)
    try:
        proposal = create_animator_proposal(animator_shot_context(shot, db), payload, provider=provider, api_key=settings.openai_api_key, model=settings.openai_animator_model, instructions=assignment.instructions)
        action.payload = {**action.payload, "proposal": proposal.model_dump()}
        action.summary, action.status = proposal.approach, "proposed"
        db.commit(); db.refresh(action)
    except AnimatorAgentError as exc:
        action.status, action.error = "failed", str(exc)
        db.commit(); db.refresh(action)
        return action
    return perform_animator_action(action, db) if assignment.autonomy == "execute" else action


@app.post("/api/characters/{character_id}/crew/design", response_model=CrewActionRead, status_code=status.HTTP_201_CREATED)
def ask_character_designer(character_id: int, payload: CharacterDesignerRequest, db: Session = Depends(get_db)):
    character = db.scalars(select(Character).options(selectinload(Character.design)).where(Character.id == character_id)).one_or_none()
    if not character:
        raise HTTPException(404, "Character not found")
    assignment = db.scalar(select(CrewAssignment).where(CrewAssignment.project_id == character.project_id, CrewAssignment.role == "character_designer", CrewAssignment.enabled.is_(True)))
    if not assignment:
        raise HTTPException(409, "Deploy the Character Designer bot first")
    provider = payload.provider or settings.visual_agent_provider
    action = CrewAction(project_id=character.project_id, assignment_id=assignment.id, role="character_designer", action_type="design_character", title=f"Design {character.name}", summary=payload.objective[:180], status="running", requires_approval=assignment.autonomy != "execute", payload={"provider": provider, "target_id": character.id, "request": payload.model_dump()})
    db.add(action); db.commit(); db.refresh(action)
    try:
        proposal = create_character_design_proposal(character_design_context(character, db), payload, provider=provider, api_key=settings.openai_api_key, model=settings.openai_visual_agent_model, instructions=assignment.instructions)
        action.payload = {**action.payload, "proposal": proposal.model_dump()}
        action.summary, action.status = proposal.rationale, "proposed"
        db.commit(); db.refresh(action)
    except VisualAgentError as exc:
        action.status, action.error = "failed", str(exc)
        db.commit(); db.refresh(action)
        return action
    return perform_character_design_action(action, db) if assignment.autonomy == "execute" else action


@app.post("/api/locations/{location_id}/crew/design", response_model=CrewActionRead, status_code=status.HTTP_201_CREATED)
def ask_background_artist(location_id: int, payload: BackgroundArtistRequest, db: Session = Depends(get_db)):
    location = db.scalars(select(WorldLocation).options(selectinload(WorldLocation.design)).where(WorldLocation.id == location_id)).one_or_none()
    if not location:
        raise HTTPException(404, "Location not found")
    assignment = db.scalar(select(CrewAssignment).where(CrewAssignment.project_id == location.project_id, CrewAssignment.role == "background_artist", CrewAssignment.enabled.is_(True)))
    if not assignment:
        raise HTTPException(409, "Deploy the Background Artist bot first")
    provider = payload.provider or settings.visual_agent_provider
    action = CrewAction(project_id=location.project_id, assignment_id=assignment.id, role="background_artist", action_type="design_background", title=f"Design {location.name}", summary=payload.objective[:180], status="running", requires_approval=assignment.autonomy != "execute", payload={"provider": provider, "target_id": location.id, "request": payload.model_dump()})
    db.add(action); db.commit(); db.refresh(action)
    try:
        proposal = create_background_design_proposal(background_design_context(location, db), payload, provider=provider, api_key=settings.openai_api_key, model=settings.openai_visual_agent_model, instructions=assignment.instructions)
        action.payload = {**action.payload, "proposal": proposal.model_dump()}
        action.summary, action.status = proposal.rationale, "proposed"
        db.commit(); db.refresh(action)
    except VisualAgentError as exc:
        action.status, action.error = "failed", str(exc)
        db.commit(); db.refresh(action)
        return action
    return perform_background_design_action(action, db) if assignment.autonomy == "execute" else action


@app.post("/api/crew-actions/{action_id}/approve", response_model=CrewActionRead)
def approve_crew_action(action_id: int, db: Session = Depends(get_db)):
    action = db.get(CrewAction, action_id)
    if not action:
        raise HTTPException(404, "Crew action not found")
    if action.status != "proposed":
        raise HTTPException(409, "Only proposed work can be approved")
    action.reviewed_at = datetime.now(timezone.utc)
    if action.action_type == "generate_voice":
        return perform_voice_action(action, db)
    if action.action_type == "develop_story":
        return perform_writer_action(action, db)
    if action.action_type == "direct_coverage":
        return perform_director_action(action, db)
    if action.action_type == "animate_shot":
        return perform_animator_action(action, db)
    if action.action_type == "design_character":
        return perform_character_design_action(action, db)
    if action.action_type == "design_background":
        return perform_background_design_action(action, db)
    return action


@app.post("/api/crew-actions/{action_id}/reject", response_model=CrewActionRead)
def reject_crew_action(action_id: int, db: Session = Depends(get_db)):
    action = db.get(CrewAction, action_id)
    if not action:
        raise HTTPException(404, "Crew action not found")
    if action.status != "proposed":
        raise HTTPException(409, "Only proposed work can be rejected")
    action.status, action.reviewed_at = "rejected", datetime.now(timezone.utc)
    db.commit(); db.refresh(action)
    return action


@app.get("/api/projects/{project_id}/audio-studio", response_model=AudioStudioRead)
def get_audio_studio(project_id: int, db: Session = Depends(get_db)):
    timeline = db.scalar(select(Timeline).where(Timeline.project_id == project_id))
    if not timeline:
        raise HTTPException(409, "Build the timeline before opening Audio Studio")
    return audio_studio_response(timeline, db)


@app.post("/api/timelines/{timeline_id}/audio/build", response_model=AudioStudioRead)
def build_audio_tracks(timeline_id: int, db: Session = Depends(get_db)):
    timeline = db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(404, "Timeline not found")
    if not db.scalar(select(AudioTrack).where(AudioTrack.timeline_id == timeline_id)):
        defaults = [("Dialogue", "dialogue"), ("Music", "music"), ("Sound FX", "sfx"), ("Ambience", "ambience")]
        for position, (name, kind) in enumerate(defaults, start=1):
            db.add(AudioTrack(timeline_id=timeline_id, name=name, kind=kind, position=position))
        db.commit()
    return audio_studio_response(timeline, db)


@app.put("/api/characters/{character_id}/voice", response_model=VoiceProfileRead)
def update_voice_profile(character_id: int, payload: VoiceProfileInput, db: Session = Depends(get_db)):
    if not db.get(Character, character_id):
        raise HTTPException(404, "Character not found")
    profile = db.scalar(select(VoiceProfile).where(VoiceProfile.character_id == character_id))
    if profile is None:
        profile = VoiceProfile(character_id=character_id)
        db.add(profile)
    else:
        profile.version += 1
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.commit(); db.refresh(profile)
    return profile


def validate_audio_cue(track: AudioTrack, payload: AudioCueInput, db: Session):
    timeline = db.get(Timeline, track.timeline_id)
    if payload.clip_id:
        clip = db.get(TimelineClip, payload.clip_id)
        if not clip or clip.timeline_id != timeline.id:
            raise HTTPException(422, "Clip does not belong to this timeline")
    if payload.character_id:
        character = db.get(Character, payload.character_id)
        if not character or character.project_id != timeline.project_id:
            raise HTTPException(422, "Character does not belong to this production")


@app.post("/api/audio-tracks/{track_id}/cues", response_model=AudioCueRead, status_code=status.HTTP_201_CREATED)
def create_audio_cue(track_id: int, payload: AudioCueInput, db: Session = Depends(get_db)):
    track = db.get(AudioTrack, track_id)
    if not track:
        raise HTTPException(404, "Audio track not found")
    validate_audio_cue(track, payload, db)
    cue = AudioCue(track_id=track_id, **payload.model_dump())
    db.add(cue); db.commit(); db.refresh(cue)
    return cue


@app.put("/api/audio-cues/{cue_id}", response_model=AudioCueRead)
def update_audio_cue(cue_id: int, payload: AudioCueInput, db: Session = Depends(get_db)):
    cue = db.get(AudioCue, cue_id)
    if not cue:
        raise HTTPException(404, "Audio cue not found")
    validate_audio_cue(db.get(AudioTrack, cue.track_id), payload, db)
    for key, value in payload.model_dump().items():
        setattr(cue, key, value)
    db.commit(); db.refresh(cue)
    return cue


@app.post("/api/audio-cues/{cue_id}/generate-scratch", response_model=AudioCueRead)
def generate_scratch_audio(cue_id: int, db: Session = Depends(get_db)):
    cue = db.get(AudioCue, cue_id)
    if not cue:
        raise HTTPException(404, "Audio cue not found")
    profile = db.scalar(select(VoiceProfile).where(VoiceProfile.character_id == cue.character_id)) if cue.character_id else None
    cue.filename = f"audio-cue-{cue.id}-{uuid4().hex[:8]}.wav"
    generate_timing_slate(render_dir / cue.filename, cue.text, cue.duration_seconds, profile.pitch if profile else 0, profile.pace if profile else 1)
    cue.uri, cue.mime_type, cue.status = f"/renders/{cue.filename}", "audio/wav", "scratch-ready"
    db.commit(); db.refresh(cue)
    return cue


@app.post("/api/audio-cues/{cue_id}/upload", response_model=AudioCueRead)
async def upload_audio_cue(cue_id: int, request: Request, filename: str, db: Session = Depends(get_db)):
    cue = db.get(AudioCue, cue_id)
    if not cue:
        raise HTTPException(404, "Audio cue not found")
    content = await request.body()
    if not content or len(content) > settings.max_artifact_bytes:
        raise HTTPException(413, "Audio file is empty or too large")
    suffix = Path(filename).suffix.lower()
    allowed = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".ogg": "audio/ogg"}
    if suffix not in allowed:
        raise HTTPException(422, "Upload WAV, MP3, M4A, or OGG audio")
    cue.filename = f"audio-cue-{cue.id}-{uuid4().hex[:8]}{suffix}"
    (render_dir / cue.filename).write_bytes(content)
    cue.uri, cue.mime_type, cue.status = f"/renders/{cue.filename}", allowed[suffix], "asset-ready"
    db.commit(); db.refresh(cue)
    return cue


@app.post("/api/timelines/{timeline_id}/render", response_model=AnimaticRenderRead, status_code=status.HTTP_201_CREATED)
def render_timeline(timeline_id: int, db: Session = Depends(get_db)):
    timeline = db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(404, "Timeline not found")
    render = AnimaticRender(timeline_id=timeline.id, status="rendering", render_settings={"fps": timeline.fps, "width": timeline.width, "height": timeline.height, "kind": "proxy_animatic"})
    db.add(render); db.commit(); db.refresh(render)
    work_dir = render_dir / f"animatic-work-{render.id}"
    try:
        data = timeline_response(timeline, db)
        clips = []
        for clip in data["clips"]:
            source = render_dir / Path(clip["storyboard_uri"]).name if clip["storyboard_uri"] else None
            clips.append({"source": source, "title": clip["shot_title"], "subtitle": f"{clip['scene_title']}  /  {clip['duration_seconds']:.1f}s  /  {clip['transition']}", "duration": clip["duration_seconds"], "transition": clip["transition"], "transition_duration": clip["transition_duration"]})
        audio_clips = []
        tracks = db.scalars(select(AudioTrack).options(selectinload(AudioTrack.cues)).where(AudioTrack.timeline_id == timeline.id, AudioTrack.muted.is_(False))).unique().all()
        for track in tracks:
            for cue in track.cues:
                if cue.uri:
                    audio_clips.append({"source": render_dir / Path(cue.uri).name, "start": cue.start_seconds, "duration": cue.duration_seconds, "volume": track.volume})
        render.filename = f"animatic-{render.id}.mp4"
        render.render_settings = {**render.render_settings, "audio_cues": len(audio_clips)}
        render_animatic(clips, render_dir / render.filename, work_dir, timeline.fps, timeline.width, timeline.height, audio_clips)
        render.uri, render.status = f"/renders/{render.filename}", "completed"
        timeline.status = "preview-ready"
    except Exception as exc:
        render.status, render.error = "failed", str(exc)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    db.commit(); db.refresh(render)
    return render


@app.post("/api/timelines/{timeline_id}/render-master", response_model=AnimaticRenderRead, status_code=status.HTTP_201_CREATED)
def render_master(timeline_id: int, payload: MasterRenderRequest, db: Session = Depends(get_db)):
    timeline = db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(404, "Timeline not found")
    if payload.profile == "4k":
        width, height = 3840, 2160
    elif payload.profile == "1080p":
        width, height = 1920, 1080
    else:
        scale = min(1, 1280 / timeline.width, 720 / timeline.height)
        width = max(2, int(timeline.width * scale) // 2 * 2)
        height = max(2, int(timeline.height * scale) // 2 * 2)
    fps = payload.fps or timeline.fps
    base_settings = {"kind": "production_master", "profile": payload.profile, "fps": fps, "width": width, "height": height}
    render = AnimaticRender(timeline_id=timeline.id, status="rendering", render_settings=base_settings)
    db.add(render); db.commit(); db.refresh(render)
    work_dir = render_dir / f"master-work-{render.id}"
    try:
        timeline_data = timeline_response(timeline, db)
        clips = []
        for clip in timeline_data["clips"]:
            clips.append({
                "motion_source": render_dir / Path(clip["motion_uri"]).name if clip["motion_uri"] else None,
                "still_source": render_dir / Path(clip["storyboard_uri"]).name if clip["storyboard_uri"] else None,
                "title": clip["shot_title"], "subtitle": f"{clip['scene_title']}  /  {clip['duration_seconds']:.1f}s",
                "duration": clip["duration_seconds"], "transition": clip["transition"], "transition_duration": clip["transition_duration"],
            })
        audio_clips = []
        tracks = db.scalars(select(AudioTrack).options(selectinload(AudioTrack.cues)).where(AudioTrack.timeline_id == timeline.id, AudioTrack.muted.is_(False))).unique().all()
        for track in tracks:
            for cue in track.cues:
                if cue.uri:
                    audio_clips.append({"source": render_dir / Path(cue.uri).name, "start": cue.start_seconds, "duration": cue.duration_seconds, "volume": track.volume})
        render.filename = f"master-{render.id}-{payload.profile}.mp4"
        manifest = render_timeline_master(clips, audio_clips, render_dir / render.filename, work_dir, fps, width, height)
        render.uri, render.status = f"/renders/{render.filename}", "completed"
        render.render_settings = {**base_settings, **manifest}
        timeline.status = "master-ready"
    except Exception as exc:
        render.status, render.error = "failed", str(exc)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    db.commit(); db.refresh(render)
    return render


def export_job_response(job: MasterExportJob, db: Session):
    segments = db.scalars(select(MasterSegment).where(MasterSegment.export_id == job.id).order_by(MasterSegment.position)).all()
    completed = sum(segment.status == "completed" for segment in segments)
    total = len(segments)
    return {"id": job.id, "timeline_id": job.timeline_id, "profile": job.profile, "fps": job.fps, "width": job.width, "height": job.height, "status": job.status, "final_filename": job.final_filename, "final_uri": job.final_uri, "error": job.error, "completed_segments": completed, "total_segments": total, "progress_percent": round(completed / total * 100, 1) if total else 0, "segments": segments}


def master_dimensions(timeline: Timeline, profile: str):
    if profile == "4k":
        return 3840, 2160
    if profile == "1080p":
        return 1920, 1080
    scale = min(1, 1280 / timeline.width, 720 / timeline.height)
    return max(2, int(timeline.width * scale) // 2 * 2), max(2, int(timeline.height * scale) // 2 * 2)


def create_segmented_export(timeline_id: int, payload: SegmentedExportRequest, db: Session, job_status: str = "planned") -> MasterExportJob:
    timeline = db.get(Timeline, timeline_id)
    if not timeline:
        raise HTTPException(404, "Timeline not found")
    timeline_data = timeline_response(timeline, db)
    if not timeline_data["clips"]:
        raise HTTPException(409, "Timeline has no clips")
    width, height = master_dimensions(timeline, payload.profile)
    fps = payload.fps or timeline.fps
    job = MasterExportJob(timeline_id=timeline.id, profile=payload.profile, fps=fps, width=width, height=height, status=job_status)
    db.add(job); db.flush()
    starts = clip_start_times(timeline_data["clips"], fps)
    tracks = db.scalars(select(AudioTrack).options(selectinload(AudioTrack.cues)).where(AudioTrack.timeline_id == timeline.id, AudioTrack.muted.is_(False))).unique().all()
    audio = [{"uri": cue.uri, "start": cue.start_seconds, "duration": cue.duration_seconds, "volume": track.volume} for track in tracks for cue in track.cues if cue.uri]
    ranges = segment_clip_ranges(timeline_data["clips"], payload.segment_size)
    for position, (start, end) in enumerate(ranges, start=1):
        segment_start = starts[start]
        segment_end = starts[end] if end < len(starts) else timeline_data["total_duration_seconds"]
        clips = [{"motion_uri": clip["motion_uri"], "still_uri": clip["storyboard_uri"], "title": clip["shot_title"], "subtitle": f"{clip['scene_title']}  /  {clip['duration_seconds']:.1f}s", "duration": clip["duration_seconds"], "transition": clip["transition"] if index > start else "cut", "transition_duration": clip["transition_duration"] if index > start else 0} for index, clip in enumerate(timeline_data["clips"][start:end], start=start)]
        segment_audio = [{**cue, "start": max(0, cue["start"] - segment_start)} for cue in audio if cue["start"] < segment_end and cue["start"] + cue["duration"] > segment_start]
        db.add(MasterSegment(export_id=job.id, position=position, manifest={"clip_start": start + 1, "clip_end": end, "start_seconds": segment_start, "end_seconds": segment_end, "clips": clips, "audio": segment_audio}))
    db.commit()
    db.refresh(job)
    return job


@app.post("/api/timelines/{timeline_id}/master-exports", response_model=MasterExportRead, status_code=status.HTTP_201_CREATED)
def plan_segmented_export(timeline_id: int, payload: SegmentedExportRequest, db: Session = Depends(get_db)):
    job = create_segmented_export(timeline_id, payload, db)
    return export_job_response(job, db)


@app.post("/api/timelines/{timeline_id}/master-exports/distributed", response_model=MasterExportRead, status_code=status.HTTP_201_CREATED)
def start_distributed_export(timeline_id: int, payload: SegmentedExportRequest, db: Session = Depends(get_db)):
    job = create_segmented_export(timeline_id, payload, db, "farm-queued")
    return export_job_response(job, db)


@app.get("/api/timelines/{timeline_id}/master-exports/latest", response_model=MasterExportRead)
def latest_master_export(timeline_id: int, db: Session = Depends(get_db)):
    job = db.scalar(select(MasterExportJob).where(MasterExportJob.timeline_id == timeline_id).order_by(MasterExportJob.id.desc()))
    if not job:
        raise HTTPException(404, "No resumable export plan yet")
    return export_job_response(job, db)


@app.get("/api/master-exports/{export_id}", response_model=MasterExportRead)
def get_master_export(export_id: int, db: Session = Depends(get_db)):
    job = db.get(MasterExportJob, export_id)
    if not job:
        raise HTTPException(404, "Master export not found")
    return export_job_response(job, db)


def render_master_segment(segment: MasterSegment, job: MasterExportJob, db: Session):
    segment.status, segment.attempts, segment.error = "rendering", segment.attempts + 1, ""
    job.status = "rendering"
    db.commit()
    work_dir = render_dir / f"segment-work-{segment.id}"
    try:
        clips = [{"motion_source": render_dir / Path(clip["motion_uri"]).name if clip.get("motion_uri") else None, "still_source": render_dir / Path(clip["still_uri"]).name if clip.get("still_uri") else None, **{key: clip[key] for key in ("title", "subtitle", "duration", "transition", "transition_duration")}} for clip in segment.manifest["clips"]]
        audio = [{"source": render_dir / Path(cue["uri"]).name, "start": cue["start"], "duration": cue["duration"], "volume": cue["volume"]} for cue in segment.manifest.get("audio", [])]
        segment.filename = f"master-export-{job.id}-segment-{segment.position:04d}.mp4"
        render_timeline_master(clips, audio, render_dir / segment.filename, work_dir, job.fps, job.width, job.height)
        segment.uri, segment.status = f"/renders/{segment.filename}", "completed"
        segment.checksum_sha256 = sha256_file(render_dir / segment.filename)
    except Exception as exc:
        segment.status, segment.error = "failed", str(exc)
        job.status, job.error = "needs-attention", str(exc)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    db.commit()


@app.post("/api/master-exports/{export_id}/run-next", response_model=MasterExportRead)
def run_next_segment(export_id: int, db: Session = Depends(get_db)):
    job = db.get(MasterExportJob, export_id)
    if not job:
        raise HTTPException(404, "Master export not found")
    segment = db.scalar(select(MasterSegment).where(MasterSegment.export_id == export_id, MasterSegment.status.in_(["queued", "failed"])).order_by(MasterSegment.position))
    if segment:
        render_master_segment(segment, job, db)
    remaining = db.scalar(select(MasterSegment).where(MasterSegment.export_id == export_id, MasterSegment.status != "completed"))
    if not remaining:
        job.status = "segments-ready"; db.commit()
    return export_job_response(job, db)


@app.post("/api/master-exports/{export_id}/run-all", response_model=MasterExportRead)
def run_all_segments(export_id: int, db: Session = Depends(get_db)):
    job = db.get(MasterExportJob, export_id)
    if not job:
        raise HTTPException(404, "Master export not found")
    for segment in db.scalars(select(MasterSegment).where(MasterSegment.export_id == export_id, MasterSegment.status.in_(["queued", "failed"])).order_by(MasterSegment.position)).all():
        render_master_segment(segment, job, db)
        if segment.status == "failed":
            break
    if not db.scalar(select(MasterSegment).where(MasterSegment.export_id == export_id, MasterSegment.status != "completed")):
        job.status = "segments-ready"; db.commit()
    return export_job_response(job, db)


@app.post("/api/master-exports/{export_id}/resume", response_model=MasterExportRead)
def resume_master_export(export_id: int, db: Session = Depends(get_db)):
    job = db.get(MasterExportJob, export_id)
    if not job:
        raise HTTPException(404, "Master export not found")
    for segment in db.scalars(select(MasterSegment).where(MasterSegment.export_id == export_id)).all():
        if segment.status == "completed":
            path = render_dir / segment.filename
            if not path.exists() or sha256_file(path) != segment.checksum_sha256:
                segment.status, segment.error, segment.checksum_sha256 = "queued", "Output missing or checksum mismatch; queued for recovery", ""
        elif segment.status in {"rendering", "leased", "failed"}:
            segment.status = "queued"
    job.status, job.error = "planned", ""
    db.commit()
    return export_job_response(job, db)


@app.post("/api/master-exports/{export_id}/dispatch", response_model=MasterExportRead)
def dispatch_master_export(export_id: int, db: Session = Depends(get_db)):
    job = db.get(MasterExportJob, export_id)
    if not job:
        raise HTTPException(404, "Master export not found")
    if job.status == "completed":
        return export_job_response(job, db)
    segments = db.scalars(select(MasterSegment).where(MasterSegment.export_id == export_id)).all()
    if not segments:
        raise HTTPException(409, "Export has no segments")
    if all(segment.status == "completed" for segment in segments):
        assemble_master_export_job(job, db)
        return export_job_response(job, db)
    for segment in segments:
        if segment.status == "failed":
            segment.status, segment.error = "queued", ""
    job.status = "farm-rendering" if any(segment.status in {"leased", "rendering"} for segment in segments) else "farm-queued"
    job.error = ""
    db.commit()
    return export_job_response(job, db)


def assemble_master_export_job(job: MasterExportJob, db: Session, strict: bool = True) -> None:
    segments = db.scalars(select(MasterSegment).where(MasterSegment.export_id == job.id).order_by(MasterSegment.position)).all()
    if not segments or any(segment.status != "completed" for segment in segments):
        message = "All segments must complete before assembly"
        if strict:
            raise HTTPException(409, message)
        job.status, job.error = "needs-attention", message
        db.commit()
        return
    files = [render_dir / segment.filename for segment in segments]
    if any(not path.exists() for path in files):
        message = "One or more segment files are missing; verify and resume the export"
        if strict:
            raise HTTPException(409, message)
        job.status, job.error = "needs-attention", message
        db.commit()
        return
    work_dir = render_dir / f"assembly-work-{job.id}"
    job.status, job.error = "assembling", ""
    db.commit()
    try:
        job.final_filename = f"master-export-{job.id}-{job.profile}.mp4"
        assemble_segments(files, render_dir / job.final_filename, work_dir)
        job.final_uri, job.status = f"/renders/{job.final_filename}", "completed"
        timeline = db.get(Timeline, job.timeline_id)
        if timeline:
            timeline.status = "master-ready"
    except Exception as exc:
        job.status, job.error = "needs-attention", str(exc)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    db.commit()


@app.post("/api/master-exports/{export_id}/assemble", response_model=MasterExportRead)
def assemble_master_export(export_id: int, db: Session = Depends(get_db)):
    job = db.get(MasterExportJob, export_id)
    if not job:
        raise HTTPException(404, "Master export not found")
    assemble_master_export_job(job, db)
    return export_job_response(job, db)


@app.post("/api/workers/{worker_id}/master-segments/claim")
def claim_master_segment(worker_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    if "master_segment" not in worker.supported_tasks:
        raise HTTPException(409, "Worker is not configured for master segments")
    for expired in db.scalars(select(MasterSegment).where(MasterSegment.status == "leased", MasterSegment.leased_until < utcnow())).all():
        expired.status, expired.worker_id, expired.leased_until = "queued", None, None
        expired_job = db.get(MasterExportJob, expired.export_id)
        if expired_job and expired_job.status.startswith("farm-"):
            expired_job.status = "farm-queued"
    db.commit()
    segment = db.scalar(select(MasterSegment).join(MasterExportJob).where(MasterSegment.status == "queued", MasterExportJob.status.in_(["farm-queued", "farm-rendering"])).order_by(MasterSegment.id))
    if not segment:
        return Response(status_code=204)
    job = db.get(MasterExportJob, segment.export_id)
    segment.status, segment.worker_id, segment.attempts = "leased", worker.id, segment.attempts + 1
    segment.leased_until = utcnow() + timedelta(seconds=settings.worker_lease_seconds)
    worker.status, worker.last_seen = "busy", utcnow()
    job.status = "farm-rendering"
    db.commit()
    return {"segment": MasterSegmentRead.model_validate(segment).model_dump(), "export": {"id": job.id, "fps": job.fps, "width": job.width, "height": job.height, "profile": job.profile}}


def leased_master_segment(worker: RenderWorker, segment_id: int, db: Session) -> MasterSegment:
    segment = db.get(MasterSegment, segment_id)
    if not segment or segment.worker_id != worker.id or segment.status != "leased":
        raise HTTPException(409, "Segment is not leased to this worker")
    return segment


@app.post("/api/workers/{worker_id}/master-segments/{segment_id}/heartbeat", response_model=MasterSegmentRead)
def heartbeat_master_segment(worker_id: int, segment_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    segment = leased_master_segment(worker, segment_id, db)
    segment.leased_until = utcnow() + timedelta(seconds=settings.worker_lease_seconds)
    worker.status, worker.last_seen = "busy", utcnow()
    db.commit(); db.refresh(segment)
    return segment


@app.post("/api/workers/{worker_id}/master-segments/{segment_id}/fail", response_model=MasterSegmentRead)
def fail_master_segment(worker_id: int, segment_id: int, payload: JobFailure, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    segment = leased_master_segment(worker, segment_id, db)
    segment.status = "queued" if payload.retryable else "failed"
    segment.error, segment.worker_id, segment.leased_until = payload.error[:4000], None, None
    worker.status, worker.last_seen = "online", utcnow()
    job = db.get(MasterExportJob, segment.export_id)
    job.status = "farm-queued" if payload.retryable else "needs-attention"
    job.error = "" if payload.retryable else segment.error
    db.commit(); db.refresh(segment)
    return segment


@app.put("/api/workers/{worker_id}/master-segments/{segment_id}/artifact", response_model=MasterSegmentRead)
async def upload_master_segment(worker_id: int, segment_id: int, request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    worker = authenticate_worker(worker_id, authorization, db)
    segment = leased_master_segment(worker, segment_id, db)
    segment.filename = f"master-export-{segment.export_id}-segment-{segment.position:04d}.mp4"
    path = render_dir / segment.filename
    temporary = render_dir / f".{segment.filename}.{uuid4().hex}.part"
    maximum = settings.max_artifact_bytes * 16
    received = 0
    checksum = hashlib.sha256()
    try:
        with temporary.open("wb") as output:
            async for chunk in request.stream():
                received += len(chunk)
                if received > maximum:
                    raise HTTPException(413, "Segment artifact is too large")
                checksum.update(chunk)
                output.write(chunk)
        if not received:
            raise HTTPException(413, "Segment artifact is empty")
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    segment.uri, segment.status, segment.checksum_sha256 = f"/renders/{segment.filename}", "completed", checksum.hexdigest()
    worker.status, worker.last_seen = "online", utcnow()
    job = db.get(MasterExportJob, segment.export_id)
    distributed = job.status.startswith("farm-")
    db.flush()
    if not db.scalar(select(MasterSegment).where(MasterSegment.export_id == segment.export_id, MasterSegment.status != "completed")):
        if distributed:
            assemble_master_export_job(job, db, strict=False)
        else:
            job.status = "segments-ready"
    db.commit(); db.refresh(segment)
    return segment


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(static_dir / "index.html")
