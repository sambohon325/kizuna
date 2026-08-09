from app.schemas import StoryBriefInput


BEAT_NAMES = ["Opening image", "Inciting change", "First commitment", "Complication", "Midpoint reversal", "Crisis", "Climactic choice", "Closing image"]


def story_shape(brief: StoryBriefInput, premise: str, themes: str, title: str) -> tuple[list[str], list[str]]:
    if brief.format == "trailer":
        return ["Immediate hook", "World promise", "Character desire", "Escalation montage", "Signature reveal", "Final button"], ["Open on the most irresistible image, sound, or unanswered question.", f"Reveal the world and genre promise behind: {premise}", "Show what the central character wants without explaining the entire plot.", "Accelerate conflict, scale, and emotional stakes through contrasting images.", f"Deliver one unforgettable reveal tied to {themes}, while protecting the ending.", "End on a sharp line, image, title, or reversal that creates desire for the full story."]
    if brief.target_duration_minutes <= 2:
        return ["Scroll-stopping hook", "Story problem", "Pressure turn", "Decisive choice", "Payoff / continuation"], ["Make the premise readable in the opening image or first line.", f"Turn the hook into one concrete problem: {premise}", f"Escalate through a visual reversal connected to {themes}.", "Force one legible choice rather than adding another subplot.", "Pay off the opening image or end on a continuation beat strong enough to earn the next installment."]
    if brief.format in {"episode", "limited series"}:
        return ["Episode hook", "Story engine", "Commitment", "Escalation", "Midpoint turn", "Relationship pressure", "Episode climax", "Series turn"], [f"Open on a question or disruption unique to this installment of {title}.", f"Activate the repeatable story engine through: {premise}", "Commit the protagonist to an episode goal with a visible cost.", f"Complicate the goal while expressing {themes} through action.", "Reveal information that changes the meaning of the episode goal.", "Let the episode conflict alter a relationship or longer character arc.", "Resolve the installment's main dramatic question through a costly action.", "Create a new condition, question, or consequence that advances the larger series spine."]
    if brief.format == "feature film":
        return ["Opening image", "Theme in action", "Inciting change", "First commitment", "Early escalation", "First culmination", "Midpoint reversal", "Consequences", "Crisis", "Final commitment", "Climactic choice", "Closing image"], [f"Establish the ordinary world and emotional absence beneath {title}.", f"Show the argument around {themes} through behavior rather than explanation.", f"Make the premise unavoidable: {premise}", "Cross the threshold into a goal that cannot be abandoned without consequence.", "Expand opposition, relationships, and the cost of the goal.", "Deliver a major attempt or confrontation that appears to redefine success.", "Reveal information that changes the meaning of the goal and the opposing force.", "Let the midpoint choice damage the safest path, relationships, or identity.", "Remove the old solution and force the protagonist to confront the central misbelief.", "Choose a new course based on what the protagonist has learned or still refuses to accept.", "Resolve the dramatic argument through the most costly, visible action in the film.", "Echo the opening with a transformed image that shows what changed and what remains."]
    return BEAT_NAMES, [f"Establish the ordinary world and the emotional absence beneath {title}.", f"An unexpected event makes the premise unavoidable: {premise}", "The protagonist crosses a threshold and accepts a goal they cannot easily abandon.", f"Pressure exposes contradictions while the theme of {themes} appears through action.", "A revelation changes the meaning of the goal and reframes the opposing force.", "The safest path disappears; relationships and identity fracture under consequence.", "The protagonist makes a costly choice that resolves the dramatic argument through action.", "Echo the opening with a transformed image that shows what changed and what remains."]


def develop_story(title: str, logline: str, brief: StoryBriefInput) -> tuple[str, list[dict[str, str]]]:
    premise = brief.premise.strip() or logline.strip() or f"A defining event changes the world of {title}."
    themes = ", ".join(brief.themes) if brief.themes else "identity and change"
    article = "an" if brief.genre.strip().lower()[:1] in "aeiou" else "a"
    synopsis = (
        f"{premise} Told as {article} {brief.genre} {brief.format} for a {brief.audience} audience, "
        f"the story explores {themes}. Its central conflict escalates from a personal disruption "
        "to an irreversible choice that reveals what the protagonist truly values."
    )
    beat_names, prompts = story_shape(brief, premise, themes, title)
    return synopsis, [{"position": str(index + 1), "name": name, "summary": summary} for index, (name, summary) in enumerate(zip(beat_names, prompts))]
