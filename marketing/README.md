# Kizuna marketing site

This directory is a standalone public site for Kizuna. It does not connect to the production database. Calls to action open the protected signup and login routes on the separate Kizuna application service.

The service includes a deliberately small publishing and community backend:

- public journal posts with draft/publish controls;
- private-beta applications and triage;
- support, feedback, feature-request, and bug tickets with reference numbers;
- configurable social links; and
- one protected website-administrator screen at `/admin`; and
- an auditable AI operations desk for support and beta intake.

## Preview locally

From the repository root:

```powershell
.\.venv\Scripts\python.exe .\marketing\preview.py
```

Open `http://127.0.0.1:8040`.

For local development only, open `http://127.0.0.1:8040/admin` and use the password printed by the preview command. The local default is `local-marketing-admin`.

## Coolify

Create a separate Dockerfile application from the same GitHub repository:

- Dockerfile location: `/marketing/Dockerfile`
- Domain: the public marketing hostname, with container port `8080`
- Environment variable: `KIZUNA_APP_URL=https://app.kizuna.com`
- Health endpoint: `/health`
- Persistent storage: mount a Coolify volume at `/data`

Required administration variables:

```text
KIZUNA_MARKETING_ADMIN_PASSWORD=<a unique password of at least 20 characters>
KIZUNA_MARKETING_SESSION_SECRET=<at least 32 random bytes represented as hex>
KIZUNA_MARKETING_COOKIE_SECURE=true
```

AI operations defaults to `assist`: the desk prepares work but does not send it. To enable low-risk automatic correspondence after testing, configure:

```text
KIZUNA_OPS_AUTOMATION_MODE=autopilot
KIZUNA_OPS_AUTO_CONFIDENCE=85
KIZUNA_OPS_AI_PROTOCOL=openai
KIZUNA_OPS_AI_MODEL=<model name>
KIZUNA_OPS_AI_API_KEY=<server-side secret>
```

For Anthropic, Google, Ollama, or a custom OpenAI-compatible service, also set `KIZUNA_OPS_AI_ENDPOINT` and use `anthropic`, `google`, `ollama`, or `openai-compatible` as the protocol. Keep `KIZUNA_OPS_AUTOMATION_MODE=assist` while verifying a new provider.

Automatic email requires the existing Kizuna SMTP settings:

```text
KIZUNA_SMTP_HOST=<smtp host>
KIZUNA_SMTP_PORT=587
KIZUNA_SMTP_USERNAME=<mailbox user>
KIZUNA_SMTP_PASSWORD=<server-side secret>
KIZUNA_SMTP_FROM_EMAIL=<verified sender address>
KIZUNA_SMTP_FROM_NAME=Kizuna Studio
KIZUNA_SMTP_STARTTLS=true
KIZUNA_SMTP_SSL=false
```

See [`docs/AI_OPERATIONS.md`](../docs/AI_OPERATIONS.md) for the autonomy policy, account-management plan, hard escalation rules, and rollout sequence.

Optional social links appear only when configured:

```text
KIZUNA_SOCIAL_INSTAGRAM=https://...
KIZUNA_SOCIAL_YOUTUBE=https://...
KIZUNA_SOCIAL_TIKTOK=https://...
KIZUNA_SOCIAL_X=https://...
KIZUNA_SOCIAL_LINKEDIN=https://...
KIZUNA_SOCIAL_DISCORD=https://...
```

If the deployed app remains on the `.technology` domain, set `KIZUNA_APP_URL=https://app.kizuna.technology` instead. No source-code change is required.

The current administrator password is intended for a very small private team. Before delegating website access broadly, replace it with named accounts, MFA, individual audit history, and role-based permissions. Before opening forms to high-volume public traffic, add Turnstile, durable rate limiting, email notifications, privacy/retention controls, and a monitored security-reporting address.
