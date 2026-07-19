# Tasks 7–9 delivery report

## Task 7 — bake-off CLI

- Added `backend/scripts/video_bakeoff.py`, which runs LTX, Hunyuan, and
  AnimateDiff serially against each supplied still.
- Successful runs write `backend/output/bakeoff/<still-stem>/<pipeline>.mp4`.
  Every attempt is summarized in `backend/output/bakeoff/report.md`; failures
  are captured in the report and cause exit code 2 after remaining pipelines
  have been attempted.
- Added `make video-bakeoff STILL=backend/output/<try-on-still>.png`.
- No live smoke generation was run because `backend/output/` contains no
  existing PNG stills. The script import, unit test, and `--help` command were
  verified instead.

## Task 8 — mobile preview

- Installed `expo-av` and added `VideoGenerateResult`.
- Added `generateVideo()` with a 900-second request timeout.
- Preview now exposes `生成短视频` below the existing actions after a still is
  available, presents the required Chinese loading/error messages, and renders
  the resulting MP4 using native controls. The UI does not expose a pipeline
  picker.

## Task 9 — documentation and model manifest

- README and AGENTS document `POST /api/comfyui/generate-video`,
  `DEFAULT_VIDEO_PIPELINE=ltx`, and `make video-bakeoff`.
- `docs/oc_short_video.md` identifies LTX as the current default and keeps the
  AnimateDiff custom-node/motion-weight installation guidance.
- Updated the ComfyUI model-locator manifest with video pipeline requirements
  and the FLUX text encoder files from the plan.

## Verification

- `cd backend && PYTHONPATH=. ../venv/bin/python -m pytest tests/ -v`:
  30 passed (one pre-existing Pydantic v2 deprecation warning).
- `cd mobile && npx tsc --noEmit`: passed.
- `backend/scripts/video_bakeoff.py --help`: passed.
- Manifest JSON parsed successfully.
