import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from urllib.parse import urlparse
from sqlalchemy import select

from app.auth import hash_password, token_hash, utcnow as auth_utcnow
from app.database import SessionLocal
from app.main import app
from app.models import AccountSecurityEvent, AccountToken, BetaInvitation, BillingEvent, Character, Project, ProjectMembership, Scene, Shot, StudioInvitation, Timeline, TimelineClip, User, UserSession, UserSubscription


def setup_admin(client, monkeypatch):
    monkeypatch.setattr("app.main.settings.auth_required", True)
    monkeypatch.setattr("app.main.settings.bootstrap_admin_key", "one-time-studio-key")
    monkeypatch.setattr("app.main.settings.cookie_secure", False)
    monkeypatch.setattr("app.main.settings.trial_signup_enabled", True)
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
    delivered = []
    monkeypatch.setattr("app.main.settings.smtp_host", "smtp.example.test")
    monkeypatch.setattr("app.main.settings.smtp_from_email", "studio@example.test")
    monkeypatch.setattr("app.main.send_email", lambda to_email, subject, body: delivered.append((to_email, subject, body)))
    project = client.post("/api/projects", headers={"X-Kizuna-CSRF": csrf}, json={"title": "Shared Production", "logline": "Role protected"}).json()
    invited = client.post("/api/settings/team/invitations", headers={"X-Kizuna-CSRF": csrf}, json={"email": "viewer@example.com", "display_name": "Review Partner", "project_access": [{"project_id": project["id"], "role": "viewer"}]})
    assert invited.status_code == 201
    assert invited.json()["email_delivery"] == "queued"
    assert delivered and delivered[0][0] == "viewer@example.com"
    assert "Shared Production: Viewer access" in delivered[0][2]
    assert invited.json()["acceptance_url"] in delivered[0][2]
    monkeypatch.setattr("app.main.settings.smtp_host", "")
    manual = client.post("/api/settings/team/invitations", headers={"X-Kizuna-CSRF": csrf}, json={"email": "manual@example.com", "display_name": "Manual Review", "project_access": [{"project_id": project["id"], "role": "viewer"}]})
    assert manual.status_code == 201
    assert manual.json()["email_delivery"] == "not_configured"
    assert manual.json()["acceptance_url"].startswith("http")
    manual_path = urlparse(manual.json()["acceptance_url"]).path
    with SessionLocal() as db:
        pending = db.get(StudioInvitation, manual.json()["id"])
        pending.expires_at = auth_utcnow() - timedelta(minutes=1)
        db.commit()
    pending_team = client.get("/api/settings/team").json()["invitations"]
    assert next(item for item in pending_team if item["id"] == manual.json()["id"])["status"] == "expired"
    monkeypatch.setattr("app.main.settings.smtp_host", "smtp.example.test")
    renewed = client.post(f"/api/settings/team/invitations/{manual.json()['id']}/resend", headers={"X-Kizuna-CSRF": csrf})
    assert renewed.status_code == 200
    assert renewed.json()["status"] == "pending"
    assert renewed.json()["email_delivery"] == "queued"
    assert urlparse(renewed.json()["acceptance_url"]).path != manual_path
    assert client.get(manual_path.replace("/invite/", "/api/auth/invitations/")).status_code == 404
    with SessionLocal() as db:
        db.add(User(email="other-admin@example.com", display_name="Other Administrator", password_hash=hash_password("other-admin-password"), role="admin"))
        db.commit()
    other_admin = TestClient(app)
    assert other_admin.post("/api/auth/login", json={"email": "other-admin@example.com", "password": "other-admin-password"}).status_code == 200
    other_csrf = other_admin.cookies.get("kizuna_csrf")
    assert other_admin.get("/api/settings/team").json()["invitations"] == []
    assert other_admin.post(f"/api/settings/team/invitations/{manual.json()['id']}/resend", headers={"X-Kizuna-CSRF": other_csrf}).status_code == 404
    assert other_admin.delete(f"/api/settings/team/invitations/{manual.json()['id']}", headers={"X-Kizuna-CSRF": other_csrf}).status_code == 404
    invite_path = urlparse(invited.json()["acceptance_url"]).path
    viewer = TestClient(app)
    assert viewer.get(invite_path.replace("/invite/", "/api/auth/invitations/")).status_code == 200
    accepted = viewer.post(invite_path.replace("/invite/", "/api/auth/invitations/"), json={"display_name": "Review Partner", "password": "viewer-secure-password"})
    assert accepted.status_code == 200
    viewer_csrf = viewer.cookies.get("kizuna_csrf")
    assert viewer.get("/api/settings/team").json()["invitations"] == []
    assert viewer.post(f"/api/settings/team/invitations/{manual.json()['id']}/resend", headers={"X-Kizuna-CSRF": viewer_csrf}).status_code == 404
    assert viewer.delete(f"/api/settings/team/invitations/{manual.json()['id']}", headers={"X-Kizuna-CSRF": viewer_csrf}).status_code == 404
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


