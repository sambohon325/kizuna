from fastapi.testclient import TestClient

from app.auth import hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Character, Project, ProjectMembership, User


def setup_admin(client, monkeypatch):
    monkeypatch.setattr("app.main.settings.auth_required", True)
    monkeypatch.setattr("app.main.settings.bootstrap_admin_key", "one-time-studio-key")
    monkeypatch.setattr("app.main.settings.cookie_secure", False)
    response = client.post("/api/auth/setup", json={"email": "owner@example.com", "display_name": "Studio Owner", "password": "long-secure-password", "bootstrap_key": "one-time-studio-key"})
    assert response.status_code == 200
    return client.cookies.get("kizuna_csrf")


def test_first_admin_setup_sessions_and_csrf(client, monkeypatch):
    monkeypatch.setattr("app.main.settings.auth_required", True)
    monkeypatch.setattr("app.main.settings.bootstrap_admin_key", "one-time-studio-key")
    monkeypatch.setattr("app.main.settings.cookie_secure", False)
    assert client.get("/api/projects").status_code == 401
    assert client.get("/", follow_redirects=False).headers["location"] == "/setup"
    denied = client.post("/api/auth/setup", json={"email": "owner@example.com", "display_name": "Owner", "password": "long-secure-password", "bootstrap_key": "wrong"})
    assert denied.status_code == 403
    csrf = setup_admin(client, monkeypatch)
    assert client.get("/api/auth/me").json()["role"] == "admin"
    assert client.post("/api/projects", json={"title": "No CSRF", "logline": ""}).status_code == 403
    created = client.post("/api/projects", headers={"X-Kizuna-CSRF": csrf}, json={"title": "Private Production", "logline": "Only its members can open it."})
    assert created.status_code == 201
    assert client.post("/api/auth/setup", json={"email": "other@example.com", "display_name": "Other", "password": "another-secure-password", "bootstrap_key": "one-time-studio-key"}).status_code == 409


def test_productions_are_isolated_by_membership(client, monkeypatch):
    csrf = setup_admin(client, monkeypatch)
    private = client.post("/api/projects", headers={"X-Kizuna-CSRF": csrf}, json={"title": "Owner Project", "logline": "private"}).json()
    with SessionLocal() as db:
        creator = User(email="creator@example.com", display_name="Second Creator", password_hash=hash_password("another-secure-password"), role="creator")
        other_project = Project(title="Creator Project", logline="separate")
        db.add_all([creator, other_project]); db.flush()
        db.add(ProjectMembership(project_id=other_project.id, user_id=creator.id, role="owner")); db.commit()
        other_project_id = other_project.id
        owner_character = Character(project_id=private["id"], name="Private Character")
        db.add(owner_character); db.commit(); owner_character_id = owner_character.id
    second = TestClient(app)
    signed_in = second.post("/api/auth/login", json={"email": "creator@example.com", "password": "another-secure-password"})
    assert signed_in.status_code == 200
    assert second.get(f"/api/projects/{private['id']}").status_code == 404
    assert second.put(f"/api/characters/{owner_character_id}", headers={"X-Kizuna-CSRF": second.cookies.get("kizuna_csrf")}, json={"name": "Intrusion", "role": "protagonist", "want": "", "need": "", "contradiction": ""}).status_code == 404
    visible = second.get("/api/projects").json()
    assert [item["id"] for item in visible] == [other_project_id]
    assert second.get(f"/api/projects/{other_project_id}").status_code == 200
    assert second.get("/api/settings/integrations").status_code == 403
