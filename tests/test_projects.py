def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_integration_settings_support_builtin_and_custom_tools(client):
    settings_response = client.get("/api/settings/integrations")
    assert settings_response.status_code == 200
    integrations = {item["key"]: item for item in settings_response.json()["integrations"]}
    assert {"openai", "anthropic", "google", "ollama", "comfyui", "adobe", "corel", "gimp"}.issubset(integrations)
    assert integrations["openai"]["configured"] is False

    configured = client.put("/api/settings/integrations/ollama", json={"display_name": "Ollama", "category": "ai", "mode": "api", "endpoint": "http://render-box:11434", "model": "studio-model", "secret_env_var": "", "configuration": {}})
    assert configured.status_code == 200
    assert configured.json()["configured"] is True
    assert configured.json()["endpoint"] == "http://render-box:11434"

    custom = client.put("/api/settings/integrations/custom-house-engine", json={"display_name": "House Engine", "category": "generation", "mode": "api", "endpoint": "http://studio-ai:9000/v1", "model": "anime-v2", "secret_env_var": "KIZUNA_HOUSE_AI_KEY", "configuration": {"description": "Private studio engine", "capabilities": ["image", "animation"]}})
    assert custom.status_code == 200
    assert custom.json()["custom"] is True
    assert custom.json()["secret_available"] is False
    assert client.delete("/api/settings/integrations/custom-house-engine").status_code == 204
    assert client.delete("/api/settings/integrations/openai").status_code == 400


def test_ai_role_routing_drives_the_contextual_assistant(client, monkeypatch):
    routing = client.get("/api/settings/ai-routing")
    assert routing.status_code == 200
    assert len(routing.json()["routes"]) == 9
    assert all(route["provider_key"] == "local" for route in routing.json()["routes"])

    connected = client.put("/api/settings/integrations/custom-story-brain", json={"display_name": "Story Brain", "category": "ai", "mode": "api", "endpoint": "http://studio-ai:9000/v1", "model": "story-v2", "secret_env_var": "", "configuration": {"protocol": "openai-compatible"}})
    assert connected.status_code == 200
    routed = client.put("/api/settings/ai-routing/assistant", json={"provider_key": "custom-story-brain", "model_override": "story-v3"})
    assert routed.status_code == 200
    assert routed.json()["ready"] is True
    assert routed.json()["model_override"] == "story-v3"

    monkeypatch.setattr("app.main.generate_text", lambda provider, **kwargs: f"Routed through {provider.name} using {provider.model}.")
    project = client.post("/api/projects", json={"title": "Router Test", "logline": "A director finds the right creative partner."}).json()
    response = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "What should I do next?", "page": "productions", "screen_context": {"heading": "Productions"}})
    assert response.status_code == 200
    assert response.json()["message"]["content"] == "Routed through Story Brain using story-v3."
    assert response.json()["message"]["context"]["provider"] == "custom-story-brain"
    assert response.json()["message"]["context"]["model"] == "story-v3"

    from app.ai_router import AIRouterError
    monkeypatch.setattr("app.main.generate_text", lambda provider, **kwargs: (_ for _ in ()).throw(AIRouterError("engine offline")))
    fallback = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "Can you still help?", "page": "writer", "screen_context": {"heading": "Writer's Room"}})
    assert fallback.status_code == 200
    assert fallback.json()["message"]["context"]["provider"] == "local"
    assert fallback.json()["message"]["context"]["fallback_reason"] == "engine offline"
    assert "Router Test" in fallback.json()["message"]["content"]

    assert client.put("/api/settings/ai-routing/not-a-role", json={"provider_key": "local"}).status_code == 404


def test_kizuna_node_onboarding_workload_control_and_usage_budget(client, monkeypatch):
    empty = client.get("/api/settings/compute")
    assert empty.status_code == 200
    assert empty.json()["nodes"] == []
    assert len(empty.json()["workloads"]) == 7
    assert "passwords or API keys" in empty.json()["privacy"]["never_sent"]

    enrollment = client.post("/api/settings/compute/enrollment").json()
    assert client.get(enrollment["download_url"]).status_code == 200
    assert "kizuna-local-capability-check" in client.get(enrollment["download_url"]).text
    profile = {"code": enrollment["code"], "node_key": "test-node-0001", "name": "Edit Suite", "os_name": "Windows", "os_version": "11", "architecture": "AMD64", "cpu_name": "Studio CPU", "logical_cores": 16, "ram_gb": 64, "gpu": [{"name": "Studio GPU", "memory_mb": 16384}], "software": ["ollama", "ffmpeg", "blender"], "benchmark_score": 123.4, "capabilities": ["local_ai", "gpu_render", "video_encode"], "timezone_offset_minutes": -300}
    enrolled = client.post("/api/nodes/enroll", json=profile)
    assert enrolled.status_code == 200
    token = enrolled.json()["token"]
    assert client.post("/api/nodes/test-node-0001/heartbeat", json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401
    heartbeat = client.post("/api/nodes/test-node-0001/heartbeat", json={"benchmark_score": 130, "metrics": {"cpu_percent": 22, "gpu_percent": 10, "memory_used_gb": 12}}, headers={"Authorization": f"Bearer {token}"})
    assert heartbeat.status_code == 200
    assert heartbeat.json()["hive"]["accepting_work"] is True
    compute = client.get("/api/settings/compute").json()
    assert compute["nodes"][0]["status"] == "online"
    assert "private local AI" in compute["nodes"][0]["strengths"]
    assert "token" not in compute["nodes"][0]
    assert compute["hive"] == {"devices": 1, "online": 1, "accepting_work": 1, "active_jobs": 0, "queued_jobs": 0, "capacity": 1, "platforms": ["Windows"]}
    assert compute["nodes"][0]["hive"]["metrics"]["cpu_percent"] == 22
    control_payload = {"paused": True, "drain": False, "max_concurrency": 3, "cpu_limit_percent": 70, "gpu_limit_percent": 85, "memory_limit_gb": 48, "available_days": [0, 1, 2, 3, 4, 5, 6], "start_hour": 0, "end_hour": 24, "priority": 75, "allowed_tasks": ["master_segment"]}
    control = client.put("/api/settings/compute/nodes/test-node-0001/control", json=control_payload)
    assert control.status_code == 200
    assert control.json()["reason"] == "Paused"
    assert client.get("/api/settings/compute").json()["hive"]["capacity"] == 3
    control_payload["paused"] = False
    assert client.put("/api/settings/compute/nodes/test-node-0001/control", json=control_payload).json()["accepting_work"] is True
    throttled = client.post("/api/nodes/test-node-0001/heartbeat", json={"metrics": {"cpu_percent": 75, "gpu_percent": 10, "memory_used_gb": 12}}, headers={"Authorization": f"Bearer {token}"})
    assert throttled.json()["hive"]["reason"] == "CPU throttle reached"

    policy = client.put("/api/settings/compute/workloads/rendering", json={"placement": "local", "node_key": "test-node-0001", "cloud_provider": ""})
    assert policy.status_code == 200
    assert policy.json()["placement"] == "local"
    assert client.put("/api/settings/compute/workloads/rendering", json={"placement": "local", "node_key": "missing", "cloud_provider": ""}).status_code == 400

    client.put("/api/settings/integrations/custom-metered", json={"display_name": "Metered AI", "category": "ai", "mode": "api", "endpoint": "http://studio-ai:9000/v1", "model": "efficient-v1", "secret_env_var": "", "configuration": {"protocol": "openai-compatible"}})
    client.put("/api/settings/ai-routing/assistant", json={"provider_key": "custom-metered", "model_override": ""})
    rate = client.post("/api/settings/ai-rates", json={"provider_key": "custom-metered", "model": "efficient-v1", "input_per_million": 1, "cached_input_per_million": 0.1, "output_per_million": 3, "currency": "USD", "source_url": "https://example.test/pricing"})
    assert rate.status_code == 200
    assert client.put("/api/settings/spend", json={"monthly_budget": 10, "warning_percent": 75, "hard_stop": True}).status_code == 200
    from app.ai_router import GeneratedText
    monkeypatch.setattr("app.main.generate_text", lambda provider, **kwargs: GeneratedText("Metered answer", 1000, 200, 500))
    project = client.post("/api/projects", json={"title": "Metered Production", "logline": "Every creative choice has a visible cost."}).json()
    answer = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "Help me plan", "page": "productions", "screen_context": {}})
    assert answer.status_code == 200
    usage = client.get("/api/settings/compute").json()["usage"]
    assert usage["requests"] == 1
    assert usage["input_tokens"] == 1000
    assert usage["estimated_cost"] == 0.00232
    assert usage["budget"]["monthly_budget"] == 10


