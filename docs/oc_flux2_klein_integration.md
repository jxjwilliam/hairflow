# FLUX.2 Klein Integration

Integration of FLUX.2 Klein 4B (Q8_0 GGUF) as an alternative AI backend alongside the existing PhotoMaker pipeline. Adds parameterized hairstyle generation (length, curl, color, bangs, volume).

## Changes

### Backend

**`backend/app/models/schemas.py`** — Extended `GenerateRequest` with generation options:
- `pipeline` — `photomaker` (default) or `flux_klein`
- `method` — `photomaker` | `txt2img` | `img2img`
- `checkpoint`, `denoise`, `steps`, `cfg` — forwarded as inference overrides

**`backend/app/services/comfyui.py`** — Added FLUX.2 Klein workflow support:
- `generate_flux2_klein()` — builds and submits a FLUX.2 Klein try-on workflow to ComfyUI
  - Uploads user photo as image input
  - Loads FLUX.2 Klein 4B Q8_0 GGUF checkpoint
  - Loads FLUX2 VAE
  - Loads Qwen 3 4B text encoder
  - Applies hairstyle prompt with dynamic parameters (length, curl, color, bangs, volume)
  - Polls ComfyUI `/history` for result
  - Saves output to `backend/output/{uuid}.png`
- Refactored shared helpers (`_upload_image`, `_poll_result`, `_build_image_params`) to allow reuse across pipelines
- `generate_hairstyle()` now routes by `pipeline` field

**`backend/app/routers/comfyui_generation.py`** — Added `POST /api/comfyui/generate-v2` endpoint accepting `HairstyleParams` (the parameterized flow). The original `/api/comfyui/generate` remains unchanged for backwards compatibility.

### Frontend

**`mobile/types.ts`** — Added `HairstyleParams` interface with `length`, `curl`, `color`, `bangs`, `volume` fields.

**`mobile/app/options.tsx`** — New options screen with parameter sliders before generation:
- Length slider (short → long)
- Curl slider (straight → curly)
- Color picker (black, brown, blonde, red, gray, white)
- Bangs toggle
- Volume slider (flat → voluminous)
- "Generate" button calls `generateWithParams()`

**`mobile/app/capture.tsx`** — Routes to options screen instead of directly to preview, passing `HairstyleParams` along the navigation chain.

**`mobile/app/preview.tsx`** — Updated to handle the FLUX.2 Klein generation result. Reads `HairstyleParams` from route params.

**`mobile/services/generation.ts`** — Added `generateWithParams()` function that posts to `/api/comfyui/generate-v2` with `HairstyleParams` payload.

## Model Files

Three models downloaded to the Pinokio ComfyUI drive
(`d1779062027621/`):

| Model | Size | Path |
|-------|------|------|
| FLUX.2 Klein 4B Q8_0 GGUF | 4.0 GB | `unet/flux-2-klein-4b-Q8_0.gguf` |
| FLUX2 VAE | 321 MB | `vae/flux2-vae.safetensors` |
| Qwen 3 4B Text Encoder | 7.5 GB | `text_encoders/qwen_3_4b.safetensors` |

**Total:** ~11.8 GB

## Files Changed

```
 backend/app/models/schemas.py             |   7 +
 backend/app/routers/comfyui_generation.py |  41 +-
 backend/app/services/comfyui.py           | 449 ++++++++++++++++++++++-
 mobile/app/capture.tsx                    |   2 +-
 mobile/app/options.tsx                    | 288 ++++++++++++++
 mobile/app/preview.tsx                    |  16 +-
 mobile/services/generation.ts             |  14 +-
 mobile/types.ts                           |   8 +
 8 files changed, 790 insertions(+), 29 deletions(-)
```
