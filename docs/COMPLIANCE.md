# Originality, rights, and release compliance

Kizuna treats compliance as a production gate, not a one-time disclaimer. Story, Creative DNA, characters, worlds, shots, edit, sound, finishing, and master stages each receive a content hash. A passing scan applies only to that exact version; edits automatically make the prior result stale.

The built-in scanner currently detects direct-copy and false-affiliation instructions, including requests to imitate a named source exactly, reproduce protected expression, lift melodies or recordings, or claim an official relationship. It also compares checksums inside the production to surface duplicate source files. Findings identify the triggering material and suggest an original or properly licensed alternative.

Administrators can connect text, trademark, visual, and audio services through the provider-neutral [scanner protocol](COMPLIANCE_SCANNERS.md). A configured service is part of the gate: if it is unavailable or returns invalid data, the scan fails closed and that outage cannot be manually overridden. External match findings can only pass through an evidence-backed reviewer decision, and every decision is added to the audit chain.

This is preliminary risk screening. It is not a comprehensive comparison against published stories, audiovisual works, trademark registries, image indexes, music-rights catalogs, or audio-fingerprint databases. Those checks require licensed/searchable corpora, specialist providers, and qualified review. Kizuna must not label a local heuristic result as legal clearance.

## Release gates

Strict gates are enabled by default. High-resolution continuous or farm masters and delivery links require:

1. a current passing scan for every production stage;
2. creator acknowledgement of responsibility for rights, licenses, disclosures, and released content; and
3. a release-clearance record from counsel, a rights-and-clearance professional, or an authorized studio reviewer, including evidence references where available.

Preview renders remain available so creators can revise flagged work. Failed or stale material cannot be released through Kizuna.

The asset rights register records source type, rights holder, license, permitted uses, territories, expiry, and evidence references against indexed production files. Licensed, commissioned, stock, and public-domain claims require evidence. Adding or changing a rights record or finding resolution makes an older release clearance stale.

## Product-facing legal notice

> Kizuna provides creative tools, automated risk screening, and production records. It does not provide legal advice or guarantee that content is original, non-infringing, registrable, or cleared for a particular use or jurisdiction. Automated systems can miss similarities and cannot determine every copyright, trademark, publicity, privacy, contract, music, or licensing issue. The creator is responsible for reviewing inputs and outputs, obtaining all necessary permissions and licenses, making required disclosures, and deciding whether and how content is released. Commercial or high-risk releases should receive qualified legal and rights-clearance review.

This notice is an honest product disclosure, not a promise that liability can be eliminated. Binding Terms of Service, warranty limitations, indemnity provisions, retention rules, privacy language, and jurisdiction-specific notices must be prepared and reviewed by qualified counsel before public launch.

## Audit ledger

Compliance scans, acknowledgement, release clearance, and registered output files create project audit events. Each event contains the prior event hash, making later changes detectable. Output records include the asset key, representation, location, SHA-256 checksum, size, and status where available.

The current database chain is tamper-evident, not independently notarized. A production deployment should add signed events, trusted timestamps, append-only/WORM export, secure identity, retention policy, access logs, and periodic external anchoring. An audit trail can support provenance and investigation but does not guarantee admissibility, prove non-infringement, or prevent legal claims.

## Adapter status

The transport, fail-closed behavior, provider evidence storage, asset-rights records, and reviewer-resolution workflow are implemented. Actual coverage depends on the corpus and jurisdiction of each service the studio connects. Concrete licensed-corpus adapters and signed/notarized audit exports remain production work.
