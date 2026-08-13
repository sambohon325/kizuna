from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from marketing.mailer import ready as mail_ready, send_text
from marketing.ops_agent import OpsDecision, decide_beta, decide_support, may_auto_execute, provider_status
from marketing.account_steward import AccountStewardError, BETA_AUTO_INVITE, provision_beta, readiness as steward_readiness, request_id as steward_request_id
from app.help_center import DOCS_ROOT, PUBLISHED_DOCS, answer_help, search_help
from marketing.editorial_agent import create_editorial_draft


ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("KIZUNA_MARKETING_DATA_DIR", ROOT / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("KIZUNA_MARKETING_DATABASE_URL", f"sqlite:///{(DATA_DIR / 'marketing.db').as_posix()}")
ADMIN_PASSWORD = os.getenv("KIZUNA_MARKETING_ADMIN_PASSWORD", "")
SESSION_SECRET = os.getenv("KIZUNA_MARKETING_SESSION_SECRET", "")
COOKIE_SECURE = os.getenv("KIZUNA_MARKETING_COOKIE_SECURE", "true").lower() in {"1", "true", "yes"}
APP_URL = os.getenv("KIZUNA_APP_URL", "https://app.kizuna.com").rstrip("/")
SOCIALS = {
    "instagram": os.getenv("KIZUNA_SOCIAL_INSTAGRAM", ""),
    "youtube": os.getenv("KIZUNA_SOCIAL_YOUTUBE", ""),
    "tiktok": os.getenv("KIZUNA_SOCIAL_TIKTOK", ""),
    "x": os.getenv("KIZUNA_SOCIAL_X", ""),
    "linkedin": os.getenv("KIZUNA_SOCIAL_LINKEDIN", ""),
    "discord": os.getenv("KIZUNA_SOCIAL_DISCORD", ""),
}
SESSION_COOKIE = "kizuna_marketing_admin"
CSRF_COOKIE = "kizuna_marketing_csrf"


def db_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class HelpQuestionInput(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class EditorialCampaignInput(BaseModel):
    brief_title: str = Field(min_length=4, max_length=180)
    content_type: str = Field(default="education", pattern="^(education|product|milestone|customer|incident|partnership|policy)$")
    approved_facts: str = Field(min_length=20, max_length=20000)
    audience: str = Field(min_length=3, max_length=300)
    goal: str = Field(min_length=10, max_length=3000)
    call_to_action: str = Field(default="Learn more at kizuna.technology.", max_length=500)
    scheduled_at: datetime | None = None


class BlogPost(Base):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    excerpt: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(120), default="Kizuna Studio")
    category: Mapped[str] = mapped_column(String(80), default="Studio notes")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    featured: Mapped[bool] = mapped_column(default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=db_now, onupdate=db_now)


class EditorialCampaign(Base):
    __tablename__ = "editorial_campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    brief_title: Mapped[str] = mapped_column(String(180))
    content_type: Mapped[str] = mapped_column(String(30), default="education", index=True)
    approved_facts: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(300))
    goal: Mapped[str] = mapped_column(Text)
    call_to_action: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    risk: Mapped[str] = mapped_column(String(30), default="low")
    approval_reason: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(String(180), default="")
    excerpt: Mapped[str] = mapped_column(String(500), default="")
    blog_body: Mapped[str] = mapped_column(Text, default="")
    social_variants: Mapped[dict] = mapped_column(JSON, default=dict)
    provider: Mapped[str] = mapped_column(String(160), default="local-editorial")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    provider_error: Mapped[str] = mapped_column(Text, default="")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    journal_post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=db_now, onupdate=db_now)


class BetaApplication(Base):
    __tablename__ = "beta_applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), index=True)
    creator_type: Mapped[str] = mapped_column(String(80))
    experience: Mapped[str] = mapped_column(String(40))
    project_summary: Mapped[str] = mapped_column(Text)
    desired_outcome: Mapped[str] = mapped_column(Text, default="")
    hardware: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    category: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    page_url: Mapped[str] = mapped_column(String(1000), default="")
    environment: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=db_now, onupdate=db_now)


