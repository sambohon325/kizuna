import os

os.environ["KIZUNA_MARKETING_DATABASE_URL"] = "sqlite:///./test_marketing.db"
os.environ["KIZUNA_MARKETING_ADMIN_PASSWORD"] = "marketing-test-password"
os.environ["KIZUNA_MARKETING_SESSION_SECRET"] = "marketing-test-session-secret"
os.environ["KIZUNA_MARKETING_COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient

from marketing.main import Base, attempts, engine, app


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    attempts.clear()


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


def test_editorial_studio_builds_fact_grounded_campaigns_and_gates_claims():
    client, csrf = admin_client()
    educational = {
        "brief_title": "Why Kizuna Help answers show their sources",
        "content_type": "education",
        "approved_facts": "The Help Agent searches a curated set of published Kizuna manuals.\nEach grounded answer includes source sections.\nIt reports when the library does not contain an answer.",
        "audience": "Creators learning the Kizuna workflow",
        "goal": "Explain how grounded help reduces confusion without inventing product instructions.",
        "call_to_action": "Explore the Help Center at kizuna.technology.",
    }
    created = client.post("/api/admin/editorial/campaigns", headers={"X-Kizuna-CSRF": csrf}, json=educational)
    assert created.status_code == 201
    campaign = created.json()
    assert campaign["status"] == "prepared"
    assert set(campaign["social_variants"]) == {"x", "linkedin", "instagram", "tiktok", "youtube"}
    assert client.post(f"/api/admin/editorial/campaigns/{campaign['id']}/journal-draft", headers={"X-Kizuna-CSRF": csrf}).status_code == 409
    approved = client.post(f"/api/admin/editorial/campaigns/{campaign['id']}/approve", headers={"X-Kizuna-CSRF": csrf})
    assert approved.json()["status"] == "approved"
    journal = client.post(f"/api/admin/editorial/campaigns/{campaign['id']}/journal-draft", headers={"X-Kizuna-CSRF": csrf})
    assert journal.status_code == 200
    assert journal.json()["status"] == "draft"
    assert client.get("/api/blog").json() == []

    sensitive = client.post("/api/admin/editorial/campaigns", headers={"X-Kizuna-CSRF": csrf}, json={**educational, "brief_title": "New partnership pricing launch", "content_type": "partnership"})
    assert sensitive.status_code == 201
    assert sensitive.json()["status"] == "needs_review"
    confidential = client.post("/api/admin/editorial/campaigns", headers={"X-Kizuna-CSRF": csrf}, json={**educational, "brief_title": "Internal only unannounced work", "approved_facts": "This confidential roadmap item is internal only and must not be announced publicly."})
    assert confidential.status_code == 201
    assert confidential.json()["status"] == "blocked"
    assert client.post(f"/api/admin/editorial/campaigns/{confidential.json()['id']}/approve", headers={"X-Kizuna-CSRF": csrf}).status_code == 409


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
    assert len(overview["ops"]) == 2
    assert all(item["agent"] in {"Beta Coordinator", "Support Concierge"} for item in overview["ops"])
    application_id = overview["beta"][0]["id"]
    ticket_id = overview["tickets"][0]["id"]
    assert admin.put(f"/api/admin/beta/{application_id}", headers={"X-Kizuna-CSRF": csrf}, json={"status": "reviewing", "notes": "Strong guided-flow candidate."}).status_code == 200
    assert admin.put(f"/api/admin/tickets/{ticket_id}", headers={"X-Kizuna-CSRF": csrf}, json={"status": "investigating", "notes": "Reproduce against an empty timeline."}).status_code == 200
    assert admin.put(f"/api/admin/beta/{application_id}", headers={"X-Kizuna-CSRF": csrf}, json={"status": "resolved", "notes": "Wrong queue state."}).status_code == 422
    assert admin.put(f"/api/admin/tickets/{ticket_id}", headers={"X-Kizuna-CSRF": csrf}, json={"status": "invited", "notes": "Wrong queue state."}).status_code == 422
    updated = admin.get("/api/admin/overview").json()
    assert updated["beta"][0]["status"] == "reviewing"
    assert updated["tickets"][0]["status"] == "investigating"


def test_ops_desk_escalates_sensitive_work_and_can_send_an_approved_reply(monkeypatch):
    public = TestClient(app)
    ticket = public.post("/api/tickets", json={"email": "owner@example.com", "category": "account", "severity": "blocking", "subject": "Unauthorized account access", "description": "I believe my account was hacked and need the ownership changed immediately.", "environment": "Windows 11"})
    assert ticket.status_code == 201
    assert ticket.json()["automation"] == "queued"

    admin, csrf = admin_client()
    overview = admin.get("/api/admin/overview").json()
    run = next(item for item in overview["ops"] if item["entity_type"] == "ticket")
    assert run["needs_human"] is True
    assert run["risk"] == "high"
    assert run["status"] == "needs_review"
    assert "passwords" in run["draft_response"]

    monkeypatch.setattr("marketing.main.send_text", lambda *args, **kwargs: (True, "sent"))
    sent = admin.post(f"/api/admin/ops/{run['id']}/execute", headers={"X-Kizuna-CSRF": csrf}, json={"response": "We secured your request for specialist review. Do not send credentials."})
    assert sent.status_code == 200
    assert sent.json()["status"] == "completed"


def test_beta_agent_enforces_original_work_boundary():
    public = TestClient(app)
    response = public.post("/api/beta", json={"name": "Fan Creator", "email": "fan@example.com", "creator_type": "Writer", "experience": "beginner", "project_summary": "I want to make fan fiction using a copyrighted character from an existing franchise.", "desired_outcome": "Generate the series."})
    assert response.status_code == 201
    assert response.json()["automation"] == "queued"
    admin, _ = admin_client()
    run = next(item for item in admin.get("/api/admin/overview").json()["ops"] if item["entity_type"] == "beta")
    assert run["classification"] == "originality review"
    assert run["needs_human"] is True


def test_account_steward_provisions_only_safe_beta_applicants(monkeypatch):
    public = TestClient(app)
    safe_payload = {"name": "Original Creator", "email": "original@example.com", "creator_type": "Independent creator", "experience": "intermediate", "project_summary": "An original story about a coastal town that trades memories for shelter.", "desired_outcome": "Test story and character continuity."}
    assert public.post("/api/beta", json=safe_payload).status_code == 201
    admin, csrf = admin_client()
    application = admin.get("/api/admin/overview").json()["beta"][0]
    monkeypatch.setattr("marketing.main.provision_beta", lambda item: {"id": 77, "cohort": "private-beta", "expires_at": "2026-08-19T12:00:00", "access_ends_at": "2026-11-10T12:00:00", "email_delivery": "queued"})
    invited = admin.post(f"/api/admin/beta/{application['id']}/invite", headers={"X-Kizuna-CSRF": csrf}, json={})
    assert invited.status_code == 200
    assert invited.json()["status"] == "invited"
    overview = admin.get("/api/admin/overview").json()
    assert overview["beta"][0]["status"] == "invited"
    assert overview["account_steward"]["records"][0]["invitation_id"] == 77

    assert public.post("/api/beta", json={"name": "Fan Creator", "email": "blocked@example.com", "creator_type": "Writer", "experience": "beginner", "project_summary": "Fan fiction using a copyrighted character from an existing franchise.", "desired_outcome": "Generate the series."}).status_code == 201
    blocked_application = next(item for item in admin.get("/api/admin/overview").json()["beta"] if item["email"] == "blocked@example.com")
    blocked = admin.post(f"/api/admin/beta/{blocked_application['id']}/invite", headers={"X-Kizuna-CSRF": csrf}, json={})
    assert blocked.status_code == 409


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


def test_public_help_agent_is_grounded_and_source_linked():
    client = TestClient(app)
    result = client.post("/api/help/ask", json={"question": "How do I choose how much AI help I want?"})
    assert result.status_code == 200
    assert result.json()["grounded"] is True
    assert result.json()["sources"]
    source = result.json()["sources"][0]
    assert source["source_path"].startswith("/docs/")
    assert client.get(source["source_path"]).status_code == 200
    assert client.get("/api/help/search", params={"q": "AI Crew approvals"}).json()["results"]
    assert client.get("/docs/NOT_PUBLISHED.md").status_code == 404
