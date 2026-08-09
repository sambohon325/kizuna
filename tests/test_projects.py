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
