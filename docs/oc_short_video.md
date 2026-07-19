# Short Video — ComfyUI Integration

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
| Reachable | **No** — connection refused on `/object_info` |
| `make discover-video-nodes` | Exit 1 (`FAIL: cannot reach ComfyUI object_info`) |
| Catalog on disk | Placeholder with empty matches until ComfyUI is up |

**Action:** Start Pinokio ComfyUI (see [`docs/ds_comfyui_setup.md`](ds_comfyui_setup.md)), then re-run `make discover-video-nodes` to replace the placeholder catalog.

### Matched class_types (placeholder — re-run discovery)

| Pipeline | Keywords | Matched nodes | Status |
|----------|----------|---------------|--------|
| **ltx** | `ltx`, `ltxv` | *(none — ComfyUI down)* | missing |
| **hunyuan** | `hunyuan` | *(none — ComfyUI down)* | missing |
| **animatediff** | `animatediff`, `animate_diff`, `ad_` | *(none — ComfyUI down)* | missing |
| **video_io** | `vhs_`, `videocombine`, `savevideo`, `createvideo` | *(none — ComfyUI down)* | missing |

After a successful run, update this table from `video_node_catalog.json`.

### AnimateDiff install (if missing after discovery)

AnimateDiff custom nodes are **not** expected on this Pinokio ComfyUI build today. If discovery shows zero matches for `animatediff`:

1. Open ComfyUI → **Manager** → Install Custom Nodes
2. Search and install **ComfyUI-AnimateDiff-Evolved** (or the official AnimateDiff pack)
3. Restart ComfyUI
4. Re-run `make discover-video-nodes`

Motion module weights are TBD after install (Task 5).

### Model inventory (on disk)

| Pipeline | Files |
|----------|-------|
| **ltx** | `ltx-video-2b-v0.9.5.safetensors`, `t5xxl_fp16.safetensors` |
| **hunyuan** | `hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors`, `hunyuan_video_vae_bf16.safetensors` |
| **animatediff** | motion module TBD after install + `realisticVisionV60B1_v60B1VAE.safetensors` |

Paths follow Pinokio ComfyUI layout under `models/` (see [`docs/ds_comfyui_setup.md`](ds_comfyui_setup.md)).
