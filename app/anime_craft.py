from __future__ import annotations

import hashlib
import json
from typing import Any


SOURCES = [
    {"id": "provided-history", "label": "Anime History and Genres Guide", "kind": "creator-provided guide"},
    {"id": "provided-writing", "label": "Anime Writing Craft Guide", "kind": "creator-provided guide"},
    {"id": "provided-visual", "label": "Anime Visual Art Craft Guide", "kind": "creator-provided guide"},
    {"id": "provided-audio", "label": "Anime Audio and Music Guide", "kind": "creator-provided guide"},
    {"id": "aja-archive", "label": "Anime TAIZEN / Animation NEXT_100", "kind": "industry archive", "url": "https://current.ndl.go.jp/en/e2563_en"},
    {"id": "japan-culture", "label": "Inheriting and Creating Culture", "kind": "Japanese government cultural context", "url": "https://www.gov-online.go.jp/eng/publicity/book/hlj/html/201909/201909_01_en.html"},
    {"id": "noh-johakyu", "label": "The Concept of Jo-ha-kyu", "kind": "National Theatre cultural reference", "url": "https://www2.ntj.jac.go.jp/dglib/contents/learn/edc22/en/category/bugaku/column.html"},
]


CRAFT_CATALOG: dict[str, Any] = {
    "version": "2026.08",
    "stance": {
        "title": "Tradition is a living practice, not a purity test",
        "summary": "Kizuna teaches historical context and transferable craft without declaring one visual language, genre, or production method to be the only authentic anime.",
        "principles": [
            "Name the tradition or production practice behind a recommendation.",
            "Explain what a convention does before recommending that it be followed.",
            "Treat eras, demographics, genres, and studio practices as overlapping lenses, not rigid boxes.",
            "Never convert a cultural tendency into a stereotype about Japanese people or creators.",
            "Support intentional departures when the creator can explain what the change contributes.",
            "Keep craft guidance separate from originality, rights, and release compliance.",
        ],
    },
    "traditions": [
        {"id": "kishotenketsu", "name": "Kisho-ten-ketsu", "department": "story", "context": "A four-part compositional lens used in several East Asian traditions. It can build meaning through development and recontextualization without making conflict the only engine.", "questions": ["What is established?", "What deepens?", "What changes the audience's reading?", "What new whole emerges?"], "caution": "Do not present this as the universal or exclusively Japanese structure of anime."},
        {"id": "jo-ha-kyu", "name": "Jo-ha-kyu", "department": "edit", "context": "A rhythmic ideal associated with gagaku and adopted by Noh and other arts: an unhurried opening, development that breaks and gathers energy, and a comparatively swift close.", "questions": ["Where may the audience settle?", "Where does the pattern break or accelerate?", "How decisive is the release?"], "caution": "Use it as a pacing lens, not a mandatory three-act template."},
        {"id": "ma", "name": "Ma - shaped interval", "department": "cross-craft", "context": "Meaning created by spacing, pause, silence, off-screen space, and the relationship between events.", "questions": ["What is gained by waiting?", "What can remain unheard or unseen?", "Does the interval invite attention rather than merely delay?"], "caution": "Ma is relational timing and space, not simply an empty shot."},
        {"id": "mono-no-aware", "name": "Mono no aware", "department": "story", "context": "Attention to transience and the feeling that beauty and loss can be inseparable.", "questions": ["What cannot be preserved?", "How does change alter the meaning of an ordinary detail?", "Can acceptance be more truthful than restoration?"], "caution": "Do not reduce the idea to cherry blossoms, sadness, or an unresolved ending."},
        {"id": "selective-animation", "name": "Selective animation", "department": "motion", "context": "Anime production often shapes attention through held drawings, cycles, camera movement, expressive poses, and concentrated passages of complex motion.", "questions": ["Which image must carry the scene?", "Where does stillness strengthen performance?", "Which change deserves the greatest animation effort?"], "caution": "Fewer drawings are not automatically inferior, and standout animation should not be described as a simple budget spike."},
        {"id": "graphic-cel-clarity", "name": "Graphic cel clarity", "department": "visual", "context": "Clear silhouettes, controlled color groups, and deliberate shadow shapes can preserve readability while making each frame feel designed.", "questions": ["Does the silhouette read?", "What does the color script argue emotionally?", "Are light and shadow repeatable across shots?"], "caution": "Digital work need not imitate physical cel artifacts to learn from graphic clarity."},
        {"id": "environment-as-agent", "name": "Environment as agent", "department": "world", "context": "Weather, architecture, objects, seasons, and non-human life can possess narrative agency and accumulate meaning through return.", "questions": ["What does this place want or resist?", "How does it change the characters' choices?", "What recurring detail gains new meaning?"], "caution": "Avoid treating Shinto, animism, or nature imagery as interchangeable decoration."},
        {"id": "ensemble-performance", "name": "Ensemble performance", "department": "performance", "context": "Character relationships can be built through reaction, timing, overlap, and gradually accumulated behavior rather than biography alone.", "questions": ["Who is listening?", "Whose reaction changes the scene?", "What does the group reveal that a solo line cannot?"], "caution": "Archetypes are starting vocabularies, never diagnoses or complete personalities."},
        {"id": "leitmotif-transformation", "name": "Leitmotif transformation", "department": "audio", "context": "A recurring musical identity can change harmony, orchestration, register, rhythm, or absence as a character, bond, or idea changes.", "questions": ["What owns this motif?", "How will its meaning transform?", "When is withholding it more powerful?"], "caution": "A motif is a dramatic system, not merely a repeated melody."},
        {"id": "sound-ma", "name": "Silence and room tone", "department": "audio", "context": "Near-silence, breath, ambience, and isolated detail can carry dramatic weight when the mix deliberately makes room for them.", "questions": ["What should the audience lean in to hear?", "Where should music release its hold?", "Which small sound locates us in the present moment?"], "caution": "Silence must be designed and monitored; it is not an unfinished soundtrack."},
        {"id": "diegetic-bridge", "name": "Diegetic score bridge", "department": "audio", "context": "Music or rhythm can emerge from the story world and cross into score, binding environment, performance, and emotion.", "questions": ["What source exists in the scene?", "When does it become subjective?", "What changes when it returns to the world?"], "caution": "The transition should carry meaning rather than function as a decorative trick."},
    ],
    "genre_lenses": [
        {"id": "battle-shonen", "name": "Battle shonen", "promise": "Growth becomes visible through trials, rivals, teams, and changing uses of power.", "watch": "Escalation that grows numerically while values and relationships stay still.", "suggested_traditions": ["selective-animation", "ensemble-performance", "graphic-cel-clarity"]},
        {"id": "shojo-relational", "name": "Shojo relational drama", "promise": "Identity and emotion become legible through relationships, framing, gesture, and interiority.", "watch": "Reducing a demographic tradition to romance, sparkle, or passive heroines.", "suggested_traditions": ["ma", "ensemble-performance", "graphic-cel-clarity"]},
        {"id": "seinen-psychological", "name": "Seinen psychological drama", "promise": "Moral pressure, subjectivity, and consequence complicate easy identification.", "watch": "Using darkness, violence, or ambiguity as a substitute for adult insight.", "suggested_traditions": ["ma", "jo-ha-kyu", "sound-ma"]},
        {"id": "josei-adult-relational", "name": "Josei adult relational drama", "promise": "Adult life and relationships are treated with social specificity and emotional consequence.", "watch": "Assuming naturalism alone creates maturity.", "suggested_traditions": ["ensemble-performance", "ma", "leitmotif-transformation"]},
        {"id": "real-robot", "name": "Real-robot mecha", "promise": "Machines sit inside institutions, logistics, politics, labor, and the human cost of conflict.", "watch": "Technical detail disconnected from institutions or consequence.", "suggested_traditions": ["environment-as-agent", "selective-animation", "leitmotif-transformation"]},
        {"id": "isekai-system", "name": "Isekai system story", "promise": "Crossing worlds exposes a coherent order that creates choices, costs, and changed identity.", "watch": "Rules that exist only to reward the protagonist or change without setup.", "suggested_traditions": ["environment-as-agent", "ensemble-performance", "kishotenketsu"]},
        {"id": "iyashikei", "name": "Iyashikei", "promise": "Attention, routine, season, place, and companionship create restorative experience.", "watch": "Confusing low conflict with low observation or low specificity.", "suggested_traditions": ["ma", "mono-no-aware", "sound-ma", "environment-as-agent"]},
        {"id": "horror-uncanny", "name": "Horror and the uncanny", "promise": "Pattern, omission, sound, space, and violated expectation produce dread.", "watch": "Defaulting to gore or stingers without an underlying dramatic pattern.", "suggested_traditions": ["ma", "sound-ma", "jo-ha-kyu"]},
        {"id": "sports-ensemble", "name": "Sports ensemble", "promise": "Physical technique reveals philosophy, belonging, rivalry, and collective growth.", "watch": "Treating victory as the only meaningful transformation.", "suggested_traditions": ["ensemble-performance", "jo-ha-kyu", "selective-animation"]},
        {"id": "cyberpunk-social", "name": "Cyberpunk social lens", "promise": "Technology, bodies, labor, architecture, and power reshape one another.", "watch": "Neon and grime without a social argument.", "suggested_traditions": ["environment-as-agent", "diegetic-bridge", "graphic-cel-clarity"]},
    ],
    "sources": SOURCES,
}


