# Kizuna product and engineering roadmap

Kizuna's north star is a provider-neutral creative production platform that can carry one story, cast, world, asset library, and approval history across anime, comics, animation, short-form video, and future formats. The platform should feel like one connected studio rather than a collection of unrelated generators.

The current Anime Studio is the proving ground for that platform. Kizuna should make this workflow reliable before splitting attention across several branded applications.

## Product decisions

1. **One platform, multiple craft workspaces.** Writer's Room, Characters, Worlds, Shots, Timeline, Audio, Compositor, Vault, and Hive share one production graph. Future Paper, Hero, Motion, and Express experiences should be additional workspaces and output modes over that graph before they become separately packaged products.
2. **An orchestration engine, not a mandatory house model.** Kizuna Core should route and coordinate OpenAI, Claude, Gemini, Ollama, ComfyUI, hosted media models, custom studio models, and future engines. Owning foundation-model training is not required for the product to deliver consistency or professional workflow.
3. **Creator-controlled storage and compute.** Story structure, lineage, approvals, checksums, and lightweight previews remain available to Kizuna. Large originals may live on Hive devices or S3-compatible storage, with explicit replica and cleanup policies.
4. **Human authority remains visible.** AI departments can propose or execute according to creator-selected autonomy, but changes, costs, rights, failures, versions, and approval gates remain inspectable.
5. **Open interchange is part of the product.** Kizuna should build strong native tools while exchanging assets and timelines with applications creators already use. Integrations must progress from saved profiles to tested round-trip adapters.
6. **Technique libraries require provenance.** Era, composition, animation economy, color, narrative structure, and archetype controls can be mixed as Creative DNA. Public presets should describe techniques and licensed influences rather than promise imitation of a living artist or unlicensed proprietary model.

## What exists now

Kizuna already has a meaningful vertical production slice:

- structured production scope, Creative DNA, story development, characters, relationships, worlds, scenes, shots, and continuity context;
- specialized browser workspaces for writing, visual development, editing, sound, compositing, rendering, storage, and compute;
- Writer, Director, Character Designer, Background Artist, Animator, Sound Producer, Editor, Producer, and contextual Assistant foundations;
- provider-neutral AI routing, configurable integrations, token accounting, cost estimates, and creator budgets;
- versioned generated assets, review selection, reversible rollback, scene composition, keyframed motion, audio mixing, animatics, and 4K-capable master assembly;
- authenticated distributed render workers and a Windows/macOS/Linux Hive companion with schedules and usage throttles;
- local/S3 backups, secure delivery links, metadata-first media residency, lightweight thumbnails, and checksum-verified Hive replication; and
- a PostgreSQL-ready container layout with Redis present in the local production topology.

This is a strong single-studio alpha. It is not yet a safe multi-user cloud service, a real-time collaborative editor, a proprietary model platform, or a marketplace.

## How the proposed ecosystem maps to Kizuna

| Proposed idea | Kizuna direction | Timing |
| --- | --- | --- |
| Creative Cloud Hub | Evolve the existing studio shell into the shared production, account, storage, compute, integration, and billing hub. | Now through cloud beta |
| Kizuna Core Model Engine | Build a model and workflow orchestration layer with provider adapters, reproducible manifests, evaluation, provenance, and cost-aware routing. Do not block on training foundation models. | Near term |
| Character & Lore Vault | Promote current character, relationship, world, Creative DNA, reference, and residency data into reusable cross-production identity packs. | Near term |
| Kizuna Express | Add guided templates after the underlying anime pipeline can reliably produce, revise, and deliver an end-to-end project. | After production beta |
| Paper and Hero | Add page, panel, bubble, lettering, branching, and reading-flow workspaces over the shared story/cast/world graph. Paper is the best first expansion. | After shared platform APIs |
| Motion | Grow the current compositor, keyframe, rig, and render systems into a deeper reusable motion workspace. It should also power Anime, Paper motion panels, and Express. | Later platform phase |
| CineReal | Treat photoreal video as a model/provider and finishing mode first. A separate product is justified only after its workflow diverges materially. | Later |
| AdForge | Build campaign variants, captions, aspect-ratio adaptation, approvals, and analytics as an Express workflow before making it a separate application. | Later |
| Asset marketplace and Showcase | Begin with private studio libraries, rights metadata, exportable packs, and moderation foundations. Commerce and community follow identity, tenancy, licensing, and abuse controls. | Last |
| Cloud GPU streaming | Prefer normal job submission, proxies, Hive compute, and progressive results first. Add WebRTC/WebGPU remote interaction only for workflows that prove they require it. | Research/later |
| Subscription tiers | Add after accounts, organizations, metering, quotas, licensing, support boundaries, and reliable cloud operations exist. | Cloud beta |

