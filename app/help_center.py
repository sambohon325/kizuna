from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"
PUBLISHED_DOCS = {
    "USER_GUIDE.md": "Getting started",
    "USER_MANUAL.md": "Getting started",
    "HELP_CENTER.md": "Getting started",
    "ASSISTANT.md": "AI & automation",
    "AI_CREW.md": "AI & automation",
    "AI_PROVIDER_ROUTING.md": "AI & automation",
    "ANIME_CRAFT_COMPASS.md": "Anime craft",
    "CHARACTER_ARC_MAP.md": "Story & characters",
    "CHARACTER_STORY.md": "Story & characters",
    "PRODUCTION_SCOPE.md": "Story & characters",
    "EDITING.md": "Picture & sound",
    "ASSET_REVIEW.md": "Assets & finishing",
    "MEDIA_STORAGE.md": "Assets & finishing",
    "RENDER_FARM.md": "Assets & finishing",
    "KIZUNA_NODE.md": "Assets & finishing",
    "INTEGRATIONS.md": "Studio setup",
    "EDITORIAL_STUDIO.md": "Studio setup",
    "MULTI_WINDOW.md": "Studio setup",
    "COMPLIANCE.md": "Originality & rights",
    "PROFESSIONAL_VERIFICATION.md": "Originality & rights",
}
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from", "get", "help", "how", "i", "in", "is", "it", "my", "need", "of", "on", "operate", "or", "the", "this", "to", "use", "want", "what", "when", "where", "with", "you", "your",
}


@dataclass(frozen=True)
class HelpSection:
    id: str
    document: str
    title: str
    section: str
    category: str
    body: str
    search_text: str


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "overview"


def plain_text(value: str) -> str:
    value = re.sub(r"```.*?```", " ", value, flags=re.S)
    value = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", value)
    value = re.sub(r"[`*_>#|]", "", value)
    value = re.sub(r"^\s*[-+]\s+", "", value, flags=re.M)
    value = re.sub(r"^\s*\d+[.)]\s+", "", value, flags=re.M)
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=1)
def catalog() -> tuple[HelpSection, ...]:
    sections: list[HelpSection] = []
    for filename, category in PUBLISHED_DOCS.items():
        path = DOCS_ROOT / filename
        if not path.exists():
            continue
        document_title = path.stem.replace("_", " ").title()
        current_heading = "Overview"
        body: list[str] = []

        def append_section() -> None:
            text = plain_text("\n".join(body))
            if not text:
                return
            section_id = f"{path.stem.casefold()}--{slug(current_heading)}"
            searchable = f"{document_title} {current_heading} {category} {text}".casefold()
            sections.append(HelpSection(section_id, filename, document_title, current_heading, category, text, searchable))

        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
            if match:
                append_section()
                body = []
                heading = plain_text(match.group(2))
                if len(match.group(1)) == 1:
                    document_title = heading
                    current_heading = "Overview"
                else:
                    current_heading = heading
            else:
                body.append(line)
        append_section()
    return tuple(sections)


def query_terms(query: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9][a-z0-9'-]+", query.casefold()) if len(term) > 1 and term not in STOP_WORDS]


def section_score(section: HelpSection, query: str) -> int:
    terms = query_terms(query)
    if not terms:
        return 0
    heading = f"{section.title} {section.section} {section.category}".casefold()
    score = sum(section.search_text.count(term) for term in terms)
    score += sum(5 for term in terms if term in heading)
    phrase = query.casefold().strip()
    if len(phrase) > 3 and phrase in section.search_text:
        score += 12
    # Prefer the plain-language guide for ordinary questions while retaining
    # specialist manuals as supporting sources for advanced detail.
    if section.document == "USER_GUIDE.md" and score:
        score += 6
    elif section.document == "USER_MANUAL.md" and score:
        score += 3
    return score


def source_dict(section: HelpSection, score: int = 0) -> dict:
    excerpt = section.body if len(section.body) <= 320 else section.body[:317].rsplit(" ", 1)[0] + "…"
    return {
        "id": section.id,
        "title": section.title,
        "section": section.section,
        "category": section.category,
        "excerpt": excerpt,
        "source_path": f"/docs/{section.document}",
        "score": score,
    }


def search_help(query: str, limit: int = 8) -> list[dict]:
    ranked = sorted(((section_score(section, query), section) for section in catalog()), key=lambda item: (-item[0], item[1].title, item[1].section))
    return [source_dict(section, score) for score, section in ranked if score > 0][: max(1, min(limit, 12))]


def answer_help(question: str) -> dict:
    terms = query_terms(question)
    ranked = sorted(((section_score(section, question), section) for section in catalog()), key=lambda item: -item[0])
    matches = [(score, section) for score, section in ranked if score > 0][:3]
    if not matches:
        return {
            "answer": "I couldn't find that in Kizuna's published help library. Try a task word such as story, character, audio, render, AI Crew, storage, or rights. If the question is about an account problem or a bug, contact Kizuna support.",
            "grounded": False,
            "sources": [],
        }
    candidates: list[tuple[int, str]] = []
    for _, section in matches:
        for sentence in re.split(r"(?<=[.!?])\s+", section.body):
            sentence = sentence.strip()
            if len(sentence) < 35 or len(sentence) > 360:
                continue
            score = sum(2 if term in sentence.casefold() else 0 for term in terms)
            if sentence.startswith(("Kizuna", "Use ", "Open ", "Select ", "The ")):
                score += 1
            candidates.append((score, sentence))
    selected: list[str] = []
    for _, sentence in sorted(candidates, key=lambda item: -item[0]):
        if sentence not in selected:
            selected.append(sentence)
        if len(selected) == 3:
            break
    if not selected:
        selected = [matches[0][1].body[:600].strip()]
    return {
        "answer": " ".join(selected),
        "grounded": True,
        "sources": [source_dict(section, score) for score, section in matches],
    }
