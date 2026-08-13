# Accounts and production isolation

Kizuna can run without sign-in only for isolated local development. The production Docker stack always sets `KIZUNA_AUTH_REQUIRED=true`, uses Secure, HttpOnly, SameSite cookies, and requires a one-time `KIZUNA_BOOTSTRAP_ADMIN_KEY` stored as a Coolify secret.

On the first visit to `https://app.kizuna.technology`, Kizuna redirects to `/setup`. The creator must enter the server-side setup key and create an administrator with a password of at least 12 characters. That first administrator is assigned ownership of any productions that existed before accounts were enabled. The setup endpoint permanently closes once the first user exists.

Passwords use salted PBKDF2-SHA256 hashes and are never stored or logged in plain text. Sessions use random tokens whose hashes are stored in the database. Browser mutations require a separate CSRF token. Five failed sign-in attempts temporarily lock the account for 15 minutes.

Every production has an explicit membership record. Project routes, nested craft records, job records, thumbnails, proxies, and render URLs are resolved back to their owning production before access is allowed. Unauthorized production IDs return `404` so the application does not disclose whether another creator's production exists. Studio-wide settings and render-farm visibility require an administrator account.

Do not make the domain public until all of these are true:

- `KIZUNA_AUTH_REQUIRED=true`;
- `KIZUNA_COOKIE_SECURE=true` behind working HTTPS;
- a strong `KIZUNA_BOOTSTRAP_ADMIN_KEY` exists only in Coolify secrets;
- Postgres, Redis, the scanner, and render workers are not publicly exposed;
- database backups and restore drills are working; and
- a second review confirms that every newly added endpoint passes through the central authorization layer.

This foundation now includes local accounts, production isolation, invitations, project roles, and session-revocation APIs. Password reset, email verification, optional MFA/passkeys, a complete end-user account center, and security event monitoring remain required before a broad public launch.

## Hosted trial accounts

The marketing call to action opens `https://app.kizuna.technology/signup`. Once the first studio administrator exists, a visitor can create a trial account and a starter production. The trial lasts 7 days by default. During the active trial, every animatic and master export is limited to 60 seconds and watermarked by the render process. Segmented farm exports carry the same policy in their job manifests, and the server enforces it again during final assembly. When the trial expires, the account becomes review-only until its entitlement is upgraded.

Configure the policy with `KIZUNA_TRIAL_DAYS`, `KIZUNA_TRIAL_EXPORT_SECONDS`, and `KIZUNA_TRIAL_WATERMARK`. Trial enforcement does not depend on browser controls.

## Account email and recovery

Kizuna uses standard SMTP rather than a provider-specific SDK. Configure `KIZUNA_SMTP_HOST`, port, username, password, from address, from name, and either STARTTLS or SSL. Keep the password in the deployment secret store. Password-reset and verification links are generated from the configured `KIZUNA_PUBLIC_URL`, expire after `KIZUNA_ACCOUNT_TOKEN_HOURS`, are stored only as hashes, and can be used once. A completed password reset revokes every existing session and records a security event.

Keep `KIZUNA_EMAIL_VERIFICATION_REQUIRED=false` while testing delivery. After a real message can be requested and completed from the deployed application, change it to `true` before opening public trial signup. Recovery and resend requests are rate-limited with `KIZUNA_ACCOUNT_EMAIL_LIMIT_PER_HOUR` and deliberately return generic responses that do not reveal whether an email address has an account.

Public trial registration also fails closed unless Cloudflare Turnstile is fully configured. The browser widget is only the first half of the control: Kizuna redeems every short-lived token through Turnstile's server-side Siteverify API, verifies the response hostname against `KIZUNA_PUBLIC_URL`, and separately limits attempts by hashed email and network address. Configure `KIZUNA_TURNSTILE_SITE_KEY`, `KIZUNA_TURNSTILE_SECRET_KEY`, and `KIZUNA_TRIAL_SIGNUP_LIMIT_PER_HOUR` before enabling signup.

## Subscriptions and entitlements

The Account workspace shows trial, email, export, and subscription status. Paid conversion uses Stripe-hosted Checkout; payment methods, invoices, plan changes, and cancellation use Stripe's hosted customer portal. Kizuna never upgrades access from a browser redirect. Only webhooks signed with `KIZUNA_STRIPE_WEBHOOK_SECRET` can change the stored subscription and entitlement, and every Stripe event ID is processed at most once.

Configure a recurring Stripe Price and add `KIZUNA_STRIPE_SECRET_KEY`, `KIZUNA_STRIPE_WEBHOOK_SECRET`, and `KIZUNA_STRIPE_CREATOR_PRICE_ID`. Register the public webhook URL `https://app.kizuna.technology/api/billing/stripe/webhook` for Checkout completion, subscription created/updated/deleted, and invoice payment failure events. Use Stripe test mode until the full purchase, portal, cancellation, and failed-payment paths have been exercised.

## App and marketing hostnames

Kizuna keeps the application and marketing URLs separate. Set `KIZUNA_PUBLIC_URL=https://app.kizuna.technology`; invitation links are generated from this value. Set `KIZUNA_MARKETING_URL=https://kizuna.technology`; the Kizuna logo on account screens links back there.

Administrators can create expiring invitations under **Settings → Team & access**. Invitations grant only the productions and roles selected by an Owner. Owners can manage membership, Editors can change production content, and Viewers are enforced as read-only by the API. Invitation tokens are stored only as hashes and the raw link is shown when it is created. The inviting Owner can renew or resend a pending invitation; renewal immediately invalidates the prior link and starts a fresh expiry window. When SMTP is configured, Kizuna queues an invitation email and records success or failure against the inviting account without writing the raw token to the audit event. The copyable link remains available as a delivery fallback. Pending-invitation lists and management actions are scoped to the inviting account rather than exposed across unrelated studios.
