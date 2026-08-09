# Production domain and access

Use the root domain for the marketing site and a dedicated `app` subdomain for the authenticated studio. Set `KIZUNA_PUBLIC_URL` to the full app origin and `KIZUNA_MARKETING_URL` to the marketing origin in Coolify, point the app subdomain at the server, attach only that hostname to the web service, and let Coolify issue and renew TLS. Kizuna keeps these values configurable so a domain spelling is never silently assumed.

DNS propagation does not make the application production-safe by itself. Keep the web service private or protected by an access gateway until Kizuna has user authentication, tenant-scoped authorization, secure secret management, backups, and tested restore procedures. Do not expose Postgres, Redis, or the compliance scanner to the public internet; only the web service should receive the public domain.

Use a strong, matching `KIZUNA_SELF_HOSTED_SCANNER_API_KEY` for the web and scanner connection and a separate `KIZUNA_SCANNER_ADMIN_KEY` for corpus administration. Store both as Coolify secrets rather than in Git.
