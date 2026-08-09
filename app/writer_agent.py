from __future__ import annotations

import json
from typing import Any

from app.schemas import StoryBriefInput, WriterProposal, WriterProposalRequest
from app.story_development import develop_story


class WriterAgentError(RuntimeError):
    pass


def _local_proposal(project: dict[str, Any], request: WriterProposalRequest) -> WriterProposal:
    brief = StoryBriefInput(**request.model_dump(exclude={"objective", "provider"}))
    synopsis, beats = develop_story(project["title"], project.get("logline", ""), brief)
    current = project.get("story_brief") or {}
    changes = [f"Created a {len(beats)}-beat dramatic spine proportioned to the release format", "Aligned the premise, genre, audience, and themes"]
    if current:
        changes = ["Rebuilt the dramatic spine from the current brief", "Preserved editable production metadata"]
    return WriterProposal(
        **brief.model_dump(), synopsis=synopsis, beats=beats,
        rationale=f"The Writer shaped this as a {brief.target_duration_minutes}-minute {brief.format}, using escalation and a final character choice to express {', '.join(brief.themes) if brief.themes else 'the central theme'}.",
        changes=changes,
        warnings=["Review character names and specific scene dialogue before expanding this outline into shots."],
    )


def create_writer_proposal(project: dict[str, Any], request: WriterProposalRequest, *, provider: str, api_key: str = "", model: str = "gpt-5.6-terra", instructions: str = "") -> WriterProposal:
    if provider == "simulation":
        return _local_proposal(project, request)
    if provider != "openai":
        raise WriterAgentError(f"Unknown writer provider: {provider}")
    if not api_key:
        raise WriterAgentError("Add KIZUNA_OPENAI_API_KEY to enable the hosted Writer bot")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise WriterAgentError("Install the OpenAI SDK to enable the hosted Writer bot") from exc
    system = (
        "You are the Writer for an original anime production studio. Return a production-ready story proposal using the supplied schema. "
        "Use era, narrative, and art-direction references as high-level craft language only; do not copy protected characters, plots, dialogue, or distinctive living-artist styles. "
        "Do not create fan fiction, unofficial sequels, unauthorized adaptations, or crossovers based on known properties; redirect the work toward original characters, worlds, and dramatic premises. "
        "Make every beat filmable, causally clear, emotionally specific, and proportional to the target duration. "
        f"Standing direction from the creator: {instructions or 'Protect originality, character causality, and visual storytelling.'}"
    )
    context = {"project": project, "request": request.model_dump(exclude={"provider"})}
    try:
        response = OpenAI(api_key=api_key).responses.parse(
            model=model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
            text_format=WriterProposal,
        )
        if not response.output_parsed:
            raise WriterAgentError("The Writer bot did not return a usable story proposal")
        return response.output_parsed
    except WriterAgentError:
        raise
    except Exception as exc:
        raise WriterAgentError(str(exc)) from exc
