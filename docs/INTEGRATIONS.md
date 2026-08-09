# Connections and tools

Kizuna is designed to be the production engine rather than a closed provider ecosystem. Settings at the bottom of the studio navigation contains three connection groups:

- AI engines for writing, reasoning, direction, and multimodal assistance;
- generation tools for images, animation, inpainting, and upscaling; and
- creative applications for layered-file and timeline handoffs.

Built-in profiles cover OpenAI, Claude, Gemini, Ollama, custom AI APIs, ComfyUI, AUTOMATIC1111/Forge, InvokeAI, Adobe Creative Cloud, Corel, GIMP, Krita, OpenToonz, Blender, and DaVinci Resolve. Studios can add their own API or file-handoff profile without changing Kizuna's database schema.

## Secret handling

Integration records store endpoint addresses, model names, and the **name** of an environment variable. API key values are not saved in the database or returned to the browser. Add the named variable to the Kizuna server environment, then restart the service.

This hub is the provider registry and handoff foundation. Individual adapters and production routing are added behind the same profiles so craft workspaces do not become tied to a single vendor.
