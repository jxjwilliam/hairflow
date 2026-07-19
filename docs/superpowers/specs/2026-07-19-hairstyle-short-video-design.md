# Short Video from Try-On Still — Design

> **Date:** 2026-07-19  
> **Status:** Approved for implementation planning  
> **Product:** Hairflow / 发型试戴  
> **Decision path:** Brainstorm → Approach A (one-time bake-off → single default in app)

---

## 1. Goal & scope

### Goal

From a successful hairstyle try-on **still** on the Preview screen, generate a **~2–3 second** MP4 with subtle hair / head motion so the user can preview the cut in motion.

### In scope

- Three ComfyUI video backends for **offline comparison**:
  - `ltx` — LTX-Video 2B (`ltx-video-2b-v0.9.5.safetensors`)
  - `hunyuan` — Hunyuan Video fp8 + existing `comfyui-hunyuanvideowrapper`
  - `animatediff` — AnimateDiff on SD1.5 (reuses Realistic Vision; requires install)
- Offline / sequential bake-off runner (CLI + Makefile) that writes side-by-side MP4s
- After the user picks a winner: **one** API path + **one** Preview button wired via `DEFAULT_VIDEO_PIPELINE`
- Save videos under `backend/output/`, serve similarly to stills

### Out of scope (MVP)

- In-app lab / compare UI (Approach C deferred)
- History / result-view re-generate video
- Concurrent multi-model runs on Mac (OOM risk on M3 18GB)
- Wan 2.1 I2V 14B (31GB — does not fit this machine)
- Real-time streaming preview

### Locked product choices

| Choice | Value |
|--------|--------|
| Source frame | Already-generated try-on still (not raw selfie) |
| Duration | ~2–3 seconds |
| App entry | Preview screen only |
| Ship strategy | Approach **A**: bake-off → pick default → single button |
| Default candidate | `ltx` until bake-off says otherwise |

---

## 2. Architecture & API

```
Preview (still ready)
  → POST /api/comfyui/generate-video
       { image_id | image_url | photo_base64 of still, pipeline? }
  → FastAPI
       → resolve still bytes (prefer local backend/output/{image_id})
       → ComfyUIService.generate_video(pipeline, image_bytes, …)
            dispatches: ltx | hunyuan | animatediff
       → save backend/output/{uuid}.mp4
  → { video_url, video_id, pipeline, duration_s }
```

### Bake-off (offline, sequential)

```
make video-bakeoff STILL=backend/output/<uuid>.png
  → scripts/video_bakeoff.py
  → for each still × {ltx, hunyuan, animatediff}:
       same service method, asyncio.Semaphore(1)
  → backend/output/bakeoff/<still_stem>/{ltx,hunyuan,animatediff}.mp4
  → backend/output/bakeoff/report.md (paths, elapsed_s, ok/fail)
```

Multi-agent use is for **implementing** the three pipelines in parallel during coding — **not** for running three generations at once on this Mac.

### Defaults & ops

| Setting | Behavior |
|---------|----------|
| `DEFAULT_VIDEO_PIPELINE` | `ltx` initially; flip after bake-off without app rewrite |
| HTTP | Sync request for MVP (same pattern as still generate); Mac timeout budget **10–15 minutes** |
| Points | Same cost as one still generate when `SKIP_POINTS_CHECK=false`; skipped in dev |
| Concurrency | Global ComfyUI semaphore(1) shared with still / multi-angle paths |

### Mobile

- Preview: button **「生成短视频」** only when a still URL exists
- Loading copy warns that Mac generation may take several minutes
- Play result with `expo-av` (new dependency); web uses `<video>`
- No pipeline picker in the app UI

---

## 3. Pipelines, models, installs

| Pipeline | Weights | ComfyUI | Install needed? |
|----------|---------|---------|-----------------|
| **ltx** | `ltx-video-2b-v0.9.5.safetensors` (~5.9G) under Pinokio `models/diffusion_models/` | Native LTX nodes in ComfyUI 0.27 **or** official LTX custom nodes if `/object_info` lacks them | Reuse existing `t5xxl_fp16.safetensors` in `clip/`. Confirm nodes at impl time |
| **hunyuan** | `hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors` + `hunyuan_video_vae_bf16.safetensors` | `comfyui-hunyuanvideowrapper` already installed | Working I2V workflow JSON; no new large download expected |
| **animatediff** | Motion module (e.g. AnimateDiff SD1.5 v3) + optional VAE | AnimateDiff custom node — **not** present today | **Yes** — install node + motion weights; base checkpoint = `realisticVisionV60B1_v60B1VAE.safetensors` |

### Shared bake-off knobs

- Resolution: ~480p or downscaled still (keep aspect)
- Length: ~24 frames @ 8–12 fps → ~2–3s
- Fixed seed per still for fair comparison
- Sequential execution only

### Known risks

- LTX / Hunyuan on M3 will be **slow** (minutes per clip) — expected for local bake-off
- AnimateDiff lightest; may look least cinematic
- If LTX nodes are missing from this ComfyUI build, install node support first — **do not** re-download the 5.9G weights already on disk
- OOM: surface as 502 with a clear memory message

### Model locator

After bake-off picks a default, update  
`~/.agents/skills/comfyui-model-locator/references/apps/hairflow.json`  
with the winning pipeline’s required filenames (and keep LTX/Hunyuan/AnimateDiff entries under a `video_*` key group if useful for `--check`).

---

## 4. UI, errors, testing

### Preview UI

1. User completes still try-on → `resultUrl` set  
2. Tap **「生成短视频」**  
3. Loading overlay  
4. On success: inline video player under the still  
5. Failure: alert; still remains usable  

### Errors

| Case | Response |
|------|----------|
| Missing / invalid still reference | 400 |
| ComfyUI down, missing node/model | 502 with `node_errors` detail (same pattern as still generate) |
| Client / proxy timeout | User-facing retry message; keep still |
| OOM / worker crash | 502 “模型内存不足…” |

### Tests

- Unit: each video workflow builder returns expected graph shape (ComfyUI mocked)
- Manual integration: at least one live LTX run against Pinokio ComfyUI
- Mobile: button disabled until still ready; mutation errors show alert

### Docs to update at implementation time

- `README.md` / `AGENTS.md` — new endpoint + `DEFAULT_VIDEO_PIPELINE`
- Optional: `docs/oc_short_video.md` with bake-off instructions

---

## 5. Implementation sequence (high level)

1. Discover / confirm LTX + Hunyuan node names via ComfyUI `/object_info`  
2. Install AnimateDiff node + motion module  
3. Implement `generate_video` dispatch + three workflow builders  
4. Add `POST /api/comfyui/generate-video` + local MP4 serve  
5. Add `scripts/video_bakeoff.py` + `make video-bakeoff`  
6. Run bake-off on 2–3 real try-on stills; user picks winner  
7. Set `DEFAULT_VIDEO_PIPELINE`; wire Preview button + `expo-av`  
8. Tests + README / hairflow.json update  

Multi-agents may implement the three builders in parallel **after** the implementation plan is written; generation jobs remain serial.

---

## 6. Success criteria

- [ ] Bake-off produces three comparable MP4s (or clear fail reasons) for the same still  
- [ ] Preview can generate and play a ~2–3s video using the chosen default pipeline  
- [ ] Switching `DEFAULT_VIDEO_PIPELINE` changes behavior without a mobile rebuild  
- [ ] No concurrent video jobs on the Mac during bake-off or app use  

---

## 7. Non-goals reminder

Do not block MVP on cloud GPU, job queues, or in-app A/B UI. Those can follow once one pipeline is proven good enough for salon demos.