## Phased delivery plan

### Phase 0 — Reliable local-first production core

Goal: turn the current single-studio alpha into a durable system that can survive long jobs, interrupted devices, application restarts, and large productions.

- automatically register every generated/rendered output with the media lifecycle;
- generate and retain editing proxies and thumbnails independently of originals;
- provide a creator-reviewed cleanup queue with fresh replica verification and no implicit deletion;
- move crew, render, media, and maintenance work onto a durable Redis-backed job contract;
- add idempotency, cancellation, retry policy, progress events, and recovery after restart;
- maintain the implemented Alembic migration path and add PostgreSQL production verification in CI;
- split the large application module into bounded production services without rewriting working craft UIs; and
- retain the implemented Operations readiness dashboard and backup archive verification, then add structured logs, service heartbeats, alert delivery, and recurring restore drills.

Exit gate: a complete short production can run locally or across a mixed-platform Hive, restart safely, recover every queued job, and prove where each required original and proxy resides.

### Phase 1 — Anime Studio production beta

Goal: make Kizuna credible for repeatable professional anime shorts, episodes, and feature planning.

- reusable Character Identity Packs with reference sets, palettes, expression/pose coverage, model/provider recipes, seeds, adapters, and rights metadata;
- reusable World and Prop Packs with layout, lighting, perspective, and continuity anchors;
- consistency evaluation across shots, with visual difference reports and creator-approved repair passes;
- production-wide AI plans with department dependencies, approval gates, budgets, and resumable Autopilot;
- stronger editing, audio automation, subtitles/captions, credits, color, loudness, and delivery presets;
- automated continuity, missing-media, frame, audio, caption, and master technical QC; and
- provider-backed story, trademark, visual, and music originality checks building on the strict Compliance Center, qualified release clearance, and output audit ledger; and
- timecoded review notes, approval states, and locked production versions.

Exit gate: a creator can take a scoped anime project from brief to reviewable master with repeatable characters/worlds, visible AI decisions, technical QC, and professional delivery files.

### Phase 2 — Secure collaborative cloud

Goal: deploy Kizuna through Coolify as a safe multi-user service without weakening its local-first model.

- extend the implemented accounts, production memberships, roles, ownership, invitations, session security, and project isolation into full organizations and studio administration;
- extend tenant-scoped route and media access with organization boundaries, broader audit history, rate limits, quotas, and secret rotation;
- production PostgreSQL migrations, Redis workers, S3-compatible originals/proxies, and signed asset access;
- team comments, assignments, timecoded review, notifications, and approval gates;
- operational monitoring, error reporting, tracing, usage dashboards, disaster recovery, and support tooling; and
- metering and billing foundations with bring-your-own-provider and studio-funded usage policies.

Exit gate: invited teams can safely collaborate on isolated productions, use cloud or Hive compute, understand costs, and recover from service or worker failure.

### Phase 3 — Interchange and extension platform

Goal: make Kizuna the engine that connects a studio's existing tools.

- a versioned internal interchange manifest for productions, identity packs, assets, timelines, reviews, and provenance;
- OpenTimelineIO and selected FCPXML/EDL interchange for picture workflows;
- layered image, audio stem, caption, and model-pack import/export where formats permit;
- tested adapters and round trips for ComfyUI, Blender, Krita/GIMP, OpenToonz, Resolve, and selected commercial tools;
- webhook/API automation, scoped integration credentials, and a documented adapter SDK; and
- conformance tests so integrations declare exactly which data survives a round trip.

