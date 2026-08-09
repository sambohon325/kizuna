# Kizuna Studio

Kizuna Studio is a browser-based, AI-powered anime production workspace. Creators can direct every detail or delegate selected departments to an AI Crew while keeping proposals, approvals, outputs, and failures visible. The platform is intentionally provider agnostic so local and hosted generation engines can be added without changing the editor.

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
- Writer's Room with project briefs, editable outlines, and a deployable Writer bot that produces schema-validated story proposals through approval or automatic execution
- Character Studio with narrative identity, visual anchors, versioned designs, style-aware reference briefs, and a Character Designer bot that can propose or apply a complete character bible before optionally queuing reference-sheet generation
- Provider-neutral image generation jobs with versioned media assets
- Unified asset review with side-by-side versions, approval and rejection notes, an explicit production master, and non-destructive rollback that invalidates stale composites
- Production vault with configurable retention, media-inclusive project ZIPs, SHA-256 verification, automatic backup pruning, and revocable download-limited delivery links
- Local ComfyUI adapter using API-format workflows; safe simulation provider by default
- Authenticated network workers with capability reporting, heartbeats, leased jobs, retries, and artifact upload
- Worlds Studio with reusable locations, parallax layers, lighting variants, continuity locks, background assets, and a Background Artist bot that can propose or apply a production-ready location bible before optionally queuing background generation
- Storyboard and Shot Planner with beat expansion, camera language, cast/location assignment, continuity prompts, and storyboard assets
- Director bot with local and hosted structured-output engines, pacing and coverage controls, performance direction, continuity-aware camera plans, non-destructive scene/shot application, and automatic timeline invalidation
- Timeline editor with clip timing, cuts/dissolves/fades, sound cues, reordering, downloadable H.264 proxy animatics, and an Editor bot that can assemble raw shots, propose reversible pacing changes, flag missing picture/motion, and optionally render a review master
- Audio & Voice Studio with versioned character voice bibles, dialogue/music/SFX/ambience lanes, timed cues, timing-slate generation, performance uploads, and animatic mixing
- AI Crew Control Room with Writer, Director, Character Designer, Background Artist, Animator, Sound Producer, and Editor roles; assist/propose/execute autonomy; standing instructions; workflow briefings; an auditable approval feed; and a persistent Producer assistant that coordinates deployed bots one safe stage at a time from story through review master
- Provider-neutral dialogue generation with a safe local timing-slate mode, optional OpenAI speech adapter, voice-rights records, required AI disclosure metadata, and per-character pronunciation entries
- Scene Compositor with shot-specific layer stacks, asset-library reuse, transforms, visibility, opacity, blend modes, virtual camera/grade plans, and flattened preview renders
- Keyframed layer motion with linear/eased interpolation, animated opacity and transforms, virtual-camera motion, versioned H.264 shot previews, and an Animator bot that proposes or applies editable acting/camera passes before optionally rendering a preview
- Continuous master export that combines current motion clips, safe still-frame fallbacks, Timeline transitions, and the Audio Studio mix at Preview, 1080p, or 4K UHD
- One-click distributed master exports with safe cut boundaries, authenticated worker dispatch, live progress, retries, SHA-256 verification, automatic final assembly, and local recovery controls
- Pillow frame normalization and bundled FFmpeg locally; system FFmpeg in the production container
- Docker Compose foundation for eventual Coolify deployment

## Next milestones

1. Add S3-compatible remote object storage and scheduled off-server backups
2. Add Redis-backed crew/render scheduling, concurrency controls, and worker scaling
3. Add delivery presets for festival, streaming, broadcast, captions, and archival masters
4. Add team review pages, timecoded notes, and approval gates
5. Add automated continuity and technical quality-control passes before master export

See [AI Crew and voice setup](docs/AI_CREW.md) for autonomy behavior and optional hosted speech configuration.
See [asset review and rollback](docs/ASSET_REVIEW.md) for the production-version workflow.
See [production storage and delivery](docs/STORAGE.md) for backup and retention settings.