def test_production_scope_changes_story_shape_and_assistant_context(client):
    project = client.post("/api/projects", json={"title": "Pocket Signal", "logline": "A courier receives one impossible message.", "scope": {"distribution_channel": "TikTok", "release_format": "ongoing_series", "aspect_ratio": "9:16", "width": 1080, "height": 1920, "target_duration_seconds": 60, "installment_count": 24, "season_count": 2, "notes": "Weekly vertical episodes"}})
    assert project.status_code == 201
    project_id = project.json()["id"]
    scope = client.get(f"/api/projects/{project_id}/scope").json()
    assert scope["summary"].startswith("Ongoing series · TikTok · 9:16 vertical · 1 min")
    assert any("vertical frame" in item for item in scope["writing_guidance"])

    story = client.put(f"/api/projects/{project_id}/story", json={"premise": "The message predicts the next sixty seconds.", "format": "feature film", "target_duration_minutes": 90, "audience": "general", "genre": "thriller", "themes": ["choice"]})
    assert story.status_code == 200
    assert story.json()["format"] == "episode"
    assert story.json()["target_duration_minutes"] == 1
    assert len(story.json()["beats"]) == 5
    assert client.get(f"/api/projects/{project_id}/scope").json()["story_status"] == "aligned"

    changed = client.put(f"/api/projects/{project_id}/scope", json={"distribution_channel": "Theatrical / festival", "release_format": "feature_film", "aspect_ratio": "2.39:1", "width": 3840, "height": 1608, "target_duration_seconds": 6600, "installment_count": 1, "season_count": 1, "notes": "Expanded feature version"})
    assert changed.status_code == 200
    assert changed.json()["story_status"] == "review_needed"
    assert client.get(f"/api/projects/{project_id}").json()["story_brief"]["target_duration_minutes"] == 110

    assistant = client.post(f"/api/projects/{project_id}/assistant", json={"message": "How should I adapt this into a feature?", "page": "writer", "screen_context": {"heading": "Writer's Room", "selection": "Story Map"}})
    assert assistant.status_code == 200
    assert "Theatrical / festival" in assistant.json()["message"]["content"]
    assert "outline needs a deliberate adaptation pass" in assistant.json()["message"]["content"]
    assert len(client.get(f"/api/projects/{project_id}/assistant/messages").json()) == 2
    from app.main import master_dimensions
    vertical = type("VerticalTimeline", (), {"width": 1080, "height": 1920})()
    assert master_dimensions(vertical, "4k") == (2160, 3840)


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


def test_production_status_uses_saved_milestones_not_screen_visits(client):
    project_id = client.post("/api/projects", json={"title": "Honest Progress"}).json()["id"]
    initial = client.get(f"/api/projects/{project_id}/production-status")
    assert initial.status_code == 200
    stages = {item["key"]: item for item in initial.json()["stages"]}
    assert initial.json()["complete_count"] == 0
    assert stages["story"]["state"] == "ready"
    assert stages["style"]["state"] == "ready"
    assert stages["characters"]["state"] == "blocked"

    client.put(
        f"/api/projects/{project_id}/style",
        json={"era_primary": "1970s", "era_secondary": "2020s", "visual": {}, "direction": {}, "narrative": {}, "archetypes": []},
    )
    client.put(
        f"/api/projects/{project_id}/story",
        json={"premise": "A signal changes the city.", "format": "short film", "target_duration_minutes": 8, "audience": "general", "genre": "science fiction", "themes": ["connection"]},
    )
    updated = client.get(f"/api/projects/{project_id}/production-status").json()
    stages = {item["key"]: item for item in updated["stages"]}
    assert updated["complete_count"] == 2
    assert stages["story"]["state"] == "complete"
    assert stages["style"]["state"] == "complete"
    assert stages["characters"]["state"] == "ready"


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


