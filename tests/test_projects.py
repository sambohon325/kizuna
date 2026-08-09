def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_style_catalog_has_eras_and_directing_traits(client):
    response = client.get("/api/style-catalog")
    assert response.status_code == 200
    catalog = response.json()
    assert len(catalog["eras"]) == 7
    assert "camera" in catalog["direction"]
    assert "kishotenketsu" in catalog["narrative"]["structure"]


def test_project_scene_and_shot_workflow(client):
    project = client.post("/api/projects", json={"title": "Signal Bloom", "logline": "A pilot hears a message from a vanished moon."})
    assert project.status_code == 201
    data = project.json()
    assert data["style_profile"]["era_primary"] == "1990s"
    scene = client.post(f"/api/projects/{data['id']}/scenes", json={"title": "The Voice", "summary": "An impossible transmission interrupts the night watch.", "position": 1})
    assert scene.status_code == 201
    shot = client.post(f"/api/scenes/{scene.json()['id']}/shots", json={"title": "Orbit reveal", "description": "A slow push toward the listening station.", "position": 1, "duration_seconds": 6})
    assert shot.status_code == 201
    result = client.get(f"/api/projects/{data['id']}").json()
    assert result["scenes"][0]["shots"][0]["title"] == "Orbit reveal"


def test_style_profile_can_be_mixed(client):
    project_id = client.post("/api/projects", json={"title": "Paper Sun"}).json()["id"]
    payload = {"era_primary": "1970s", "era_secondary": "2020s", "visual": {"linework": "graphic"}, "direction": {"camera": "theatrical"}, "narrative": {"structure": "jo-ha-kyu"}, "archetypes": ["flawed mentor"]}
    response = client.put(f"/api/projects/{project_id}/style", json=payload)
    assert response.status_code == 200
    assert response.json()["era_secondary"] == "2020s"


