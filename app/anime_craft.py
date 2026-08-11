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


GLOSSARY = [
    {"id": "anime", "term": "アニメ", "reading": "anime", "english": "animation / anime", "department": "history", "meaning": "In Japanese, a general abbreviation for animation. Outside Japan, anime commonly names animation associated with Japanese production and its many evolving lineages.", "production_use": "Use the term for a broad medium and production ecology, not a single drawing style or genre.", "caution": "Do not imply that every anime shares one visual language, audience, structure, or cultural position.", "source_ids": ["provided-history", "aja-archive"]},
    {"id": "e-conte", "term": "絵コンテ", "reading": "e-konte", "english": "storyboard / continuity board", "department": "shots", "meaning": "A production blueprint that communicates shot order, framing, action, dialogue, timing, and audiovisual intent.", "production_use": "Connect story beats to camera-ready shots and make timing decisions before expensive animation begins.", "caution": "It is more than an illustration gallery; timing and continuity are part of the document.", "source_ids": ["provided-visual"]},
    {"id": "layout", "term": "レイアウト", "reading": "reiauto", "english": "layout", "department": "visual", "meaning": "The shot-level plan for composition, perspective, character placement, camera, and the relationship between animation and background.", "production_use": "Use layouts to lock staging and spatial clarity before separating the shot into production layers.", "caution": "The English loanword has a specific animation-production use and should not be reduced to page arrangement.", "source_ids": ["provided-visual"]},
    {"id": "genga", "term": "原画", "reading": "genga", "english": "key animation", "department": "motion", "meaning": "Key drawings that establish major poses, movement, and acting decisions for a cut.", "production_use": "Concentrate the clearest performance and motion decisions in the drawings that define the action.", "caution": "Production responsibilities vary; do not use the term as a generic label for any polished frame.", "source_ids": ["provided-visual"]},
    {"id": "douga", "term": "動画", "reading": "dōga", "english": "in-between / clean-up animation", "department": "motion", "meaning": "In the animation pipeline, drawings that clean and connect key animation according to timing and movement instructions.", "production_use": "Plan how key poses become consistent, readable motion across the cut.", "caution": "In everyday Japanese the word can also mean video; production context changes its meaning.", "source_ids": ["provided-visual"]},
    {"id": "sakuga", "term": "作画", "reading": "sakuga", "english": "drawing / animation work", "department": "motion", "meaning": "A broad production term for the drawing and animation work; international fandom also uses it for especially notable passages of animation.", "production_use": "Discuss the specific acting, timing, draftsmanship, effects, or motion choices that make a passage effective.", "caution": "Do not treat sakuga as a synonym for high frame count, expense, or spectacle alone.", "source_ids": ["provided-visual"]},
    {"id": "satsuei", "term": "撮影", "reading": "satsuei", "english": "compositing / photography", "department": "finish", "meaning": "The production stage that combines animation, backgrounds, effects, camera treatment, and color into the finished image.", "production_use": "Use it to reason about depth, atmosphere, focus, motion treatment, and the unity of final layers.", "caution": "Although the word can mean photography, in a digital anime pipeline it commonly includes compositing work.", "source_ids": ["provided-visual"]},
    {"id": "bijutsu-kantoku", "term": "美術監督", "reading": "bijutsu kantoku", "english": "art director", "department": "worlds", "meaning": "A role responsible for the visual direction and consistency of environments and background art.", "production_use": "Translate story and geography into a repeatable world language for locations, lighting, color, and atmosphere.", "caution": "Role boundaries and credits differ by production; never use the title to justify imitating an individual professional's body of work.", "source_ids": ["provided-visual"]},
    {"id": "iro-shitei", "term": "色指定", "reading": "iro shitei", "english": "color designation", "department": "visual", "meaning": "The specification of approved colors for characters and elements so they remain consistent across cuts and conditions.", "production_use": "Build reusable palettes and controlled variations for lighting, emotion, time, and continuity.", "caution": "Color scripts and final compositing can alter appearance; a swatch alone is not the entire color system.", "source_ids": ["provided-visual"]},
    {"id": "seiyuu", "term": "声優", "reading": "seiyū", "english": "voice performer", "department": "sound", "meaning": "A professional voice performer working across animation and other media.", "production_use": "Direct intention, breath, timing, relationship, and subtext rather than treating voice as interchangeable audio.", "caution": "Voice identity, consent, contracts, and disclosure remain rights matters, including for synthetic voices.", "source_ids": ["provided-audio"]},
    {"id": "gekiban", "term": "劇伴", "reading": "gekiban", "english": "dramatic underscore", "department": "sound", "meaning": "Music composed or selected to accompany dramatic action and shape the audience's reading of a scene.", "production_use": "Design score around perspective, structure, transformation, and meaningful absence.", "caution": "Underscore should serve the production's dramatic system, not reproduce the musical identity of a known work or composer.", "source_ids": ["provided-audio"]},
    {"id": "ma", "term": "間", "reading": "ma", "english": "shaped interval / relational space", "department": "cross-craft", "meaning": "Meaning created through the relationship between events, sounds, bodies, or spaces—including pause, silence, and negative space.", "production_use": "Ask what attention, anticipation, tenderness, discomfort, or clarity becomes possible because an interval is shaped.", "caution": "It does not simply mean emptiness, slowness, or inserting a static shot.", "source_ids": ["provided-writing", "provided-visual", "provided-audio"]},
    {"id": "jo-ha-kyu", "term": "序破急", "reading": "jo-ha-kyū", "english": "opening, break/development, rapid close", "department": "edit", "meaning": "A rhythmic concept associated with court music and developed across Japanese performing arts: introduction, development or breaking-open, and acceleration toward a close.", "production_use": "Use it to inspect how energy gathers and releases within a gesture, scene, episode, or larger work.", "caution": "It is a flexible rhythmic lens, not a compulsory three-act screenplay formula.", "source_ids": ["provided-writing", "noh-johakyu"]},
    {"id": "kishotenketsu", "term": "起承転結", "reading": "kishōtenketsu", "english": "introduction, development, turn, integration", "department": "story", "meaning": "A four-part compositional pattern found in multiple East Asian traditions, often emphasizing development and a recontextualizing turn.", "production_use": "Map what is established, deepened, reframed, and newly understood without requiring confrontation to be the sole engine.", "caution": "It is neither universal to anime nor exclusively Japanese, and it need not produce exactly four scene cards.", "source_ids": ["provided-writing"]},
    {"id": "mono-no-aware", "term": "もののあはれ", "reading": "mono no aware", "english": "sensitivity to transience", "department": "story", "meaning": "An aesthetic and literary idea concerning an attentive emotional response to impermanence and the inseparability of beauty and loss.", "production_use": "Let ordinary details change meaning as time passes, relationships shift, or something cannot be preserved.", "caution": "Do not reduce it to sadness, cherry-blossom imagery, or a vague claim about a timeless national character.", "source_ids": ["provided-history"]},
    {"id": "cel-ga", "term": "セル画", "reading": "seru-ga", "english": "animation cel", "department": "visual", "meaning": "A painted transparent sheet used in photographed cel-animation workflows; the term also names surviving physical production artwork.", "production_use": "Study economical color grouping, repeatable shapes, and designed shadow boundaries without faking material artifacts.", "caution": "Digital anime does not become more authentic by superficially adding dust, weave, or cel damage.", "source_ids": ["provided-history", "provided-visual", "aja-archive"]},
]


