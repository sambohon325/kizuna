# Marketing beta and support system

Kizuna's marketing service keeps early-access outreach and website support separate from production accounts and creative data. It uses its own SQLite database under `/data`, its own administrator session, and never queries the Anime Studio database.

## Implemented beta intake

The public beta application records:

- name and contact email;
- creator role and self-described experience level;
- a summary of the original project the applicant wants to explore;
- the outcome they hope to test; and
- optional high-level hardware or production-tool context.

Repeated active applications from the same normalized email are acknowledged without creating duplicates. The administrator can move an applicant through `new`, `reviewing`, `invited`, `waitlisted`, and `closed`, with private notes.

The form is an application, not automatic access. This lets Kizuna invite small cohorts based on the workflows being tested and the support capacity available. The Anime Studio trial remains a separate protected signup system.

## Implemented ticket intake

The public form accepts bugs, account questions, billing questions, feature requests, feedback, and other support issues. It records an impact level, summary, description, optional page/workspace, optional device/browser context, and contact email. Every valid submission receives a random reference such as `KZ-260812-A1B2C3`.

Administrators triage tickets through `open`, `investigating`, `resolved`, and `closed`, with private notes. Attachments are intentionally not supported in the first version so visitors cannot upload executable files, confidential story media, or large data into the marketing service.

## Privacy and safety boundary

- Forms tell visitors not to submit passwords, API keys, or confidential media.
- Honeypot fields reduce basic automated submissions.
- Per-network in-memory limits slow repeated submissions and login attempts.
- Admin mutations require both a valid signed session and a matching CSRF token.
- Blog articles are stored as plain text with limited paragraph, heading, and quote presentation; administrators cannot publish arbitrary HTML or scripts.
- Beta and ticket records do not grant application access or change production entitlements.

These controls are suitable for a controlled preview, not a large public launch. A privacy policy must define collection purpose, retention, deletion requests, contact practices, and subprocessors before public intake opens.

## Beta operating plan

### Cohort 0 — internal and trusted reviewers

- 5–10 people under direct contact;
- validate the application, invitation, onboarding, and ticket lifecycle;
- manually acknowledge every issue; and
- establish severity definitions and response expectations.

### Cohort 1 — closed creator beta

- 20–50 invited creators across Beginner, Intermediate, and Professional modes;
- assign testing themes by cohort rather than asking everyone to test everything;
- connect applicants to actual Kizuna accounts through explicit invitations;
- review weekly completion, drop-off, support volume, render reliability, and cost; and
- publish a clear list of known limitations.

### Cohort 2 — expanded beta

- add named support ownership and response targets;
- introduce consented product analytics and in-app feedback context;
- add Turnstile and durable Redis-backed abuse limits;
- send transactional application/ticket confirmations and admin alerts;
- add a public status page and searchable known-issues area; and
- formalize data retention and deletion workflows.

### Public trial gate

Do not treat the public marketing form as the launch gate. Public trial signup should open only after account recovery, email verification, Turnstile, billing tests, isolated restore rehearsal, monitoring, legal pages, support ownership, and incident procedures are all verified on the deployed stack.

## Next technical slices

1. Add SMTP confirmations and internal notifications without exposing submitted details in logs.
2. Add Cloudflare Turnstile and Redis-backed rate limits shared across replicas and restarts.
3. Link an accepted beta record to a single-use Anime Studio invitation while preserving separate databases through a narrow signed service call.
4. Add named marketing administrators, MFA, roles, and immutable admin audit events.
5. Add ticket replies, requester-visible status lookup using a separate secret, and a searchable known-issues page.
6. Add configurable retention, export, and deletion workflows for privacy requests.
