# Anime Craft Compass

Kizuna treats anime as a living, historically situated field of practice. The Craft Compass connects story, visual development, motion, worldbuilding, performance, editing, and sound without pretending that one genre convention or studio tendency defines authentic anime.

## Product stance

- Teach where a practice comes from and what it can accomplish.
- Present conventions as lenses and questions, not cultural purity tests.
- Distinguish demographic traditions, genres, production methods, eras, and individual bodies of work.
- Never turn Japanese aesthetics into generic decoration or claims about all Japanese creators.
- Let creators align, intentionally depart, or revise their compass as the work develops.
- Keep craft guidance advisory. Originality, rights, consent, and release compliance remain separate enforceable gates.

## Source review

The initial catalog synthesizes the four creator-provided guides covering history and genres, writing, visual craft, and audio. Their strongest shared insight is that style is an argument: structure, designed stillness, color, movement, environment, music, silence, and performance should reinforce what the production wants the audience to notice and feel.

The guides are useful orientation material, but several formulations are too absolute to become software rules. Kizuna therefore does not encode these claims as facts:

- Kisho-ten-ketsu is not labeled the single native or universal Japanese story structure.
- Jo-ha-kyu is introduced through its performing-arts context and used as a rhythmic lens, not a replacement name for three-act structure.
- Ma is treated as a shaped relationship among events, spaces, and sounds, not merely a long empty shot.
- Limited animation is treated as a designed production language, not automatically a compromise or inferior frame rate.
- Sakuga is not reduced to a sudden increase in budget.
- Genre, demographic, studio, director, and era tendencies are not interchangeable style presets.
- Hair color, eye shape, vocal register, and archetype shorthand are never treated as deterministic personality rules.

The catalog also references the Association of Japanese Animations' archival work through Anime TAIZEN, Japanese public cultural material about inheritance and continued creation, and National Theatre material on jo-ha-kyu. Future catalog releases should add Japanese-language scholarship, practitioner interviews, production texts, and paid cultural review.

Style Lab now includes a searchable bilingual craft library. Recognized Japanese production, literary, and aesthetic terms show their Japanese form, romanized reading, plain-language meaning, practical production use, caution, and catalog sources. English teaching labels that do not have an honest one-to-one Japanese equivalent are explicitly identified instead of receiving invented translations. Guided paths introduce foundations, story rhythm, and the studio pipeline without hiding the deeper catalog from professional users.

Every saved Craft Compass pins a catalog version and a compact snapshot of the production's selected traditions, genre lenses, related glossary entries, and sources. A later catalog release never silently changes the production's AI context. Style Lab shows the pinned and current versions, explains the reviewed changes, and requires a written rationale before adoption. Migration preserves creative intent and selections, refreshes their framework snapshot, and records hashed rationale and framework evidence in the audit ledger.

## Stored production intent

The `style_profiles.craft` document stores:

- the work's creative intent;
- cultural and research context;
- a primary genre lens and supporting lenses;
- traditions the creator wants the crew to study;
- firm craft anchors;
- flexible choices;
- decisions about current guidance findings.

All AI providers receive the relevant compass through project context. The Writer and Director contexts receive the complete compass and current advisory review. The embedded assistant receives the same review and must always offer three paths when it notices tension: realign, continue intentionally, or revise the compass.

## Advisory review

`GET /api/projects/{project_id}/craft-compass` evaluates saved work against the current compass. `POST /api/projects/{project_id}/craft-review` can focus on a production stage. Reviews are deterministic and explainable; every finding includes why it matters and three possible responses.

`POST /api/projects/{project_id}/craft-decisions` records the creator's rationale in the production audit ledger. A decision to continue intentionally resolves the advisory conversation. A plan to realign or revise remains visible until the underlying production or compass changes.

The Compass icon in the fixed bottom dock opens a stage-specific panel that follows Writer's Room, Style Lab, Character Studio, Worlds, Storyboard & Shot Planner, Timeline, Audio, finishing, and studio operations. It names the relevant selected traditions, explains open creative tensions, cites saved production evidence behind applicable findings, and lets the creator record an intentional decision without covering the active desk until requested. Evidence can identify character story anchors and relationships, location functions and approved background versions, scene and shot numbers with approved storyboards, timeline clip durations and transitions, and named audio regions with timecodes. When no compass has been set, the panel returns the creator directly to the Craft Compass step in Style Lab. A guidance service failure remains non-blocking so creative work can continue.

Each of those desks also includes **Sources & invention**. A creator can record whether a decision came from research, direct observation, consultation, a creative reference, or original invention; name what the source contributed; and explain how the crew transformed it into new production work. Links and research-log references are optional, while every create or edit action is recorded in the audit chain. These notes document creative reasoning and cultural care. They do not replace asset licenses, participant consent, originality scans, or qualified rights clearance.

The initial rules deliberately cover only high-confidence, explainable tensions, including:

- restorative iyashikei and ma paired with rapid-impact editing;
- cyberpunk imagery without a stated social question;
- isekai worlds with locations but no visible rules, costs, or limits;
- a literal beat-count reading of kisho-ten-ketsu;
- ensemble performance selected while characters remain isolated or thinly defined;
- graphic clarity or selective animation selected before character identity locks exist;
- ma selected as an anchor but absent from shot language;
- sound-ma selected without a deliberately quiet region in the current mix;
- leitmotif transformation selected while music cues describe repetition but no change.

This engine should grow through reviewed craft rules, not opaque similarity scoring or a model's unsupported opinion.

## Next research and product work

1. Commission Japanese animation historians, working animators, writers, sound professionals, and cultural advisors to review the catalog.
2. Add reviewed pronunciation audio, contested interpretations, and Japanese-language reading recommendations.
3. Expand beginner learning paths while preserving compact professional controls.
4. Add side-by-side framework diffs and an administrator rollback path before the second catalog release.