DEFAULT_COMPASS = {
    "intent": "",
    "cultural_context": "",
    "primary_genre": "",
    "genre_lenses": [],
    "tradition_ids": [],
    "anchors": [],
    "flexible": [],
    "departures": [],
}


def normalize_compass(value: dict[str, Any] | None) -> dict[str, Any]:
    result = {**DEFAULT_COMPASS, **(value or {})}
    for key in ("genre_lenses", "tradition_ids", "anchors", "flexible", "departures"):
        result[key] = result.get(key) if isinstance(result.get(key), list) else []
    return result


def craft_prompt_context(value: dict[str, Any] | None, department: str) -> str:
    compass = normalize_compass(value)
    if not compass["intent"] and not compass["tradition_ids"]:
        return ""
    tradition_map = {item["id"]: item for item in CRAFT_CATALOG["traditions"]}
    selected = [tradition_map[item] for item in compass["tradition_ids"] if item in tradition_map and tradition_map[item]["department"] in {department, "cross-craft"}]
    if not selected:
        selected = [tradition_map[item] for item in compass["tradition_ids"] if item in tradition_map]
    lenses = "; ".join(f"{item['name']}: {item['context']}" for item in selected[:4])
    anchors = "; ".join(compass["anchors"][:6])
    return f"Creative intent: {compass['intent'] or 'still being discovered'}. Craft lenses: {lenses or 'none selected for this department'}. Anchors: {anchors or 'none declared'}. Use these as questions and transferable practices, not as permission to imitate a title, studio, or artist."


