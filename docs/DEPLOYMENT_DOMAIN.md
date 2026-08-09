# Production domain and access

Kizuna's intended public hostname is `https://kizuna.technology`. Set `KIZUNA_PUBLIC_URL=https://kizuna.technology` in Coolify, point the domain's DNS records at the server, attach the domain to the web service, and let Coolify issue and renew TLS.

DNS propagation does not make the application production-safe by itself. Keep the web service private or protected by an access gateway until Kizuna has user authentication, tenant-scoped authorization, secure secret management, backups, and tested restore procedures. Do not expose Postgres, Redis, or the compliance scanner to the public internet; only the web service should receive the public domain.

Use a strong, matching `KIZUNA_SELF_HOSTED_SCANNER_API_KEY` for the web and scanner connection and a separate `KIZUNA_SCANNER_ADMIN_KEY` for corpus administration. Store both as Coolify secrets rather than in Git.
