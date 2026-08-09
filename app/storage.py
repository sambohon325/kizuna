from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def create_archive(destination: Path, manifest: dict, assets: list[Path]) -> tuple[int, str, int]:
    included = 0
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        seen: set[str] = set()
        for source in assets:
            source = source.resolve()
            if not source.is_file() or source.name in seen:
                continue
            archive.write(source, f"assets/{source.name}")
            seen.add(source.name); included += 1
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return destination.stat().st_size, digest, included


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
        size, digest, included = create_archive(destination, manifest, assets)
        return key, size, digest, included

    def delete(self, key: str) -> None:
        path = self.resolve(key)
        if path.is_file():
            path.unlink()


class S3ProductionStorage:
    """S3-compatible object store. Credentials stay in the standard SDK provider chain."""

    def __init__(self, bucket: str, endpoint_url: str = "", region: str = "", prefix: str = "kizuna", client=None):
        self.bucket = bucket.strip()
        self.endpoint_url = endpoint_url.strip() or None
        self.region = region.strip() or None
        self.prefix = prefix.strip().strip("/")
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self.bucket)

    @property
    def client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("s3", endpoint_url=self.endpoint_url, region_name=self.region)
        return self._client

    def object_key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def create_backup(self, project_id: int, filename: str, manifest: dict, assets: list[Path]) -> tuple[str, int, str, int]:
        if not self.configured:
            raise RuntimeError("S3 storage is not configured")
        key = f"backups/project-{project_id}/{filename}"
        with tempfile.TemporaryDirectory(prefix="kizuna-s3-backup-") as temp_dir:
            archive = Path(temp_dir) / filename
            size, digest, included = create_archive(archive, manifest, assets)
            self.client.upload_file(str(archive), self.bucket, self.object_key(key), ExtraArgs={"ContentType": "application/zip", "Metadata": {"sha256": digest}})
        return key, size, digest, included

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self.object_key(key))

    def presigned_download(self, key: str, filename: str, expires_seconds: int = 900) -> str:
        return self.client.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": self.object_key(key), "ResponseContentDisposition": f'attachment; filename="{filename}"'}, ExpiresIn=expires_seconds)

    def test_connection(self) -> tuple[bool, str]:
        if not self.configured:
            return False, "Add a bucket name to enable off-server backups."
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True, "Off-server storage is ready."
        except Exception as exc:
            return False, f"Could not reach the configured bucket: {str(exc)[:180]}"