def test_writer_room_develops_structured_story_and_character(client):
    project_id = client.post("/api/projects", json={"title": "Glass Horizon", "logline": "A courier crosses a city that forgets itself each dawn."}).json()["id"]
    response = client.put(f"/api/projects/{project_id}/story", json={"premise": "A courier must deliver yesterday's final memory before sunrise.", "format": "short film", "target_duration_minutes": 12, "audience": "teen and adult", "genre": "memory mystery", "themes": ["identity", "duty versus freedom"]})
    assert response.status_code == 200
    assert len(response.json()["beats"]) == 8
    assert "memory mystery" in response.json()["synopsis"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Mika", "role": "reluctant protagonist", "want": "Finish the route", "need": "Accept help", "contradiction": "Preserves memories while avoiding her own"})
    assert character.status_code == 201
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["characters"][0]["name"] == "Mika"
    assert project["story_brief"]["target_duration_minutes"] == 12
    beats = response.json()["beats"]
    beats[0]["summary"] = "A silent train crosses an impossible reflection."
    edited = client.patch(f"/api/projects/{project_id}/story/outline", json={"synopsis": response.json()["synopsis"], "beats": beats})
    assert edited.status_code == 200
    assert edited.json()["beats"][0]["summary"].startswith("A silent train")


def test_character_design_compiles_style_aware_reference_brief(client):
    project_id = client.post("/api/projects", json={"title": "Red Current"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Ari", "role": "quiet protector", "want": "Keep the crew alive", "need": "Trust their judgment", "contradiction": "Protects everyone while refusing care"}).json()
    design_payload = {"appearance": {"silhouette": "long asymmetrical coat", "hair": "short silver undercut", "eyes": "amber, heavy upper lid"}, "palette": ["charcoal", "oxide red", "warm amber"], "wardrobe": ["weathered flight coat", "utility boots"], "consistency_anchors": ["split left eyebrow", "red collar tab", "triangular earring"]}
    response = client.put(f"/api/characters/{character['id']}/design", json=design_payload)
    assert response.status_code == 200
    design = response.json()
    assert "1990s blended with 2020s" in design["reference_brief"]
    assert "triangular earring" in design["reference_brief"]
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["characters"][0]["design"]["palette"][1] == "oxide red"
    updated = client.put(f"/api/characters/{character['id']}", json={"name": "Ari", "role": "quiet protector", "want": "Save the entire station", "need": "Trust their judgment", "contradiction": "Protects everyone while refusing care"})
    assert updated.status_code == 200
    assert updated.json()["want"] == "Save the entire station"
    versioned = client.put(f"/api/characters/{character['id']}/design", json=design_payload)
    assert versioned.json()["version"] == 2
    providers = client.get("/api/generation/providers")
    assert providers.status_code == 200
    assert providers.json()["active"] == "mock"
    generation = client.post(f"/api/characters/{character['id']}/generate", json={"provider": "mock", "seed": 42})
    assert generation.status_code == 201
    job = generation.json()
    assert job["status"] == "completed"
    assert job["assets"][0]["mime_type"] == "image/svg+xml"
    preview = client.get(job["assets"][0]["uri"])
    assert preview.status_code == 200
    assert "REFERENCE SHEET SIMULATION" in preview.text


def test_generation_requires_character_design(client):
    project_id = client.post("/api/projects", json={"title": "No Sheet"}).json()["id"]
    character_id = client.post(f"/api/projects/{project_id}/characters", json={"name": "Ren"}).json()["id"]
    response = client.post(f"/api/characters/{character_id}/generate", json={"provider": "mock"})
    assert response.status_code == 409


def test_render_worker_claims_uploads_and_completes_farm_job(client):
    project_id = client.post("/api/projects", json={"title": "Farm Test"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Iona", "role": "navigator"}).json()
    client.put(f"/api/characters/{character['id']}/design", json={"appearance": {"silhouette": "short cape"}, "palette": ["navy", "gold"], "wardrobe": ["flight suit"], "consistency_anchors": ["star hair clip"]})
    queued = client.post(f"/api/characters/{character['id']}/generate", json={"provider": "farm"})
    assert queued.status_code == 201
    assert queued.json()["status"] == "queued"

    registration = client.post("/api/workers/register", headers={"X-Enrollment-Secret": "local-dev-enrollment"}, json={"name": "gpu-one", "hostname": "render-01", "capabilities": {"gpu": "RTX 4090", "vram_gb": 24}, "supported_tasks": ["character_reference"]})
    assert registration.status_code == 201
    worker = registration.json()
    headers = {"Authorization": f"Bearer {worker['token']}"}
    heartbeat = client.post(f"/api/workers/{worker['id']}/heartbeat", headers=headers, json={"status": "online"})
    assert heartbeat.status_code == 200
    claimed = client.post(f"/api/workers/{worker['id']}/claim", headers=headers)
    assert claimed.status_code == 200
    job_id = claimed.json()["id"]
    upload = client.put(f"/api/workers/{worker['id']}/jobs/{job_id}/artifacts/reference.png", headers={**headers, "Content-Type": "image/png"}, content=b"fake-png-for-integration-test")
    assert upload.status_code == 201
    completed = client.post(f"/api/workers/{worker['id']}/jobs/{job_id}/complete", headers=headers, json={"result_data": {"render_seconds": 12.4}})
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["assets"][0]["asset_metadata"]["worker_id"] == worker["id"]
    farm = client.get("/api/render-farm/status").json()
    assert farm["workers"][0]["status"] == "online"
    assert farm["jobs"][0]["assets"] == 1


def test_worker_api_rejects_invalid_token(client):
    response = client.post("/api/workers/999/claim", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


def test_world_studio_versions_design_and_generates_background_asset(client):
    project_id = client.post("/api/projects", json={"title": "Cloud Archive"}).json()["id"]
    location = client.post(f"/api/projects/{project_id}/locations", json={"name": "The Listening Hall", "narrative_function": "A sanctuary that gradually becomes a trap", "description": "A suspended archive built around a silent radio telescope.", "geography": "high orbit above a storm planet", "time_period": "retro-future"})
    assert location.status_code == 201
    location_id = location.json()["id"]
    design_payload = {"appearance": {"architecture": "brutalist rings and delicate antennae", "materials": "oxidized steel and amber glass", "atmosphere": "thin mist and drifting dust", "scale": "monumental"}, "palette": ["charcoal", "amber", "storm blue"], "layers": ["foreground cables", "performance deck", "telescope ring", "storm planet"], "lighting_variants": ["quiet dawn", "emergency red", "eclipse"], "continuity_anchors": ["broken west antenna", "three amber windows", "central circular hatch"]}
    design = client.put(f"/api/locations/{location_id}/design", json=design_payload)
    assert design.status_code == 200
    assert "1990s blended with 2020s" in design.json()["reference_brief"]
    versioned = client.put(f"/api/locations/{location_id}/design", json=design_payload)
    assert versioned.json()["version"] == 2
    generation = client.post(f"/api/locations/{location_id}/generate", json={"provider": "mock", "seed": 99})
    assert generation.status_code == 201
    assert generation.json()["status"] == "completed"
    assert generation.json()["assets"][0]["version"] == 1
    preview = client.get(generation.json()["assets"][0]["uri"])
    assert "BACKGROUND CONCEPT SIMULATION" in preview.text
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["locations"][0]["design"]["layers"][2] == "telescope ring"


def test_background_generation_requires_design(client):
    project_id = client.post("/api/projects", json={"title": "Empty World"}).json()["id"]
    location_id = client.post(f"/api/projects/{project_id}/locations", json={"name": "Blank Room"}).json()["id"]
    response = client.post(f"/api/locations/{location_id}/generate", json={"provider": "mock"})
    assert response.status_code == 409


def test_story_expands_into_shot_plans_and_generates_storyboard(client):
    project_id = client.post("/api/projects", json={"title": "Shot Test", "logline": "A pilot follows a signal beyond the mapped sky."}).json()["id"]
    client.put(f"/api/projects/{project_id}/story", json={"premise": "A pilot follows a forbidden signal.", "format": "short film", "target_duration_minutes": 8, "genre": "orbital mystery", "audience": "general", "themes": ["identity"]})
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Ari", "role": "pilot"}).json()
    client.put(f"/api/characters/{character['id']}/design", json={"appearance": {"hair": "silver undercut"}, "consistency_anchors": ["split eyebrow"]})
    location = client.post(f"/api/projects/{project_id}/locations", json={"name": "Listening Hall"}).json()
    client.put(f"/api/locations/{location['id']}/design", json={"appearance": {"architecture": "orbital rings"}, "continuity_anchors": ["central hatch"]})
    expanded = client.post(f"/api/projects/{project_id}/expand-story", json={"shots_per_beat": 2})
    assert expanded.status_code == 200
    project = expanded.json()
    assert len(project["scenes"]) == 8
    assert len(project["scenes"][0]["shots"]) == 2
    shot = project["scenes"][0]["shots"][0]
    assert shot["plan"]["camera"]["shot_size"] == "wide"
    plan_payload = {"location_id": location["id"], "character_ids": [character["id"]], "action": "Ari enters beneath the silent telescope.", "dialogue": "Is anyone listening?", "camera": {"shot_size": "wide", "angle": "low", "lens": "24mm", "movement": "slow push"}, "lighting": "quiet dawn", "continuity_notes": "Keep Ari frame-left and the hatch centered."}
    planned = client.put(f"/api/shots/{shot['id']}/plan", json=plan_payload)
    assert planned.status_code == 200
    assert "Ari" in planned.json()["storyboard_prompt"]
    assert "central hatch" in planned.json()["storyboard_prompt"]
    storyboard = client.post(f"/api/shots/{shot['id']}/storyboard", json={"provider": "mock"})
    assert storyboard.status_code == 201
    assert storyboard.json()["assets"][0]["version"] == 1
    preview = client.get(storyboard.json()["assets"][0]["uri"])
    assert "STORYBOARD FRAME SIMULATION" in preview.text
    conflict = client.post(f"/api/projects/{project_id}/expand-story", json={"shots_per_beat": 2})
    assert conflict.status_code == 409


def test_timeline_edits_reorders_and_renders_proxy(client):
    project_id = client.post("/api/projects", json={"title": "Picture Edit"}).json()["id"]
    scene_id = client.post(f"/api/projects/{project_id}/scenes", json={"title": "Opening", "position": 1}).json()["id"]
    first = client.post(f"/api/scenes/{scene_id}/shots", json={"title": "Signal wakes", "position": 1, "duration_seconds": 0.6}).json()
    second = client.post(f"/api/scenes/{scene_id}/shots", json={"title": "Ari turns", "position": 2, "duration_seconds": 0.6}).json()
    timeline_response = client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 12, "width": 320, "height": 180})
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert [clip["shot_id"] for clip in timeline["clips"]] == [first["id"], second["id"]]

    first_clip, second_clip = timeline["clips"]
    edited = client.put(f"/api/timeline-clips/{second_clip['id']}", json={"duration_seconds": 0.8, "transition": "dissolve", "transition_duration": 0.2, "audio_cue": "Radio tone blooms."})
    assert edited.status_code == 200
    assert edited.json()["clips"][1]["audio_cue"] == "Radio tone blooms."
    reordered = client.put(f"/api/timelines/{timeline['id']}/clips/order", json={"clip_ids": [second_clip["id"], first_clip["id"]]})
    assert reordered.json()["clips"][0]["shot_id"] == second["id"]

    rendered = client.post(f"/api/timelines/{timeline['id']}/render")
    assert rendered.status_code == 201
    assert rendered.json()["status"] == "completed", rendered.json().get("error")
    video = client.get(rendered.json()["uri"])
    assert video.status_code == 200
    assert video.headers["content-type"] == "video/mp4"


def test_audio_studio_builds_voice_cues_and_mixes_animatic(client):
    project_id = client.post("/api/projects", json={"title": "Sound Pass"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Ari", "role": "pilot"}).json()
    voice = client.put(f"/api/characters/{character['id']}/voice", json={"texture": "clear and weathered", "energy": "contained urgency", "pace": 0.9, "pitch": -1, "direction_notes": "Precise until the final word."})
    assert voice.status_code == 200
    assert voice.json()["texture"] == "clear and weathered"

    scene_id = client.post(f"/api/projects/{project_id}/scenes", json={"title": "Contact", "position": 1}).json()["id"]
    client.post(f"/api/scenes/{scene_id}/shots", json={"title": "Ari answers", "position": 1, "duration_seconds": 0.8})
    timeline = client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 12, "width": 320, "height": 180}).json()
    studio = client.post(f"/api/timelines/{timeline['id']}/audio/build")
    assert studio.status_code == 200
    assert [track["kind"] for track in studio.json()["tracks"]] == ["dialogue", "music", "sfx", "ambience"]
    dialogue_track = studio.json()["tracks"][0]
    cue = client.post(f"/api/audio-tracks/{dialogue_track['id']}/cues", json={"character_id": character["id"], "start_seconds": 0.1, "duration_seconds": 0.5, "text": "Is anyone listening?", "direction": "A guarded whisper."})
    assert cue.status_code == 201
    scratch = client.post(f"/api/audio-cues/{cue.json()['id']}/generate-scratch")
    assert scratch.json()["status"] == "scratch-ready"
    assert client.get(scratch.json()["uri"]).headers["content-type"] == "audio/wav"

    rendered = client.post(f"/api/timelines/{timeline['id']}/render")
    assert rendered.json()["status"] == "completed", rendered.json().get("error")
    assert rendered.json()["render_settings"]["audio_cues"] == 1


def test_scene_compositor_builds_layers_renders_and_feeds_timeline(client):
    project_id = client.post("/api/projects", json={"title": "Layer Test"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Ari", "role": "pilot"}).json()
    location = client.post(f"/api/projects/{project_id}/locations", json={"name": "Listening Hall"}).json()
    scene_id = client.post(f"/api/projects/{project_id}/scenes", json={"title": "Contact", "position": 1}).json()["id"]
    shot = client.post(f"/api/scenes/{scene_id}/shots", json={"title": "Ari enters", "position": 1, "duration_seconds": 1}).json()
    client.put(f"/api/shots/{shot['id']}/plan", json={"location_id": location["id"], "character_ids": [character["id"]], "action": "Ari enters.", "camera": {"movement": "slow push"}})
    timeline = client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 12, "width": 320, "height": 180}).json()

    composition_response = client.post(f"/api/shots/{shot['id']}/composition/build")
    assert composition_response.status_code == 200
    composition = composition_response.json()
    assert [layer["kind"] for layer in composition["layers"]] == ["background", "character"]
    assert composition["camera"]["move"] == "slow push"
    character_layer = composition["layers"][1]
    layer_payload = {key: character_layer[key] for key in ("name", "kind", "source_kind", "source_asset_id", "source_uri", "z_index", "visible", "opacity", "blend_mode", "transform", "animation")}
    layer_payload["transform"] = {"x": 0.35, "y": 0.6, "scale": 0.85, "rotation": -2}
    edited = client.put(f"/api/composition-layers/{character_layer['id']}", json=layer_payload)
    assert edited.json()["transform"]["x"] == 0.35

    rendered = client.post(f"/api/compositions/{composition['id']}/render")
    assert rendered.status_code == 201
    assert rendered.json()["status"] == "completed", rendered.json().get("error")
    preview = client.get(rendered.json()["uri"])
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    updated_timeline = client.get(f"/api/projects/{project_id}/timeline").json()
    assert updated_timeline["clips"][0]["storyboard_uri"] == rendered.json()["uri"]

    layer_payload["animation"] = {"intent": "drift into frame", "easing": "ease-in-out", "end": {"x": 0.55, "y": 0.58, "scale": 0.95, "rotation": 1, "opacity": 0.8}}
    client.put(f"/api/composition-layers/{character_layer['id']}", json=layer_payload)
    motion = client.post(f"/api/compositions/{composition['id']}/render-video", json={"quality": "proxy", "fps": 8})
    assert motion.status_code == 201
    assert motion.json()["status"] == "completed", motion.json().get("error")
    assert motion.json()["render_settings"]["frame_count"] == 8
    video = client.get(motion.json()["uri"])
    assert video.status_code == 200
    assert video.headers["content-type"] == "video/mp4"
    refreshed = client.get(f"/api/shots/{shot['id']}/composition").json()
    assert refreshed["latest_motion_uri"] == motion.json()["uri"]

    client.post(f"/api/scenes/{scene_id}/shots", json={"title": "Signal answers", "position": 2, "duration_seconds": 0.6})
    rebuilt_timeline = client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 8, "width": 320, "height": 180}).json()
    studio = client.post(f"/api/timelines/{rebuilt_timeline['id']}/audio/build").json()
    ambience = next(track for track in studio["tracks"] if track["kind"] == "ambience")
    cue = client.post(f"/api/audio-tracks/{ambience['id']}/cues", json={"start_seconds": 0.1, "duration_seconds": 0.3, "text": "Carrier tone"}).json()
    client.post(f"/api/audio-cues/{cue['id']}/generate-scratch")
    master = client.post(f"/api/timelines/{rebuilt_timeline['id']}/render-master", json={"profile": "preview", "fps": 8})
    assert master.status_code == 201
    assert master.json()["status"] == "completed", master.json().get("error")
    assert master.json()["render_settings"]["motion_clips"] == 1
    assert master.json()["render_settings"]["fallback_clips"] == 1
    assert master.json()["render_settings"]["audio_cues"] == 1
    assert master.json()["render_settings"]["width"] == 320
    assert client.get(master.json()["uri"]).headers["content-type"] == "video/mp4"
