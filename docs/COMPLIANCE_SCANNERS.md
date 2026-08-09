# Kizuna compliance scanner protocol

Kizuna can call studio-hosted, commercial, or homebrew originality services without coupling the production workflow to one vendor. Add an endpoint under **Settings → Originality & rights scanners**, choose the categories it covers, and keep its secret in the environment variable named by the integration profile.

## Request

Kizuna sends `POST /scan` by default with `Content-Type: application/json` and `X-Kizuna-Protocol: kizuna-compliance-v1`. The path, timeout, authentication header, and authentication scheme can be changed in the integration configuration.

```json
{
  "protocol_version": "kizuna-compliance-v1",
  "project_id": 42,
  "stage": "story",
  "categories": ["text", "trademark"],
  "subject_hash": "sha256-of-current-stage",
  "content": {"project": {}, "story": {}},
  "verified_professional_works": [
    {
      "claim_id": 7,
      "title": "Signal Garden",
      "external_ids": ["catalog:signal-garden-2024"],
      "authorization_scope": "Verified scope supplied by the reviewer"
    }
  ]
}
```

The connected service receives the current stage snapshot. Studios should only connect trusted endpoints, disclose this transfer to creators, apply appropriate retention terms, and avoid sending confidential work to an unapproved provider. A multi-tenant deployment should add tenant-scoped endpoint allowlists and outbound network controls.

## Response

Return a JSON object no larger than 1 MB. `status` may be `pass`, `review`, or `blocked`; `matches` may contain up to 100 results.

```json
{
  "status": "review",
  "matches": [
    {
      "severity": "review",
      "score": 0.91,
      "source": "Corpus record or registry result",
      "source_id": "catalog:signal-garden-2024",
      "url": "https://evidence.example/result/123",
      "message": "A possible passage match needs review.",
      "evidence": "Short provider-supplied comparison evidence.",
      "suggestion": "Revise the passage or document applicable rights."
    }
  ]
}
```

Kizuna sanitizes and bounds provider data, stores request and response hashes, preserves match evidence, and records the provider run. Provider errors, invalid responses, timeouts, or responses over 1 MB block the stage. Availability failures cannot be cleared as false positives; the service must be restored or disabled and the current stage scanned again.

Scanners should return a stable `source_id` whenever possible. Kizuna only treats a result as a verified professional self-match when that identifier exactly matches an independently verified work claim, or when the normalized source title exactly matches the verified claim title. A fuzzy name or general professional badge never suppresses a finding.

## Categories and configuration

Supported categories are `text`, `trademark`, `visual`, and `audio`. Built-in scanner slots infer their category from their key. Custom compliance integrations should include a `categories` array in configuration.

Optional configuration fields are:

- `scan_path` — defaults to `/scan`;
- `timeout_seconds` — 1–120 seconds, default 30;
- `auth_header` — defaults to `Authorization`;
- `auth_scheme` — defaults to `Bearer`; and
- `categories` — one or more supported categories.

Secrets are read at request time from the integration's named environment variable and are never returned through the settings API.

## Bundled self-hosted reference scanner

The Docker stack includes `compliance-scanner`, an internal service at `http://compliance-scanner:8090`. In Studio Settings, enable **Kizuna self-hosted reference scanner** and keep all four categories in its configuration. Set the same strong value for `KIZUNA_SELF_HOSTED_SCANNER_API_KEY` on Kizuna; Docker passes it to the scanner as its API key.

The scanner only indexes records listed in `/data/corpus/manifest.jsonl`. Every newline-delimited JSON record must include `id`, `title`, `category`, `rights_basis`, and `evidence_ref`. Text, visual, and audio records also need a relative `path` beneath the corpus directory, or text may use an inline `text` value. Paths cannot escape the corpus directory.

```json
{"id":"studio:owned-pilot-v1","title":"Owned Pilot","category":"text","path":"owned-pilot.txt","rights_basis":"Studio-owned production","evidence_ref":"contract:2026-014","source_url":"https://rights.example/studio/owned-pilot"}
{"id":"registry:example-title","title":"Example Title","category":"trademark","text":"Example Title","rights_basis":"Licensed title-clearance dataset","evidence_ref":"license:titles-2026"}
{"id":"studio:owned-frame","title":"Owned Frame","category":"visual","path":"owned-frame.png","rights_basis":"Studio-owned production","evidence_ref":"asset-ledger:44"}
```

Records without documented rights metadata are rejected. Mount or copy only material the studio is authorized to use for matching; Kizuna does not ship a scraped catalog of protected works. `GET /health` exposes aggregate counts. `GET /corpus` and `POST /corpus/reload` require the scanner admin bearer key; administration stays disabled until `KIZUNA_SCANNER_ADMIN_KEY` is set.

This service provides reference-match signals, not legal conclusions. The title check is not a trademark registry search; the audio check detects recording similarity rather than composition or melody ownership; and perceptual image hashes are not a substitute for visual-rights review.
