# Production domain and access

Use `https://kizuna.technology` for the marketing site and `https://app.kizuna.technology` for the authenticated studio. Set `KIZUNA_PUBLIC_URL=https://app.kizuna.technology` and `KIZUNA_MARKETING_URL=https://kizuna.technology` in Coolify, point the app subdomain at the server, attach only that hostname to the web service, and let Coolify issue and renew TLS.

The marketing site's free-trial call to action should link to `https://app.kizuna.technology/signup`. Kizuna creates a 7-day trial account and a starter production there. Trial animatics and masters are enforced server-side at a maximum of 60 seconds and always carry the configured Kizuna trial watermark. The marketing site must present those limits before signup; changing or hiding the browser text does not remove the backend enforcement.

DNS propagation does not make the application production-safe by itself. Keep the web service private or protected by an access gateway until Kizuna has user authentication, tenant-scoped authorization, secure secret management, backups, and tested restore procedures. Do not expose Postgres, Redis, or the compliance scanner to the public internet; only the web service should receive the public domain.

Use a strong, matching `KIZUNA_SELF_HOSTED_SCANNER_API_KEY` for the web and scanner connection and a separate `KIZUNA_SCANNER_ADMIN_KEY` for corpus administration. Store both as Coolify secrets rather than in Git.
