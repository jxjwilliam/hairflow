# Hairstyle — Agent Guide

AI 虚拟发型试戴 App（MVP 阶段），面向国内理发行业。

## Tech Stack

- **Frontend:** React Native (Expo SDK 57), Expo Router, TypeScript, @tanstack/react-query, axios
- **Backend:** Python 3.12, FastAPI, uvicorn, httpx, Pillow, mediapipe, opencv-python-headless, SQLAlchemy async (SQLite)
- **AI:** Local **ComfyUI** multi-pipeline — **PhotoMaker v1** + SD1.5 (`photon_v1.safetensors`) default; also `sd15`, `flux` (FLUX.1 Schnell GGUF), `flux_klein` (FLUX.2 Klein 4B GGUF, native edit workflow)
- **Face detection:** MediaPipe (local), not Aliyun Vision
- **Storage (dev):** Local disk — `backend/output/` for generations, `backend/static/thumbnails/` for catalog; SQLite `backend/hairstyle.db` for users/orders/points
- **Legacy (removed):** Meitu mtlab API (`meitu.py`), Alibaba OSS (`oss.py`), legacy `/api/generate` endpoint — all cleaned up

## Architecture

- Monorepo: `mobile/` + `backend/`
- Mobile → HTTP (JWT Bearer) → Backend → **ComfyUI** (`COMFYUI_URL`, default `http://127.0.0.1:8188`)
- Active generate endpoints: `POST /api/comfyui/generate` (still image) and `POST /api/comfyui/generate-video` (short MP4)
- Templates served from `backend/data/templates_comfyui.json`
- SQLite database (`app/database.py`, models in `app/models/{user,order,points_ledger}.py`)
- Auth: phone + dev magic code `888888` → JWT (`app/routers/auth.py`); points/membership/mock-payment implemented; `SKIP_POINTS_CHECK=true` by default in dev

```
Mobile generation.ts
  → POST /api/comfyui/generate { photo_base64, style_id: templateId, pipeline, method, ... }
  → face_service (MediaPipe)
  → comfyui_service.generate(pipeline, method, …)   # dispatches per-pipeline workflow
  → save backend/output/{uuid}.png
  → { image_url, image_id }
```

## Key Patterns

### Backend (FastAPI)
- Pydantic v2 models in `app/models/schemas.py`
- Routers in `app/routers/` — each file is a module-level router
- Services in `app/services/` — prefer shared module-level instances (`comfyui_service`, `face_service`)
- Settings via `pydantic-settings` from `.env`, accessed as `from app.config import settings`
- Static files: `app.mount("/static", StaticFiles(...))` for catalog thumbnails
- Templates list rewrites relative `/static/...` thumbnails to absolute URLs via `request.base_url`
- `style_id` in API responses is merged from legacy `templates.json` (Meitu ids) when present; ComfyUI lookup uses **template `id`** (`m1`, `w1`, …)
- Chinese comments OK in data files, prefer English in code

### Frontend (Expo)
- File-based routing via Expo Router (`app/` directory)
- API calls in `services/` using axios instance from `services/api.ts`
- Server state via `@tanstack/react-query`
- Components are functional + hooks, no class components
- `mobile/types.ts` holds shared TypeScript interfaces
- Image loading: `expo-image` (not React Native Image)
- Photo picker: `expo-image-picker`, returns base64
- Save to album: `expo-media-library`
- Share: `expo-sharing`
- **Generate:** `services/generation.ts` posts to `/api/comfyui/generate` with `style_id` = **template id** (from route)
- **Short video:** Preview calls `/api/comfyui/generate-video` with the generated still URL; no pipeline picker. `DEFAULT_VIDEO_PIPELINE=ltx` selects the backend default.

### Project State
- 15 seed templates (7 men, 8 women) in `backend/data/templates_comfyui.json`
- Catalog PNGs in `backend/static/thumbnails/{id}.png` (regenerate via `scripts/generate_thumbnails.py`)
- PhotoMaker try-on workflows in `backend/static/workflows/photomaker_hairstyle_*.json`
- Catalog txt2img workflow: `backend/static/workflows/txt2img_hairstyle_catalog.json`
- Meitu path (`POST /api/generate`) preserved but not used by the app
- Face detection is **MediaPipe** (`app/services/face.py`), not a stub

## Adding a New Template
1. Add entry to `backend/data/templates_comfyui.json` with:
   - `id`, `name`, `category`, `tags`, `thumbnail`, `description`
   - `positive_prompt`, `negative_prompt`, `checkpoint`, `photomaker_model`, `width`, `height`, `steps`, `cfg`, `denoise`
2. Optionally add matching `style_id` in `templates.json` for Meitu legacy compatibility
3. Generate catalog thumb: `python scripts/generate_thumbnails.py --id <id> --force`
4. Optionally add a PhotoMaker workflow JSON under `backend/static/workflows/` for manual ComfyUI testing

## Running

