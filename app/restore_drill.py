from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy.orm import Session

from app.job_queue import update_progress
from app.models import DurableJob, ProjectBackup
from app.operations import verify_local_backup


def _local_archive(backup: ProjectBackup, storage_root: Path) -> Path:
    backend, separator, key = backup.storage_key.partition(":")
    if not separator:
        backend, key = "local", backup.storage_key
    if backend != "local":
        raise ValueError("Automated recovery drills currently require a local backup archive.")
    root = storage_root.resolve()
    archive = (root / key).resolve()
    if root not in archive.parents or not archive.is_file():
        raise FileNotFoundError("The local backup archive is missing.")
    return archive


def execute_restore_drill_job(db: Session, job: DurableJob, storage_root: Path) -> dict:
    started = time.perf_counter()
    backup = db.get(ProjectBackup, int(job.payload.get("backup_id") or 0))
    if backup is None or backup.status != "completed":
        raise RuntimeError("The selected completed backup no longer exists.")
    archive_path = _local_archive(backup, storage_root)
    update_progress(db, job, 15, "Verifying the source backup and its audit checksum")
    verification = verify_local_backup(backup, storage_root)
    db.flush()

    update_progress(db, job, 40, "Reading every archived file without changing production data")
    recovered_assets = []
    expanded_bytes = 0
    with ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        names: set[str] = set()
        for entry in archive.infolist():
            normalized = Path(entry.filename.replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts:
                raise ValueError("The backup contains an unsafe archive path.")
            if entry.is_dir():
                continue
            if entry.filename in names:
                raise ValueError("The backup contains duplicate archive paths.")
            names.add(entry.filename)
            digest = hashlib.sha256()
            size = 0
            with archive.open(entry) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
            if size != entry.file_size:
                raise ValueError(f"Recovered size does not match the archive catalog for {entry.filename}.")
            expanded_bytes += size
            if entry.filename.startswith("assets/"):
                recovered_assets.append({"path": entry.filename, "size_bytes": size, "sha256": digest.hexdigest()})

    project = manifest.get("project") or {}
    required = {"id", "title", "status", "created_at"}
    if not required.issubset(project) or int(project.get("id") or 0) != backup.project_id:
        raise ValueError("The recovered production identity is incomplete or incorrect.")
    collections = {name: len(project.get(name) or []) for name in ("characters", "locations", "scenes")}
    if any(not isinstance(project.get(name, []), list) for name in collections):
        raise ValueError("A recovered production collection has an invalid structure.")
    if len(recovered_assets) != backup.asset_count:
        raise ValueError("The recovered media count does not match the backup audit record.")

    update_progress(db, job, 75, "Rebuilding and reopening the temporary recovery catalog")
    catalog = {
        "format": "kizuna-recovery-catalog",
        "version": 1,
        "source_backup_id": backup.id,
        "source_checksum_sha256": backup.checksum_sha256,
        "project": project,
        "asset_inventory": manifest.get("assets") or [],
        "recovered_files": recovered_assets,
    }
    with tempfile.TemporaryDirectory(prefix="kizuna-restore-drill-") as temp_dir:
        catalog_path = Path(temp_dir) / "recovery-catalog.json"
        encoded = json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode("utf-8")
        catalog_path.write_bytes(encoded)
        reopened = json.loads(catalog_path.read_text(encoding="utf-8"))
        if reopened.get("source_checksum_sha256") != backup.checksum_sha256 or reopened.get("project", {}).get("title") != project["title"]:
            raise ValueError("The temporary recovery catalog could not be reopened consistently.")
        catalog_checksum = hashlib.sha256(catalog_path.read_bytes()).hexdigest()

    update_progress(db, job, 95, "Recovery rehearsal passed; removing temporary files")
    return {
        "passed": True,
        "backup_id": backup.id,
        "project_id": backup.project_id,
        "project_title": project["title"],
        "archive_entries": verification["entries"],
        "expanded_bytes": expanded_bytes,
        "recovered_assets": len(recovered_assets),
        "project_counts": collections,
        "catalog_checksum_sha256": catalog_checksum,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "temporary_files_removed": True,
        "message": "The backup was read end-to-end and rebuilt as a temporary recovery catalog without changing the active production.",
    }