class OpsRun(Base):
    __tablename__ = "ops_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    agent: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), index=True)
    classification: Mapped[str] = mapped_column(String(80))
    risk: Mapped[str] = mapped_column(String(20), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    summary: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    draft_response: Mapped[str] = mapped_column(Text)
    actions_json: Mapped[str] = mapped_column(Text, default="[]")
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    auto_executed: Mapped[bool] = mapped_column(Boolean, default=False)
    provider: Mapped[str] = mapped_column(String(160), default="local-policy")
    provider_error: Mapped[str] = mapped_column(Text, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=db_now, onupdate=db_now)


class OpsDelivery(Base):
    __tablename__ = "ops_deliveries"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    channel: Mapped[str] = mapped_column(String(30), default="email")
    recipient: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(30), index=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)


class AccountProvisioning(Base):
    __tablename__ = "account_provisioning"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    invitation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cohort: Mapped[str] = mapped_column(String(80), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    access_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_delivery: Mapped[str] = mapped_column(String(30), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=db_now, onupdate=db_now)


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(engine)


def db_session():
    with SessionLocal() as db:
        yield db


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def post_dict(item: BlogPost, include_body: bool = False) -> dict:
    result = {"id": item.id, "title": item.title, "slug": item.slug, "excerpt": item.excerpt, "author": item.author, "category": item.category, "status": item.status, "featured": item.featured, "published_at": item.published_at, "created_at": item.created_at, "updated_at": item.updated_at}
    if include_body:
        result["body"] = item.body
    return result


def campaign_dict(item: EditorialCampaign) -> dict:
    return {
        "id": item.id, "brief_title": item.brief_title, "content_type": item.content_type,
        "approved_facts": item.approved_facts, "audience": item.audience, "goal": item.goal,
        "call_to_action": item.call_to_action, "status": item.status, "risk": item.risk,
        "approval_reason": item.approval_reason, "title": item.title, "excerpt": item.excerpt,
        "blog_body": item.blog_body, "social_variants": item.social_variants,
        "provider": item.provider, "input_tokens": item.input_tokens, "output_tokens": item.output_tokens,
        "provider_error": item.provider_error, "scheduled_at": item.scheduled_at,
        "approved_at": item.approved_at, "journal_post_id": item.journal_post_id,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }


def ops_dict(item: OpsRun) -> dict:
    return {
        "id": item.id, "entity_type": item.entity_type, "entity_id": item.entity_id,
        "agent": item.agent, "status": item.status, "classification": item.classification,
        "risk": item.risk, "confidence": item.confidence, "summary": item.summary,
        "recommended_action": item.recommended_action, "draft_response": item.draft_response,
        "actions": json.loads(item.actions_json or "[]"), "needs_human": item.needs_human,
        "auto_executed": item.auto_executed, "provider": item.provider,
        "provider_error": item.provider_error, "input_tokens": item.input_tokens,
        "output_tokens": item.output_tokens, "created_at": item.created_at, "updated_at": item.updated_at,
    }


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return value[:180] or f"post-{secrets.token_hex(4)}"


def session_signature(expires: int) -> str:
    return hmac.new(SESSION_SECRET.encode(), str(expires).encode(), hashlib.sha256).hexdigest()


def require_admin(admin_session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> None:
    if not admin_session or not SESSION_SECRET:
        raise HTTPException(401, "Administrator sign-in required")
    try:
        expires_text, supplied = admin_session.split(".", 1)
        expires = int(expires_text)
    except (ValueError, TypeError):
        raise HTTPException(401, "Administrator sign-in required")
    if expires < int(time.time()) or not hmac.compare_digest(supplied, session_signature(expires)):
        raise HTTPException(401, "Administrator sign-in required")


def require_csrf(request: Request, csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE)) -> None:
    supplied = request.headers.get("X-Kizuna-CSRF", "")
    if not supplied or not csrf_cookie or not secrets.compare_digest(supplied, csrf_cookie):
        raise HTTPException(403, "Security token missing or expired")


attempts: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(request: Request, bucket: str, maximum: int = 6, seconds: int = 3600) -> None:
    address = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip() or (request.client.host if request.client else "unknown")
    key = hashlib.sha256(f"{bucket}:{address}".encode()).hexdigest()
    now = time.time()
    entries = attempts[key]
    while entries and entries[0] < now - seconds:
        entries.popleft()
    if len(entries) >= maximum:
        raise HTTPException(429, "Please wait before submitting again")
    entries.append(now)


class AdminLogin(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class PostInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    slug: str = Field(default="", max_length=190)
    excerpt: str = Field(default="", max_length=500)
    body: str = Field(min_length=20, max_length=100_000)
    author: str = Field(default="Kizuna Studio", max_length=120)
    category: str = Field(default="Studio notes", max_length=80)
    status: str = Field(default="draft", pattern="^(draft|published)$")
    featured: bool = False


class BetaInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=320)
    creator_type: str = Field(min_length=2, max_length=80)
    experience: str = Field(pattern="^(beginner|intermediate|professional)$")
    project_summary: str = Field(min_length=20, max_length=5000)
    desired_outcome: str = Field(default="", max_length=3000)
    hardware: str = Field(default="", max_length=500)
    website: str = Field(default="", max_length=200)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class TicketInput(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    category: str = Field(pattern="^(bug|account|billing|feature|feedback|other)$")
    severity: str = Field(default="normal", pattern="^(low|normal|high|blocking)$")
    subject: str = Field(min_length=4, max_length=180)
    description: str = Field(min_length=20, max_length=8000)
    page_url: str = Field(default="", max_length=1000)
    environment: str = Field(default="", max_length=1000)
    company: str = Field(default="", max_length=200)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return BetaInput.valid_email(value)


class BetaTriageInput(BaseModel):
    status: str = Field(pattern="^(new|reviewing|invited|waitlisted|closed)$")
    notes: str = Field(default="", max_length=5000)


class TicketTriageInput(BaseModel):
    status: str = Field(pattern="^(open|investigating|resolved|closed)$")
    notes: str = Field(default="", max_length=5000)


class OpsExecuteInput(BaseModel):
    response: str = Field(default="", max_length=6000)


app = FastAPI(title="Kizuna Public Site", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/assets", StaticFiles(directory=ROOT.parent / "app" / "static" / "assets"), name="assets")


def public_url(value: str) -> str:
    value = value.strip()
    return value if value.startswith(("https://", "http://")) else ""


@app.middleware("http")
async def public_safety(request: Request, call_next):
    content_length = request.headers.get("content-length", "0")
    if request.method in {"POST", "PUT", "PATCH"}:
        try:
            too_large = int(content_length) > 200_000
        except ValueError:
            too_large = True
        if too_large:
            return JSONResponse({"detail": "Request is too large"}, status_code=413)

    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'self'; "
        "base-uri 'self'; form-action 'self'"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config.js")
def public_config():
    payload = {
        "appUrl": public_url(APP_URL) or "https://app.kizuna.com",
        "socials": {key: clean for key, value in SOCIALS.items() if (clean := public_url(value))},
    }
    source = "window.KIZUNA_MARKETING=" + json.dumps(payload, separators=(",", ":")) + ";"
    return Response(source, media_type="application/javascript", headers={"Cache-Control": "no-store"})


@app.get("/api/blog")
def public_posts(db: Session = Depends(db_session)):
    posts = db.scalars(select(BlogPost).where(BlogPost.status == "published").order_by(BlogPost.featured.desc(), BlogPost.published_at.desc(), BlogPost.id.desc())).all()
    return [post_dict(item) for item in posts]


@app.get("/api/blog/{slug}")
def public_post(slug: str, db: Session = Depends(db_session)):
    item = db.scalar(select(BlogPost).where(BlogPost.slug == slug, BlogPost.status == "published"))
    if item is None:
        raise HTTPException(404, "Article not found")
    return post_dict(item, include_body=True)


@app.get("/api/help/search")
def public_help_search(q: str = Query(min_length=2, max_length=200), limit: int = Query(default=8, ge=1, le=12)):
    return {"query": q, "results": search_help(q, max(1, min(limit, 12)))}


@app.post("/api/help/ask")
def public_help_answer(payload: HelpQuestionInput, request: Request):
    rate_limit(request, "help", maximum=30)
    return answer_help(payload.question)


@app.get("/docs/{document}", include_in_schema=False)
def public_help_document(document: str):
    if document not in PUBLISHED_DOCS:
        raise HTTPException(404, "Help document not found")
    return FileResponse(DOCS_ROOT / document, media_type="text/markdown; charset=utf-8")


def store_ops_run(db: Session, entity_type: str, entity_id: int, decision: OpsDecision) -> OpsRun:
    item = OpsRun(
        entity_type=entity_type, entity_id=entity_id, agent=decision.agent,
        status="needs_review" if decision.needs_human else "prepared",
        classification=decision.classification, risk=decision.risk, confidence=decision.confidence,
        summary=decision.summary, recommended_action=decision.recommended_action,
        draft_response=decision.draft_response, actions_json=json.dumps(decision.actions),
        needs_human=decision.needs_human, provider=decision.provider,
        provider_error=decision.provider_error, input_tokens=decision.input_tokens,
        output_tokens=decision.output_tokens,
    )
    db.add(item); db.flush()
    return item


def deliver_run(db: Session, run: OpsRun, email: str, subject: str, response_text: str = "") -> bool:
    body = response_text.strip() or run.draft_response
    sent, note = send_text(email, subject, body)
    db.add(OpsDelivery(run_id=run.id, recipient=email, subject=subject, status="sent" if sent else "failed", error="" if sent else note))
    if sent:
        run.status = "auto_completed" if run.auto_executed else "completed"
    return sent


def beta_record_dict(item: BetaApplication) -> dict:
    return {"id": item.id, "name": item.name, "email": item.email, "creator_type": item.creator_type, "experience": item.experience, "project_summary": item.project_summary, "desired_outcome": item.desired_outcome, "hardware": item.hardware}


def provision_beta_account(db: Session, item: BetaApplication) -> AccountProvisioning:
    record = db.scalar(select(AccountProvisioning).where(AccountProvisioning.application_id == item.id))
    if record is None:
        record = AccountProvisioning(application_id=item.id, request_id=steward_request_id(item.id, item.email))
        db.add(record); db.flush()
    if record.status == "invited":
        return record
    record.status, record.error = "processing", ""
    db.commit()
    try:
        result = provision_beta(beta_record_dict(item))
        record.status = "invited"
        record.invitation_id = result.get("id")
        record.cohort = str(result.get("cohort", ""))
        record.expires_at = datetime.fromisoformat(str(result["expires_at"]).replace("Z", "+00:00")).replace(tzinfo=None) if result.get("expires_at") else None
        record.access_ends_at = datetime.fromisoformat(str(result["access_ends_at"]).replace("Z", "+00:00")).replace(tzinfo=None) if result.get("access_ends_at") else None
        record.email_delivery = str(result.get("email_delivery", ""))
        item.status = "invited"
    except (AccountStewardError, ValueError, TypeError) as exc:
        record.status, record.error = "failed", str(exc)[:1000]
    db.commit(); db.refresh(record)
    return record


def process_beta_record(db: Session, item: BetaApplication, force: bool = False) -> OpsRun:
    existing = db.scalar(select(OpsRun).where(OpsRun.entity_type == "beta", OpsRun.entity_id == item.id).order_by(OpsRun.id.desc()))
    if existing and not force:
        return existing
    decision = decide_beta({"experience": item.experience, "creator_type": item.creator_type, "project_summary": item.project_summary, "desired_outcome": item.desired_outcome, "hardware": item.hardware})
    run = store_ops_run(db, "beta", item.id, decision)
    if may_auto_execute(decision):
        if BETA_AUTO_INVITE:
            provisioning = provision_beta_account(db, item)
            run.auto_executed = provisioning.status == "invited"
            run.status = "auto_completed" if run.auto_executed else "prepared"
        else:
            run.auto_executed = True
            if deliver_run(db, run, item.email, "We received your Kizuna beta application"):
                item.status = "reviewing"
            else:
                run.auto_executed = False
    db.commit(); db.refresh(run)
    return run


def process_ticket_record(db: Session, item: SupportTicket, force: bool = False) -> OpsRun:
    existing = db.scalar(select(OpsRun).where(OpsRun.entity_type == "ticket", OpsRun.entity_id == item.id).order_by(OpsRun.id.desc()))
    if existing and not force:
        return existing
    decision = decide_support({"reference": item.reference, "category": item.category, "severity": item.severity, "subject": item.subject, "description": item.description, "page_url": item.page_url, "environment": item.environment})
    run = store_ops_run(db, "ticket", item.id, decision)
    if may_auto_execute(decision):
        run.auto_executed = True
        if deliver_run(db, run, item.email, f"Kizuna support · {item.reference}"):
            if item.category == "bug":
                item.status = "investigating"
        else:
            run.auto_executed = False
    db.commit(); db.refresh(run)
    return run


def process_beta_background(application_id: int) -> None:
    with SessionLocal() as db:
        item = db.get(BetaApplication, application_id)
        if item is not None:
            process_beta_record(db, item)


def process_ticket_background(ticket_id: int) -> None:
    with SessionLocal() as db:
        item = db.get(SupportTicket, ticket_id)
        if item is not None:
            process_ticket_record(db, item)


@app.post("/api/beta", status_code=201)
def apply_beta(payload: BetaInput, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(db_session)):
    rate_limit(request, "beta", maximum=4)
    if payload.website:
        return {"received": True}
    existing = db.scalar(select(BetaApplication).where(BetaApplication.email == payload.email.lower(), BetaApplication.status.in_(["new", "reviewing", "invited", "waitlisted"])))
    if existing:
        return {"received": True}
    item = BetaApplication(name=payload.name.strip(), email=payload.email.lower(), creator_type=payload.creator_type.strip(), experience=payload.experience, project_summary=payload.project_summary.strip(), desired_outcome=payload.desired_outcome.strip(), hardware=payload.hardware.strip())
    db.add(item); db.commit(); db.refresh(item)
    mode = provider_status()["mode"]
    if mode != "off":
        background_tasks.add_task(process_beta_background, item.id)
    return {"received": True, "automation": "queued" if mode != "off" else "off"}


@app.post("/api/tickets", status_code=201)
def create_ticket(payload: TicketInput, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(db_session)):
    rate_limit(request, "tickets", maximum=8)
    if payload.company:
        return {"received": True, "reference": "KZ-RECEIVED"}
    reference = f"KZ-{utcnow():%y%m%d}-{secrets.token_hex(3).upper()}"
    item = SupportTicket(reference=reference, email=payload.email.lower(), category=payload.category, severity=payload.severity, subject=payload.subject.strip(), description=payload.description.strip(), page_url=payload.page_url.strip(), environment=payload.environment.strip())
    db.add(item); db.commit(); db.refresh(item)
    mode = provider_status()["mode"]
    if mode != "off":
        background_tasks.add_task(process_ticket_background, item.id)
    return {"received": True, "reference": reference, "automation": "queued" if mode != "off" else "off"}


@app.post("/api/admin/login")
def admin_login(payload: AdminLogin, response: Response, request: Request):
    rate_limit(request, "admin-login", maximum=8, seconds=900)
    if not ADMIN_PASSWORD or not SESSION_SECRET:
        raise HTTPException(503, "Marketing administration is not configured")
    if not secrets.compare_digest(payload.password, ADMIN_PASSWORD):
        raise HTTPException(401, "Invalid administrator password")
    expires = int((datetime.now(timezone.utc) + timedelta(hours=12)).timestamp())
    csrf = secrets.token_urlsafe(32)
    response.set_cookie(SESSION_COOKIE, f"{expires}.{session_signature(expires)}", max_age=43200, httponly=True, secure=COOKIE_SECURE, samesite="strict", path="/")
    response.set_cookie(CSRF_COOKIE, csrf, max_age=43200, httponly=False, secure=COOKIE_SECURE, samesite="strict", path="/")
    return {"signed_in": True, "csrf": csrf}


@app.post("/api/admin/logout", status_code=204, dependencies=[Depends(require_admin), Depends(require_csrf)])
def admin_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/"); response.delete_cookie(CSRF_COOKIE, path="/")


@app.get("/api/admin/overview", dependencies=[Depends(require_admin)])
def admin_overview(db: Session = Depends(db_session)):
    posts = db.scalars(select(BlogPost).order_by(BlogPost.updated_at.desc())).all()
    campaigns = db.scalars(select(EditorialCampaign).order_by(EditorialCampaign.created_at.desc()).limit(250)).all()
    beta = db.scalars(select(BetaApplication).order_by(BetaApplication.created_at.desc()).limit(250)).all()
    tickets = db.scalars(select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(250)).all()
    ops = db.scalars(select(OpsRun).order_by(OpsRun.created_at.desc()).limit(300)).all()
    provisioning = db.scalars(select(AccountProvisioning).order_by(AccountProvisioning.created_at.desc()).limit(250)).all()
    return {
        "posts": [post_dict(item, include_body=True) for item in posts],
        "campaigns": [campaign_dict(item) for item in campaigns],
        "beta": [{"id": item.id, "name": item.name, "email": item.email, "creator_type": item.creator_type, "experience": item.experience, "project_summary": item.project_summary, "desired_outcome": item.desired_outcome, "hardware": item.hardware, "status": item.status, "notes": item.notes, "created_at": item.created_at} for item in beta],
        "tickets": [{"id": item.id, "reference": item.reference, "email": item.email, "category": item.category, "severity": item.severity, "subject": item.subject, "description": item.description, "page_url": item.page_url, "environment": item.environment, "status": item.status, "notes": item.notes, "created_at": item.created_at, "updated_at": item.updated_at} for item in tickets],
        "ops": [ops_dict(item) for item in ops],
        "ops_config": {**provider_status(), "email_ready": mail_ready()},
        "account_steward": {**steward_readiness(), "records": [{"application_id": item.application_id, "status": item.status, "invitation_id": item.invitation_id, "cohort": item.cohort, "expires_at": item.expires_at, "access_ends_at": item.access_ends_at, "email_delivery": item.email_delivery, "error": item.error} for item in provisioning]},
    }


@app.post("/api/admin/beta/{application_id}/invite", dependencies=[Depends(require_admin), Depends(require_csrf)])
def invite_beta_applicant(application_id: int, db: Session = Depends(db_session)):
    item = db.get(BetaApplication, application_id)
    if item is None:
        raise HTTPException(404, "Application not found")
    decision = db.scalar(select(OpsRun).where(OpsRun.entity_type == "beta", OpsRun.entity_id == item.id).order_by(OpsRun.id.desc()))
    if decision is None:
        decision = process_beta_record(db, item)
    if decision.needs_human or decision.risk != "low":
        raise HTTPException(409, "Resolve the application review before issuing account access")
    record = provision_beta_account(db, item)
    if record.status != "invited":
        raise HTTPException(503, record.error or "Account invitation could not be created")
    return {"application_id": item.id, "status": record.status, "invitation_id": record.invitation_id, "cohort": record.cohort, "expires_at": record.expires_at, "access_ends_at": record.access_ends_at, "email_delivery": record.email_delivery}


@app.post("/api/admin/ops/run", dependencies=[Depends(require_admin), Depends(require_csrf)])
def run_ops_desk(db: Session = Depends(db_session)):
    created = 0
    for item in db.scalars(select(BetaApplication).order_by(BetaApplication.id)).all():
        before = db.scalar(select(OpsRun.id).where(OpsRun.entity_type == "beta", OpsRun.entity_id == item.id))
        process_beta_record(db, item)
        created += int(before is None)
    for item in db.scalars(select(SupportTicket).order_by(SupportTicket.id)).all():
        before = db.scalar(select(OpsRun.id).where(OpsRun.entity_type == "ticket", OpsRun.entity_id == item.id))
        process_ticket_record(db, item)
        created += int(before is None)
    return {"processed": created}


@app.post("/api/admin/ops/{run_id}/execute", dependencies=[Depends(require_admin), Depends(require_csrf)])
def execute_ops_run(run_id: int, payload: OpsExecuteInput, db: Session = Depends(db_session)):
    run = db.get(OpsRun, run_id)
    if run is None:
        raise HTTPException(404, "Operations run not found")
    if run.status in {"completed", "auto_completed"}:
        return ops_dict(run)
    if run.entity_type == "ticket":
        entity = db.get(SupportTicket, run.entity_id)
        subject = f"Kizuna support · {entity.reference}" if entity else "Kizuna support"
    else:
        entity = db.get(BetaApplication, run.entity_id)
        subject = "Your Kizuna beta application"
    if entity is None:
        raise HTTPException(404, "Related record not found")
    if not deliver_run(db, run, entity.email, subject, payload.response):
        db.commit()
        raise HTTPException(503, "Email delivery is not configured or failed")
    db.commit(); db.refresh(run)
    return ops_dict(run)


def unique_slug(db: Session, desired: str, item_id: int | None = None) -> str:
    base = slugify(desired)
    candidate, index = base, 2
    while db.scalar(select(BlogPost.id).where(BlogPost.slug == candidate, BlogPost.id != item_id)) is not None:
        candidate, index = f"{base}-{index}", index + 1
    return candidate


@app.post("/api/admin/editorial/campaigns", status_code=201, dependencies=[Depends(require_admin), Depends(require_csrf)])
def create_editorial_campaign(payload: EditorialCampaignInput, db: Session = Depends(db_session)):
    draft = create_editorial_draft(payload.brief_title, payload.approved_facts, payload.audience, payload.goal, payload.call_to_action, payload.content_type)
    item = EditorialCampaign(
        brief_title=payload.brief_title.strip(), content_type=payload.content_type,
        approved_facts=payload.approved_facts.strip(), audience=payload.audience.strip(), goal=payload.goal.strip(),
        call_to_action=payload.call_to_action.strip(), status="blocked" if draft.risk == "blocked" else "needs_review" if draft.needs_approval else "prepared",
        risk=draft.risk, approval_reason=draft.rationale, title=draft.title, excerpt=draft.excerpt,
        blog_body=draft.blog_body, social_variants=draft.social, provider=draft.provider,
        input_tokens=draft.input_tokens, output_tokens=draft.output_tokens, provider_error=draft.provider_error,
        scheduled_at=payload.scheduled_at.replace(tzinfo=None) if payload.scheduled_at and payload.scheduled_at.tzinfo else payload.scheduled_at,
    )
    db.add(item); db.commit(); db.refresh(item)
    return campaign_dict(item)


@app.post("/api/admin/editorial/campaigns/{campaign_id}/approve", dependencies=[Depends(require_admin), Depends(require_csrf)])
def approve_editorial_campaign(campaign_id: int, db: Session = Depends(db_session)):
    item = db.get(EditorialCampaign, campaign_id)
    if item is None:
        raise HTTPException(404, "Editorial campaign not found")
    if item.status == "blocked":
        raise HTTPException(409, "Remove confidential or unannounced material and create a new factual brief")
    item.status, item.approved_at = "approved", utcnow()
    db.commit(); db.refresh(item)
    return campaign_dict(item)


@app.post("/api/admin/editorial/campaigns/{campaign_id}/journal-draft", dependencies=[Depends(require_admin), Depends(require_csrf)])
def create_campaign_journal_draft(campaign_id: int, db: Session = Depends(db_session)):
    item = db.get(EditorialCampaign, campaign_id)
    if item is None:
        raise HTTPException(404, "Editorial campaign not found")
    if item.status != "approved":
        raise HTTPException(409, "Approve the campaign facts and copy before creating publishing assets")
    if item.journal_post_id:
        post = db.get(BlogPost, item.journal_post_id)
        if post is not None:
            return post_dict(post, include_body=True)
    post = BlogPost(title=item.title, slug=unique_slug(db, item.title), excerpt=item.excerpt, body=item.blog_body, author="Kizuna Studio", category="Studio notes", status="draft", featured=False)
    db.add(post); db.flush()
    item.journal_post_id, item.status = post.id, "ready"
    db.commit(); db.refresh(post)
    return post_dict(post, include_body=True)


@app.post("/api/admin/posts", status_code=201, dependencies=[Depends(require_admin), Depends(require_csrf)])
def create_post(payload: PostInput, db: Session = Depends(db_session)):
    item = BlogPost(title=payload.title.strip(), slug=unique_slug(db, payload.slug or payload.title), excerpt=payload.excerpt.strip(), body=payload.body.strip(), author=payload.author.strip(), category=payload.category.strip(), status=payload.status, featured=payload.featured, published_at=utcnow() if payload.status == "published" else None)
    db.add(item); db.commit(); db.refresh(item)
    return post_dict(item, include_body=True)


@app.put("/api/admin/posts/{post_id}", dependencies=[Depends(require_admin), Depends(require_csrf)])
def update_post(post_id: int, payload: PostInput, db: Session = Depends(db_session)):
    item = db.get(BlogPost, post_id)
    if item is None: raise HTTPException(404, "Post not found")
    was_published = item.status == "published"
    item.title, item.slug, item.excerpt, item.body = payload.title.strip(), unique_slug(db, payload.slug or payload.title, item.id), payload.excerpt.strip(), payload.body.strip()
    item.author, item.category, item.status, item.featured = payload.author.strip(), payload.category.strip(), payload.status, payload.featured
    if payload.status == "published" and not was_published: item.published_at = utcnow()
    db.commit()
    return post_dict(item, include_body=True)


@app.delete("/api/admin/posts/{post_id}", status_code=204, dependencies=[Depends(require_admin), Depends(require_csrf)])
def delete_post(post_id: int, db: Session = Depends(db_session)):
    item = db.get(BlogPost, post_id)
    if item is None: raise HTTPException(404, "Post not found")
    db.delete(item); db.commit()


@app.put("/api/admin/beta/{application_id}", dependencies=[Depends(require_admin), Depends(require_csrf)])
def triage_beta(application_id: int, payload: BetaTriageInput, db: Session = Depends(db_session)):
    item = db.get(BetaApplication, application_id)
    if item is None: raise HTTPException(404, "Application not found")
    item.status, item.notes = payload.status, payload.notes.strip(); db.commit()
    return {"updated": True}


@app.put("/api/admin/tickets/{ticket_id}", dependencies=[Depends(require_admin), Depends(require_csrf)])
def triage_ticket(ticket_id: int, payload: TicketTriageInput, db: Session = Depends(db_session)):
    item = db.get(SupportTicket, ticket_id)
    if item is None: raise HTTPException(404, "Ticket not found")
    item.status, item.notes = payload.status, payload.notes.strip(); db.commit()
    return {"updated": True}


def static_file_endpoint(path: Path):
    def serve_file():
        return FileResponse(path)
    return serve_file


for filename in ("marketing.css", "community.css", "marketing.js", "admin.css", "admin-fixes.css", "admin.js", "robots.txt", "sitemap.xml"):
    path = ROOT / filename
    if path.exists():
        app.add_api_route(f"/{filename}", static_file_endpoint(path), methods=["GET"], include_in_schema=False)


@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(ROOT / "admin.html")


@app.get("/{path:path}", include_in_schema=False)
def marketing_page(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Not found")
    return FileResponse(ROOT / "index.html")
