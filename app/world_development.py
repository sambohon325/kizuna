from app.models import StyleProfile, WorldLocation
from app.schemas import LocationDesignInput
from app.anime_craft import craft_prompt_context


def compile_background_brief(location: WorldLocation, design: LocationDesignInput, style: StyleProfile | None) -> str:
    appearance = ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in design.appearance.items() if value)
    palette = ", ".join(design.palette) or "project color script"
    layers = ", ".join(design.layers) or "foreground, performance plane, middle distance, deep background, atmosphere"
    lighting = ", ".join(design.lighting_variants) or "neutral story lighting"
    anchors = "; ".join(design.continuity_anchors) or "preserve landmark positions, horizon, entrances, and scale"
    era = f"{style.era_primary} blended with {style.era_secondary}" if style else "project-defined anime"
    visual = ", ".join(str(value) for value in (style.visual.values() if style else []))
    craft = craft_prompt_context(style.craft if style else None, "world")
    description = (location.description or "develop from the project story").rstrip(". ")
    return (
        f"Create an original anime production background concept for {location.name}. "
        f"Narrative function: {location.narrative_function or 'primary story location'}. "
        f"World description: {description}. "
        f"Geography and period: {location.geography or 'unspecified geography'}, {location.time_period or 'story-defined period'}. "
        f"Appearance: {appearance or 'readable staging, strong depth, and a distinct silhouette'}. Palette: {palette}. "
        f"Layer plan: {layers}. Lighting variants required: {lighting}. "
        f"Art direction: {era}; {visual or 'clean production linework and painted background treatment'}. {craft} "
        "Provide a wide establishing composition with clear character staging zones, camera-ready perspective, scale reference, and separate parallax layers. "
        f"Continuity locks: {anchors}. Keep the environment original, coherent, and reusable across shots."
    )
