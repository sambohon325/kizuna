# Kizuna Node and cost controls

Kizuna Node is a small, provider-neutral Python companion that lets a creator make a computer available to the studio. It does not grant Kizuna general remote-control access.

## Enroll a computer

1. Open **Settings → Computers & costs**.
2. Select **Add this computer**.
3. Download `kizuna_node.py`.
4. Run the preview command to inspect the exact capability profile.
5. Run the generated enrollment command and approve the profile.
6. Run the monitor command whenever the computer should remain available.

Enrollment codes expire after 20 minutes and can be used once. The node receives a separate long-lived credential after enrollment and stores it in the user's Kizuna configuration directory. Production deployments should expose the Kizuna server through HTTPS before enrolling computers over the internet.

The current download is a cross-platform Python script and requires Python 3.10 or newer. A signed Windows/macOS installer and background-service wrapper should be produced before general public distribution.

## Scanner privacy

The default `creative` software level reports creative-production tools only. `none` omits software names. `all` reports installed application or package names and must be selected explicitly.

The profile can contain OS and architecture, CPU name and logical cores, total RAM, detected GPU names and memory, selected software names, a short local CPU benchmark, and derived capabilities. It never scans or uploads project files, prompts, scripts, passwords, API keys, license keys, documents, or browser history.

## Local and cloud placement

Every workload can be set to:

- **Let Kizuna decide** for capability-aware scheduling.
- **On my computer** with an optional preferred node.
- **In the cloud** with an optional preferred cloud connection.

The policies currently cover writing, image generation, animation, audio, editing/compositing, final rendering, and upscaling. These policies are persisted now; individual executors will adopt them as the corresponding production adapters are connected.

## AI usage and cost

Provider responses are normalized into input, cached-input, and output token counts. This matches the categories exposed by modern provider APIs; OpenAI also exposes organization-level usage grouped by model and related dimensions in its [official usage API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage).

Pricing changes independently of Kizuna, so the studio does not silently hard-code permanent rates. Add the exact provider key, model ID, current input/cached/output rates per million tokens, and an official pricing link. Kizuna records immutable usage events and applies the configured rate when each request completes.

The monthly budget can warn at a chosen percentage. When **Use local guidance after the limit** is enabled, routed Assistant calls fall back to Kizuna's built-in guidance after the configured budget is reached.

Cost figures are estimates, not invoices. Provider dashboards remain the source of truth for billing, credits, taxes, batch discounts, service tiers, non-token media charges, and account-specific agreements.
