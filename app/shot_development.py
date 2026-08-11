from app.models import Character, Shot, StyleProfile, WorldLocation
from app.schemas import ShotPlanInput
from app.anime_craft import craft_prompt_context


def sentence(value: str) -> str:
    value = value.strip()
    return value if not value or value[-1] in ".?!" else f"{value}."


def compile_storyboard_prompt(shot: Shot, plan: ShotPlanInput, style: StyleProfile | None, location: WorldLocation | None, characters: list[Character]) -> str:
    camera = ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in plan.camera.items() if value)
    era = f"{style.era_primary} blended with {style.era_secondary}" if style else "project-defined anime"
    visual = ", ".join(str(value) for value in (style.visual.values() if style else []))
    direction = ", ".join(str(value) for value in (style.direction.values() if style else []))
    craft = craft_prompt_context(style.craft if style else None, "motion")
    location_text = location.name if location else "an intentionally minimal production space"
    location_locks = "; ".join(location.design.continuity_anchors) if location and location.design else "preserve screen direction and horizon"
    character_text = ", ".join(character.name for character in characters) or "no featured character"
    character_locks = []
    for character in characters:
        if character.design:
            character_locks.append(f"{character.name}: {'; '.join(character.design.consistency_anchors)}")
    return (
        f"Create an original 16:9 anime storyboard frame for shot {shot.position}, {shot.title}. "
        f"Shot action: {sentence(plan.action or shot.description)} Dialogue intent: {sentence(plan.dialogue or 'visual storytelling only')} "
        f"Location: {location_text}. Featured characters: {character_text}. "
        f"Camera plan: {camera or 'medium-wide eye-level composition, clear staging'}. Lighting: {plan.lighting or 'follow the location color script'}. "
        f"Art direction: {era}; visual language: {visual or 'production linework and cel shading'}; directing language: {direction or 'character-led clarity'}. {craft} "
        "Draw a clean grayscale production storyboard with readable silhouettes, composition, eyelines, screen direction, depth planes, and motion arrows where useful. "
        f"Location continuity: {location_locks}. Character identity locks: {' | '.join(character_locks) or 'maintain approved model sheets'}. "
        f"Shot continuity notes: {sentence(plan.continuity_notes or 'match adjacent shots and preserve geography')} No captions, logos, or copyrighted characters."
    )