def test_writer_bot_proposes_auditable_story_before_applying_it(client):
    project_id = client.post("/api/projects", json={"title": "Neon Pilgrim", "logline": "A shrine courier carries the last sunrise through an underground city."}).json()["id"]
    deployed = client.post(f"/api/projects/{project_id}/crew/deploy", json={"roles": ["writer"], "autonomy": "propose"})
    assert deployed.status_code == 200
    payload = {"premise": "A courier must deliver a captured sunrise before the city forgets daylight.", "format": "feature film", "target_duration_minutes": 96, "audience": "teen and adult", "genre": "science fantasy", "themes": ["memory", "chosen duty"], "objective": "Build a visual, emotionally decisive feature outline.", "provider": "simulation"}
    proposed = client.post(f"/api/projects/{project_id}/crew/writer/propose", json=payload)
    assert proposed.status_code == 201
    action = proposed.json()
    assert action["status"] == "proposed"
    assert action["payload"]["proposal"]["target_duration_minutes"] == 96
    assert len(action["payload"]["proposal"]["beats"]) == 12
    assert client.get(f"/api/projects/{project_id}").json()["story_brief"] is None

    approved = client.post(f"/api/crew-actions/{action['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    brief = client.get(f"/api/projects/{project_id}").json()["story_brief"]
    assert brief["format"] == "feature film"
    assert brief["themes"] == ["memory", "chosen duty"]
    providers = client.get("/api/writer/providers").json()
    assert providers["providers"][0]["ready"] is True
    assignment = deployed.json()["assignments"][0]
    client.put(f"/api/crew-assignments/{assignment['id']}", json={"enabled": True, "autonomy": "execute", "instructions": "Favor visual storytelling."})
    payload["target_duration_minutes"] = 97
    automatic = client.post(f"/api/projects/{project_id}/crew/writer/propose", json=payload)
    assert automatic.json()["status"] == "completed"
    assert client.get(f"/api/projects/{project_id}").json()["story_brief"]["target_duration_minutes"] == 97


def test_crew_modes_replace_active_departments_and_allow_manual_mode(client):
    project_id = client.post("/api/projects", json={"title": "Small Crew"}).json()["id"]
    deployed = client.post(
        f"/api/projects/{project_id}/crew/deploy",
        json={"roles": ["writer", "director"], "autonomy": "propose"},
    )
    assert deployed.status_code == 200
    assert {item["role"] for item in deployed.json()["assignments"] if item["enabled"]} == {"writer", "director"}

    manual = client.post(
        f"/api/projects/{project_id}/crew/deploy",
        json={"roles": [], "autonomy": "propose"},
    )
    assert manual.status_code == 200
    assert not any(item["enabled"] for item in manual.json()["assignments"])

    custom = client.post(
        f"/api/projects/{project_id}/crew/deploy",
        json={"roles": ["editor", "sound_producer"], "autonomy": "execute"},
    )
    enabled = [item for item in custom.json()["assignments"] if item["enabled"]]
    assert {item["role"] for item in enabled} == {"editor", "sound_producer"}
    assert all(item["autonomy"] == "execute" for item in enabled)


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


def test_visual_development_bots_apply_bibles_then_queue_generation(client):
    project_id = client.post("/api/projects", json={"title": "Paper Comet", "logline": "A courier crosses a city folded from forgotten letters."}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Iri", "role": "courier", "want": "Deliver the final letter", "need": "Accept being remembered", "contradiction": "Carries every story except her own"}).json()
    location = client.post(f"/api/projects/{project_id}/locations", json={"name": "Folded City", "narrative_function": "A maze that reveals memory", "description": "A dense city made from layered paper architecture.", "geography": "vertical river valley", "time_period": "dreamlike near future"}).json()
    deployed = client.post(f"/api/projects/{project_id}/crew/deploy", json={"roles": ["character_designer", "background_artist"], "autonomy": "propose"})
    assert deployed.status_code == 200

    character_action = client.post(f"/api/characters/{character['id']}/crew/design", json={"objective": "Make Iri readable in silhouette.", "provider": "simulation", "queue_generation": True, "generation_provider": "mock"})
    assert character_action.status_code == 201
    assert character_action.json()["status"] == "proposed"
    assert client.get(f"/api/projects/{project_id}").json()["characters"][0]["design"] is None
    character_applied = client.post(f"/api/crew-actions/{character_action.json()['id']}/approve")
    assert character_applied.json()["status"] == "completed"
    assert character_applied.json()["result"]["generation_status"] == "completed"
    assert character_applied.json()["result"]["generation_queued"] is True
    character_design = client.get(f"/api/projects/{project_id}").json()["characters"][0]["design"]
    assert len(character_design["consistency_anchors"]) == 5
    character_asset = character_applied.json()["result"]["generation_assets"][0]
    assert character_asset["mime_type"] == "image/svg+xml"
    assert client.get(character_asset["uri"]).status_code == 200
    assert "production reference sheet" in character_design["reference_brief"].lower()

    background_action = client.post(f"/api/locations/{location['id']}/crew/design", json={"objective": "Build reusable staging layers.", "provider": "simulation", "queue_generation": True, "generation_provider": "mock"})
    assert background_action.status_code == 201
    assert background_action.json()["status"] == "proposed"
    background_applied = client.post(f"/api/crew-actions/{background_action.json()['id']}/approve")
    assert background_applied.json()["status"] == "completed"
    assert background_applied.json()["result"]["generation_status"] == "completed"
    assert background_applied.json()["result"]["generation_assets"][0]["mime_type"] == "image/svg+xml"
    world = client.get(f"/api/projects/{project_id}").json()["locations"][0]["design"]
    assert len(world["layers"]) == 5
    assert len(world["lighting_variants"]) == 4
    assert client.get("/api/visual-development/providers").json()["providers"][0]["ready"] is True


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


def test_director_bot_proposes_and_applies_non_destructive_coverage(client):
    project_id = client.post("/api/projects", json={"title": "Quiet Orbit", "logline": "A mechanic follows a heartbeat through an abandoned station."}).json()["id"]
    client.put(f"/api/projects/{project_id}/story", json={"premise": "A mechanic must find the source of an impossible heartbeat.", "format": "short film", "target_duration_minutes": 10, "audience": "general", "genre": "science mystery", "themes": ["grief", "renewal"]})
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Noa", "role": "mechanic"}).json()
    location = client.post(f"/api/projects/{project_id}/locations", json={"name": "Silent Station", "description": "An abandoned orbital repair station."}).json()
    legacy_scene = client.post(f"/api/projects/{project_id}/scenes", json={"title": "Legacy scene", "summary": "Hand-built work to preserve.", "position": 99}).json()
    legacy_shot = client.post(f"/api/scenes/{legacy_scene['id']}/shots", json={"title": "Legacy shot", "position": 1, "duration_seconds": 2}).json()
    timeline = client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 12, "width": 320, "height": 180}).json()
    deployed = client.post(f"/api/projects/{project_id}/crew/deploy", json={"roles": ["director"], "autonomy": "propose"})
    assert deployed.status_code == 200

    proposed = client.post(f"/api/projects/{project_id}/crew/director/propose", json={"objective": "Create restrained coverage with strong geography.", "shots_per_beat": 2, "pacing": "restrained", "provider": "simulation"})
    assert proposed.status_code == 201
    action = proposed.json()
    assert action["status"] == "proposed"
    assert len(action["payload"]["proposal"]["scenes"]) == 8
    assert len(action["payload"]["proposal"]["scenes"][0]["shots"]) == 2
    assert client.get(f"/api/projects/{project_id}").json()["scenes"][0]["title"] == "Legacy scene"

    approved = client.post(f"/api/crew-actions/{action['id']}/approve")
    assert approved.status_code == 200
    result = approved.json()["result"]
    assert approved.json()["status"] == "completed"
    assert result["non_destructive"] is True
    assert result["timeline_needs_rebuild"] is True
    project = client.get(f"/api/projects/{project_id}").json()
    assert any(scene["id"] == legacy_scene["id"] for scene in project["scenes"])
    assert any(shot["id"] == legacy_shot["id"] for scene in project["scenes"] for shot in scene["shots"])
    directed = next(scene for scene in project["scenes"] if scene["position"] == 1)
    assert directed["shots"][0]["plan"]["location_id"] == location["id"]
    assert directed["shots"][0]["plan"]["character_ids"] == [character["id"]]
    assert directed["shots"][0]["plan"]["camera"]["shot_size"] == "wide"
    assert client.get(f"/api/projects/{project_id}/timeline").json()["status"] == "needs-rebuild"
    rebuilt = client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 12, "width": 320, "height": 180})
    assert rebuilt.json()["status"] == "draft"
    assert len(rebuilt.json()["clips"]) == sum(len(scene["shots"]) for scene in project["scenes"])
    assert client.get("/api/director/providers").json()["providers"][0]["ready"] is True


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


