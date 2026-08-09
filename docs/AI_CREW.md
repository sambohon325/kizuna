# AI Crew and voice setup

Kizuna supports two equally important ways to create: direct the production manually, or delegate specific departments to an AI Crew. Deploy only the roles you want for each production.

## Autonomy levels

- **Assist only** keeps the bot available for guidance without allowing it to change production assets.
- **Propose for approval** lets the bot prepare work, but a creator must approve it before Kizuna writes the result into the production.
- **Execute automatically** lets the bot complete supported tasks immediately. Every action and failure is still recorded in the activity feed.

The Writer can read the production logline, Creative DNA, existing story, cast, assignment, and standing direction; produce a schema-validated synopsis and beat proposal; and apply it after approval or automatically. The Sound Producer can take a saved dialogue cue, combine its character voice bible, line direction, and pronunciation dictionary, generate a performance, and attach the result to the timeline cue.

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
