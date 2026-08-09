from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from scanner.config import settings
from scanner.corpus import Corpus, VALID_CATEGORIES
from scanner.matching import scan

app = FastAPI(title="Kizuna Reference Scanner", version="0.1.0")
corpus = Corpus(Path(settings.corpus_directory))


class ScanRequest(BaseModel):
    protocol_version: str
    project_id: int
    stage: str
    categories: list[str] = Field(default_factory=list, max_length=4)
    subject_hash: str
    content: dict[str, Any]
    verified_professional_works: list[dict[str, Any]] = Field(default_factory=list)


def require_key(authorization: str | None, expected: str) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if expected and (not token or not secrets.compare_digest(token, expected)):
        raise HTTPException(401, "Invalid scanner credentials")


@app.get("/health")
def health():
    corpus.refresh_if_changed()
    return {"status": "ok", "service": "kizuna-reference-scanner", **corpus.status()}


@app.get("/corpus")
def corpus_status(authorization: str | None = Header(default=None)):
    if not settings.admin_key:
        raise HTTPException(503, "Scanner administration is disabled until an admin key is configured")
    require_key(authorization, settings.admin_key)
    corpus.refresh_if_changed()
    return {**corpus.status(), "errors": corpus.errors[:100]}


@app.post("/corpus/reload")
def reload_corpus(authorization: str | None = Header(default=None)):
    if not settings.admin_key:
        raise HTTPException(503, "Scanner administration is disabled until an admin key is configured")
    require_key(authorization, settings.admin_key)
    corpus.reload()
    return {"status": "reloaded", **corpus.status(), "errors": corpus.errors[:100]}


@app.post("/scan")
def scan_content(payload: ScanRequest, authorization: str | None = Header(default=None)):
    require_key(authorization, settings.api_key)
    if payload.protocol_version != "kizuna-compliance-v1":
        raise HTTPException(400, "Unsupported protocol version")
    categories = {item.lower() for item in payload.categories}
    if not categories or categories - VALID_CATEGORIES:
        raise HTTPException(422, "At least one supported category is required")
    corpus.refresh_if_changed()
    matches = scan(payload.content, categories, corpus.records, settings)
    status = "blocked" if any(item["severity"] == "block" for item in matches) else "review" if matches else "pass"
    return {"status": status, "matches": matches, "corpus_records": len(corpus.records)}
