# AI Crew and voice setup

Kizuna supports two equally important ways to create: direct the production manually, or delegate specific departments to an AI Crew. Deploy only the roles you want for each production.

## Autonomy levels

- **Assist only** keeps the bot available for guidance without allowing it to change production assets.
- **Propose for approval** lets the bot prepare work, but a creator must approve it before Kizuna writes the result into the production.
- **Execute automatically** lets the bot complete supported tasks immediately. Every action and failure is still recorded in the activity feed.

The Writer can read the production logline, Creative DNA, existing story, cast, assignment, and standing direction; produce a schema-validated synopsis and beat proposal; and apply it after approval or automatically. The Director converts an approved outline into scenes, shot coverage, camera language, performance intent, timing, cast/location assignments, and continuity notes. Director changes update matching positions or add missing coverage without deleting extra creator work; an existing timeline is marked for rebuild.

The Character Designer turns a character's narrative role, traits, arc, Creative DNA, and existing design into a versioned production bible: silhouette and appearance rules, palette, wardrobe, consistency anchors, and a reusable reference-sheet brief. The Background Artist does the same for locations, producing architecture and atmosphere direction, palette, parallax layers, lighting variants, continuity locks, and a reusable background brief. Each bot applies the bible first and can then queue generation through the selected provider, so a generation failure never discards approved design work.

The Animator reads a saved shot plan, its camera direction, continuity notes, duration, Creative DNA, cast, location, and existing compositor layers. It proposes a virtual-camera move, acting beats, timing guidance, and editable end keyframes for every layer. Approval can build a missing composition, apply the motion as a new composition version, and optionally render a proxy or full-resolution MP4. A render failure does not discard the approved motion pass.

The Sound Producer can take a saved dialogue cue, combine its character voice bible, line direction, and pronunciation dictionary, generate a performance, and attach the result to the timeline cue.

## Visual-development providers

The built-in simulation engine creates deterministic, editable proposals without an external account. A hosted OpenAI engine can return the same validated proposal structure when an API key is configured:

```env
KIZUNA_VISUAL_AGENT_PROVIDER=openai
KIZUNA_OPENAI_VISUAL_AGENT_MODEL=gpt-5.6-terra
KIZUNA_ANIMATOR_PROVIDER=openai
KIZUNA_OPENAI_ANIMATOR_MODEL=gpt-5.6-terra
KIZUNA_OPENAI_API_KEY=your-key
```

Reference-sheet generation supports the local mock engine, the network render farm, or ComfyUI. Background generation supports the mock engine or ComfyUI. The bot's generation selector is independent of its proposal engine.

## Voice providers

Timing slates are the safe default and need no external account. To enable OpenAI speech, add these values to `.env` and restart Kizuna:

```env
KIZUNA_OPENAI_API_KEY=your-key
KIZUNA_VOICE_PROVIDER=openai
KIZUNA_OPENAI_VOICE_MODEL=gpt-4o-mini-tts
KIZUNA_OPENAI_VOICE=coral
```

Install the project dependencies again after pulling this change so the optional hosted adapter is available:

```powershell
python -m pip install -e ".[dev]"
```

Before generating a hosted AI performance, save a voice-rights record in Audio Studio. Kizuna records whether disclosure is required with every generated result. Do not upload, clone, or imitate a person's voice without the necessary authorization, and disclose AI-generated speech to the audience.
