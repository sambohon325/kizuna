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

Configure the policy with `KIZUNA_TRIAL_DAYS`, `KIZUNA_TRIAL_EXPORT_SECONDS`, and `KIZUNA_TRIAL_WATERMARK`. Before opening public self-service signup, connect verified email delivery, password recovery, signup abuse controls, and billing-driven entitlement upgrades. Trial enforcement does not depend on browser controls.

## App and marketing hostnames

Kizuna keeps the application and marketing URLs separate. Set `KIZUNA_PUBLIC_URL=https://app.kizuna.technology`; invitation links are generated from this value. Set `KIZUNA_MARKETING_URL=https://kizuna.technology`; the Kizuna logo on account screens links back there.

Administrators can create expiring invitation links under **Settings → Team & access**. Invitations grant only the productions and roles selected by an Owner. Owners can manage membership, Editors can change production content, and Viewers are enforced as read-only by the API. Invitation tokens are stored only as hashes and the raw link is shown once when it is created.
