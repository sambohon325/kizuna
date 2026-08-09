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
from app.database import Base, engine, get_db
from app.character_development import compile_reference_brief
from app.generation import ComfyUIProvider, MockProvider, ProviderError
from app.models import AnimaticRender, BackgroundAsset, BackgroundJob, Character, CharacterDesign, GenerationJob, LocationDesign, MediaAsset, Project, RenderWorker, Scene, Shot, ShotPlan, StoryboardAsset, StoryboardJob, StoryBrief, StyleProfile, Timeline, TimelineClip, WorkerAssignment, WorldLocation
from app.schemas import AnimaticRenderRead, BackgroundJobRead, CharacterDesignInput, CharacterDesignRead, CharacterInput, CharacterRead, GenerationJobRead, GenerationRequest, JobCompletion, JobFailure, LocationDesignInput, LocationDesignRead, ProjectCreate, ProjectRead, RenderWorkerRead, SceneCreate, SceneRead, ShotCreate, ShotPlanInput, ShotPlanRead, ShotRead, StoryboardJobRead, StoryBriefInput, StoryBriefRead, StoryExpansionRequest, StoryOutlineUpdate, StyleProfileInput, StyleProfileRead, TimelineBuildRequest, TimelineClipUpdate, TimelineOrderUpdate, TimelineRead, WorkerHeartbeat, WorkerRegistration, WorkerRegistrationResult, WorldLocationInput, WorldLocationRead
from app.shot_development import compile_storyboard_prompt
from app.style_catalog import STYLE_CATALOG
from app.story_development import develop_story
from app.world_development import compile_background_brief

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name, version="0.1.0")
static_dir = Path(__file__).parent / "static"
render_dir = Path(settings.render_directory).resolve()
render_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/renders", StaticFiles(directory=render_dir), name="renders")


def project_query():
    return select(Project).options(selectinload(Project.style_profile), selectinload(Project.story_brief), selectinload(Project.characters).selectinload(Character.design), selectinload(Project.locations).selectinload(WorldLocation.design), selectinload(Project.scenes).selectinload(Scene.shots).selectinload(Shot.plan))


def timeline_response(timeline: Timeline, db: Session):
    clips = db.scalars(select(TimelineClip).where(TimelineClip.timeline_id == timeline.id).order_by(TimelineClip.position)).all()
    output = []
    for clip in clips:
        shot = db.get(Shot, clip.shot_id)
        scene = db.get(Scene, shot.scene_id)
        asset = db.scalar(select(StoryboardAsset).where(StoryboardAsset.shot_id == shot.id).order_by(StoryboardAsset.version.desc(), StoryboardAsset.id.desc()))
        output.append({
            "id": clip.id, "timeline_id": clip.timeline_id, "shot_id": clip.shot_id, "position": clip.position,
            "duration_seconds": clip.duration_seconds, "transition": clip.transition,
            "transition_duration": clip.transition_duration, "audio_cue": clip.audio_cue,
            "shot_title": shot.title, "scene_title": scene.title, "storyboard_uri": asset.uri if asset else "",
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
    db.commit()
    return {"workers": [RenderWorkerRead.model_validate(worker).model_dump() for worker in workers], "jobs": [{"id": job.id, "character_id": job.character_id, "status": job.status, "error": job.error, "assets": len(db.scalars(select(MediaAsset).where(MediaAsset.generation_job_id == job.id)).all())} for job in jobs]}


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
        render.filename = f"animatic-{render.id}.mp4"
        render_animatic(clips, render_dir / render.filename, work_dir, timeline.fps, timeline.width, timeline.height)
        render.uri, render.status = f"/renders/{render.filename}", "completed"
        timeline.status = "preview-ready"
    except Exception as exc:
        render.status, render.error = "failed", str(exc)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    db.commit(); db.refresh(render)
    return render


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(static_dir / "index.html")
