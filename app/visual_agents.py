from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from app.schemas import BackgroundArtistRequest, BackgroundDesignProposal, CharacterDesignProposal, CharacterDesignerRequest


class VisualAgentError(RuntimeError):
    pass


ProposalT = TypeVar("ProposalT", bound=BaseModel)


def _hosted_proposal(schema: type[ProposalT], context: dict[str, Any], *, api_key: str, model: str, system: str) -> ProposalT:
    if not api_key:
        raise VisualAgentError("Add KIZUNA_OPENAI_API_KEY to enable hosted visual-development bots")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise VisualAgentError("Install the OpenAI SDK to enable hosted visual-development bots") from exc
    try:
        response = OpenAI(api_key=api_key).responses.parse(model=model, input=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(context, ensure_ascii=False)}], text_format=schema)
        if not response.output_parsed:
            raise VisualAgentError("The visual-development bot did not return a usable proposal")
        return response.output_parsed
    except VisualAgentError:
        raise
    except Exception as exc:
        raise VisualAgentError(str(exc)) from exc


def create_character_design_proposal(context: dict[str, Any], request: CharacterDesignerRequest, *, provider: str, api_key: str = "", model: str = "gpt-5.6-terra", instructions: str = "") -> CharacterDesignProposal:
    character = context["character"]
    if provider == "simulation":
        name, role = character["name"], character.get("role") or "story lead"
        return CharacterDesignProposal(
            appearance={"silhouette": f"Readable asymmetrical silhouette shaped by the {role} function", "body_language": "Weight held with purposeful restraint; hands reveal emotion first", "face": "Simple production geometry with a distinct brow and cheek rhythm", "hair": "Graphic shape with one unmistakable break in the contour", "eyes": "High-contrast iris and upper-lid shape readable at medium distance", "signature_detail": f"A small personal object tied to {character.get('want') or name}'s goal"},
            palette=["charcoal anchor", "story accent", "warm skin neutral", "controlled highlight"],
            wardrobe=[f"Functional base costume for a {role}", "single story-changing accessory", "simplified action variant"],
            consistency_anchors=["unchanged head-to-body proportion", "signature hair contour", "fixed eye and brow geometry", "accent color remains in the same costume zone", "signature object stays on the same side"],
            rationale=f"The design makes {name}'s role readable in silhouette while using controlled asymmetry to externalize the character contradiction.",
            changes=["Defined production silhouette and face construction", "Created wardrobe hierarchy and palette", "Locked five cross-shot identity anchors"],
            warnings=["Review cultural symbols, costume practicality, and accessibility before final model-sheet generation."],
        )
    if provider != "openai":
        raise VisualAgentError(f"Unknown visual agent provider: {provider}")
    system = "You are a Character Designer for an original anime production. Return an animation-ready design bible in the supplied schema, with economical shapes, readable silhouette, palette logic, wardrobe variants, and precise cross-shot consistency anchors. Never imitate a living artist, copy protected characters, or design fan-fiction and unofficial derivative works based on known properties. " + (instructions or "")
    return _hosted_proposal(CharacterDesignProposal, {"production": context, "assignment": request.model_dump(exclude={"provider"})}, api_key=api_key, model=model, system=system)


def create_background_design_proposal(context: dict[str, Any], request: BackgroundArtistRequest, *, provider: str, api_key: str = "", model: str = "gpt-5.6-terra", instructions: str = "") -> BackgroundDesignProposal:
    location = context["location"]
    if provider == "simulation":
        name = location["name"]
        return BackgroundDesignProposal(
            appearance={"architecture": f"A strong landmark silhouette organized around {name}'s narrative function", "materials": "One dominant structural material, one reflective accent, and visible wear history", "atmosphere": "Depth-separated haze with restrained particulate motion", "scale": "Human-scale performance zone against one monumental reference", "staging_zones": "Primary dialogue plane, action crossing, reveal axis, and safe effects corridor", "perspective": "Locked horizon and reusable wide-lens perspective grid"},
            palette=["deep structural neutral", "narrative accent", "atmospheric distance color", "practical light color"],
            layers=["foreground occlusion", "character performance plane", "midground landmark", "deep environment", "atmosphere and effects"],
            lighting_variants=["neutral continuity master", "emotional warm variant", "danger or disruption variant", "silhouette transition variant"],
            continuity_anchors=["fixed horizon height", "landmark remains on the same screen side", "entrances keep stable geography", "staging plane scale never changes", "practical lights retain count and placement"],
            rationale=f"The environment turns {name} into a reusable stage with stable geography, clear depth planes, and lighting variants that carry story state.",
            changes=["Defined reusable staging geography", "Separated five parallax layers", "Created four lighting masters and five continuity locks"],
            warnings=["Confirm architectural and cultural references are original before final background generation."],
        )
    if provider != "openai":
        raise VisualAgentError(f"Unknown visual agent provider: {provider}")
    system = "You are a Background Artist for an original anime production. Return a camera-ready environment bible in the supplied schema, with clear geography, reusable staging zones, parallax layers, lighting variants, scale, perspective, and precise continuity anchors. Never imitate a living artist, copy protected locations, or design fan-fiction and unofficial derivative works based on known properties. " + (instructions or "")
    return _hosted_proposal(BackgroundDesignProposal, {"production": context, "assignment": request.model_dump(exclude={"provider"})}, api_key=api_key, model=model, system=system)
