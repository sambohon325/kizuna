# Kizuna Studio

Kizuna Studio is a browser-based, AI-assisted anime production workspace. The current vertical slice manages productions, Creative DNA style bibles, structured story development, characters, worlds, shots, picture editing, and proxy animatics. It is intentionally model-provider agnostic so local and hosted generation engines can be added without changing the editor.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The local setup uses SQLite and creates `anime_studio.db` automatically.

To connect a render machine, see [ComfyUI provider setup](docs/COMFYUI.md).
For distributed workers, see [network render farm setup](docs/RENDER_FARM.md).

## Test

```powershell
pytest
```

## Architecture

- FastAPI API and browser application
- SQLAlchemy persistence (SQLite locally, PostgreSQL-ready)
- Structured Creative DNA rather than opaque prompt presets
- Writer's Room with project briefs, generated dramatic beats, and editable outlines
- Character Studio with narrative identity, visual anchors, versioned designs, and style-aware reference briefs
- Provider-neutral image generation jobs with versioned media assets
- Local ComfyUI adapter using API-format workflows; safe simulation provider by default
- Authenticated network workers with capability reporting, heartbeats, leased jobs, retries, and artifact upload
- Worlds Studio with reusable locations, parallax layers, lighting variants, continuity locks, and background assets
- Storyboard and Shot Planner with beat expansion, camera language, cast/location assignment, continuity prompts, and storyboard assets
- Timeline editor with clip timing, cuts/dissolves/fades, sound cues, reordering, and downloadable H.264 proxy animatics
- Audio & Voice Studio with versioned character voice bibles, dialogue/music/SFX/ambience lanes, timed cues, timing-slate generation, performance uploads, and animatic mixing
- Scene Compositor with shot-specific layer stacks, asset-library reuse, transforms, visibility, opacity, blend modes, virtual camera/grade plans, and flattened preview renders
- Keyframed layer motion with linear/eased interpolation, animated opacity and transforms, virtual-camera motion, and versioned H.264 shot previews
- Continuous master export that combines current motion clips, safe still-frame fallbacks, Timeline transitions, and the Audio Studio mix at Preview, 1080p, or 4K UHD
- Pillow frame normalization and bundled FFmpeg locally; system FFmpeg in the production container
- Docker Compose foundation for eventual Coolify deployment

## Next milestones

1. Resumable segmented master jobs and render-farm scheduling for feature-length exports
2. AI voice-provider adapters with consent metadata and pronunciation controls
3. Production object storage, checksums, review states, and asset approval
4. Redis-backed production queue and worker scaling
5. Delivery presets for festival, streaming, broadcast, captions, and archival masters