READING_PATHS = [
    {"id": "foundations", "name": "Foundations without shortcuts", "level": "beginner", "purpose": "Learn the medium, production vocabulary, and the difference between studying craft and copying surface style.", "term_ids": ["anime", "e-conte", "layout", "genga", "douga", "satsuei"], "tradition_ids": ["selective-animation", "graphic-cel-clarity"]},
    {"id": "story-rhythm", "name": "Story, rhythm, and attention", "level": "all levels", "purpose": "Explore several ways anime can shape meaning through structure, interval, impermanence, performance, and place.", "term_ids": ["kishotenketsu", "jo-ha-kyu", "ma", "mono-no-aware"], "tradition_ids": ["kishotenketsu", "jo-ha-kyu", "ma", "mono-no-aware", "ensemble-performance", "environment-as-agent"]},
    {"id": "studio-pipeline", "name": "From board to finished cut", "level": "production", "purpose": "Follow how a visual idea travels through storyboard, layout, drawing, color, art direction, voice, score, and compositing.", "term_ids": ["e-conte", "layout", "genga", "douga", "iro-shitei", "bijutsu-kantoku", "seiyuu", "gekiban", "satsuei"], "tradition_ids": ["selective-animation", "graphic-cel-clarity", "sound-ma", "leitmotif-transformation"]},
]


CRAFT_CATALOG: dict[str, Any] = {
    "version": "2026.08.1",
    "release": {
        "published": "2026-08-11",
        "title": "Bilingual craft foundations",
        "summary": "Adds reviewed Japanese terminology, transparent Kizuna teaching labels, provenance, and guided learning paths without changing a production automatically.",
        "changes": [
            "Bilingual production, story, visual, motion, and audio terminology",
            "Per-entry production use, caution, and source provenance",
            "Beginner, story-rhythm, and studio-pipeline learning paths",
        ],
    },
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
    "glossary": GLOSSARY,
    "reading_paths": READING_PATHS,
    "language_notice": "Japanese terms are shown where a recognized production, literary, or aesthetic term exists. English teaching labels are not given invented Japanese equivalents.",
}


