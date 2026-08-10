# Kizuna Studio

Kizuna Studio is a browser-based, AI-powered anime production workspace. Creators can direct every detail or delegate selected departments to an AI Crew while keeping proposals, approvals, outputs, and failures visible. The platform is intentionally provider agnostic so local and hosted generation engines can be added without changing the editor.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The local setup uses SQLite, creates `anime_studio.db` automatically, and applies versioned database migrations before startup.

To connect a render machine, see [ComfyUI provider setup](docs/COMFYUI.md).
For distributed workers, see [network render farm setup](docs/RENDER_FARM.md).

## Test

```powershell
pytest
```

## Architecture

- FastAPI API and browser application
- SQLAlchemy persistence (SQLite locally, PostgreSQL-ready)
- Versioned Alembic schema migrations with guarded adoption of existing databases, idempotent startup upgrades, and an ordered Coolify migration service
- Structured Creative DNA rather than opaque prompt presets
- Writer's Room with project briefs, editable outlines, and a deployable Writer bot that produces schema-validated story proposals through approval or automatic execution
- Character Studio with narrative identity, visual anchors, versioned designs, style-aware reference briefs, and a Character Designer bot that can propose or apply a complete character bible before optionally queuing reference-sheet generation
- Provider-neutral image generation jobs with versioned media assets
- Unified asset review with side-by-side versions, approval and rejection notes, an explicit production master, and non-destructive rollback that invalidates stale composites
- Production vault with local or S3-compatible destinations, automatic off-server schedules, configurable retention, media-inclusive project ZIPs, SHA-256 verification, backup pruning, and revocable download-limited delivery links
- Automatic metadata-first media lifecycle with independent image/video/audio working proxies, checksum-verified Hive replication, freshness-gated cleanup eligibility, and creator approval that never silently deletes an original
- A durable database-backed job ledger with idempotency, progress history, cancellation, bounded retries, expired-lease recovery, optional Redis dispatch, and a separate production worker; local development can execute working-media jobs inline
- A stage-aware Compliance Center with preliminary checks, provider-neutral text/trademark/visual/audio scanners, fail-closed outages, evidence-backed finding resolution, an asset rights register, stale-scan invalidation, strict release gates, and hash-chained audit events
- An enforced original-work-only charter that rejects fan-fiction and unofficial derivative requests, plus independently reviewable professional identities and exact prior-work claims for creators working with their own catalog
- Local ComfyUI adapter using API-format workflows; safe simulation provider by default
- Authenticated network workers with capability reporting, heartbeats, leased jobs, retries, and artifact upload
- Worlds Studio with reusable locations, parallax layers, lighting variants, continuity locks, background assets, and a Background Artist bot that can propose or apply a production-ready location bible before optionally queuing background generation
- Storyboard and Shot Planner with beat expansion, camera language, cast/location assignment, continuity prompts, and storyboard assets
- Director bot with local and hosted structured-output engines, pacing and coverage controls, performance direction, continuity-aware camera plans, non-destructive scene/shot application, and automatic timeline invalidation
- Timeline editor with draggable magnetic clip ordering, zoom, clip timing, cuts/dissolves/fades, sound cues, downloadable H.264 proxy animatics, and an Editor bot that can assemble raw shots, propose reversible pacing changes, flag missing picture/motion, and optionally render a review master
- Audio & Voice Studio with a zoomable multitrack arrangement, snapping, playhead placement, draggable and resizable regions, non-destructive duplication, source-preserving audio splits, dialogue/music/SFX/ambience lanes, performance uploads, and animatic mixing
- Simple AI Crew modes (Guided, Autopilot, Manual, or Custom) with Writer, Director, Character Designer, Background Artist, Animator, Sound Producer, and Editor departments; advanced autonomy and standing instructions remain available on demand, while approvals and the Producer's next action stay front and center
- Progressive-disclosure workspaces that keep everyday creative actions visible and tuck technical export, voice-rights, and provider settings into clearly labeled setup panels
- A server-backed production milestone tracker where green means a saved completion requirement was actually met; ready, in-progress, and blocked work remain visually distinct without duplicating sidebar navigation
- A focused Story Map view that connects each outline beat to its scene, shot coverage, assigned cast, and world; production gaps are surfaced inline and linked resources open directly in their craft workspace
- A character-arc focus inside the Story Map that follows planned appearances, suggests beginning/turn/ending placements, and surfaces relationship intersections without marking unfinished work complete
- A three-view Character Studio for narrative identity, versioned history and emotional arcs, character relationships, and visual model development without combining every craft into one form
- Full-canvas craft dashboards with glass surfaces instead of modal-style outer boxes, plus dedicated multi-monitor windows that retain the selected production
- A studio-wide Connections & Tools hub for OpenAI, Claude, Gemini, Ollama, custom AI APIs, generation engines, and handoffs to Adobe, Corel, GIMP, Krita, OpenToonz, Blender, and Resolve; secret values remain server-side
- A privacy-first Kizuna Node companion with one-time enrollment, Windows/macOS/Linux builds, a mixed-platform Hive, per-device schedules and usage throttles, local/cloud workload placement, AI token accounting, editable model rates, monthly budgets, and savings guidance
- Production scope shared across creation, dashboard, writing, timelines, mastering, and AI context: distribution channel, one-off/trailer/feature/series format, aspect ratio, target runtime, installments, and seasons can evolve without deleting existing work
- A persistent floating Kizuna Assistant that follows the active craft workspace, reads backend production progress and scope, remembers project conversations, and links creators to relevant next actions
- Provider-neutral dialogue generation with a safe local timing-slate mode, optional OpenAI speech adapter, voice-rights records, required AI disclosure metadata, and per-character pronunciation entries
- Scene Compositor with shot-specific layer stacks, asset-library reuse, transforms, visibility, opacity, blend modes, virtual camera/grade plans, and flattened preview renders
- Keyframed layer motion with linear/eased interpolation, animated opacity and transforms, virtual-camera motion, versioned H.264 shot previews, and an Animator bot that proposes or applies editable acting/camera passes before optionally rendering a preview
- Continuous master export that combines current motion clips, safe still-frame fallbacks, Timeline transitions, and the Audio Studio mix at Preview, 1080p, or 4K UHD
- One-click distributed master exports with safe cut boundaries, authenticated worker dispatch, live progress, retries, SHA-256 verification, automatic final assembly, and local recovery controls
- Pillow frame normalization and bundled FFmpeg locally; system FFmpeg in the production container
- Docker Compose foundation for eventual Coolify deployment