def _finding(code: str, stage: str, title: str, why: str, continue_prompt: str, realign_prompt: str, level: str = "notice", evidence: list[str] | None = None) -> dict[str, Any]:
    return {"id": f"{stage}:{code}", "stage": stage, "level": level, "title": title, "why": why, "evidence": evidence or [], "choices": {"continue": continue_prompt, "realign": realign_prompt, "revise_compass": "Update the Craft Compass so the production's stated intent matches its evolving direction."}}


def _timecode(seconds: float) -> str:
    value = max(0, int(seconds or 0))
    return f"{value // 60:02d}:{value % 60:02d}"


def _review_lookup(project: Any) -> dict[tuple[str, int], Any]:
    return {(item.asset_type, item.asset_id): item for item in (getattr(project, "asset_reviews", []) or [])}


def _reviewed_version(assets: list[Any], asset_type: str, reviews: dict[tuple[str, int], Any]) -> str:
    reviewed = []
    for asset in assets or []:
        review = reviews.get((asset_type, asset.id))
        if review and (review.selected or review.status == "approved"):
            reviewed.append((bool(review.selected), asset.version, review.status))
    if not reviewed:
        return ""
    selected, version, status = sorted(reviewed, reverse=True)[0]
    return f"; {'selected' if selected else status} {asset_type} asset v{version}"