TRADITION_METADATA = {
    "kishotenketsu": {"japanese": "起承転結", "reading": "kishōtenketsu", "term_ids": ["kishotenketsu"], "source_ids": ["provided-writing"]},
    "jo-ha-kyu": {"japanese": "序破急", "reading": "jo-ha-kyū", "term_ids": ["jo-ha-kyu"], "source_ids": ["provided-writing", "noh-johakyu"]},
    "ma": {"japanese": "間", "reading": "ma", "term_ids": ["ma"], "source_ids": ["provided-writing", "provided-visual", "provided-audio"]},
    "mono-no-aware": {"japanese": "もののあはれ", "reading": "mono no aware", "term_ids": ["mono-no-aware"], "source_ids": ["provided-history"]},
    "selective-animation": {"japanese": "", "reading": "selective animation (Kizuna teaching label)", "term_ids": ["genga", "douga", "sakuga"], "source_ids": ["provided-history", "provided-visual", "aja-archive"]},
    "graphic-cel-clarity": {"japanese": "", "reading": "graphic cel clarity (Kizuna teaching label)", "term_ids": ["cel-ga", "iro-shitei"], "source_ids": ["provided-visual", "aja-archive"]},
    "environment-as-agent": {"japanese": "", "reading": "environment as agent (Kizuna teaching label)", "term_ids": ["bijutsu-kantoku", "layout"], "source_ids": ["provided-writing", "provided-visual"]},
    "ensemble-performance": {"japanese": "", "reading": "ensemble performance (Kizuna teaching label)", "term_ids": ["seiyuu"], "source_ids": ["provided-writing", "provided-audio"]},
    "leitmotif-transformation": {"japanese": "", "reading": "leitmotif transformation", "term_ids": ["gekiban"], "source_ids": ["provided-audio"]},
    "sound-ma": {"japanese": "間", "reading": "ma applied to sound", "term_ids": ["ma", "gekiban"], "source_ids": ["provided-audio"]},
    "diegetic-bridge": {"japanese": "", "reading": "diegetic score bridge", "term_ids": ["gekiban"], "source_ids": ["provided-audio"]},
}

for tradition in CRAFT_CATALOG["traditions"]:
    tradition.update(TRADITION_METADATA.get(tradition["id"], {"japanese": "", "reading": tradition["name"], "term_ids": [], "source_ids": []}))


DEFAULT_COMPASS = {
    "intent": "",
    "cultural_context": "",
    "primary_genre": "",
    "genre_lenses": [],
    "tradition_ids": [],
    "anchors": [],
    "flexible": [],
    "departures": [],
    "catalog_version": "",
    "catalog_adopted_at": "",
    "catalog_snapshot": {},
}

LEGACY_CATALOG_VERSION = "2026.08"


def compass_has_framework(value: dict[str, Any]) -> bool:
    return bool(value.get("intent") or value.get("tradition_ids") or value.get("genre_lenses") or value.get("anchors"))


def catalog_snapshot(tradition_ids: list[str], genre_lenses: list[str], primary_genre: str = "", version: str | None = None) -> dict[str, Any]:
    snapshot_version = version or CRAFT_CATALOG["version"]
    tradition_map = {item["id"]: item for item in CRAFT_CATALOG["traditions"]}
    genre_map = {item["id"]: item for item in CRAFT_CATALOG["genre_lenses"]}
    selected_traditions = [tradition_map[item] for item in tradition_ids if item in tradition_map]
    selected_genre_ids = list(dict.fromkeys([primary_genre, *genre_lenses]))
    selected_genres = [genre_map[item] for item in selected_genre_ids if item in genre_map]
    if snapshot_version == LEGACY_CATALOG_VERSION:
        selected_traditions = [{key: item[key] for key in ("id", "name", "department", "context", "questions", "caution")} | {"japanese": "", "reading": item["name"], "term_ids": [], "source_ids": []} for item in selected_traditions]
    term_ids = list(dict.fromkeys(term_id for item in selected_traditions for term_id in item.get("term_ids", [])))
    glossary_map = {item["id"]: item for item in CRAFT_CATALOG["glossary"]}
    selected_terms = [glossary_map[item] for item in term_ids if item in glossary_map]
    source_ids = list(dict.fromkeys(source_id for item in [*selected_traditions, *selected_terms] for source_id in item.get("source_ids", [])))
    source_map = {item["id"]: item for item in CRAFT_CATALOG["sources"]}
    return {
        "version": snapshot_version,
        "review_rules_version": snapshot_version,
        "traditions": selected_traditions,
        "genre_lenses": selected_genres,
        "glossary": selected_terms,
        "sources": [source_map[item] for item in source_ids if item in source_map],
    }


