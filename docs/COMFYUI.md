# ComfyUI provider setup

Kizuna defaults to the `mock` provider so development never consumes GPU time accidentally. To enable a local ComfyUI worker:

1. Build and test a character-sheet workflow in ComfyUI.
2. Export it using **Save (API Format)**.
3. Note the node IDs for positive text, negative text, and the sampler seed.
4. Place the workflow JSON somewhere readable by Kizuna.
5. Configure the environment:

```env
KIZUNA_GENERATION_PROVIDER=comfyui
KIZUNA_COMFYUI_URL=http://RENDER-MACHINE-IP:8188
KIZUNA_COMFYUI_WORKFLOW_PATH=C:/path/to/character-sheet-api.json
KIZUNA_COMFYUI_POSITIVE_NODE=6
KIZUNA_COMFYUI_NEGATIVE_NODE=7
KIZUNA_COMFYUI_SAMPLER_NODE=3
```

Restart Kizuna after changing these values.

Kizuna submits the complete API-format workflow to `POST /prompt`, stores the returned `prompt_id`, checks `/history/{prompt_id}`, and copies completed `/view` outputs into its own asset directory. This keeps finished assets available even when the render worker goes offline.

Only expose ComfyUI over a trusted private network such as Tailscale or WireGuard. Do not publish port 8188 directly to the internet.

The workflow owns model selection, resolution, ControlNet/reference conditioning, LoRAs, sampler settings, and upscale stages. Kizuna owns the production prompt, identity locks, seed, job state, and resulting asset versions.
