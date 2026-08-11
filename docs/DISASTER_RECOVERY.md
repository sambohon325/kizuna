# Kizuna recovery and restore drills

Kizuna uses two complementary recovery layers:

1. **Infrastructure recovery** restores PostgreSQL and the persistent Coolify volumes after a server loss. Keep the server backup outside the server it protects.
2. **Production archives** preserve a portable project package with its story structure, cast, worlds, scenes, shots, asset inventory, and optionally the referenced generated media.

Neither layer should be treated as a substitute for the other.

## Automated production-archive drill

The `backup-scheduler` checks once per scheduling cycle whether the newest local production backup needs a recovery rehearsal. By default, a drill is due every 168 hours. The drill runs through the durable job worker and:

- verifies the stored SHA-256 audit checksum;
- checks every ZIP entry and rejects unsafe or duplicate paths;
- reads and hashes every archived byte;
- validates the production identity and core collections;
- confirms the recovered media count matches the backup record;
- rebuilds and reopens a recovery catalog in an isolated temporary directory;
- removes every temporary drill file when complete.

It never changes or overwrites the active production. Results remain in the durable job history and appear in **Settings → Operations**. Administrators can also select **Run recovery drill** after making an important backup.

Set `KIZUNA_RESTORE_DRILL_INTERVAL_HOURS` to change the interval. The default weekly schedule is a reasonable starting point.

## What a passing drill proves

A pass proves that the selected Kizuna production archive is present, internally consistent, readable end-to-end, and reconstructable as a recovery catalog on the current server.

It does **not** prove that:

- an off-server copy exists;
- the entire PostgreSQL database can be restored;
- Coolify, DNS, email, AI-provider, or payment credentials have been preserved;
- an S3-only archive can currently be rehearsed automatically;
- a project archive can yet be imported over an active production through the browser.

These are separate controls. Keep infrastructure backups enabled even when every project drill passes.

## Coolify recovery rehearsal

Perform this controlled rehearsal before public trials and after major database changes:

1. Confirm a recent PostgreSQL/server backup and the persistent `storage_data` and `render_data` volumes exist outside the live server.
2. Record the currently deployed Git commit and the database revision shown in **Settings → Operations**.
3. Create a fresh production backup and run **Run recovery drill**. Save the resulting job ID and completion time.
4. Restore the infrastructure backup into an isolated rehearsal server—not over the live server.
5. Deploy the recorded Git commit and allow the `migrate` service to finish.
6. Point the rehearsal environment only at its restored database and copied volumes. Do not reuse live email, Stripe, or worker credentials.
7. Sign in, open several productions, and confirm story, characters, worlds, shots, assets, audit records, and delivery restrictions are present.
8. Open **Settings → Operations** and confirm database, Redis, web, worker, scheduler, scanner, storage, backups, and recovery drill state.
9. Render a short watermarked preview and create a new backup on the rehearsal server.
10. Record the rehearsal date, source backup, restored commit, database revision, observed gaps, and decision to pass or remediate.

Delete the isolated rehearsal environment only after the record is saved. Never perform a first restore test directly against production.

## Current Phase 0 boundary

Kizuna now automates production-archive rehearsals and exposes their evidence. Before public trials, the remaining recovery work is PostgreSQL-backed CI, an isolated full-stack Coolify rehearsal, external alert delivery, and a reviewed project-import design that never overwrites active work without an explicit recovery decision.