Exit gate: creators can move approved materials into external tools and return revisions without losing identity, version, timing, review, or provenance context.

### Phase 4 — Express and adaptive publishing

Goal: expose the proven production engine through a simpler guided experience.

- goal-driven templates for trailers, one-minute vertical series, landscape web episodes, teasers, and pitch packages;
- automatic script and edit restructuring when runtime, series format, distribution channel, or aspect ratio changes;
- safe-area, caption, crop/reframe, thumbnail, title-card, and delivery variants from one approved production;
- a simplified AI-first flow that hides department detail until the creator asks for it; and
- reusable brand/story kits backed by the same Character & Lore Vault.

Exit gate: a non-specialist can generate, revise, and deliver a coherent short production while an expert can open the same project in the deep craft workspaces.

### Phase 5 — New storytelling workspaces

Goal: expand media types without fragmenting the platform.

1. **Paper:** manga/webtoon pages, panels, bubbles, lettering, screentones, reading order, and interactive branches.
2. **Hero:** Western-comic page language and interactive graphic-novel presentation, sharing Paper's layout engine.
3. **Motion:** deeper 2D rigs, vector/keyframe tools, camera paths, reusable animation systems, and optional 3D bridges.
4. **CineReal:** photoreal production controls and providers where rights, identity, consent, and provenance requirements are mature.
5. **AdForge:** campaign briefs, product/brand controls, high-volume variants, review, publishing handoffs, and analytics connections.

Each workspace must reuse the shared production graph, identity packs, asset residency, AI routing, jobs, approvals, spend controls, and interchange APIs.

### Phase 6 — Ecosystem and enterprise

Goal: support a governed creator economy after the platform is safe and reliable.

- private team libraries followed by licensed public assets and templates;
- contributor identity, license terms, model/voice consent, provenance, moderation, reporting, and takedown processes;
- Showcase publishing and optional remix permissions;
- enterprise SSO, policy controls, private model endpoints, regional data handling, and API access; and
- subscription/credit packaging derived from measured infrastructure cost and creator value rather than assumed competitor pricing.

## Immediate build sequence

The next four implementation slices should remain inside Phase 0:

1. **Automatic media lifecycle — implemented:** generated assets, audio, shot renders, animatics, and masters enter residency tracking automatically; working proxies are produced; cleanup approval requires fresh checksum-matching replicas and does not delete the original.
2. **Durable job foundation — implemented:** the shared database job envelope, Redis wakeups, inline development fallback, worker leases, retry/cancellation controls, event history, proxy executor, media-transfer integration, storage audits, production backups, AI Crew proposal generation, Sound Producer voice generation, still and motion composites, timeline animatics, continuous masters, and checksum-verified segmented-master assembly are implemented. The creator-facing Activity workspace exposes progress, failures, cancellation, retry, and job history. Next harden operational diagnostics and capacity controls.
3. **Schema migrations and production database verification — migration foundation implemented:** Alembic now owns a complete baseline, safely adopts matching legacy databases without losing productions, rejects unsafe partial schemas, and orders Coolify services behind a dedicated migration job. Next run the migration suite against PostgreSQL in CI while retaining SQLite for simple local development.
4. **Operational readiness — first slice implemented:** Docker keeps a lightweight liveness endpoint, while administrators now have database, Redis fallback, writable-storage, capacity, durable-queue, expired-lease, and backup-state diagnostics in Studio Settings. The latest local backup can be read end-to-end to verify its checksum, ZIP entries, manifest version, and production identity without overwriting production data. Accounts, invitations, roles, production isolation, password recovery, protected trials, and Stripe entitlement foundations are also implemented. Next add PostgreSQL CI, structured logs, worker/service heartbeats, alert delivery, automated recurring restore drills, and a final Coolify disaster-recovery runbook before public trials.

This order converts existing features into dependable platform services. It also keeps the door open for every useful part of the proposed suite without prematurely multiplying products, infrastructure, or model-training obligations.