def test_trial_signup_and_export_limits(client, monkeypatch):
    setup_admin(client, monkeypatch)
    delivered = []
    monkeypatch.setattr("app.main.settings.email_verification_required", True)
    monkeypatch.setattr("app.main.settings.smtp_host", "smtp.example.test")
    monkeypatch.setattr("app.main.settings.smtp_from_email", "security@example.test")
    monkeypatch.setattr("app.main.turnstile_ready", lambda: True)
    monkeypatch.setattr("app.main.verify_turnstile", lambda token, remote_ip: token == "human-token")
    monkeypatch.setattr("app.main.send_email", lambda to_email, subject, body: delivered.append((to_email, subject, body)))
    trial = TestClient(app)
    created = trial.post("/api/auth/trial", json={"email": "trial@example.com", "display_name": "Trial Creator", "password": "trial-secure-password", "challenge_token": "human-token"})
    assert created.status_code == 201
    account = created.json()
    assert account["account_tier"] == "trial"
    assert account["trial_active"] is True
    assert account["trial_export_seconds"] == 60
    remaining = datetime.fromisoformat(account["trial_ends_at"]) - auth_utcnow()
    assert timedelta(days=6, hours=23) < remaining <= timedelta(days=7)
    verify_url = next(line for line in delivered[0][2].splitlines() if line.startswith("http"))
    assert trial.post(f"/api/auth/verify/{urlparse(verify_url).path.rsplit('/', 1)[-1]}").status_code == 200
    assert trial.post("/api/auth/login", json={"email": "trial@example.com", "password": "trial-secure-password"}).status_code == 200
    project_id = account["project_id"]
    with SessionLocal() as db:
        scene = Scene(project_id=project_id, title="Trial Scene", position=1)
        db.add(scene); db.flush()
        shot = Shot(scene_id=scene.id, title="Long Trial Shot", position=1, duration_seconds=80)
        timeline = Timeline(project_id=project_id, fps=24, width=1920, height=1080)
        db.add_all([shot, timeline]); db.flush()
        db.add(TimelineClip(timeline_id=timeline.id, shot_id=shot.id, position=1, duration_seconds=80))
        db.commit(); timeline_id = timeline.id
    planned = trial.post(f"/api/timelines/{timeline_id}/master-exports", headers={"X-Kizuna-CSRF": trial.cookies.get("kizuna_csrf")}, json={"profile": "preview", "segment_size": 4})
    assert planned.status_code == 201
    export = planned.json()
    assert export["watermarked"] is True
    assert export["max_duration_seconds"] == 60
    assert export["segments"][-1]["manifest"]["end_seconds"] == 60
    assert export["segments"][-1]["manifest"]["watermark_text"].startswith("KIZUNA TRIAL")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "trial@example.com"))
        user.trial_ends_at = auth_utcnow() - timedelta(seconds=1)
        db.commit()
    expired = trial.post(f"/api/timelines/{timeline_id}/master-exports", headers={"X-Kizuna-CSRF": trial.cookies.get("kizuna_csrf")}, json={"profile": "preview"})
    assert expired.status_code == 402


