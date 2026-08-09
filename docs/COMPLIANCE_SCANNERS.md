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
  "content": {"project": {}, "story": {}}
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
      "url": "https://evidence.example/result/123",
      "message": "A possible passage match needs review.",
      "evidence": "Short provider-supplied comparison evidence.",
      "suggestion": "Revise the passage or document applicable rights."
    }
  ]
}
```

Kizuna sanitizes and bounds provider data, stores request and response hashes, preserves match evidence, and records the provider run. Provider errors, invalid responses, timeouts, or responses over 1 MB block the stage. Availability failures cannot be cleared as false positives; the service must be restored or disabled and the current stage scanned again.

## Categories and configuration

Supported categories are `text`, `trademark`, `visual`, and `audio`. Built-in scanner slots infer their category from their key. Custom compliance integrations should include a `categories` array in configuration.

Optional configuration fields are:

- `scan_path` — defaults to `/scan`;
- `timeout_seconds` — 1–120 seconds, default 30;
- `auth_header` — defaults to `Authorization`;
- `auth_scheme` — defaults to `Bearer`; and
- `categories` — one or more supported categories.

Secrets are read at request time from the integration's named environment variable and are never returned through the settings API.
