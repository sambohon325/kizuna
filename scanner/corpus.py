from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_CATEGORIES = {"text", "trademark", "visual", "audio"}


@dataclass(frozen=True)
class CorpusRecord:
    record_id: str
    title: str
    category: str
    path: Path | None
    text: str
    rights_basis: str
    evidence_ref: str
    source_url: str


class Corpus:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.records: list[CorpusRecord] = []
        self.errors: list[str] = []
        self.manifest_mtime = -1.0
        self.reload()

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.jsonl"

    def _safe_path(self, value: str) -> Path:
        candidate = (self.root / value).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("path leaves the corpus directory")
        if not candidate.is_file():
            raise ValueError("referenced file does not exist")
        return candidate

    def reload(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.records, self.errors = [], []
        if not self.manifest.exists():
            self.manifest_mtime = -1.0
            return
        self.manifest_mtime = self.manifest.stat().st_mtime
        for line_number, raw_line in enumerate(self.manifest.read_text(encoding="utf-8").splitlines(), 1):
            if not raw_line.strip():
                continue
            try:
                item: dict[str, Any] = json.loads(raw_line)
                record_id = str(item.get("id", "")).strip()
                title = str(item.get("title", "")).strip()
                category = str(item.get("category", "")).strip().lower()
                rights_basis = str(item.get("rights_basis", "")).strip()
                evidence_ref = str(item.get("evidence_ref", "")).strip()
                if not record_id or not title or category not in VALID_CATEGORIES:
                    raise ValueError("id, title, and a valid category are required")
                if not rights_basis or not evidence_ref:
                    raise ValueError("rights_basis and evidence_ref are required")
                text = str(item.get("text", "")).strip()
                path_value = str(item.get("path", "")).strip()
                path = self._safe_path(path_value) if path_value else None
                if category != "trademark" and path is None and not text:
                    raise ValueError("a path or text value is required")
                self.records.append(CorpusRecord(record_id, title, category, path, text, rights_basis, evidence_ref, str(item.get("source_url", "")).strip()))
            except (ValueError, json.JSONDecodeError, OSError) as exc:
                self.errors.append(f"line {line_number}: {exc}")

    def refresh_if_changed(self) -> None:
        mtime = self.manifest.stat().st_mtime if self.manifest.exists() else -1.0
        if mtime != self.manifest_mtime:
            self.reload()

    def status(self) -> dict[str, Any]:
        counts = {category: 0 for category in sorted(VALID_CATEGORIES)}
        for record in self.records:
            counts[record.category] += 1
        return {"records": len(self.records), "categories": counts, "invalid_records": len(self.errors), "manifest_present": self.manifest.exists()}