def test_account_steward_issues_single_use_beta_access(client, monkeypatch):
    setup_admin(client, monkeypatch)
    secret = "account-steward-test-secret-that-is-long-enough"
    delivered = []
    monkeypatch.setattr("app.main.settings.account_steward_secret", secret)
    monkeypatch.setattr("app.main.settings.account_steward_admin_email", "owner@example.com")
    monkeypatch.setattr("app.main.settings.beta_invitation_days", 7)
    monkeypatch.setattr("app.main.settings.beta_access_days", 90)
    monkeypatch.setattr("app.main.smtp_ready", lambda: True)
    monkeypatch.setattr("app.main.schedule_beta_invitation_email", lambda invitation, acceptance_url, background_tasks: delivered.append(acceptance_url))
    payload = {"request_id": "beta-42-7c4f6a8d2e1b9c30", "application_id": "42", "email": "beta@example.com", "display_name": "Beta Creator", "experience": "beginner", "creator_type": "Independent creator", "cohort": "private-beta"}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json", "X-Kizuna-Timestamp": timestamp, "X-Kizuna-Signature": f"sha256={signature}"}

    assert TestClient(app).post("/api/internal/account-steward/beta-invitations", content=body, headers={**headers, "X-Kizuna-Signature": "sha256=invalid"}).status_code == 401
    created = TestClient(app).post("/api/internal/account-steward/beta-invitations", content=body, headers=headers)
    assert created.status_code == 201
    assert created.json()["email_delivery"] == "queued"
    assert "acceptance_url" not in created.json()
    assert len(delivered) == 1
    retried = TestClient(app).post("/api/internal/account-steward/beta-invitations", content=body, headers=headers)
    assert retried.status_code == 201
    assert retried.json()["id"] == created.json()["id"]

    raw_token = urlparse(delivered[0]).path.rsplit("/", 1)[-1]
    beta = TestClient(app)
    inspected = beta.get(f"/api/auth/beta-invitations/{raw_token}")
    assert inspected.status_code == 200
    accepted = beta.post(f"/api/auth/beta-invitations/{raw_token}", json={"display_name": "Beta Creator", "password": "beta-secure-password"})
    assert accepted.status_code == 200
    assert accepted.json()["account_tier"] == "beta"
    assert accepted.json()["beta_active"] is True
    assert beta.get(f"/api/projects/{accepted.json()['starter_project_id']}").status_code == 200
    assert beta.post(f"/api/auth/beta-invitations/{raw_token}", json={"display_name": "Again", "password": "another-secure-password"}).status_code == 404
    with SessionLocal() as db:
        invitation = db.scalar(select(BetaInvitation).where(BetaInvitation.source_application_id == "42"))
        user = db.scalar(select(User).where(User.email == "beta@example.com"))
        membership = db.scalar(select(ProjectMembership).where(ProjectMembership.user_id == user.id))
        assert invitation.accepted_at is not None
        assert membership.role == "owner"
        assert db.scalar(select(AccountSecurityEvent).where(AccountSecurityEvent.event_type == "beta_invitation_created")) is not None
        assert db.scalar(select(AccountSecurityEvent).where(AccountSecurityEvent.event_type == "beta_invitation_accepted")) is not None


