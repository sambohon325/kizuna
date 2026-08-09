from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
from array import array
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from scanner.config import ScannerSettings
from scanner.corpus import CorpusRecord

TOKEN = re.compile(r"[\w']+", re.UNICODE)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".mp4", ".mov", ".webm"}


def strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in strings(item)]
    return []


def normalized(value: str) -> str:
    return " ".join(TOKEN.findall(value.casefold()))


def shingles(value: str, width: int = 5) -> set[tuple[str, ...]]:
    words = normalized(value).split()
    if len(words) < width:
        return {tuple(words)} if words else set()
    return {tuple(words[index:index + width]) for index in range(len(words) - width + 1)}


def text_score(candidate: str, reference: str) -> float:
    left, right = shingles(candidate), shingles(reference)
    return len(left & right) / len(left | right) if left and right else 0.0


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_hash(path: Path) -> int:
    with Image.open(path) as source:
        image = source.convert("L").resize((9, 8))
        pixels = list(image.getdata())
    bits = [pixels[row * 9 + column] > pixels[row * 9 + column + 1] for row in range(8) for column in range(8)]
    return sum(int(bit) << index for index, bit in enumerate(bits))


def image_score(candidate: Path, reference: Path) -> float:
    if file_hash(candidate) == file_hash(reference):
        return 1.0
    return 1.0 - ((image_hash(candidate) ^ image_hash(reference)).bit_count() / 64)


def ffmpeg_path(settings: ScannerSettings) -> str:
    if settings.ffmpeg_path:
        return settings.ffmpeg_path
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("ffmpeg is unavailable") from exc


def audio_envelope(path: Path, settings: ScannerSettings) -> list[float]:
    command = [ffmpeg_path(settings), "-v", "error", "-i", str(path), "-t", "180", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"]
    output = subprocess.run(command, capture_output=True, timeout=45, check=True).stdout
    samples = array("h"); samples.frombytes(output)
    window = 2000
    values = []
    for start in range(0, len(samples), window):
        chunk = samples[start:start + window]
        values.append(math.sqrt(sum(sample * sample for sample in chunk) / max(1, len(chunk))))
    peak = max(values, default=0.0)
    return [value / peak for value in values] if peak else []


def resample(values: list[float], size: int = 256) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return values * size
    return [values[round(index * (len(values) - 1) / (size - 1))] for index in range(size)]


def audio_score(candidate: Path, reference: Path, settings: ScannerSettings) -> float:
    if file_hash(candidate) == file_hash(reference):
        return 1.0
    left, right = resample(audio_envelope(candidate, settings)), resample(audio_envelope(reference, settings))
    if not left or not right:
        return 0.0
    left_mean, right_mean = sum(left) / len(left), sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    denominator = math.sqrt(sum((a - left_mean) ** 2 for a in left) * sum((b - right_mean) ** 2 for b in right))
    return max(0.0, numerator / denominator) if denominator else 0.0


def resolve_media(value: str, settings: ScannerSettings) -> Path | None:
    mappings = (("/renders/", Path(settings.render_directory).resolve()), ("/storage/", Path(settings.storage_directory).resolve()))
    for prefix, root in mappings:
        if value.startswith(prefix):
            candidate = (root / value.removeprefix(prefix)).resolve()
            if root in candidate.parents and candidate.is_file() and candidate.suffix.lower() in MEDIA_SUFFIXES and candidate.stat().st_size <= settings.max_input_bytes:
                return candidate
    return None


def match_result(record: CorpusRecord, category: str, score: float, evidence: str) -> dict[str, Any]:
    noun = {"text": "text passage", "trademark": "reference title", "visual": "image", "audio": "recording"}[category]
    return {"severity": "block" if score >= 0.98 else "review", "score": round(score, 4), "source": record.title, "source_id": record.record_id, "url": record.source_url, "message": f"A possible {noun} match needs review.", "evidence": evidence[:500], "suggestion": "Revise the material or have a qualified reviewer document the applicable rights and clearance decision."}


def scan(content: Any, categories: set[str], records: list[CorpusRecord], settings: ScannerSettings) -> list[dict[str, Any]]:
    values = strings(content)
    narrative = "\n".join(value for value in values if not value.startswith(("/renders/", "/storage/")))[:settings.max_input_bytes]
    short_values = {normalized(value) for value in values if 2 <= len(normalized(value).split()) <= 12}
    media = [path for value in values if (path := resolve_media(value, settings))]
    matches: list[dict[str, Any]] = []
    for record in records:
        if record.category not in categories:
            continue
        try:
            if record.category == "text":
                reference = record.text or record.path.read_text(encoding="utf-8")
                score = text_score(narrative, reference)
                if score >= settings.text_threshold:
                    matches.append(match_result(record, "text", score, f"Five-word phrase overlap score: {score:.1%}."))
            elif record.category == "trademark":
                reference = normalized(record.text or record.title)
                score = max((SequenceMatcher(None, value, reference).ratio() for value in short_values), default=0.0)
                if score >= settings.title_threshold:
                    matches.append(match_result(record, "trademark", score, f"Reference-title similarity score: {score:.1%}. This is not an official trademark search."))
            elif record.category == "visual" and record.path:
                score = max((image_score(path, record.path) for path in media if path.suffix.lower() in IMAGE_SUFFIXES), default=0.0)
                if score >= settings.visual_threshold:
                    matches.append(match_result(record, "visual", score, f"Perceptual image similarity score: {score:.1%}."))
            elif record.category == "audio" and record.path:
                score = max((audio_score(path, record.path, settings) for path in media if path.suffix.lower() not in IMAGE_SUFFIXES), default=0.0)
                if score >= settings.audio_threshold:
                    matches.append(match_result(record, "audio", score, f"Acoustic-envelope similarity score: {score:.1%}; composition and melody clearance still require specialist review."))
        except (OSError, UnicodeError, UnidentifiedImageError, subprocess.SubprocessError, RuntimeError):
            continue
    return sorted(matches, key=lambda item: item["score"], reverse=True)[:100]
