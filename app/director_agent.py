from __future__ import annotations

import json
from typing import Any

from app.schemas import DirectorProposal, DirectorProposalRequest, DirectorSceneProposal, DirectorShotProposal


class DirectorAgentError(RuntimeError):
    pass


CAMERA_COVERAGE = [
    ("wide", "eye level", "28mm", "slow push", "Establish geography and screen direction", "deep focus"),
    ("medium", "eye level", "40mm", "locked", "Hold the character against meaningful negative space", "character and immediate action"),
    ("close-up", "slightly low", "65mm", "subtle push", "Let the eyes carry the turn", "eyes and breath"),
    ("insert", "high", "85mm", "locked", "Isolate the object or physical consequence", "decisive detail"),
    ("medium close-up", "over shoulder", "50mm", "tracking", "Preserve the eyeline while pressure shifts", "performance plane"),
    ("extreme wide", "high", "24mm", "pull back", "End on transformed scale and relationship", "environment and silhouette"),
]


def _local_proposal(project: dict[str, Any], request: DirectorProposalRequest) -> DirectorProposal:
    story = project.get("story_brief")
    if not story or not story.get("beats"):
        raise DirectorAgentError("Approve a Writer outline before asking the Director for coverage")
    character_names = [item["name"] for item in project.get("characters", [])[:3]]
    location_name = project.get("locations", [{}])[0].get("name", "") if project.get("locations") else ""
    pace_duration = {"restrained": 6.0, "balanced": 4.5, "kinetic": 3.0}[request.pacing]
    scenes = []
    for scene_position, beat in enumerate(story["beats"], start=1):
        shots = []
        for shot_position in range(1, request.shots_per_beat + 1):
            size, angle, lens, movement, composition, focus = CAMERA_COVERAGE[(shot_position - 1) % len(CAMERA_COVERAGE)]
            summary = str(beat.get("summary", "")).strip()
            shots.append(DirectorShotProposal(
                position=shot_position,
                title=f"{beat.get('name', f'Beat {scene_position}')} · {shot_position}",
                description=summary,
                duration_seconds=pace_duration + (1.5 if shot_position == 1 else 0),
                shot_size=size, angle=angle, lens=lens, movement=movement, composition=composition, focus=focus,
                action=summary,
                lighting="Follow the location color script and preserve face readability",
                continuity_notes="Maintain established screen direction, eyeline, props, wardrobe, and emotional carryover",
                performance_intent="Begin in the previous beat's emotional residue, then make the scene turn visible through behavior",
                character_names=character_names,
                location_name=location_name,
            ))
        scenes.append(DirectorSceneProposal(position=scene_position, title=str(beat.get("name", f"Scene {scene_position}")), summary=str(beat.get("summary", "")), dramatic_goal=f"Make the {str(beat.get('name', 'story')).lower()} change visible and irreversible.", shots=shots))
    total = sum(shot.duration_seconds for scene in scenes for shot in scene.shots)
    return DirectorProposal(
        approach=f"A {request.pacing} coverage skeleton that moves from geographic clarity to performance detail at each dramatic turn.",
        estimated_duration_seconds=round(total, 2), scenes=scenes,
        continuity_rules=["Preserve screen direction within every scene", "Carry emotional state across cuts", "Use inserts only for story-changing details", "Keep approved character and location anchors unchanged"],
        changes=[f"Planned {len(scenes)} scenes", f"Created {sum(len(scene.shots) for scene in scenes)} continuity-aware shots"],
        warnings=["This is a coverage skeleton; expand action and dialogue beats before final animation timing."],
    )


def create_director_proposal(project: dict[str, Any], request: DirectorProposalRequest, *, provider: str, api_key: str = "", model: str = "gpt-5.6-terra", instructions: str = "") -> DirectorProposal:
    if provider == "simulation":
        return _local_proposal(project, request)
    if provider != "openai":
        raise DirectorAgentError(f"Unknown director provider: {provider}")
    if not api_key:
        raise DirectorAgentError("Add KIZUNA_OPENAI_API_KEY to enable the hosted Director bot")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise DirectorAgentError("Install the OpenAI SDK to enable the hosted Director bot") from exc
    system = (
        "You are the Director of an original anime production. Return a practical, production-ready directing proposal in the supplied schema. "
        "Build filmable coverage with screen direction, eyelines, performance beats, purposeful camera choices, duration estimates, and continuity. "
        "Treat historical art-direction references as broad craft vocabulary only; never copy protected characters, plots, frames, or a living artist's distinctive style. "
        "Do not direct fan fiction, unofficial sequels, unauthorized adaptations, or crossovers based on known properties. "
        f"Creator standing direction: {instructions or 'Protect story clarity, performance, continuity, and economical coverage.'}"
    )
    try:
        response = OpenAI(api_key=api_key).responses.parse(
            model=model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"project": project, "assignment": request.model_dump(exclude={"provider"})}, ensure_ascii=False)}],
            text_format=DirectorProposal,
        )
        if not response.output_parsed:
            raise DirectorAgentError("The Director bot did not return a usable coverage proposal")
        return response.output_parsed
    except DirectorAgentError:
        raise
    except Exception as exc:
        raise DirectorAgentError(str(exc)) from exc
