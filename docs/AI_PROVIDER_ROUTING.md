# AI provider routing

Kizuna can assign a different AI engine to each production role while keeping every role usable with built-in local guidance.

## Configure an engine

1. Open **Settings** from the bottom of the left navigation.
2. Set up OpenAI, Claude, Gemini, Ollama, or a custom AI connection.
3. Put secrets in server environment variables. Kizuna stores only the environment-variable name.
4. In **AI Role Routing**, choose an engine for each craft role.
5. Optionally enter a role-specific model override. Otherwise the connection's default model is used.

The Studio Assistant is the first role connected end-to-end through the router. Writer, Director, Character Designer, Background Artist, Animator, Editor, Sound Producer, and Producer assignments are persisted now and will be connected to their individual proposal workflows incrementally.

## Supported text protocols

- OpenAI uses the Responses API.
- Claude uses the Messages API.
- Gemini uses `generateContent`.
- Ollama uses its local `/api/generate` endpoint with streaming disabled.
- Custom AI connections default to an OpenAI-compatible `/chat/completions` endpoint. Set `configuration.protocol` to another supported adapter when extending the registry.

## Failure behavior

The Assistant never becomes unusable because an external engine is offline. If the selected provider is unavailable, times out, returns an error, or produces an empty response, Kizuna uses its built-in project-aware guidance and records the fallback reason with the assistant message.

The browser never receives API keys. Hosted provider secrets must exist in the Coolify or local server environment before that provider is marked ready.