def test_audio_regions_split_duplicate_and_delete_non_destructively(client):
    project_id = client.post("/api/projects", json={"title": "Audio Cutting Room"}).json()["id"]
    scene_id = client.post(f"/api/projects/{project_id}/scenes", json={"title": "Pulse", "position": 1}).json()["id"]
    client.post(f"/api/scenes/{scene_id}/shots", json={"title": "Signal pulse", "position": 1, "duration_seconds": 1})
    timeline = client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 12, "width": 320, "height": 180}).json()
    track = client.post(f"/api/timelines/{timeline['id']}/audio/build").json()["tracks"][2]
    cue = client.post(f"/api/audio-tracks/{track['id']}/cues", json={"start_seconds": .1, "duration_seconds": .6, "text": "Radio pulse"}).json()
    source = client.post(f"/api/audio-cues/{cue['id']}/generate-scratch").json()

    split = client.post(f"/api/audio-cues/{cue['id']}/split", json={"split_seconds": .25})
    assert split.status_code == 200
    first, second = split.json()
    assert first["duration_seconds"] == .25
    assert second["start_seconds"] == .35
    assert second["duration_seconds"] == .35
    assert first["uri"] != second["uri"] != source["uri"]
    assert client.get(first["uri"]).headers["content-type"] == "audio/wav"
    assert client.get(second["uri"]).headers["content-type"] == "audio/wav"

    duplicate = client.post(f"/api/audio-cues/{second['id']}/duplicate", json={"offset_seconds": .2})
    assert duplicate.status_code == 201
    assert duplicate.json()["start_seconds"] == .55
    assert duplicate.json()["uri"] == second["uri"]
    assert client.delete(f"/api/audio-cues/{duplicate.json()['id']}").status_code == 204
    cues = client.get(f"/api/projects/{project_id}/audio-studio").json()["tracks"][2]["cues"]
    assert [item["id"] for item in cues] == [first["id"], second["id"]]


