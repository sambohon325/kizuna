# Production storage and delivery

Kizuna's Production Vault packages a project's structured creative data and, when enabled, its locally available generated media into a portable ZIP archive. Every archive records its SHA-256 checksum and remains downloadable until its retention policy removes it.

## Local and off-server storage

Local development writes vault data to `storage/`. The Coolify-ready Compose configuration mounts `/app/storage` as a persistent volume, separately from generated render media and PostgreSQL data.

Configure the provider and default policy with:

```env
KIZUNA_STORAGE_BACKEND=local
KIZUNA_STORAGE_DIRECTORY=/app/storage
KIZUNA_BACKUP_RETENTION_DAYS=30
KIZUNA_BACKUP_MAX_COPIES=10
```

Each production may choose local or S3-compatible storage and override retention days, maximum backup copies, whether generated media is included, and the automatic backup interval. Creating a backup immediately enforces that policy.

The Compose stack includes a dedicated `backup-scheduler` service. It checks due production schedules without requiring a browser tab to remain open, records success or failure, and calculates the next run. Local and scheduler services share the same persistent render and vault volumes.

The scheduler also queues a weekly, non-destructive recovery drill for the newest local production archive. The worker reads every archived byte, rebuilds and reopens a temporary recovery catalog, validates the project and media counts, then removes the temporary files. The result appears in **Settings → Operations** and durable job history. See [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) for what this proves and the separate full-stack rehearsal procedure.

## S3-compatible vault

Kizuna supports AWS S3 and services that expose an S3-compatible API, including Cloudflare R2, MinIO, and Backblaze. Configure the server or Coolify environment:

```env
KIZUNA_S3_BUCKET=studio-vault
KIZUNA_S3_ENDPOINT_URL=https://optional-provider-endpoint
KIZUNA_S3_REGION=optional-region
KIZUNA_S3_PREFIX=kizuna
AWS_ACCESS_KEY_ID=provided-outside-source-control
AWS_SECRET_ACCESS_KEY=provided-outside-source-control
AWS_SESSION_TOKEN=optional-temporary-session-token
```

AWS deployments may use the normal SDK credential chain instead of static keys. Kizuna never returns credential values to the browser. Off-server downloads use short-lived presigned URLs, while the database retains the archive checksum, size, asset count, and destination.

The local Python process can create local backups without Boto3 configuration. The production image installs Boto3 for S3-compatible uploads.

## Secure delivery links

A delivery link is tied to an asset owned by one production. The creator chooses its expiration and download limit. Kizuna stores only a SHA-256 hash of the random link secret, increments the counter on each download, and returns `410 Gone` after expiration, revocation, or limit exhaustion.

The complete URL is shown only when it is created. Copy it then; existing links can be audited or revoked but their secret cannot be recovered from the database.
