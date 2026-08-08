from app.models import Character, StyleProfile
from app.schemas import CharacterDesignInput


def compile_reference_brief(character: Character, design: CharacterDesignInput, style: StyleProfile | None) -> str:
    appearance = ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in design.appearance.items() if value)
    palette = ", ".join(design.palette) or "project palette"
    wardrobe = ", ".join(design.wardrobe) or "story-appropriate base costume"
    anchors = "; ".join(design.consistency_anchors) or "preserve facial proportions, silhouette, and signature costume details"
    era = f"{style.era_primary} blended with {style.era_secondary}" if style else "project-defined anime"
    visual = ", ".join(str(value) for value in (style.visual.values() if style else []))
    return (
        f"Create an original production reference sheet for {character.name}, the {character.role}. "
        f"Narrative contradiction: {character.contradiction or 'to be discovered'}. "
        f"Appearance: {appearance or 'distinct readable silhouette'}. Palette: {palette}. Wardrobe: {wardrobe}. "
        f"Art direction: {era}; {visual or 'clean production linework and cel shading'}. "
        "Show neutral turnaround views, full-body front/side/back, face construction, six core expressions, hand scale, and costume callouts. "
        f"Non-negotiable consistency anchors: {anchors}. Keep the design original and production-ready."
    )