def test_password_reset_is_generic_single_use_and_revokes_sessions(client, monkeypatch):
    setup_admin(client, monkeypatch)
    delivered = []
    monkeypatch.setattr("app.main.settings.smtp_host", "smtp.example.test")
    monkeypatch.setattr("app.main.settings.smtp_from_email", "security@example.test")
    monkeypatch.setattr("app.main.send_email", lambda to_email, subject, body: delivered.append((to_email, subject, body)))

    known = client.post("/api/auth/password/forgot", json={"email": "owner@example.com"})
    unknown = client.post("/api/auth/password/forgot", json={"email": "unknown@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(delivered) == 1
    reset_url = next(line for line in delivered[0][2].splitlines() if line.startswith("http"))
    raw_token = urlparse(reset_url).path.rsplit("/", 1)[-1]
    with SessionLocal() as db:
        stored = db.scalar(select(AccountToken).where(AccountToken.purpose == "password_reset"))
        assert stored.token_hash == token_hash(raw_token)
        assert raw_token != stored.token_hash
        assert db.scalar(select(UserSession).where(UserSession.user_id == stored.user_id)) is not None

    assert client.get(f"/api/auth/password/reset/{raw_token}").json() == {"valid": True}
    mismatch = client.post(f"/api/auth/password/reset/{raw_token}", json={"password": "new-long-secure-password", "confirm_password": "different-secure-password"})
    assert mismatch.status_code == 422
    completed = client.post(f"/api/auth/password/reset/{raw_token}", json={"password": "new-long-secure-password", "confirm_password": "new-long-secure-password"})
    assert completed.status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.post(f"/api/auth/password/reset/{raw_token}", json={"password": "another-long-password", "confirm_password": "another-long-password"}).status_code == 404
    assert TestClient(app).post("/api/auth/login", json={"email": "owner@example.com", "password": "long-secure-password"}).status_code == 401
    assert TestClient(app).post("/api/auth/login", json={"email": "owner@example.com", "password": "new-long-secure-password"}).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(AccountSecurityEvent).where(AccountSecurityEvent.event_type == "password_reset_completed")) is not None


def test_required_email_verification_blocks_login_until_link_is_used(client, monkeypatch):
    setup_admin(client, monkeypatch)
    delivered = []
    monkeypatch.setattr("app.main.settings.email_verification_required", True)
    monkeypatch.setattr("app.main.settings.smtp_host", "smtp.example.test")
    monkeypatch.setattr("app.main.settings.smtp_from_email", "security@example.test")
    monkeypatch.setattr("app.main.turnstile_ready", lambda: True)
    monkeypatch.setattr("app.main.verify_turnstile", lambda token, remote_ip: token == "human-token")
    monkeypatch.setattr("app.main.send_email", lambda to_email, subject, body: delivered.append((to_email, subject, body)))
    trial = TestClient(app)
    created = trial.post("/api/auth/trial", json={"email": "verify@example.com", "display_name": "Verify Creator", "password": "trial-secure-password", "challenge_token": "human-token"})
    assert created.status_code == 201
    assert created.json()["verification_required"] is True
    assert trial.cookies.get("kizuna_session") is None
    assert trial.post("/api/auth/login", json={"email": "verify@example.com", "password": "trial-secure-password"}).status_code == 401
    verify_url = next(line for line in delivered[0][2].splitlines() if line.startswith("http"))
    raw_token = urlparse(verify_url).path.rsplit("/", 1)[-1]
    assert trial.post(f"/api/auth/verify/{raw_token}").status_code == 200
    assert trial.post(f"/api/auth/verify/{raw_token}").status_code == 404
    signed_in = trial.post("/api/auth/login", json={"email": "verify@example.com", "password": "trial-secure-password"})
    assert signed_in.status_code == 200
    assert signed_in.json()["email_verified"] is True


def test_trial_signup_fails_closed_without_human_verification(client, monkeypatch):
    setup_admin(client, monkeypatch)
    monkeypatch.setattr("app.main.settings.email_verification_required", True)
    monkeypatch.setattr("app.main.settings.smtp_host", "smtp.example.test")
    monkeypatch.setattr("app.main.settings.smtp_from_email", "security@example.test")
    monkeypatch.setattr("app.main.turnstile_ready", lambda: True)
    monkeypatch.setattr("app.main.verify_turnstile", lambda token, remote_ip: False)
    blocked = TestClient(app).post("/api/auth/trial", json={"email": "bot@example.com", "display_name": "Bot", "password": "trial-secure-password", "challenge_token": "invalid"})
    assert blocked.status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == "bot@example.com")) is None


