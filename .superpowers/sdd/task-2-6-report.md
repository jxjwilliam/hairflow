# Hairflow short-video Tasks 2–6 report

Date: 2026-07-19

## Status

- Task 2 complete: video settings, request/response schemas, source validation,
  ComfyUI HTTP client helpers, media-aware history polling, and serialized video
  generation dispatch are implemented.
- Task 3 complete: parameterized LTX image-to-video API workflow is at
  `backend/static/workflows/ltx_i2v_hairstyle.json`. It uses the confirmed LTX
  UNET and T5 names and was accepted by the live `/prompt` validator.
- Task 4 complete: parameterized Hunyuan image-to-video API workflow is at
  `backend/static/workflows/hunyuan_i2v_hairstyle.json`, uses the confirmed fp8
  UNET and bf16 VAE, and was accepted by live `/prompt` validation.
- Task 5 partially complete: `ComfyUI-AnimateDiff-Evolved` was cloned at
  external commit `2a12eaa`; ComfyUI must restart and a motion module (for
  example `v3_sd15_mm.ckpt`) must still be installed. The repository has a
  documented placeholder workflow referencing Realistic Vision, so LTX and
  Hunyuan are not blocked.
- Task 6 complete: `POST /api/comfyui/generate-video` resolves a local image
  ID/URL or base64 still, writes an MP4 under `backend/output`, and serves MP4s
  with `video/mp4`.

## Commit

- `d04438b feat: add short video generation backend`

## Tests

`cd backend && PYTHONPATH=. ../venv/bin/python -m pytest tests/ -v`

Result: 29 passed. The only warning is the pre-existing Pydantic v2
class-based-settings deprecation.

## Concerns

- LTX and Hunyuan graph submissions were accepted by ComfyUI, but completion
  was deliberately not awaited; their prompt IDs were `fbf16ad4-b051-477d-978d-fb3119307a9b`
  and `adfdc7a7-40bf-4f0c-94c0-da44a2fc0c80`. A sequential bake-off should
  verify output quality, duration, and Mac memory use before selecting a default.
- The external AnimateDiff clone does not take effect until Pinokio ComfyUI is
  restarted; its motion-model weight is not present or validated yet.