def pinned_catalog_status(value: dict[str, Any] | None) -> dict[str, Any]:
    compass = normalize_compass(value)
    explicit_version = compass.get("catalog_version", "")
    pinned_version = explicit_version or (LEGACY_CATALOG_VERSION if compass_has_framework(compass) else "")
    update_available = bool(pinned_version and pinned_version != CRAFT_CATALOG["version"])
    if not pinned_version:
        state = "not_adopted"
        notice = "Save the Craft Compass to adopt the current reviewed catalog."
    elif update_available:
        state = "update_available"
        notice = f"This production remains on catalog {pinned_version}. Review the changes before adopting {CRAFT_CATALOG['version']}."
    else:
        state = "current"
        notice = f"This production is pinned to catalog {pinned_version}."
    return {
        "state": state,
        "pinned_version": pinned_version or None,
        "current_version": CRAFT_CATALOG["version"],
        "adopted_at": compass.get("catalog_adopted_at") or None,
        "update_available": update_available,
        "notice": notice,
        "release": CRAFT_CATALOG["release"],
        "snapshot_counts": {
            "traditions": len((compass.get("catalog_snapshot") or {}).get("traditions", [])),
            "genre_lenses": len((compass.get("catalog_snapshot") or {}).get("genre_lenses", [])),
            "glossary": len((compass.get("catalog_snapshot") or {}).get("glossary", [])),
            "sources": len((compass.get("catalog_snapshot") or {}).get("sources", [])),
        },
    }


def normalize_compass(value: dict[str, Any] | None) -> dict[str, Any]:
    result = {**DEFAULT_COMPASS, **(value or {})}
    for key in ("genre_lenses", "tradition_ids", "anchors", "flexible", "departures"):
        result[key] = result.get(key) if isinstance(result.get(key), list) else []
    result["catalog_snapshot"] = result.get("catalog_snapshot") if isinstance(result.get("catalog_snapshot"), dict) else {}
    return result


def craft_prompt_context(value: dict[str, Any] | None, department: str) -> str:
    compass = normalize_compass(value)
    if not compass["intent"] and not compass["tradition_ids"]:
        return ""
    snapshot = compass.get("catalog_snapshot") or {}
    framework_traditions = snapshot.get("traditions") or CRAFT_CATALOG["traditions"]
    framework_glossary = snapshot.get("glossary") or CRAFT_CATALOG["glossary"]
    tradition_map = {item["id"]: item for item in framework_traditions}
    selected = [tradition_map[item] for item in compass["tradition_ids"] if item in tradition_map and tradition_map[item]["department"] in {department, "cross-craft"}]
    if not selected:
        selected = [tradition_map[item] for item in compass["tradition_ids"] if item in tradition_map]
    lenses = "; ".join(f"{item.get('japanese') + ' (' + item.get('reading', item['name']) + ')' if item.get('japanese') else item.get('reading', item['name'])}: {item['context']}" for item in selected[:4])
    term_ids = list(dict.fromkeys(term_id for item in selected for term_id in item.get("term_ids", [])))
    term_map = {item["id"]: item for item in framework_glossary}
    vocabulary = "; ".join(f"{term_map[term_id]['term']} ({term_map[term_id]['reading']}): {term_map[term_id]['production_use']} Caution: {term_map[term_id]['caution']}" for term_id in term_ids[:5] if term_id in term_map)
    anchors = "; ".join(compass["anchors"][:6])
    pinned_version = compass.get("catalog_version") or (LEGACY_CATALOG_VERSION if compass_has_framework(compass) else CRAFT_CATALOG["version"])
    return f"Pinned craft catalog: {pinned_version}. Creative intent: {compass['intent'] or 'still being discovered'}. Craft lenses: {lenses or 'none selected for this department'}. Relevant vocabulary: {vocabulary or 'none selected for this department'}. Anchors: {anchors or 'none declared'}. Use these as questions and transferable practices, not as permission to imitate a title, studio, or artist. Do not invent Japanese equivalents for Kizuna teaching labels."


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
    return {"status": "needs_intent" if unresolved else "aligned_or_intentional", "advisory": True, "blocking": False, "summary": f"{len(unresolved)} open craft conversation{'s' if len(unresolved) != 1 else ''}", "findings": relevant, "compass": compass, "catalog": pinned_catalog_status(compass), "review_hash": digest, "distinction": "Craft guidance is advisory. Originality, rights, consent, and release compliance remain separate enforceable gates."}
