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
