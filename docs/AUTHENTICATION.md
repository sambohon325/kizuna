# Accounts and production isolation

Kizuna can run without sign-in only for isolated local development. The production Docker stack always sets `KIZUNA_AUTH_REQUIRED=true`, uses Secure, HttpOnly, SameSite cookies, and requires a one-time `KIZUNA_BOOTSTRAP_ADMIN_KEY` stored as a Coolify secret.

On the first visit to `https://kizuna.technology`, Kizuna redirects to `/setup`. The creator must enter the server-side setup key and create an administrator with a password of at least 12 characters. That first administrator is assigned ownership of any productions that existed before accounts were enabled. The setup endpoint permanently closes once the first user exists.

Passwords use salted PBKDF2-SHA256 hashes and are never stored or logged in plain text. Sessions use random tokens whose hashes are stored in the database. Browser mutations require a separate CSRF token. Five failed sign-in attempts temporarily lock the account for 15 minutes.

Every production has an explicit membership record. Project routes, nested craft records, job records, thumbnails, proxies, and render URLs are resolved back to their owning production before access is allowed. Unauthorized production IDs return `404` so the application does not disclose whether another creator's production exists. Studio-wide settings and render-farm visibility require an administrator account.

Do not make the domain public until all of these are true:

- `KIZUNA_AUTH_REQUIRED=true`;
- `KIZUNA_COOKIE_SECURE=true` behind working HTTPS;
- a strong `KIZUNA_BOOTSTRAP_ADMIN_KEY` exists only in Coolify secrets;
- Postgres, Redis, the scanner, and render workers are not publicly exposed;
- database backups and restore drills are working; and
- a second review confirms that every newly added endpoint passes through the central authorization layer.

This slice establishes local accounts and production isolation. Password reset, email verification, invitations, optional MFA/passkeys, organization roles, session-management UI, and security event monitoring remain required before a broad public launch.