def review_project_craft(project: Any, stage: str = "all") -> dict[str, Any]:
    style = getattr(project, "style_profile", None)
    compass = normalize_compass(getattr(style, "craft", None) if style else None)
    brief = getattr(project, "story_brief", None)
    findings: list[dict[str, Any]] = []
    if not compass["intent"].strip():
        findings.append(_finding("missing-intent", "compass", "Name what this production is trying to contribute", "Craft choices are easier to evaluate when the creator has stated the work's emotional and artistic purpose.", "Continue exploring and write the intent after discovery.", "Write a one- or two-sentence creative intent before asking departments to optimize the work.", "setup"))
    if not compass["tradition_ids"]:
        findings.append(_finding("missing-traditions", "compass", "Choose at least one craft tradition to study", "A tradition gives the crew shared questions and vocabulary; it does not dictate a look.", "Continue without a named tradition and keep all guidance exploratory.", "Select one tradition whose questions genuinely serve this story.", "setup"))
    genre_text = " ".join([getattr(brief, "genre", "") or "", compass.get("primary_genre", ""), *compass["genre_lenses"]]).lower()
    narrative = getattr(style, "narrative", {}) if style else {}
    direction = getattr(style, "direction", {}) if style else {}
    reviews = _review_lookup(project)
    timeline = getattr(project, "timeline", None)
    clips = getattr(timeline, "clips", []) or [] if timeline else []
    audio_tracks = getattr(timeline, "audio_tracks", []) or [] if timeline else []
    if "iyash" in genre_text and direction.get("editing") == "rapid impact" and "ma" in compass["tradition_ids"]:
        edit_evidence = ["Style direction: editing is set to ‘rapid impact’."]
        edit_evidence.extend(f"Timeline clip {clip.position:02d} · {getattr(getattr(clip, 'shot', None), 'title', 'Untitled shot')}: {clip.duration_seconds:g}s, {clip.transition}." for clip in clips[:5])
        findings.append(_finding("iyashikei-rapid-edit", "edit", "Rapid-impact cutting is pulling against the restorative lens", "Iyashikei and ma often depend on duration, routine, and room for attention. The contrast may be productive, but it should be deliberate.", "Keep the rapid cutting and explain what disruption or counter-rhythm it contributes.", "Try contemplative or tension-and-release editing for everyday and environmental beats.", evidence=edit_evidence))
    if "cyberpunk" in genre_text and not any("power" in x.lower() or "labor" in x.lower() or "class" in x.lower() for x in [compass["intent"], getattr(brief, "premise", "") if brief else ""]):
        cyber_evidence = [f"Creative intent: {compass['intent'] or 'not written'}", f"Premise: {getattr(brief, 'premise', '') or 'not written'}"]
        cyber_evidence.extend(f"Location · {location.name}: {location.narrative_function or location.description or 'no social function recorded'}{_reviewed_version(getattr(location, 'background_assets', []), 'background', reviews)}" for location in (getattr(project, "locations", []) or [])[:4])
        findings.append(_finding("cyberpunk-surface", "worlds", "The cyberpunk lens has a visual signal but no social question yet", "Cyberpunk becomes more than neon when technology and architecture reveal who has power, who performs labor, and who bears the cost.", "Continue with atmosphere first and record the social question during world development.", "Add a power, labor, body, surveillance, or class question to the premise or Craft Compass.", evidence=cyber_evidence))
    if "isekai" in genre_text:
        locations = getattr(project, "locations", []) or []
        world_text = " ".join(f"{getattr(x, 'narrative_function', '')} {getattr(x, 'description', '')}" for x in locations).lower()
        if locations and not any(word in world_text for word in ("rule", "cost", "limit", "system", "law", "ritual")):
            evidence = [f"Location · {location.name}: {location.narrative_function or location.description or 'no narrative rule recorded'}{_reviewed_version(getattr(location, 'background_assets', []), 'background', reviews)}" for location in locations[:6]]
            findings.append(_finding("isekai-rules", "worlds", "The other-world system has places but no visible costs or rules", "System stories gain tension when rules create choices and consequences instead of only advantages.", "Keep the rules implicit and identify how the audience will infer them through action.", "Add one cost, limit, law, ritual, or failure condition to the world bible.", evidence=evidence))
    if narrative.get("structure") == "kishotenketsu" and brief and brief.beats and len(brief.beats) != 4:
        findings.append(_finding("kishotenketsu-count", "story", "The selected structure and beat count are not a literal match - and that may be fine", "Kisho-ten-ketsu is more useful as a relationship among functions than as a demand for exactly four cards.", "Keep the current beat count and label which beats establish, deepen, reframe, and connect.", "Condense or regroup the beat map around those four functions."))
    characters = getattr(project, "characters", []) or []
    if characters and "ensemble-performance" in compass["tradition_ids"]:
        relationship_count = sum(len(getattr(character, "relationships", []) or []) for character in characters)
        thin_characters = []
        ensemble_evidence = []
        for character in characters:
            profile = getattr(character, "story_profile", None)
            story_signals = sum(bool((getattr(character, key, "") or "").strip()) for key in ("want", "need", "contradiction"))
            story_signals += sum(bool((getattr(profile, key, "") or "").strip()) for key in ("history", "formative_event", "arc_start", "arc_end")) if profile else 0
            relationships = len(getattr(character, "relationships", []) or [])
            ensemble_evidence.append(f"{character.name}: {story_signals}/7 story anchors; {relationships} defined relationship{'s' if relationships != 1 else ''}")
            if story_signals < 3:
                thin_characters.append(character.name)
        if len(characters) > 1 and (relationship_count == 0 or thin_characters):
            findings.append(_finding("ensemble-in-isolation", "characters", "The ensemble lens is selected, but parts of the cast are still defined in isolation", "Ensemble performance becomes playable through wants, contradictions, listening, reaction, and relationships that change over time - not through role labels alone.", "Keep selected characters deliberately opaque and record how performance or later scenes will reveal their relational function.", "Add a concrete want, contradiction, formative pressure, and at least one changing relationship for the underdefined cast members.", evidence=ensemble_evidence))
    if characters and {"graphic-cel-clarity", "selective-animation"}.intersection(compass["tradition_ids"]):
        unlocked = [character for character in characters if not getattr(character, "design", None) or not (character.design.consistency_anchors or [])]
        if unlocked:
            evidence = []
            for character in unlocked:
                assets = [asset for asset in (getattr(project, "media_assets", []) or []) if asset.character_id == character.id]
                evidence.append(f"{character.name}: {'visual model not started' if not getattr(character, 'design', None) else 'no consistency anchors saved'}{_reviewed_version(assets, 'character', reviews)}")
            findings.append(_finding("identity-locks", "characters", "Some character designs do not yet have repeatable identity locks", "Graphic clarity and selective animation depend on a few stable shapes, colors, proportions, and details surviving changes in angle, pose, expression, and drawing complexity.", "Leave selected identities flexible during exploration and name the point when they must lock for production.", "Save two or three observable consistency anchors for each listed character before generating model views or final shots.", evidence=evidence))
    if "ma" in compass["tradition_ids"] and getattr(project, "scenes", None):
        shots = [(scene, shot) for scene in project.scenes for shot in getattr(scene, "shots", [])]
        shot_plans = [getattr(shot, "plan", None) for _, shot in shots]
        texts = " ".join(f"{getattr(plan, 'action', '')} {getattr(plan, 'continuity_notes', '')}" for plan in shot_plans if plan).lower()
        if shot_plans and not any(word in texts for word in ("pause", "silence", "still", "breath", "hold", "room tone", "negative space")):
            evidence = [f"Scene {scene.position:02d} / Shot {shot.position:02d} · {shot.title}: {shot.duration_seconds:g}s; no shaped interval in action or continuity{_reviewed_version(getattr(shot, 'storyboard_assets', []), 'storyboard', reviews)}" for scene, shot in shots[:6]]
            findings.append(_finding("ma-not-staged", "shots", "Ma is an anchor but has not reached the shot language", "A declared craft principle only guides production when it becomes a concrete choice of duration, framing, performance, or sound.", "Keep it as a later editorial or sound decision and note where it will enter.", "Add a purposeful hold, pause, off-screen space, breath, or room-tone beat to selected shots.", evidence=evidence))
    cues = [(track, cue) for track in audio_tracks for cue in (getattr(track, "cues", []) or [])]
    if cues and "sound-ma" in compass["tradition_ids"]:
        quiet_terms = ("silence", "room tone", "ambience", "ambient", "breath", "quiet", "unscored", "space", "air")
        if not any(term in f"{cue.text} {cue.direction}".lower() for _, cue in cues for term in quiet_terms):
            evidence = [f"{track.name} · {_timecode(cue.start_seconds)}–{_timecode(cue.start_seconds + cue.duration_seconds)}: {cue.text or cue.direction or 'unnamed cue'}" for track, cue in cues[:6]]
            findings.append(_finding("sound-ma-not-designed", "sound", "Silence and room tone are selected, but no quiet region is designed in the current mix", "Sound-ma becomes audible through deliberate contrast: room tone, breath, isolated detail, or a meaningful release from music and dialogue.", "Keep the current density and explain where contrast will enter during the final mix.", "Name a room-tone, breath, isolated-detail, or deliberately unscored region in Audio Studio.", evidence=evidence))
    music_cues = [(track, cue) for track, cue in cues if track.kind == "music"]
    if music_cues and "leitmotif-transformation" in compass["tradition_ids"]:
        transform_terms = ("transform", "variation", "reprise", "register", "harmony", "orchestration", "withhold", "return", "fragment")
        if not any(term in f"{cue.text} {cue.direction}".lower() for _, cue in music_cues for term in transform_terms):
            evidence = [f"{track.name} · {_timecode(cue.start_seconds)}: {cue.text or cue.direction or 'unnamed music cue'}" for track, cue in music_cues[:6]]
            findings.append(_finding("motif-without-arc", "sound", "The music cues repeat an identity, but do not yet describe how it changes", "Leitmotif becomes dramatic when harmony, register, rhythm, orchestration, fragmentation, return, or absence changes its meaning.", "Keep the motif stable and explain why constancy is the dramatic choice.", "Give at least one music cue a named variation, transformation, withholding, or return.", evidence=evidence))
    departures = {item.get("finding_id"): item for item in compass["departures"] if isinstance(item, dict)}
    for finding in findings:
        if finding["id"] in departures:
            finding["decision"] = departures[finding["id"]]
            finding["level"] = "intentional" if departures[finding["id"]].get("decision") == "continue" else "planned"
        finding["resolved"] = finding.get("decision", {}).get("decision") == "continue"
    relevant = findings if stage == "all" else [item for item in findings if item["stage"] in {stage, "compass"}]
    unresolved = [item for item in relevant if not item["resolved"]]
    digest = hashlib.sha256(json.dumps({"compass": compass, "findings": relevant}, sort_keys=True, default=str).encode()).hexdigest()
    return {"status": "needs_intent" if unresolved else "aligned_or_intentional", "advisory": True, "blocking": False, "summary": f"{len(unresolved)} open craft conversation{'s' if len(unresolved) != 1 else ''}", "findings": relevant, "compass": compass, "review_hash": digest, "distinction": "Craft guidance is advisory. Originality, rights, consent, and release compliance remain separate enforceable gates."}
