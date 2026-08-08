from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import Base, engine, get_db
from app.character_development import compile_reference_brief
from app.models import Character, CharacterDesign, Project, Scene, Shot, StoryBrief, StyleProfile
from app.schemas import CharacterDesignInput, CharacterDesignRead, CharacterInput, CharacterRead, ProjectCreate, ProjectRead, SceneCreate, SceneRead, ShotCreate, ShotRead, StoryBriefInput, StoryBriefRead, StoryOutlineUpdate, StyleProfileInput, StyleProfileRead
from app.style_catalog import STYLE_CATALOG
from app.story_development import develop_story

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name, version="0.1.0")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def project_query():
    return select(Project).options(selectinload(Project.style_profile), selectinload(Project.story_brief), selectinload(Project.characters).selectinload(Character.design), selectinload(Project.scenes).selectinload(Scene.shots))


@app.get("/api/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/style-catalog")
def style_catalog():
    return STYLE_CATALOG


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


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(static_dir / "index.html")
