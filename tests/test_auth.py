from fastapi.testclient import TestClient
from urllib.parse import urlparse

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


def test_invitations_roles_and_session_revocation(client, monkeypatch):
    csrf = setup_admin(client, monkeypatch)
    project = client.post("/api/projects", headers={"X-Kizuna-CSRF": csrf}, json={"title": "Shared Production", "logline": "Role protected"}).json()
    invited = client.post("/api/settings/team/invitations", headers={"X-Kizuna-CSRF": csrf}, json={"email": "viewer@example.com", "display_name": "Review Partner", "project_access": [{"project_id": project["id"], "role": "viewer"}]})
    assert invited.status_code == 201
    invite_path = urlparse(invited.json()["acceptance_url"]).path
    viewer = TestClient(app)
    assert viewer.get(invite_path.replace("/invite/", "/api/auth/invitations/")).status_code == 200
    accepted = viewer.post(invite_path.replace("/invite/", "/api/auth/invitations/"), json={"display_name": "Review Partner", "password": "viewer-secure-password"})
    assert accepted.status_code == 200
    viewer_csrf = viewer.cookies.get("kizuna_csrf")
    assert viewer.get(f"/api/projects/{project['id']}").status_code == 200
    blocked = viewer.post(f"/api/projects/{project['id']}/characters", headers={"X-Kizuna-CSRF": viewer_csrf}, json={"name": "Blocked Edit", "role": "protagonist", "want": "", "need": "", "contradiction": ""})
    assert blocked.status_code == 403
    viewer_id = accepted.json()["id"]
    promoted = client.put(f"/api/settings/team/projects/{project['id']}/members/{viewer_id}", headers={"X-Kizuna-CSRF": csrf}, json={"role": "editor"})
    assert promoted.status_code == 200
    allowed = viewer.post(f"/api/projects/{project['id']}/characters", headers={"X-Kizuna-CSRF": viewer_csrf}, json={"name": "Allowed Edit", "role": "protagonist", "want": "", "need": "", "contradiction": ""})
    assert allowed.status_code == 201
    sessions = viewer.get("/api/auth/sessions").json()
    assert len(sessions) == 1 and sessions[0]["current"] is True
    assert viewer.delete(f"/api/auth/sessions/{sessions[0]['id']}", headers={"X-Kizuna-CSRF": viewer_csrf}).status_code == 204
    assert viewer.get("/api/auth/me").status_code == 401