### ComfyUI (required for generate)
- Start Pinokio ComfyUI (or equivalent) on `8188`
- Models: `photon_v1.safetensors`, `photomaker-v1.bin` (not v2)
- See `docs/ds_comfyui_setup.md`

### Backend
```bash
cd backend
cp .env.example .env   # COMFYUI_URL defaults to http://127.0.0.1:8188
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Mobile
```bash
cd mobile
npx expo start
```

`mobile/services/api.ts` auto-detects the backend host per platform (web=localhost, Android emulator=10.0.2.2, device=LAN IP from expo).

### Tests
```bash
cd backend
PYTHONPATH=. pytest tests/ -v
```

### Catalog thumbnails
```bash
cd backend
python scripts/generate_thumbnails.py
python scripts/generate_thumbnails.py --id m1 --force --seed 42
```

### Video bake-off
```bash
make video-bakeoff STILL=backend/output/<try-on-still>.png
```
Runs LTX, Hunyuan, and AnimateDiff sequentially and writes MP4s plus
`backend/output/bakeoff/report.md`. `DEFAULT_VIDEO_PIPELINE` defaults to `ltx`.

## API Endpoints

| Method | Path | Status |
|--------|------|--------|
| GET | `/` | Health check |
| GET | `/api/templates` | List (optional `?category=men|women`); absolute thumbnail URLs |
| GET | `/api/templates/{id}` | Detail |
| POST | `/api/comfyui/generate` | **Primary** — multi-pipeline (`photo_base64` + `style_id` = template id + `pipeline`/`method`) |
| POST | `/api/comfyui/regenerate` | Parameter-adjusted regeneration (length/curl/color → prompt) |
| POST | `/api/comfyui/generate-multi` | 4-angle generation (front/left/right/back) |
| POST | `/api/comfyui/generate-video` | Generate a short MP4 from `image_id`, `image_url`, or `photo_base64`; default pipeline from `DEFAULT_VIDEO_PIPELINE` |
| GET | `/api/comfyui/output/{filename}` | Serve local generation output |
| POST | `/api/v1/auth/sms/send` · `/sms/login` | Phone login (dev magic code `888888`) → JWT |
| POST | `/api/v1/auth/wechat/login` · `/alipay/login` | Third-party login (stub) |
| GET | `/api/v1/auth/me` | Current user profile (JWT) |
| GET | `/api/v1/payment/packages` · POST `/order` · POST `/mock/notify` | Points packages / order / mock payment callback |
| GET | `/api/v1/membership/tiers` · POST `/upgrade` · GET `/my-status` | Membership tiers / upgrade / status |
| POST | `/api/recommend/by-photo` | Face-shape detection + template recommendation |
| POST | `/api/generate` | Legacy Meitu (not used by mobile) |
| POST | `/api/regenerate` | Legacy stub (returns 501) |

## TypeScript Interfaces (mobile/types.ts)

```typescript
interface Template {
  id: string; name: string; category: string;
  tags: string[]; style_id: string;
  thumbnail: string; description: string;
}

interface GenerateResult {
  image_url: string;
  image_id: string;
}
```

## Conventions

- **No class components** — functional + hooks only
- **No `as any` / `@ts-ignore` / `@ts-expect-error`** — type errors must be properly solved
- **Error handling** — never empty catch blocks, always show user-facing feedback
- **Commits** — only when explicitly requested

## P1 Items (implemented)
- ~~Hairstyle parameter sliders (length, curl, color)~~ ✅ via `/api/comfyui/regenerate` + `ParamPanel.tsx`
- ~~Multi-view switching~~ ✅ via `/api/comfyui/generate-multi` + `AngleSelector.tsx`
- ~~Before/after comparison~~ ✅ `BeforeAfterSlider.tsx`
- ~~User login~~ ✅ phone + magic code (WeChat/Alipay still stubs)
- ~~Credit consumption + payment~~ ✅ points + mock payment (`SKIP_POINTS_CHECK=true` in dev)

## P1/P2 Items (not yet implemented)
- Real SMS channel + real WeChat/Alipay payments
- Cloud generation history, favorites
- Workflow upgrades (HairPort / ACE++)

## Pipeline Notes (flux_klein)
- `flux_klein` img2img uses the **native edit workflow** (`_build_flux_klein_edit_workflow`): `CLIPLoader(type="flux2")` + `qwen_3_4b.safetensors`, selfie injected via `ReferenceLatent`, `CFGGuider(1.0)` + `euler` + `Flux2Scheduler` — preserves facial identity; see `docs/oc_flux2_klein_integration.md`
- flux pipelines only accept `.gguf` checkpoint overrides (template SD1.5 checkpoint is ignored)
- ComfyUI 400 validation details are surfaced in the 502 response body
- Required models: `flux-2-klein-4b-Q8_0.gguf` (unet), `qwen_3_4b.safetensors` (text_encoders), `flux2-vae.safetensors` (vae)
