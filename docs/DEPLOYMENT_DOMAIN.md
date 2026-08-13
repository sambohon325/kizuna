# Production domain and access

Use `https://kizuna.com` for the marketing site and `https://app.kizuna.com` for the authenticated studio when those are the selected production domains. The same build can continue using the existing `.technology` pairing instead. The important boundary is that the public marketing site and authenticated application remain separate services.

Set `KIZUNA_PUBLIC_URL` to the final app hostname and `KIZUNA_MARKETING_URL` to the final public hostname in the application service. Point the app subdomain at the Kizuna application, attach only that hostname to the web service, and let Coolify issue and renew TLS. The standalone marketing service is built from `marketing/Dockerfile`; set its `KIZUNA_APP_URL` to the same application hostname so every sign-in and signup action reaches the correct service.

The marketing site's free-trial call to action links to the app service's `/signup` route. Kizuna creates a 7-day trial account and a starter production there. Trial animatics and masters are enforced server-side at a maximum of 60 seconds and always carry the configured Kizuna trial watermark. The marketing site presents those limits before signup; changing or hiding the browser text does not remove the backend enforcement.

DNS propagation does not make the application production-safe by itself. Keep the web service private or protected by an access gateway until Kizuna has user authentication, tenant-scoped authorization, secure secret management, backups, and tested restore procedures. Do not expose Postgres, Redis, or the compliance scanner to the public internet; only the web service should receive the public domain.

Use a strong, matching `KIZUNA_SELF_HOSTED_SCANNER_API_KEY` for the web and scanner connection and a separate `KIZUNA_SCANNER_ADMIN_KEY` for corpus administration. Store both as Coolify secrets rather than in Git.
