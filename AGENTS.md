# Hairstyle — Agent Guide

AI 虚拟发型试戴 App（MVP 阶段），面向国内理发行业。

## Tech Stack

- **Frontend:** React Native (Expo SDK 57), Expo Router, TypeScript, @tanstack/react-query, axios
- **Backend:** Python 3.12, FastAPI, uvicorn, httpx, Pillow, mediapipe, opencv-python-headless
- **AI:** Local **ComfyUI** + **PhotoMaker v1** + SD1.5 (`photon_v1.safetensors`)
- **Face detection:** MediaPipe (local), not Aliyun Vision
- **Storage (dev):** Local disk — `backend/output/` for generations, `backend/static/thumbnails/` for catalog
- **Legacy (unused by mobile):** Meitu mtlab API (`meitu.py`), Alibaba OSS (`oss.py`)

## Architecture

- Monorepo: `mobile/` + `backend/`
- Mobile → HTTP → Backend → **ComfyUI** (`COMFYUI_URL`, default `http://127.0.0.1:8188`)
- Active generate endpoint: `POST /api/comfyui/generate`
- Templates served from `backend/data/templates_comfyui.json`
- No database in MVP (JSON templates + local files)
- No user system, no auth, no payments in MVP

```
Mobile generation.ts
  → POST /api/comfyui/generate { photo_base64, style_id: templateId }
  → face_service (MediaPipe)
  → comfyui_service (PhotoMaker workflow)
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
- **Generate:** `services/generation.ts` posts to `/api/comfyui/generate` with `style_id` = **template id** (from route), not Meitu `meitu_style_*`

### Project State
- 15 seed templates (7 men, 8 women) in `backend/data/templates_comfyui.json`
- Catalog PNGs in `backend/static/thumbnails/{id}.png` (regenerate via `scripts/generate_thumbnails.py`)
- PhotoMaker try-on workflows in `backend/workflows/photomaker_hairstyle_*.json`
- Catalog txt2img workflow: `backend/workflows/txt2img_hairstyle_catalog.json`
- Meitu path (`POST /api/generate`) preserved but not used by the app
- Face detection is **MediaPipe** (`app/services/face.py`), not a stub

## Adding a New Template
1. Add entry to `backend/data/templates_comfyui.json` with:
   - `id`, `name`, `category`, `tags`, `thumbnail`, `description`
   - `positive_prompt`, `negative_prompt`, `checkpoint`, `photomaker_model`, `width`, `height`, `steps`, `cfg`, `denoise`
2. Optionally add matching `style_id` in `templates.json` for Meitu legacy compatibility
3. Generate catalog thumb: `python scripts/generate_thumbnails.py --id <id> --force`
4. Optionally add a PhotoMaker workflow JSON under `backend/workflows/` for manual ComfyUI testing

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

## API Endpoints

| Method | Path | Status |
|--------|------|--------|
| GET | `/` | Health check |
| GET | `/api/templates` | List (optional `?category=men|women`); absolute thumbnail URLs |
| GET | `/api/templates/{id}` | Detail |
| POST | `/api/comfyui/generate` | **Primary** — PhotoMaker try-on (`photo_base64` + `style_id` = template id) |
| GET | `/api/comfyui/output/{filename}` | Serve local generation output |
| POST | `/api/generate` | Legacy Meitu (not used by mobile) |
| POST | `/api/regenerate` | Not yet implemented (returns 501) |

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

## P1 Items (not yet implemented)
- Hairstyle parameter sliders (length, curl, color, bangs)
- Multi-view switching
- Before/after comparison
- User login (phone/WeChat/Alipay)
- Credit consumption + payment
