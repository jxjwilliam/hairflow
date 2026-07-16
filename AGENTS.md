# Hairstyle — Agent Guide

AI 虚拟发型试戴 App（MVP 阶段），面向国内理发行业。

## Tech Stack

- **Frontend:** React Native (Expo SDK 57), Expo Router, TypeScript, @tanstack/react-query, axios
- **Backend:** Python 3.12, FastAPI, uvicorn, httpx, Pillow, aliyun-oss-python-sdk
- **AI API:** 美图奇想大模型 (Meitu)
- **Storage:** 阿里云 OSS

## Architecture

- Monorepo: `mobile/` + `backend/`
- Mobile → HTTP → Backend → Meitu API + Alibaba OSS
- No database in MVP (JSON file for templates, OSS for images)
- No user system, no auth, no payments in MVP

## Key Patterns

### Backend (FastAPI)
- Pydantic v2 models in `app/models/schemas.py`
- Routers in `app/routers/` — each file is a module-level router
- Services in `app/services/` — stateless classes, instantiated per-request
- Settings via `pydantic-settings` from `.env` file, accessed as `from app.config import settings`
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

### Project State
- 15 seed templates (7 men, 8 women) in `backend/data/templates.json`
- Meitu API endpoint is a placeholder — real endpoint needed when API key is obtained
- OSS service uses lazy init — safe to call before `.env` is configured
- Face detection is a stub (`app/services/face.py`)

## Adding a New Template
1. Add JSON entry to `backend/data/templates.json`
2. Fields: `id`, `name`, `category`, `tags`, `style_id`, `thumbnail`, `description`

## Running

### Backend
```bash
cd backend
cp .env.example .env   # then fill in keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Mobile
```bash
cd mobile
npx expo start
```

`mobile/services/api.ts` auto-detects the backend host per platform (web=localhost, Android emulator=10.0.2.2, device=LAN IP from expo).

## API Endpoints

| Method | Path | Status |
|--------|------|--------|
| GET | `/` | Health check |
| GET | `/api/templates` | List (optional `?category=men|women`) |
| GET | `/api/templates/{id}` | Detail |
| POST | `/api/generate` | Generate hairstyle (body: `photo_base64` + `style_id`) |
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
- **Commits** — only when explicitly requested (Sisyphus does not auto-commit)

## P1 Items (not yet implemented)
- Hairstyle parameter sliders (length, curl, color, bangs)
- Multi-view switching
- Before/after comparison
- User login (phone/WeChat/Alipay)
- Credit consumption + payment
