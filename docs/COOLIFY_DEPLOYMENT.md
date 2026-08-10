# Coolify staging deployment

Deploy Kizuna as a Docker Compose resource from `https://github.com/sambohon325/kizuna`, branch `main`, base directory `/`, compose file `/docker-compose.yml`.

## Public routing

Assign only the `web` service this domain:

`https://app.kizuna.technology:8000`

The `:8000` tells Coolify which container port to proxy; visitors still use the normal URL `https://app.kizuna.technology`. Do not assign public domains or host port mappings to Postgres, Redis, the compliance scanner, workers, or migration service.

DNS needs an `A` record named `app` pointing to the public IPv4 address of the server running this resource. If IPv6 is configured, its `AAAA` record must point to that same deployment server or be removed until IPv6 routing is ready.

## Required Coolify variables

Set these before the first deployment. Mark all secrets as secret/masked and never commit their values.

- `KIZUNA_PUBLIC_URL=https://app.kizuna.technology`
- `KIZUNA_MARKETING_URL=https://kizuna.technology`
- `POSTGRES_USER=kizuna`
- `POSTGRES_DB=kizuna`
- `POSTGRES_PASSWORD` — unique random hex secret
- `KIZUNA_BOOTSTRAP_ADMIN_KEY` — unique random secret used only for first administrator setup
- `KIZUNA_WORKER_ENROLLMENT_SECRET` — unique random secret for render-node enrollment
- `KIZUNA_SELF_HOSTED_SCANNER_API_KEY` — unique random secret shared by Kizuna and its scanner
- `KIZUNA_SCANNER_ADMIN_KEY` — separate unique random scanner-administration secret
- `KIZUNA_GENERATION_PROVIDER=mock` for the first staging smoke test; change routing only after workers/providers are connected
- `KIZUNA_TRIAL_DAYS=7`
- `KIZUNA_TRIAL_SIGNUP_ENABLED=false` while staging is private
- `KIZUNA_TRIAL_EXPORT_SECONDS=60`
- `KIZUNA_TRIAL_WATERMARK=KIZUNA TRIAL | kizuna.technology`
- `KIZUNA_EMAIL_VERIFICATION_REQUIRED=false` until SMTP is tested
- `KIZUNA_ACCOUNT_TOKEN_HOURS=1`
- `KIZUNA_ACCOUNT_EMAIL_LIMIT_PER_HOUR=5`
- `KIZUNA_SMTP_HOST`, `KIZUNA_SMTP_PORT`, `KIZUNA_SMTP_USERNAME`, `KIZUNA_SMTP_PASSWORD`, `KIZUNA_SMTP_FROM_EMAIL`, and `KIZUNA_SMTP_FROM_NAME` for any standard SMTP provider
- `KIZUNA_SMTP_STARTTLS=true` for port 587, or set STARTTLS false and `KIZUNA_SMTP_SSL=true` when the provider requires implicit TLS

Generate a safe 64-character hex secret in PowerShell with:

```powershell
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
```

Run it separately for each secret. Keep the values in a password manager.

## First deployment check

1. Deploy and watch the build logs.
2. The `migrate` service should exit successfully after upgrading the database. It is intentionally excluded from ongoing health checks.
3. `postgres`, `redis`, `web`, `job-worker`, `backup-scheduler`, and `compliance-scanner` should remain running; the web health check calls `/api/health`.
4. Open `https://app.kizuna.technology/api/health` and confirm `status` is `ok` and a database revision is present.
5. Open `https://app.kizuna.technology/setup`, enter the bootstrap key, and create the first administrator.
6. Sign in, create a staging production, sign out, and sign back in.
7. Confirm named volumes exist for Postgres, Redis, renders, storage, and the scanner corpus before uploading irreplaceable media.

Keep `KIZUNA_TRIAL_SIGNUP_ENABLED=false` while SMTP and recovery are tested. First configure SMTP with `KIZUNA_EMAIL_VERIFICATION_REQUIRED=false`, redeploy, request a password reset, and complete it. Then set verification to true, create and verify a test trial account, and confirm a second use of either link fails. Public signup should remain off until billing upgrades, broader signup abuse controls, and a restore drill are complete.
