# Production storage and delivery

Kizuna's Production Vault packages a project's structured creative data and, when enabled, its locally available generated media into a portable ZIP archive. Every archive records its SHA-256 checksum and remains downloadable until its retention policy removes it.

## Local and Coolify storage

Local development writes vault data to `storage/`. The Coolify-ready Compose configuration mounts `/app/storage` as a persistent volume, separately from generated render media and PostgreSQL data.

Configure the provider and default policy with:

```env
KIZUNA_STORAGE_BACKEND=local
KIZUNA_STORAGE_DIRECTORY=/app/storage
KIZUNA_BACKUP_RETENTION_DAYS=30
KIZUNA_BACKUP_MAX_COPIES=10
```

Each production may override retention days, maximum backup copies, and whether generated media is included. Creating a backup immediately enforces that policy. Remote S3-compatible storage is the next provider planned for this abstraction.

## Secure delivery links

A delivery link is tied to an asset owned by one production. The creator chooses its expiration and download limit. Kizuna stores only a SHA-256 hash of the random link secret, increments the counter on each download, and returns `410 Gone` after expiration, revocation, or limit exhaustion.

The complete URL is shown only when it is created. Copy it then; existing links can be audited or revoked but their secret cannot be recovered from the database.
