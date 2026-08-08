# Kizuna Studio

Kizuna Studio is a browser-based, AI-assisted anime production workspace. The current vertical slice manages productions, Creative DNA style bibles, structured story development, scenes, and shots. It is intentionally model-provider agnostic so local and hosted generation engines can be added without changing the editor.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The local setup uses SQLite and creates `anime_studio.db` automatically.

## Test

```powershell
pytest
```

## Architecture

- FastAPI API and browser application
- SQLAlchemy persistence (SQLite locally, PostgreSQL-ready)
- Structured Creative DNA rather than opaque prompt presets
- Writer's Room with project briefs, generated dramatic beats, and editable outlines
- Provider and render-worker interfaces to be added behind stable job APIs
- Docker Compose foundation for eventual Coolify deployment

## Next milestones

1. AI provider adapters for screenplay and outline development
2. Character and location asset libraries
3. Storyboard generation jobs and review workflow
4. Redis-backed render queue and authenticated remote workers
5. Timeline, audio, compositing, and FFmpeg export
