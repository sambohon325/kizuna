import json

from fastapi.testclient import TestClient
from PIL import Image

import scanner.main as scanner_main
from scanner.config import ScannerSettings
from scanner.corpus import Corpus
from scanner.matching import scan


def test_corpus_requires_rights_metadata_and_confines_paths(tmp_path):
    (tmp_path / "owned.txt").write_text("An original studio passage with enough words for a useful comparison.", encoding="utf-8")
    records = [
        {"id": "owned", "title": "Owned", "category": "text", "path": "owned.txt", "rights_basis": "studio owned", "evidence_ref": "ledger:1"},
        {"id": "missing-rights", "title": "No rights", "category": "text", "path": "owned.txt"},
        {"id": "escape", "title": "Escape", "category": "text", "path": "../outside.txt", "rights_basis": "unknown", "evidence_ref": "none"},
    ]
    (tmp_path / "manifest.jsonl").write_text("\n".join(json.dumps(item) for item in records), encoding="utf-8")
    corpus = Corpus(tmp_path)
    assert [item.record_id for item in corpus.records] == ["owned"]
    assert len(corpus.errors) == 2


def test_scanner_matches_text_titles_and_images(tmp_path):
    image_path = tmp_path / "reference.png"
    Image.new("RGB", (32, 32), "#0fe0d0").save(image_path)
    records = [
        {"id": "text:1", "title": "Owned script", "category": "text", "text": "the silver train crosses the quiet valley beneath a fractured moon", "rights_basis": "studio owned", "evidence_ref": "ledger:2"},
        {"id": "title:1", "title": "Signal Garden", "category": "trademark", "text": "Signal Garden", "rights_basis": "licensed dataset", "evidence_ref": "license:3"},
        {"id": "image:1", "title": "Owned frame", "category": "visual", "path": "reference.png", "rights_basis": "studio owned", "evidence_ref": "ledger:4"},
    ]
    (tmp_path / "manifest.jsonl").write_text("\n".join(json.dumps(item) for item in records), encoding="utf-8")
    corpus = Corpus(tmp_path)
    settings = ScannerSettings(render_directory=str(tmp_path), storage_directory=str(tmp_path), text_threshold=0.3)
    matches = scan({"project": {"title": "Signal Garden"}, "story": "the silver train crosses the quiet valley beneath a fractured moon", "frame": "/renders/reference.png"}, {"text", "trademark", "visual"}, corpus.records, settings)
    assert {item["source_id"] for item in matches} == {"text:1", "title:1", "image:1"}


def test_scanner_api_auth_and_protocol(tmp_path, monkeypatch):
    monkeypatch.setattr(scanner_main.settings, "api_key", "scanner-secret")
    monkeypatch.setattr(scanner_main, "corpus", Corpus(tmp_path))
    client = TestClient(scanner_main.app)
    payload = {"protocol_version": "kizuna-compliance-v1", "project_id": 1, "stage": "story", "categories": ["text"], "subject_hash": "abc", "content": {}, "verified_professional_works": []}
    assert client.post("/scan", json=payload).status_code == 401
    response = client.post("/scan", json=payload, headers={"Authorization": "Bearer scanner-secret"})
    assert response.status_code == 200
    assert response.json()["status"] == "pass"