def test_ai_crew_delegates_and_approves_sound_producer_work(client):
    project_id = client.post("/api/projects", json={"title": "Delegated Signal"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Mika", "role": "radio operator"}).json()
    client.put(f"/api/characters/{character['id']}/voice", json={"provider": "simulation", "provider_voice_id": "coral", "direction_notes": "Quiet confidence."})
    scene_id = client.post(f"/api/projects/{project_id}/scenes", json={"title": "Contact", "position": 1}).json()["id"]
    client.post(f"/api/scenes/{scene_id}/shots", json={"title": "Mika responds", "position": 1, "duration_seconds": 1})
    timeline = client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 12, "width": 320, "height": 180}).json()
    studio = client.post(f"/api/timelines/{timeline['id']}/audio/build").json()
    cue = client.post(f"/api/audio-tracks/{studio['tracks'][0]['id']}/cues", json={"character_id": character["id"], "duration_seconds": 0.6, "text": "Kizuna, do you copy?", "direction": "A close-mic whisper."}).json()

    roles = client.get("/api/crew/roles")
    assert roles.status_code == 200
    assert {role["id"] for role in roles.json()} >= {"writer", "animator", "sound_producer", "editor"}
    deployed = client.post(f"/api/projects/{project_id}/crew/deploy", json={"roles": ["writer", "sound_producer"], "autonomy": "propose"})
    assert deployed.status_code == 200
    assert len(deployed.json()["assignments"]) == 2
    pronunciation = client.post(f"/api/projects/{project_id}/pronunciations", json={"character_id": character["id"], "term": "Kizuna", "pronunciation": "kee-zoo-nah"})
    assert pronunciation.status_code == 201

    proposed = client.post(f"/api/audio-cues/{cue['id']}/crew/generate-voice", json={"provider": "simulation"})
    assert proposed.status_code == 201
    assert proposed.json()["status"] == "proposed"
    approved = client.post(f"/api/crew-actions/{proposed.json()['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert approved.json()["result"]["provider"] == "simulation"
    assert client.get(approved.json()["result"]["uri"]).headers["content-type"] == "audio/wav"
    crew = client.get(f"/api/projects/{project_id}/crew").json()
    assert crew["actions"][0]["status"] == "completed"
    assert client.get("/api/voice/providers").json()["providers"][0]["ready"] is True


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

    export_plan = client.post(f"/api/timelines/{rebuilt_timeline['id']}/master-exports", json={"profile": "preview", "fps": 8, "segment_size": 1})
    assert export_plan.status_code == 201
    export = export_plan.json()
    assert export["total_segments"] == 2
    first_pass = client.post(f"/api/master-exports/{export['id']}/run-next").json()
    assert first_pass["completed_segments"] == 1
    assert first_pass["progress_percent"] == 50
    assert len(first_pass["segments"][0]["checksum_sha256"]) == 64
    resumed = client.post(f"/api/master-exports/{export['id']}/resume").json()
    assert resumed["completed_segments"] == 1
    finished = client.post(f"/api/master-exports/{export['id']}/run-all").json()
    assert finished["status"] == "segments-ready"
    assembled = client.post(f"/api/master-exports/{export['id']}/assemble")
    assert assembled.json()["status"] == "completed", assembled.json().get("error")
    assert client.get(assembled.json()["final_uri"]).headers["content-type"] == "video/mp4"

    held_plan = client.post(f"/api/timelines/{rebuilt_timeline['id']}/master-exports", json={"profile": "preview", "fps": 8, "segment_size": 2}).json()
    worker = client.post("/api/workers/register", headers={"X-Enrollment-Secret": "local-dev-enrollment"}, json={"name": "Master Worker", "hostname": "render-02", "supported_tasks": ["master_segment"]}).json()
    headers = {"Authorization": f"Bearer {worker['token']}"}
    assert client.post(f"/api/workers/{worker['id']}/master-segments/claim", headers=headers).status_code == 204
    farm_response = client.post(f"/api/timelines/{rebuilt_timeline['id']}/master-exports/distributed", json={"profile": "preview", "fps": 8, "segment_size": 2})
    assert farm_response.status_code == 201
    farm_plan = farm_response.json()
    assert farm_plan["status"] == "farm-queued"
    claimed = client.post(f"/api/workers/{worker['id']}/master-segments/claim", headers=headers)
    assert claimed.status_code == 200
    segment_id = claimed.json()["segment"]["id"]
    renewed = client.post(f"/api/workers/{worker['id']}/master-segments/{segment_id}/heartbeat", headers=headers)
    assert renewed.json()["status"] == "leased"
    retry = client.post(f"/api/workers/{worker['id']}/master-segments/{segment_id}/fail", headers=headers, json={"error": "temporary encoder failure", "retryable": True})
    assert retry.json()["status"] == "queued"
    claimed_again = client.post(f"/api/workers/{worker['id']}/master-segments/claim", headers=headers)
    assert claimed_again.json()["segment"]["id"] == segment_id
    assert claimed_again.json()["segment"]["attempts"] == 2
    artifact = client.get(assembled.json()["final_uri"]).content
    uploaded = client.put(f"/api/workers/{worker['id']}/master-segments/{segment_id}/artifact", headers={**headers, "Content-Type": "video/mp4"}, content=artifact)
    assert uploaded.json()["status"] == "completed"
    assert len(uploaded.json()["checksum_sha256"]) == 64
    completed_farm = client.get(f"/api/master-exports/{farm_plan['id']}").json()
    assert completed_farm["status"] == "completed", completed_farm.get("error")
    assert client.get(completed_farm["final_uri"]).headers["content-type"] == "video/mp4"
    dispatched = client.post(f"/api/master-exports/{held_plan['id']}/dispatch").json()
    assert dispatched["status"] == "farm-queued"
    farm = client.get("/api/render-farm/status").json()
    assert any(segment["id"] == segment_id and segment["status"] == "completed" for segment in farm["master_segments"])


def test_animator_bot_applies_editable_motion_and_renders_preview(client):
    project_id = client.post("/api/projects", json={"title": "Motion Thread"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Sora", "role": "signal runner"}).json()
    location = client.post(f"/api/projects/{project_id}/locations", json={"name": "Relay Roof"}).json()
    scene_id = client.post(f"/api/projects/{project_id}/scenes", json={"title": "The Reply", "position": 1}).json()["id"]
    shot = client.post(f"/api/scenes/{scene_id}/shots", json={"title": "Sora hears the signal", "position": 1, "duration_seconds": 0.5}).json()
    client.put(f"/api/shots/{shot['id']}/plan", json={"location_id": location["id"], "character_ids": [character["id"]], "action": "Sora stops, listens, and looks up.", "camera": {"movement": "slow push"}, "continuity_notes": "Keep Sora screen-left."})
    client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 4, "width": 160, "height": 90})
    deployed = client.post(f"/api/projects/{project_id}/crew/deploy", json={"roles": ["animator"], "autonomy": "propose"})
    assert deployed.status_code == 200

    proposed = client.post(f"/api/shots/{shot['id']}/crew/animate", json={"objective": "Make the listening beat readable with restrained motion.", "provider": "simulation", "render_preview": True, "quality": "proxy", "fps": 4})
    assert proposed.status_code == 201
    assert proposed.json()["status"] == "proposed"
    assert len(proposed.json()["payload"]["proposal"]["layer_motions"]) == 2
    assert client.get(f"/api/shots/{shot['id']}/composition").status_code == 404

    approved = client.post(f"/api/crew-actions/{proposed.json()['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert approved.json()["result"]["preview_status"] == "completed", approved.json()["result"].get("preview_error")
    assert client.get(approved.json()["result"]["preview_uri"]).headers["content-type"] == "video/mp4"
    composition = client.get(f"/api/shots/{shot['id']}/composition").json()
    assert composition["camera"]["end_scale"] == 1.08
    assert all(layer["animation"]["intent"] for layer in composition["layers"])
    assert composition["latest_motion_uri"] == approved.json()["result"]["preview_uri"]
    assert client.get("/api/animation/providers").json()["providers"][0]["ready"] is True


def test_editor_bot_assembles_timeline_then_renders_review_master(client):
    project_id = client.post("/api/projects", json={"title": "Cut Thread"}).json()["id"]
    first_scene = client.post(f"/api/projects/{project_id}/scenes", json={"title": "Before", "position": 1}).json()
    second_scene = client.post(f"/api/projects/{project_id}/scenes", json={"title": "After", "position": 2}).json()
    first = client.post(f"/api/scenes/{first_scene['id']}/shots", json={"title": "The held breath", "position": 1, "duration_seconds": 0.5}).json()
    second = client.post(f"/api/scenes/{second_scene['id']}/shots", json={"title": "The answer", "position": 1, "duration_seconds": 0.5}).json()
    client.put(f"/api/shots/{first['id']}/plan", json={"action": "A hand stops above the receiver.", "camera": {"movement": "locked"}})
    client.put(f"/api/shots/{second['id']}/plan", json={"action": "The receiver lights.", "dialogue": "I hear you.", "camera": {"movement": "slow push"}})
    client.post(f"/api/projects/{project_id}/crew/deploy", json={"roles": ["editor"], "autonomy": "propose"})

    proposed = client.post(f"/api/projects/{project_id}/crew/editor/propose", json={"objective": "Build the first emotional assembly.", "pacing": "kinetic", "provider": "simulation"})
    assert proposed.status_code == 201
    assert proposed.json()["status"] == "proposed"
    assert len(proposed.json()["payload"]["proposal"]["clips"]) == 2
    assert client.get(f"/api/projects/{project_id}/timeline").status_code == 404
    approved = client.post(f"/api/crew-actions/{proposed.json()['id']}/approve")
    assert approved.json()["status"] == "completed"
    timeline = client.get(f"/api/projects/{project_id}/timeline").json()
    assert timeline["status"] == "edit-ready"
    assert [clip["shot_id"] for clip in timeline["clips"]] == [first["id"], second["id"]]

    client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 4, "width": 160, "height": 90})
    review = client.post(f"/api/projects/{project_id}/crew/editor/propose", json={"objective": "Prepare a balanced review cut.", "pacing": "balanced", "provider": "simulation", "render_review": True, "review_profile": "preview"})
    assert review.json()["payload"]["proposal"]["clips"][1]["transition"] == "dissolve"
    rendered = client.post(f"/api/crew-actions/{review.json()['id']}/approve")
    assert rendered.json()["result"]["review_status"] == "completed", rendered.json()["result"].get("review_error")
    assert client.get(rendered.json()["result"]["review_uri"]).headers["content-type"] == "video/mp4"
    assert rendered.json()["result"]["review_settings"]["fallback_clips"] == 2
    assert client.get("/api/editing/providers").json()["providers"][0]["ready"] is True


