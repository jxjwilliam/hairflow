# Short Video — ComfyUI Integration

## Current default and bake-off

The initial bake-off winner and API default is **LTX**:

```env
DEFAULT_VIDEO_PIPELINE=ltx
```

Run all three candidates serially against a generated still:

```bash
make video-bakeoff STILL=backend/output/<try-on-still>.png
```

The command writes each MP4 to `backend/output/bakeoff/<still-stem>/` and
records successful and failed attempts in `backend/output/bakeoff/report.md`.
Failures are expected for AnimateDiff until its custom nodes and motion
weights are installed.

## Node discovery results (live · 2026-07-19)

Catalog: `backend/data/video_node_catalog.json`  
ComfyUI: `http://127.0.0.1:8188`

| Pipeline | missing | Key class_types (sample) |
|----------|---------|--------------------------|
| ltx | False | `LTXVImgToVideo`, `EmptyLTXVLatentVideo`, `LTXVConditioning`, `LTXVScheduler` (+ 37 total) |
| hunyuan | False | `HunyuanImageToVideo`, `EmptyHunyuanLatentVideo`, `TextEncodeHunyuanVideo_ImageToVideo` (+ 17 total) |
| animatediff | True | *(none — install required)* |
| video_io | False | `ByteDanceCreateVideoAsset`, `CreateVideo`, `DecodeAndSaveVideo`, `SaveVideo` |

Full lists are in the catalog JSON.


> **Date:** 2026-07-19  
> **Scope:** Task 1 — node discovery catalog (no generation yet)

Design spec: [`docs/superpowers/specs/2026-07-19-hairstyle-short-video-design.md`](superpowers/specs/2026-07-19-hairstyle-short-video-design.md)

---

## Node discovery

### Catalog

Frozen node inventory: [`backend/data/video_node_catalog.json`](../backend/data/video_node_catalog.json)

Regenerate from a running ComfyUI:

```bash
curl -s -m 3 http://127.0.0.1:8188/system_stats | head -c 100
make discover-video-nodes
```

Script: [`backend/scripts/discover_video_nodes.py`](../backend/scripts/discover_video_nodes.py) — probes `GET {COMFYUI_URL}/object_info` and matches `class_type` names by keyword.

### Discovery run (2026-07-19)

| Item | Result |
|------|--------|
| ComfyUI URL | `http://127.0.0.1:8188` |
| Reachable | **Yes** — live `/object_info` was queried |
| Catalog on disk | `backend/data/video_node_catalog.json` is the frozen live inventory |

**Action:** Start Pinokio ComfyUI (see [`docs/ds_comfyui_setup.md`](ds_comfyui_setup.md)), then re-run `make discover-video-nodes` to replace the placeholder catalog.

### LTX graph

`backend/static/workflows/ltx_i2v_hairstyle.json` is an API-format graph using:

`LoadImage` → `ImageScale` → `UNETLoader` (`ltx-video-2b-v0.9.5.safetensors`) +
`CLIPLoader` (`t5xxl_fp16.safetensors`, `ltxv`) + `VAELoader` →
`CLIPTextEncode` → `LTXVConditioning` → `LTXVImgToVideo` →
`ModelSamplingLTXV` / `LTXVScheduler` / `SamplerCustomAdvanced` →
`VAEDecode` → `CreateVideo` → `SaveVideo`.

The graph uses 512×768, a requested 24 frames plus the required initial still
(25 latent frames), and 8 fps. A live `/prompt` validation on 2026-07-19
accepted the graph (`fbf16ad4-b051-477d-978d-fb3119307a9b`); completion was
not awaited because local jobs must remain sequential.

### Hunyuan graph

`backend/static/workflows/hunyuan_i2v_hairstyle.json` uses `UNETLoader`,
`DualCLIPLoader` (`hunyuan_video`), `VAELoader`,
`CLIPTextEncodeHunyuanDiT`, `HunyuanImageToVideo`, `KSampler`,
`VAEDecode`, `CreateVideo`, and `SaveVideo`, with the existing Hunyuan fp8
UNET and bf16 VAE. Its live `/prompt` validation was accepted
(`adfdc7a7-40bf-4f0c-94c0-da44a2fc0c80`); generation was not awaited.

### Matched class_types

| Pipeline | Keywords | Matched nodes | Status |
|----------|----------|---------------|--------|
| **ltx** | `ltx`, `ltxv` | `LTXVImgToVideo`, `LTXVConditioning`, `LTXVScheduler` (+ more) | available |
| **hunyuan** | `hunyuan` | `HunyuanImageToVideo`, `TextEncodeHunyuanVideo_ImageToVideo` (+ more) | available |
| **animatediff** | `animatediff`, `animate_diff`, `ad_` | *(none until ComfyUI restarts)* | install pending restart |
| **video_io** | `vhs_`, `videocombine`, `savevideo`, `createvideo` | `CreateVideo`, `SaveVideo` | available |

After a successful run, update this table from `video_node_catalog.json`.

### AnimateDiff install (if missing after discovery)

AnimateDiff custom nodes are **not** expected on this Pinokio ComfyUI build today. If discovery shows zero matches for `animatediff`:

1. `ComfyUI-AnimateDiff-Evolved` was cloned to
   `/Users/william.jiang/Samsung/pinokio/api/comfy.git/app/custom_nodes/ComfyUI-AnimateDiff-Evolved`
   at commit `2a12eaa`.
2. Restart Pinokio ComfyUI so it loads the extension.
3. Install an SD1.5 motion module such as `v3_sd15_mm.ckpt` in the extension's
   documented AnimateDiff model path.
4. Re-run `make discover-video-nodes`; only then can the placeholder
   `animatediff_i2v_hairstyle.json` be exercised. It intentionally references
   `realisticVisionV60B1_v60B1VAE.safetensors`.

### Model inventory (on disk)

| Pipeline | Files |
|----------|-------|
| **ltx** | `ltx-video-2b-v0.9.5.safetensors`, `t5xxl_fp16.safetensors` |
| **hunyuan** | `hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors`, `hunyuan_video_vae_bf16.safetensors` |
| **animatediff** | motion module TBD after install + `realisticVisionV60B1_v60B1VAE.safetensors` |

Paths follow Pinokio ComfyUI layout under `models/` (see [`docs/ds_comfyui_setup.md`](ds_comfyui_setup.md)).
