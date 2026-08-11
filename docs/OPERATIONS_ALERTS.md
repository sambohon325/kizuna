# External operations alerts

Kizuna keeps **Settings → Operations** as the complete source of current readiness. External delivery is an optional attention channel so an administrator does not need to keep the page open.

## Delivery channels

Configure either or both channels in Coolify:

```env
KIZUNA_OPERATIONS_ALERT_EMAIL=operations@example.com
KIZUNA_OPERATIONS_ALERT_WEBHOOK_URL=https://alerts.example.com/kizuna
KIZUNA_OPERATIONS_ALERT_WEBHOOK_SECRET=replace-with-a-long-random-secret
```

Email uses the existing `KIZUNA_SMTP_*` settings. The webhook receives JSON over HTTPS. When a webhook secret is configured, Kizuna signs the exact request body with HMAC-SHA256 and sends `X-Kizuna-Signature: sha256=<digest>`.

The webhook payload includes `event`, `title`, `text`, `content`, `severity`, `alert_key`, `message`, `action`, `studio_url`, and `sent_at`. The duplicate `text` and `content` fields make the generic payload easier to adapt to common chat and automation services. Use a small relay when the destination requires a provider-specific authentication or message format.

## Noise and retry controls

```env
KIZUNA_OPERATIONS_ALERT_MIN_SEVERITY=error
KIZUNA_OPERATIONS_ALERT_COOLDOWN_MINUTES=360
KIZUNA_OPERATIONS_ALERT_RETRY_MINUTES=15
KIZUNA_OPERATIONS_ALERT_RETENTION_DAYS=90
```

- `MIN_SEVERITY` accepts `warning` or `error`. Production should normally begin with `error`.
- A matching delivered condition is suppressed during the cooldown.
- A failed delivery is eligible for another attempt after the retry interval.
- Delivery history older than the retention window is removed by the scheduler.

Changing the alert message, severity, or recommended action creates a new fingerprint and can notify immediately. Kizuna never places SMTP passwords, webhook URLs, or signing secrets in the database or browser response. Stored evidence contains only a masked target, safe alert text, status, response code, timestamps, and whether an error occurred.

## Verification

After redeploying:

1. Open **Settings → Operations**.
2. Confirm **External alerts** reports the expected channel names.
3. Select **Send test alert**.
4. Confirm the message arrives and Operations reports the last delivery as `delivered`.
5. For a webhook, independently verify the HMAC signature in the receiving service.

The backup scheduler evaluates active operational errors on its normal cycle. A delivery failure is itself shown as an Operations error and written to the structured Coolify logs.
