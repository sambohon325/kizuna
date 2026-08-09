from __future__ import annotations

import json
from typing import Any

from app.schemas import AnimatorCameraProposal, AnimatorLayerProposal, AnimatorProposal, AnimatorProposalRequest


class AnimatorAgentError(RuntimeError):
    pass


def _camera_motion(planned_move: str) -> AnimatorCameraProposal:
    move = (planned_move or "locked").lower()
    values: dict[str, Any] = {"move": move, "start_scale": 1, "end_scale": 1, "pan_x": 0, "pan_y": 0, "easing": "ease-in-out"}
    if "push" in move:
        values["end_scale"] = 1.08
        values["intent"] = "Let the camera arrive with the emotional realization."
    elif "pull" in move:
        values.update({"start_scale": 1.08, "end_scale": 1, "intent": "Reveal the changed relationship between the figure and the world."})
    elif "pan" in move or "track" in move:
        values.update({"end_scale": 1.03, "pan_x": 0.06, "intent": "Follow the action while preserving screen direction."})
    elif "tilt" in move:
        values.update({"end_scale": 1.02, "pan_y": -0.05, "intent": "Reveal vertical scale without losing the performance plane."})
    else:
        values["intent"] = "Keep the frame stable and let acting carry the beat."
    return AnimatorCameraProposal(**values)


def _local_proposal(context: dict[str, Any], request: AnimatorProposalRequest) -> AnimatorProposal:
    shot = context.get("shot") or {}
    plan = shot.get("plan") or {}
    layers = context.get("layers") or []
    if not plan:
        raise AnimatorAgentError("Save a shot plan before asking the Animator for motion")
    if not layers:
        raise AnimatorAgentError("The shot needs at least one anticipated or existing composition layer")
    motions = []
    character_index = 0
    for layer in layers:
        transform = layer.get("transform") or {}
        x, y = float(transform.get("x", 0.5)), float(transform.get("y", 0.5))
        scale, rotation = float(transform.get("scale", 1)), float(transform.get("rotation", 0))
        kind = layer.get("kind", "custom")
        if kind == "background":
            end = (x - 0.012, y, scale * 1.02, rotation, float(layer.get("opacity", 1)))
            intent = "A restrained parallax drift that supports the camera without changing geography."
        elif kind == "character":
            direction = 1 if character_index % 2 == 0 else -1
            character_index += 1
            end = (x + 0.018 * direction, y - 0.008, scale * 1.018, rotation + 0.5 * direction, float(layer.get("opacity", 1)))
            intent = f"Hold the pose, then expose the emotional turn through breath, weight, and a small silhouette change: {plan.get('action', shot.get('description', ''))}"
        elif kind == "effect":
            end = (x + 0.035, y - 0.025, scale * 1.06, rotation + 1.5, max(0.65, float(layer.get("opacity", 1)) - 0.12))
            intent = "Use effects as a timed accent after the performance beat, not continuous noise."
        else:
            end = (x + 0.01, y, scale * 1.01, rotation, float(layer.get("opacity", 1)))
            intent = "Maintain a subtle secondary-motion pass without competing with the subject."
        motions.append(AnimatorLayerProposal(layer_id=layer.get("id"), layer_name=layer.get("name", kind.title()), kind=kind, intent=intent, easing="ease-in-out", end_x=end[0], end_y=end[1], end_scale=end[2], end_rotation=end[3], end_opacity=end[4]))
    return AnimatorProposal(
        approach=f"An economical, performance-first motion pass for {shot.get('title', 'the shot')} that concentrates movement around the dramatic change.",
        camera=_camera_motion((plan.get("camera") or {}).get("movement", "locked")),
        layer_motions=motions,
        acting_beats=["Settle into the opening pose and preserve the incoming emotion", "Initiate the physical action with one readable lead", "Land the emotional turn before the cut"],
        timing_notes=["Favor held poses with short, intentional transitions", "Offset secondary motion after the primary action", "Protect the final readable pose for editorial flexibility"],
        changes=[f"Planned motion for {len(motions)} layer{'s' if len(motions) != 1 else ''}", "Prepared a virtual-camera move", "Added an acting and timing pass"],
        warnings=["This first pass interpolates editable layer and camera keyframes; detailed character drawing remains a later production pass."],
    )


def create_animator_proposal(context: dict[str, Any], request: AnimatorProposalRequest, *, provider: str, api_key: str = "", model: str = "gpt-5.6-terra", instructions: str = "") -> AnimatorProposal:
    if provider == "simulation":
        return _local_proposal(context, request)
    if provider != "openai":
        raise AnimatorAgentError(f"Unknown animator provider: {provider}")
    if not api_key:
        raise AnimatorAgentError("Add KIZUNA_OPENAI_API_KEY to enable the hosted Animator bot")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AnimatorAgentError("Install the OpenAI SDK to enable the hosted Animator bot") from exc
    system = (
        "You are the animation director for an original 2D anime production. Return a practical motion proposal in the supplied schema. "
        "Use economical posing, readable acting, purposeful camera movement, staggered secondary action, stable continuity, and the supplied layer IDs and names. "
        "All end values are normalized compositor controls. Never add, remove, rename, or invent layers. Never imitate a living animator or reproduce protected characters or shots. "
        f"Creator standing direction: {instructions or 'Prioritize readable performance, continuity, and production-efficient motion.'}"
    )
    try:
        response = OpenAI(api_key=api_key).responses.parse(
            model=model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"shot_context": context, "assignment": request.model_dump(exclude={"provider"})}, ensure_ascii=False)}],
            text_format=AnimatorProposal,
        )
        if not response.output_parsed:
            raise AnimatorAgentError("The Animator bot did not return a usable motion proposal")
        return response.output_parsed
    except AnimatorAgentError:
        raise
    except Exception as exc:
        raise AnimatorAgentError(str(exc)) from exc