def test_signed_billing_webhook_is_idempotent_and_controls_entitlement(client, monkeypatch):
    setup_admin(client, monkeypatch)
    with SessionLocal() as db:
        user = User(email="billing@example.com", display_name="Billing Creator", password_hash=hash_password("billing-secure-password"), role="creator", account_tier="trial", email_verified_at=auth_utcnow())
        db.add(user);db.commit();user_id=user.id
    billing_client = TestClient(app)
    assert billing_client.post("/api/auth/login", json={"email": "billing@example.com", "password": "billing-secure-password"}).status_code == 200
    monkeypatch.setattr("app.main.settings.stripe_secret_key", "sk_test_kizuna")
    monkeypatch.setattr("app.main.settings.stripe_webhook_secret", "whsec_kizuna")
    monkeypatch.setattr("app.main.settings.stripe_creator_price_id", "price_creator")
    monkeypatch.setattr("app.main.stripe_request", lambda path, fields: {"id": "cs_test_kizuna", "url": "https://checkout.stripe.test/session"})
    billing = billing_client.get("/api/account/billing").json()
    assert billing["checkout_ready"] is True
    checkout = billing_client.post("/api/account/billing/checkout", headers={"X-Kizuna-CSRF": billing_client.cookies.get("kizuna_csrf")})
    assert checkout.json()["url"] == "https://checkout.stripe.test/session"

    event = {"id": "evt_kizuna_1", "type": "customer.subscription.created", "data": {"object": {"id": "sub_kizuna", "customer": "cus_kizuna", "status": "active", "current_period_end": int(time.time()) + 86400, "cancel_at_period_end": False, "metadata": {"kizuna_user_id": str(user_id), "plan_key": "creator"}}}}
    payload = json.dumps(event, separators=(",", ":")).encode();timestamp = int(time.time())
    signature = hmac.new(b"whsec_kizuna", f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    headers = {"Stripe-Signature": f"t={timestamp},v1={signature}", "Content-Type": "application/json"}
    assert TestClient(app).post("/api/billing/stripe/webhook", content=payload, headers={**headers, "Stripe-Signature": f"t={timestamp},v1=invalid"}).status_code == 400
    assert TestClient(app).post("/api/billing/stripe/webhook", content=payload, headers=headers).status_code == 200
    assert TestClient(app).post("/api/billing/stripe/webhook", content=payload, headers=headers).status_code == 200
    with SessionLocal() as db:
        assert db.get(User, user_id).account_tier == "creator"
        assert db.scalar(select(UserSubscription).where(UserSubscription.user_id == user_id)).status == "active"
        assert len(db.scalars(select(BillingEvent).where(BillingEvent.event_id == "evt_kizuna_1")).all()) == 1

    canceled = {"id": "evt_kizuna_2", "type": "customer.subscription.deleted", "data": {"object": {"id": "sub_kizuna", "customer": "cus_kizuna", "status": "canceled", "metadata": {"kizuna_user_id": str(user_id), "plan_key": "creator"}}}}
    canceled_payload = json.dumps(canceled, separators=(",", ":")).encode();canceled_signature = hmac.new(b"whsec_kizuna", f"{timestamp}.".encode() + canceled_payload, hashlib.sha256).hexdigest()
    assert TestClient(app).post("/api/billing/stripe/webhook", content=canceled_payload, headers={"Stripe-Signature": f"t={timestamp},v1={canceled_signature}", "Content-Type": "application/json"}).status_code == 200
    with SessionLocal() as db:
        canceled_user = db.get(User, user_id)
        assert canceled_user.account_tier == "trial"
        assert canceled_user.trial_ends_at <= auth_utcnow()