def test_producer_workflow_routes_deployed_bots_and_resumes_after_approval(client):
    project_id = client.post("/api/projects", json={"title": "Producer Thread", "logline": "A signal reunites a divided city."}).json()["id"]
    client.post(f"/api/projects/{project_id}/characters", json={"name": "Mina", "role": "relay keeper"})
    client.post(f"/api/projects/{project_id}/locations", json={"name": "Signal Tower", "narrative_function": "The city hears itself again"})
    roles = ["writer", "character_designer", "background_artist", "director", "animator", "editor", "sound_producer"]
    client.post(f"/api/projects/{project_id}/crew/deploy", json={"roles": roles, "autonomy": "propose"})
    started = client.post(f"/api/projects/{project_id}/producer/workflow", json={"objective": "Coordinate a reviewable short film.", "provider": "simulation", "render_motion_previews": False})
    assert started.status_code == 200
    workflow = started.json()
    assert workflow["current_stage"] == "story"
    assert workflow["stages"][0]["status"] == "ready"
    workflow_id = workflow["id"]

    writing = client.post(f"/api/producer-workflows/{workflow_id}/advance")
    assert writing.status_code == 200
    assert writing.json()["status"] == "awaiting_approval"
    writer_action_id = writing.json()["last_action_id"]
    crew = client.get(f"/api/projects/{project_id}/crew").json()
    writer_action = next(item for item in crew["actions"] if item["id"] == writer_action_id)
    assert writer_action["role"] == "writer"
    assert client.post(f"/api/producer-workflows/{workflow_id}/advance").status_code == 409
    client.post(f"/api/crew-actions/{writer_action_id}/approve")

    resumed = client.get(f"/api/projects/{project_id}/producer/workflow").json()
    assert resumed["current_stage"] == "cast"
    character_step = client.post(f"/api/producer-workflows/{workflow_id}/advance").json()
    client.post(f"/api/crew-actions/{character_step['last_action_id']}/approve")
    assert client.get(f"/api/projects/{project_id}/producer/workflow").json()["current_stage"] == "worlds"

    background_step = client.post(f"/api/producer-workflows/{workflow_id}/advance").json()
    client.post(f"/api/crew-actions/{background_step['last_action_id']}/approve")
    directing = client.post(f"/api/producer-workflows/{workflow_id}/advance").json()
    assert directing["current_stage"] == "direction"
    assert directing["status"] == "awaiting_approval"
    director_action = next(item for item in client.get(f"/api/projects/{project_id}/crew").json()["actions"] if item["id"] == directing["last_action_id"])
    assert director_action["role"] == "director"


