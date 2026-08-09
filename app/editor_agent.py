from __future__ import annotations

import json
from typing import Any

from app.schemas import EditorClipProposal, EditorProposal, EditorProposalRequest


class EditorAgentError(RuntimeError):
    pass


def _local_proposal(context: dict[str, Any], request: EditorProposalRequest) -> EditorProposal:
    source_clips = context.get("clips") or []
    if not source_clips:
        raise EditorAgentError("Build at least one shot before asking the Editor for an assembly")
    pace_factor = {"restrained": 1.15, "balanced": 1.0, "kinetic": 0.82}[request.pacing]
    clips = []
    previous_scene = None
    for position, source in enumerate(source_clips, start=1):
        current = float(source.get("duration_seconds") or 4)
        plan = source.get("plan") or {}
        dialogue_words = len(str(plan.get("dialogue", "")).split())
        dialogue_floor = dialogue_words / 2.6 + 0.8 if dialogue_words else 0
        duration = max(0.65, min(30, max(current * pace_factor, dialogue_floor)))
        new_scene = previous_scene is not None and source.get("scene_title") != previous_scene
        if position == 1 or not new_scene or request.pacing == "kinetic":
            transition, transition_duration = "cut", 0
        else:
            transition = "dissolve"
            transition_duration = min(0.8 if request.pacing == "restrained" else 0.45, duration / 4)
        previous_scene = source.get("scene_title")
        rationale = "Protect dialogue readability and the outgoing pose" if dialogue_words else "Cut on the completed visual action and preserve screen direction"
        if new_scene:
            rationale += "; mark the scene change without slowing the story turn"
        clips.append(EditorClipProposal(clip_id=source.get("clip_id"), shot_id=source["shot_id"], shot_title=source.get("shot_title", f"Shot {position}"), position=position, duration_seconds=round(duration, 3), transition=transition, transition_duration=round(transition_duration, 3), rationale=rationale))
    runtime = sum(item.duration_seconds for item in clips) - sum(item.transition_duration for item in clips[1:] if item.transition != "cut")
    missing_motion = sum(1 for item in source_clips if not item.get("motion_uri"))
    missing_picture = sum(1 for item in source_clips if not item.get("motion_uri") and not item.get("storyboard_uri"))
    flags = []
    if missing_motion:
        flags.append(f"{missing_motion} clip{'s' if missing_motion != 1 else ''} will use still-frame fallback until animation is rendered")
    if missing_picture:
        flags.append(f"{missing_picture} clip{'s' if missing_picture != 1 else ''} have no current picture asset")
    return EditorProposal(
        approach=f"A {request.pacing} continuity assembly that cuts on completed actions, protects dialogue, and reserves transitions for meaningful scene changes.",
        clips=clips,
        estimated_runtime_seconds=round(max(0, runtime), 3),
        rhythm_notes=["Enter each shot as late as clarity allows", "Hold emotional reactions longer than connective actions", "Protect the final pose so downstream trims remain possible"],
        continuity_checks=["Preserve scene order and shot coverage", "Maintain screen direction across adjacent cuts", "Keep dialogue clips long enough for natural delivery", "Use dissolves only at explicit scene boundaries"],
        quality_flags=flags,
        changes=[f"Timed {len(clips)} clips", f"Planned {sum(1 for item in clips if item.transition != 'cut')} scene transition{'s' if sum(1 for item in clips if item.transition != 'cut') != 1 else ''}", f"Estimated a {runtime:.1f}-second review cut"],
        warnings=["The proposal changes timeline timing and transitions only; it never deletes shots, audio, or source assets."],
    )


def create_editor_proposal(context: dict[str, Any], request: EditorProposalRequest, *, provider: str, api_key: str = "", model: str = "gpt-5.6-terra", instructions: str = "") -> EditorProposal:
    if provider == "simulation":
        return _local_proposal(context, request)
    if provider != "openai":
        raise EditorAgentError(f"Unknown editor provider: {provider}")
    if not api_key:
        raise EditorAgentError("Add KIZUNA_OPENAI_API_KEY to enable the hosted Editor bot")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise EditorAgentError("Install the OpenAI SDK to enable the hosted Editor bot") from exc
    system = (
        "You are the picture editor for an original 2D anime production. Return a practical edit proposal in the supplied schema. "
        "Include every supplied shot exactly once, using the supplied shot_id and clip_id. Preserve narrative order. Shape duration around action, dialogue, reaction, screen direction, and available picture or motion. "
        "Use cuts by default and transitions only when they communicate a real time, place, or emotional change. Never remove source material. "
        "Do not facilitate fan fiction or unofficial derivative works based on known properties. "
        f"Creator standing direction: {instructions or 'Prioritize story clarity, emotional rhythm, continuity, and reversible editorial choices.'}"
    )
    try:
        response = OpenAI(api_key=api_key).responses.parse(
            model=model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"timeline_context": context, "assignment": request.model_dump(exclude={"provider"})}, ensure_ascii=False)}],
            text_format=EditorProposal,
        )
        if not response.output_parsed:
            raise EditorAgentError("The Editor bot did not return a usable edit proposal")
        return response.output_parsed
    except EditorAgentError:
        raise
    except Exception as exc:
        raise EditorAgentError(str(exc)) from exc
