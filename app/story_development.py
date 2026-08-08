from app.schemas import StoryBriefInput


BEAT_NAMES = ["Opening image", "Inciting change", "First commitment", "Complication", "Midpoint reversal", "Crisis", "Climactic choice", "Closing image"]


def develop_story(title: str, logline: str, brief: StoryBriefInput) -> tuple[str, list[dict[str, str]]]:
    premise = brief.premise.strip() or logline.strip() or f"A defining event changes the world of {title}."
    themes = ", ".join(brief.themes) if brief.themes else "identity and change"
    article = "an" if brief.genre.strip().lower()[:1] in "aeiou" else "a"
    synopsis = (
        f"{premise} Told as {article} {brief.genre} {brief.format} for a {brief.audience} audience, "
        f"the story explores {themes}. Its central conflict escalates from a personal disruption "
        "to an irreversible choice that reveals what the protagonist truly values."
    )
    prompts = [
        f"Establish the ordinary world and the emotional absence beneath {title}.",
        f"An unexpected event makes the premise unavoidable: {premise}",
        "The protagonist crosses a threshold and accepts a goal they cannot easily abandon.",
        f"Pressure exposes contradictions while the theme of {themes} appears through action.",
        "A revelation changes the meaning of the goal and reframes the opposing force.",
        "The safest path disappears; relationships and identity fracture under consequence.",
        "The protagonist makes a costly choice that resolves the dramatic argument through action.",
        "Echo the opening with a transformed image that shows what changed and what remains.",
    ]
    return synopsis, [{"position": str(index + 1), "name": name, "summary": summary} for index, (name, summary) in enumerate(zip(BEAT_NAMES, prompts))]