def test_asset_reviews_select_compare_and_rollback_without_deleting_versions(client):
    project_id = client.post("/api/projects", json={"title": "Review Thread"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Ari", "role": "pilot"}).json()
    location = client.post(f"/api/projects/{project_id}/locations", json={"name": "Listening Hall"}).json()
    client.put(f"/api/characters/{character['id']}/design", json={"appearance": {"silhouette": "long coat"}, "palette": ["charcoal"], "wardrobe": ["flight coat"], "consistency_anchors": ["red collar"]})
    client.put(f"/api/locations/{location['id']}/design", json={"appearance": {"architecture": "orbital rings"}, "palette": ["amber"], "layers": ["deck", "planet"], "lighting_variants": ["dawn"], "continuity_anchors": ["broken antenna"]})
    character_v1 = client.post(f"/api/characters/{character['id']}/generate", json={"provider": "mock", "seed": 1}).json()["assets"][0]
    character_v2 = client.post(f"/api/characters/{character['id']}/generate", json={"provider": "mock", "seed": 2}).json()["assets"][0]
    background_v1 = client.post(f"/api/locations/{location['id']}/generate", json={"provider": "mock", "seed": 1}).json()["assets"][0]
    background_v2 = client.post(f"/api/locations/{location['id']}/generate", json={"provider": "mock", "seed": 2}).json()["assets"][0]
    scene = client.post(f"/api/projects/{project_id}/scenes", json={"title": "Contact", "position": 1}).json()
    shot = client.post(f"/api/scenes/{scene['id']}/shots", json={"title": "Ari listens", "position": 1, "duration_seconds": 1}).json()
    client.put(f"/api/shots/{shot['id']}/plan", json={"location_id": location["id"], "character_ids": [character["id"]], "action": "Ari listens.", "camera": {"movement": "locked"}})
    storyboard_v1 = client.post(f"/api/shots/{shot['id']}/storyboard", json={"provider": "mock", "seed": 1}).json()["assets"][0]
    storyboard_v2 = client.post(f"/api/shots/{shot['id']}/storyboard", json={"provider": "mock", "seed": 2}).json()["assets"][0]

    review = client.get(f"/api/projects/{project_id}/asset-reviews").json()
    assert len(review["assets"]) == 6
    assert review["pending"] == 6
    for asset_type, asset in (("character", character_v1), ("background", background_v1), ("storyboard", storyboard_v1)):
        selected = client.put(f"/api/assets/{asset_type}/{asset['id']}/review", json={"status": "approved", "notes": "Approved continuity master", "selected": True})
        assert selected.status_code == 200
        assert selected.json()["active"] is True

    client.post(f"/api/projects/{project_id}/timeline/build", json={"fps": 8, "width": 320, "height": 180})
    composition = client.post(f"/api/shots/{shot['id']}/composition/build").json()
    assert [layer["source_asset_id"] for layer in composition["layers"]] == [background_v1["id"], character_v1["id"]]
    assert client.get(f"/api/projects/{project_id}/timeline").json()["clips"][0]["storyboard_uri"] == storyboard_v1["uri"]

    switched = client.put(f"/api/assets/character/{character_v2['id']}/review", json={"status": "approved", "notes": "Try alternate", "selected": True}).json()
    assert composition["id"] in switched["affected_compositions"]
    updated = client.get(f"/api/shots/{shot['id']}/composition").json()
    assert updated["version"] == composition["version"] + 1
    assert updated["layers"][1]["source_asset_id"] == character_v2["id"]

    rollback = client.put(f"/api/assets/character/{character_v1['id']}/review", json={"status": "approved", "notes": "Rollback to approved master", "selected": True}).json()
    assert rollback["selected"] is True
    rolled_back = client.get(f"/api/shots/{shot['id']}/composition").json()
    assert rolled_back["version"] == updated["version"] + 1
    assert rolled_back["layers"][1]["source_asset_id"] == character_v1["id"]
    assert len(client.get(f"/api/projects/{project_id}/asset-reviews").json()["assets"]) == 6
    assert background_v2["id"] != background_v1["id"] and storyboard_v2["id"] != storyboard_v1["id"]


def test_character_story_profile_and_relationships_are_editable(client):
    project_id = client.post("/api/projects", json={"title": "Two Lights"}).json()["id"]
    ari = client.post(f"/api/projects/{project_id}/characters", json={"name": "Ari", "role": "protector"}).json()
    mika = client.post(f"/api/projects/{project_id}/characters", json={"name": "Mika", "role": "witness"}).json()
    profile_payload = {"history": "Raised aboard the listening station.", "formative_event": "Survived the first signal.", "secret": "Recognizes the voice.", "fear": "Losing the crew.", "misbelief": "Control keeps everyone safe.", "arc_start": "Refuses help.", "arc_turn": "Trusts Mika with the signal.", "arc_end": "Shares responsibility.", "stakes": "The station and Ari's identity."}
    profile = client.put(f"/api/characters/{ari['id']}/story-profile", json=profile_payload)
    assert profile.status_code == 200
    assert profile.json()["version"] == 1
    assert client.get(f"/api/characters/{ari['id']}/story-profile").json()["secret"] == "Recognizes the voice."
    assert client.put(f"/api/characters/{ari['id']}/story-profile", json=profile_payload).json()["version"] == 2

    relationship = client.put(f"/api/characters/{ari['id']}/relationships", json={"target_character_id": mika["id"], "relationship_type": "uneasy ally", "public_dynamic": "Professional distance", "private_truth": "Ari trusts Mika most", "tension": "They disagree about revealing the signal", "arc": "Suspicion becomes partnership"})
    assert relationship.status_code == 200
    assert relationship.json()["target_name"] == "Mika"
    listed = client.get(f"/api/characters/{ari['id']}/relationships").json()
    assert len(listed) == 1 and listed[0]["arc"] == "Suspicion becomes partnership"
    assert client.delete(f"/api/character-relationships/{relationship.json()['id']}").status_code == 204
    assert client.get(f"/api/characters/{ari['id']}/relationships").json() == []


def test_project_backups_retention_and_expiring_delivery_links(client, monkeypatch):
    import shutil
    from pathlib import Path
    import app.main as main_module
    from app.storage import LocalProductionStorage

    storage_path = Path("work/test-production-storage").resolve()
    if storage_path.exists():
        shutil.rmtree(storage_path)
    monkeypatch.setattr(main_module, "production_storage", LocalProductionStorage(storage_path))
    project_id = client.post("/api/projects", json={"title": "Archive Test"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Ari"}).json()
    client.put(f"/api/characters/{character['id']}/design", json={"appearance": {"silhouette": "long coat"}, "consistency_anchors": ["red collar"]})
    asset = client.post(f"/api/characters/{character['id']}/generate", json={"provider": "mock", "seed": 9}).json()["assets"][0]
    policy = client.put(f"/api/projects/{project_id}/storage-policy", json={"retention_days": 30, "max_backups": 1, "include_media": True})
    assert policy.json()["backend"] == "local"

    first = client.post(f"/api/projects/{project_id}/backups").json()
    second = client.post(f"/api/projects/{project_id}/backups").json()
    backups = client.get(f"/api/projects/{project_id}/backups").json()
    assert [item["id"] for item in backups] == [second["id"]]
    assert backups[0]["backend"] == "local"
    assert second["asset_count"] == 1
    assert len(second["checksum_sha256"]) == 64
    assert client.get(second["download_url"]).headers["content-type"] == "application/zip"
    assert client.get(f"/api/backups/{first['id']}/download").status_code == 404

    scheduled = client.put(f"/api/projects/{project_id}/backup-schedule", json={"enabled": True, "interval_hours": 24})
    assert scheduled.status_code == 200
    from datetime import timedelta
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import BackupSchedule
    with SessionLocal() as db:
        schedule = db.scalar(select(BackupSchedule).where(BackupSchedule.project_id == project_id))
        schedule.next_run_at = main_module.utcnow() - timedelta(minutes=1); db.commit()
        result = main_module.run_due_backups(db)
    assert result == {"due": 1, "completed": 1, "failed": 0}
    assert client.get(f"/api/projects/{project_id}/backup-schedule").json()["last_status"] == "completed"

    delivery = client.post(f"/api/projects/{project_id}/delivery-links", json={"asset_uri": asset["uri"], "label": "Studio review", "expires_hours": 24, "max_downloads": 1})
    assert delivery.status_code == 201
    url = delivery.json()["url"]
    assert client.get(url).status_code == 200
    assert client.get(url).status_code == 410
    revoked = client.post(f"/api/delivery-links/{delivery.json()['id']}/revoke")
    assert revoked.json()["revoked"] is True
    shutil.rmtree(storage_path)


def test_s3_compatible_storage_upload_download_and_delete():
    from pathlib import Path
    import shutil
    from app.storage import S3ProductionStorage

    class FakeS3:
        def __init__(self): self.objects = {}
        def upload_file(self, source, bucket, key, ExtraArgs=None): self.objects[(bucket, key)] = Path(source).read_bytes()
        def delete_object(self, Bucket, Key): self.objects.pop((Bucket, Key), None)
        def generate_presigned_url(self, method, Params, ExpiresIn): return f"https://vault.test/{Params['Key']}?expires={ExpiresIn}"
        def head_bucket(self, Bucket): return {"bucket": Bucket}

    temp_path = Path("work/test-s3-storage").resolve()
    if temp_path.exists(): shutil.rmtree(temp_path)
    temp_path.mkdir(parents=True)
    client = FakeS3(); storage = S3ProductionStorage("studio-vault", "https://s3.example", "auto", "productions", client=client)
    asset = temp_path / "frame.png"; asset.write_bytes(b"frame")
    key, size, checksum, count = storage.create_backup(7, "project.zip", {"project": {"title": "Signal"}}, [asset])
    assert ("studio-vault", f"productions/{key}") in client.objects
    assert size > 0 and len(checksum) == 64 and count == 1
    assert storage.presigned_download(key, "project.zip", 300).endswith("expires=300")
    assert storage.test_connection() == (True, "Off-server storage is ready.")
    storage.delete(key)
    assert client.objects == {}
    shutil.rmtree(temp_path)


def test_media_index_keeps_thumbnails_and_tracks_hive_originals(client, monkeypatch):
    import shutil
    from pathlib import Path
    import app.main as main_module

    thumbnail_root = Path("work/test-media-thumbnails").resolve()
    if thumbnail_root.exists(): shutil.rmtree(thumbnail_root)
    thumbnail_root.mkdir(parents=True)
    monkeypatch.setattr(main_module, "thumbnail_dir", thumbnail_root)
    project_id = client.post("/api/projects", json={"title": "Local First Media"}).json()["id"]
    character = client.post(f"/api/projects/{project_id}/characters", json={"name": "Mika"}).json()
    client.put(f"/api/characters/{character['id']}/design", json={"appearance": {"silhouette": "radio coat"}, "consistency_anchors": ["blue headset"]})
    generated = client.post(f"/api/characters/{character['id']}/generate", json={"provider": "mock", "seed": 41}).json()
    index = client.get(f"/api/projects/{project_id}/media-index")
    assert index.status_code == 200
    media = index.json(); item = next(entry for entry in media["assets"] if entry["source_kind"] == "media_asset")
    assert media["summary"]["server_original_bytes"] > 0
    assert media["summary"]["lightweight_server_bytes"] > 0
    assert item["preview_uri"].startswith("/api/media/thumbnails/")
    assert client.get(item["preview_uri"]).headers["content-type"] in {"image/jpeg", "image/svg+xml"}

    enrollment = client.post("/api/settings/compute/enrollment").json()
    profile = {"code": enrollment["code"], "node_key": "media-node-0001", "name": "Creator Workstation", "os_name": "Linux", "architecture": "x86_64", "logical_cores": 12, "ram_gb": 32, "capabilities": ["video_encode"]}
    enrolled = client.post("/api/nodes/enroll", json=profile).json(); headers = {"Authorization": f"Bearer {enrolled['token']}"}
    original = next(place for place in item["residencies"] if place["representation"] == "original" and place["backend"] == "server")
    registered = client.post(f"/api/nodes/media-node-0001/projects/{project_id}/media-residencies", headers=headers, json={"items": [{"asset_key": item["asset_key"], "representation": "original", "object_ref": "vault://mika-reference-v1", "checksum_sha256": original["checksum_sha256"], "size_bytes": original["size_bytes"], "status": "available"}]})
    assert registered.json()["registered"] == 1
    policy = client.put(f"/api/projects/{project_id}/media-storage-policy", json={"original_strategy": "hive", "preferred_node_key": "media-node-0001", "keep_server_proxies": True, "thumbnail_width": 480, "proxy_width": 1280, "minimum_replicas": 1, "evict_server_originals": True})
    assert policy.status_code == 200
    refreshed = client.get(f"/api/projects/{project_id}/media-index").json()
    assert refreshed["summary"]["hive_original_bytes"] == original["size_bytes"]
    assert refreshed["summary"]["hive_assets"] == 1
    assert client.get(generated["assets"][0]["uri"]).status_code == 200
    shutil.rmtree(thumbnail_root)
