# Professional identity and prior-work verification

Kizuna's Creator Profile & Rights screen supports professionals who may legitimately resemble or continue their own earlier work. It is designed for individual artists, writers, directors, studios, estates, and authorized representatives.

## Creator flow

1. Submit a professional name, legal name or organization, role, official website, biography, and identity evidence.
2. Submit individual work claims with title, credited role, release year, stable catalog or registry identifiers, authorization scope, and evidence.
3. Wait for independent review. Creators cannot verify themselves from the browser UI.
4. Once both identity and a work claim are verified, connected compliance scanners receive the narrow verified-work context.

Editing a verified identity returns the identity and all verified work claims to `pending`. A rejected submission retains the reviewer note so the creator can correct the evidence and resubmit.

## Compliance behavior

Verification is not an allowlist for a person's style and never disables compliance. It affects only an exact match to a verified work title or external identifier. That match is retained in the scan as `verified_prior_work`, with its authorization scope, and becomes a warning instead of a release blocker. Approximate matches, unrelated properties, disputed work, and unverified claims follow the normal review workflow.

The no-fan-fiction policy applies to every account, including verified professionals. A professional continuing their own property should describe it as an authorized production tied to the verified work claim, not as fan fiction.

## Reviewer setup

Set `KIZUNA_VERIFICATION_ADMIN_KEY` only in the trusted review service environment. The internal review endpoints require this secret header and are unavailable when it is not configured. Production deployment still needs authenticated reviewer accounts, role-based access, rate limiting, secure evidence storage, sanctions and fraud review, an appeals process, identity-provider integrations, and privacy/retention terms. The current shared-key endpoint is a foundation for that service, not a public verification system.

Every submission and decision creates a verification event. Evidence references should point to secure records rather than embedding sensitive identity documents directly in Kizuna's general database.
