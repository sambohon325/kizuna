import os

os.environ["KIZUNA_MARKETING_DATABASE_URL"] = "sqlite:///./test_marketing.db"
os.environ["KIZUNA_MARKETING_ADMIN_PASSWORD"] = "marketing-test-password"
os.environ["KIZUNA_MARKETING_SESSION_SECRET"] = "marketing-test-session-secret"
os.environ["KIZUNA_MARKETING_COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient

from marketing.main import Base, engine, app


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def admin_client() -> tuple[TestClient, str]:
    client = TestClient(app)
    response = client.post("/api/admin/login", json={"password": "marketing-test-password"})
    assert response.status_code == 200
    return client, response.json()["csrf"]


def test_blog_drafts_and_publishing():
    client, csrf = admin_client()
    draft = client.post("/api/admin/posts", headers={"X-Kizuna-CSRF": csrf}, json={"title": "Building Kizuna carefully", "excerpt": "A studio development note.", "body": "This is a sufficiently long first paragraph.\n\n## What comes next\n\nThe work continues.", "status": "draft", "featured": True})
    assert draft.status_code == 201
    assert client.get("/api/blog").json() == []
    post = draft.json()
    published = client.put(f"/api/admin/posts/{post['id']}", headers={"X-Kizuna-CSRF": csrf}, json={"title": post["title"], "slug": post["slug"], "excerpt": post["excerpt"], "body": post["body"], "author": post["author"], "category": post["category"], "status": "published", "featured": True})
    assert published.status_code == 200
    public = client.get("/api/blog").json()
    assert len(public) == 1 and "body" not in public[0]
    article = client.get(f"/api/blog/{post['slug']}").json()
    assert article["body"].startswith("This is")
    assert client.post("/api/admin/posts", json={"title": "No CSRF", "body": "This body is long enough to validate."}).status_code == 403


def test_beta_applications_and_ticket_triage():
    public = TestClient(app)
    beta_payload = {"name": "Beta Creator", "email": "creator@example.com", "creator_type": "Independent creator", "experience": "beginner", "project_summary": "An original short about memory and a disappearing city.", "desired_outcome": "Test the guided workflow.", "hardware": "Windows"}
    assert public.post("/api/beta", json=beta_payload).status_code == 201
    assert public.post("/api/beta", json=beta_payload).status_code == 201
    ticket = public.post("/api/tickets", json={"email": "creator@example.com", "category": "bug", "severity": "high", "subject": "Timeline cannot open", "description": "I opened the production timeline after creating shots and received an empty workspace.", "page_url": "/timeline", "environment": "Windows 11 · Chrome"})
    assert ticket.status_code == 201
    assert ticket.json()["reference"].startswith("KZ-")

    admin, csrf = admin_client()
    overview = admin.get("/api/admin/overview").json()
    assert len(overview["beta"]) == 1
    assert len(overview["tickets"]) == 1
    application_id = overview["beta"][0]["id"]
    ticket_id = overview["tickets"][0]["id"]
    assert admin.put(f"/api/admin/beta/{application_id}", headers={"X-Kizuna-CSRF": csrf}, json={"status": "reviewing", "notes": "Strong guided-flow candidate."}).status_code == 200
    assert admin.put(f"/api/admin/tickets/{ticket_id}", headers={"X-Kizuna-CSRF": csrf}, json={"status": "investigating", "notes": "Reproduce against an empty timeline."}).status_code == 200
    assert admin.put(f"/api/admin/beta/{application_id}", headers={"X-Kizuna-CSRF": csrf}, json={"status": "resolved", "notes": "Wrong queue state."}).status_code == 422
    assert admin.put(f"/api/admin/tickets/{ticket_id}", headers={"X-Kizuna-CSRF": csrf}, json={"status": "invited", "notes": "Wrong queue state."}).status_code == 422
    updated = admin.get("/api/admin/overview").json()
    assert updated["beta"][0]["status"] == "reviewing"
    assert updated["tickets"][0]["status"] == "investigating"


def test_public_config_and_admin_protection():
    client = TestClient(app)
    health = client.get("/health")
    assert health.json() == {"status": "ok"}
    assert health.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors" in health.headers["content-security-policy"]
    assert "app.kizuna.com" in client.get("/config.js").text
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/does-not-exist").status_code == 404
    assert client.get("/admin").status_code == 200
    assert client.get("/blog/a-future-post").status_code == 200
