from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


class LocalProductionStorage:
    """Safe local object store used in development and single-server installs."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError("Storage key escapes the configured root")
        return path

    def create_backup(self, project_id: int, filename: str, manifest: dict, assets: list[Path]) -> tuple[str, int, str, int]:
        key = f"backups/project-{project_id}/{filename}"
        destination = self.resolve(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        included = 0
        with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
            seen: set[str] = set()
            for source in assets:
                source = source.resolve()
                if not source.is_file() or source.name in seen:
                    continue
                archive.write(source, f"assets/{source.name}")
                seen.add(source.name)
                included += 1
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        return key, destination.stat().st_size, digest, included

    def delete(self, key: str) -> None:
        path = self.resolve(key)
        if path.is_file():
            path.unlink()