## Next milestones

1. Migrate crew and render workloads onto the durable job contract; media transfer, storage audits, and production backups now use the shared ledger
2. Add PostgreSQL migration verification in CI
3. Add health checks, job diagnostics, backup restore verification, and the guarded Coolify deployment path
4. Add authentication and tenant isolation before any public deployment

See [the phased Kizuna roadmap](docs/ROADMAP.md) for how Anime Studio becomes the shared foundation for Express, Paper, Hero, Motion, CineReal, AdForge, collaboration, integrations, and the future creator ecosystem.

See [AI Crew and voice setup](docs/AI_CREW.md) for autonomy behavior and optional hosted speech configuration.
See [AI provider routing](docs/AI_PROVIDER_ROUTING.md) for assigning OpenAI, Claude, Gemini, Ollama, or custom engines to studio roles.
See [Kizuna Node and mixed-platform Hive](docs/KIZUNA_NODE.md) for computer enrollment, privacy, schedules, usage throttles, workload placement, and AI budget monitoring.
See [asset review and rollback](docs/ASSET_REVIEW.md) for the production-version workflow.
See [character story development](docs/CHARACTER_STORY.md) for histories, arcs, and relationship records.
See [multi-window workspaces](docs/MULTI_WINDOW.md) for multi-monitor usage and direct workspace links.
See [production storage and delivery](docs/STORAGE.md) for backup and retention settings.
See [metadata-first media storage](docs/MEDIA_STORAGE.md) for local originals, lightweight previews, and Hive residency tracking.
See [durable production jobs](docs/JOBS.md) for retries, cancellation, worker recovery, Redis dispatch, and local inline behavior.
See [originality, rights, and release compliance](docs/COMPLIANCE.md) for enforced gates and audit limitations, and [professional verification](docs/PROFESSIONAL_VERIFICATION.md) for creator identity and prior-work claims.
See [picture and audio editing](docs/EDITING.md) for tactile edit controls.
See [database migrations](docs/DATABASE_MIGRATIONS.md) for local upgrades, existing-database adoption, and Coolify startup behavior.
See [self-hosted compliance scanners](docs/COMPLIANCE_SCANNERS.md) for lawful corpus ingestion and scanner protocol details, and [production domain and access](docs/DEPLOYMENT_DOMAIN.md) for `kizuna.technology` deployment guidance.
See [accounts and production isolation](docs/AUTHENTICATION.md) before exposing any Kizuna deployment to the internet.
