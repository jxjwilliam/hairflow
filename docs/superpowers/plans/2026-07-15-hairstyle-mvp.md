# AI Hairstyle MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working mobile app where users upload a photo, choose a hairstyle template, and get an AI-generated preview.

**Architecture:** React Native (Expo) frontend communicates with Python FastAPI backend. Backend calls Meitu AI API for hair generation and stores images on Alibaba Cloud OSS. MVP has no user system, no payments, no database — just the core try-on flow.

**Tech Stack:** Expo SDK 52+ (TypeScript), Python FastAPI, Meitu AI API, Alibaba OSS, JSON file for template data.

---

## File Structure

```
hairstyle/
├── mobile/                          # Expo app
│   ├── app/
│   │   ├── _layout.tsx              # Root layout + QueryClientProvider
│   │   ├── (tabs)/
│   │   │   ├── _layout.tsx          # Bottom tab nav (Home, Profile placeholder)
│   │   │   └── index.tsx            # Home — template grid + category tabs
│   │   ├── capture.tsx              # Camera / photo picker
│   │   ├── pick-template.tsx        # Template selection after photo
│   │   └── preview.tsx              # AI result display + save/share
│   ├── components/
│   │   ├── TemplateCard.tsx         # Single template thumbnail card
│   │   ├── TemplateGrid.tsx         # Grid of template cards
│   │   ├── CategoryTabs.tsx         # Horizontal category filter pills
│   │   ├── PhotoCapture.tsx         # Camera/upload button + preview
│   │   ├── LoadingOverlay.tsx       # Full-screen loading with progress text
│   │   ├── ResultView.tsx           # Full-screen result image display
│   │   └── ActionButtons.tsx        # Save + Share buttons
│   ├── services/
│   │   ├── api.ts                   # Axios instance + interceptors
│   │   ├── generation.ts           # POST /generate, /regenerate
│   │   └── templates.ts            # GET /templates
│   └── package.json                 # Managed by Expo
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry + CORS
│   │   ├── config.py                # Settings from env
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py           # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── meitu.py             # Meitu AI API client
│   │   │   ├── oss.py               # Alibaba OSS upload
│   │   │   └── face.py              # Face detection stub
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── generation.py        # /api/generate, /api/regenerate
│   │       └── templates.py         # /api/templates
│   ├── data/
│   │   └── templates.json           # 20-30 seed templates
│   ├── tests/
│   │   └── test_generation.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
└── .gitignore
```

---

### Task 1: Init Expo project

**Files:**
- Create: `mobile/` (via `npx create-expo-app`)

- [ ] **Step 1: Create Expo project**

```bash
cd /Users/william.jiang/my-tests/my-fun/hairstyle
npx create-expo-app@latest mobile --template blank-typescript
cd mobile
npx expo install expo-router expo-image expo-image-picker expo-media-library expo-sharing @tanstack/react-query axios react-native-safe-area-context react-native-screens
```

- [ ] **Step 2: Verify project runs**

```bash
cd /Users/william.jiang/my-tests/my-fun/hairstyle/mobile
npx expo start --no-dev --minify 2>&1 | head -5
```

Expected: Metro bundler starts, shows QR code.

---

### Task 2: Init FastAPI backend skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: Create backend directory structure**

```bash
mkdir -p /Users/william.jiang/my-tests/my-fun/hairstyle/backend/app/{models,services,routers}
mkdir -p /Users/william.jiang/my-tests/my-fun/hairstyle/backend/data
mkdir -p /Users/william.jiang/my-tests/my-fun/hairstyle/backend/tests
```

- [ ] **Step 2: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
httpx==0.27.0
Pillow==11.0.0
python-multipart==0.0.12
aliyun-oss2==2.18.0
python-dotenv==1.0.0
```

- [ ] **Step 3: Create backend/app/__init__.py**

Empty file.

- [ ] **Step 4: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    meitu_api_key: str = ""
    meitu_api_secret: str = ""
    oss_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key: str = ""
    oss_secret_key: str = ""
    ali_cloud_vision_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

- [ ] **Step 5: Create backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import generation, templates

app = FastAPI(title="Hairstyle MVP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(templates.router)
app.include_router(generation.router)


@app.get("/")
async def root():
    return {"status": "ok"}
```

- [ ] **Step 6: Verify backend starts**

```bash
cd /Users/william.jiang/my-tests/my-fun/hairstyle/backend
pip install -r requirements.txt -q
uvicorn app.main:app --port 8000 &
sleep 2
curl http://localhost:8000/
kill %1 2>/dev/null
```

Expected: `{"status":"ok"}`

---

### Task 3: Create seed template data

**Files:**
- Create: `backend/data/templates.json`

- [ ] **Step 1: Create templates.json with 20 seed hairstyles**

```json
[
  {
    "id": "m1",
    "name": "清爽短发",
    "category": "men",
    "tags": ["短发", "清爽", "商务"],
    "style_id": "meitu_style_001",
    "thumbnail": "https://via.placeholder.com/200x260?text=Short",
    "description": "干净利落的短发造型"
  },
  {
    "id": "m2",
    "name": "纹理碎发",
    "category": "men",
    "tags": ["短发", "纹理", "休闲"],
    "style_id": "meitu_style_002",
    "thumbnail": "https://via.placeholder.com/200x260?text=Texture",
    "description": "有层次感的碎发效果"
  },
  {
    "id": "m3",
    "name": "韩式微分",
    "category": "men",
    "tags": ["中发", "韩式", "时尚"],
    "style_id": "meitu_style_003",
    "thumbnail": "https://via.placeholder.com/200x260?text=Korean",
    "description": "韩系微分发型"
  },
  {
    "id": "w1",
    "name": "法式大波浪",
    "category": "women",
    "tags": ["长发", "卷发", "优雅"],
    "style_id": "meitu_style_004",
    "thumbnail": "https://via.placeholder.com/200x260?text=Wave",
    "description": "浪漫法式大波浪"
  },
  {
    "id": "w2",
    "name": "及肩锁骨发",
    "category": "women",
    "tags": ["中发", "直发", "知性"],
    "style_id": "meitu_style_005",
    "thumbnail": "https://via.placeholder.com/200x260?text=Lob",
    "description": "优雅锁骨发"
  },
  {
    "id": "w3",
    "name": "蛋蛋卷",
    "category": "women",
    "tags": ["中发", "卷发", "可爱"],
    "style_id": "meitu_style_006",
    "thumbnail": "https://via.placeholder.com/200x260?text=EggRoll",
    "description": "俏皮蛋蛋卷发型"
  },
  {
    "id": "w4",
    "name": "公主切",
    "category": "women",
    "tags": ["长发", "直发", "个性"],
    "style_id": "meitu_style_007",
    "thumbnail": "https://via.placeholder.com/200x260?text=Princess",
    "description": "二次元感公主切"
  },
  {
    "id": "m4",
    "name": "美式寸头",
    "category": "men",
    "tags": ["超短", "硬朗", "美式"],
    "style_id": "meitu_style_008",
    "thumbnail": "https://via.placeholder.com/200x260?text=Buzz",
    "description": "硬朗寸头"
  },
  {
    "id": "w5",
    "name": "黑长直",
    "category": "women",
    "tags": ["长发", "直发", "经典"],
    "style_id": "meitu_style_009",
    "thumbnail": "https://via.placeholder.com/200x260?text=LongStraight",
    "description": "经典黑长直"
  },
  {
    "id": "m5",
    "name": "复古油头",
    "category": "men",
    "tags": ["短发", "复古", "绅士"],
    "style_id": "meitu_style_010",
    "thumbnail": "https://via.placeholder.com/200x260?text=Pompadour",
    "description": "经典复古油头"
  },
  {
    "id": "w6",
    "name": "羊毛卷",
    "category": "women",
    "tags": ["中发", "卷发", "复古"],
    "style_id": "meitu_style_011",
    "thumbnail": "https://via.placeholder.com/200x260?text=Wool",
    "description": "蓬松羊毛卷"
  },
  {
    "id": "m6",
    "name": "侧分纹理",
    "category": "men",
    "tags": ["中发", "纹理", "成熟"],
    "style_id": "meitu_style_012",
    "thumbnail": "https://via.placeholder.com/200x260?text=SidePart",
    "description": "成熟侧分纹理"
  },
  {
    "id": "w7",
    "name": "波波头",
    "category": "women",
    "tags": ["短发", "直发", "干练"],
    "style_id": "meitu_style_013",
    "thumbnail": "https://via.placeholder.com/200x260?text=Bob",
    "description": "经典波波头"
  },
  {
    "id": "m7",
    "name": "飞机头",
    "category": "men",
    "tags": ["超短", "个性", "潮流"],
    "style_id": "meitu_style_014",
    "thumbnail": "https://via.placeholder.com/200x260?text=Spike",
    "description": "个性飞机头"
  },
  {
    "id": "w8",
    "name": "木马卷",
    "category": "women",
    "tags": ["长发", "卷发", "甜美"],
    "style_id": "meitu_style_015",
    "thumbnail": "https://via.placeholder.com/200x260?text=WoodHorse",
    "description": "甜美木马卷"
  }
]
```

---

### Task 4: Backend — Pydantic schemas

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/schemas.py`

- [ ] **Step 1: Create models/__init__.py**

Empty file.

- [ ] **Step 2: Create backend/app/models/schemas.py**

```python
from pydantic import BaseModel
from typing import Optional


class TemplateOut(BaseModel):
    id: str
    name: str
    category: str
    tags: list[str]
    style_id: str
    thumbnail: str
    description: str


class GenerateRequest(BaseModel):
    photo_base64: str
    style_id: str


class RegenerateRequest(BaseModel):
    image_id: str
    length: Optional[float] = None
    curl: Optional[float] = None
    color: Optional[str] = None
    bang_style: Optional[str] = None


class GenerateResponse(BaseModel):
    image_url: str
    image_id: str


class UploadResponse(BaseModel):
    url: str
    image_id: str
```

---

### Task 5: Backend — Templates API

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/templates.py`

- [ ] **Step 1: Create routers/__init__.py**

Empty file.

- [ ] **Step 2: Create backend/app/routers/templates.py**

```python
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.models.schemas import TemplateOut

router = APIRouter(prefix="/api/templates", tags=["templates"])

TEMPLATES_PATH = Path(__file__).parent.parent.parent / "data" / "templates.json"


def _load_templates() -> list[dict]:
    with open(TEMPLATES_PATH) as f:
        return json.load(f)


@router.get("", response_model=list[TemplateOut])
async def list_templates(category: str | None = None):
    templates = _load_templates()
    if category:
        templates = [t for t in templates if t["category"] == category]
    return templates


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: str):
    templates = _load_templates()
    for t in templates:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")
```

- [ ] **Step 3: Quick test**

```bash
cd /Users/william.jiang/my-tests/my-fun/hairstyle/backend
uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/templates | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} templates loaded')"
curl -s http://localhost:8000/api/templates?category=women | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} women templates')"
kill %1 2>/dev/null
```

Expected: "15 templates loaded", "8 women templates"

---

### Task 6: Backend — OSS service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/oss.py`

- [ ] **Step 1: Create services/__init__.py**

Empty file.

- [ ] **Step 2: Create backend/app/services/oss.py**

```python
import io
import uuid
from typing import BinaryIO
import oss2
from app.config import settings


class OSSService:
    def __init__(self):
        auth = oss2.Auth(settings.oss_access_key, settings.oss_secret_key)
        self.bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)

    def upload_image(self, data: bytes, content_type: str = "image/png") -> str:
        image_id = f"gen/{uuid.uuid4().hex}.png"
        self.bucket.put_object(image_id, io.BytesIO(data), headers={"Content-Type": content_type})
        url = f"https://{settings.oss_bucket}.{settings.oss_endpoint}/{image_id}"
        return url, image_id


oss_service = OSSService()
```

---

### Task 7: Backend — Meitu API service

**Files:**
- Create: `backend/app/services/meitu.py`

- [ ] **Step 1: Create backend/app/services/meitu.py**

```python
import httpx
from app.config import settings


class MeituService:
    def __init__(self):
        self.base_url = "https://api.meitu.com/v1"  # TODO: confirm actual endpoint
        self.api_key = settings.meitu_api_key
        self.api_secret = settings.meitu_api_secret

    async def generate_hairstyle(self, photo_base64: str, style_id: str) -> bytes:
        """Call Meitu hairstyle generation API and return image bytes."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/hairstyle/generate",
                json={
                    "api_key": self.api_key,
                    "api_secret": self.api_secret,
                    "image": photo_base64,
                    "style_id": style_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Assume API returns base64-encoded result image
            result_base64 = data["data"]["result_image"]
            import base64
            return base64.b64decode(result_base64)

    async def regenerate_hairstyle(
        self, photo_base64: str, style_id: str, params: dict
    ) -> bytes:
        """Call Meitu API with adjustment parameters."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            body = {
                "api_key": self.api_key,
                "api_secret": self.api_secret,
                "image": photo_base64,
                "style_id": style_id,
            }
            if "length" in params:
                body["hair_length"] = params["length"]
            if "curl" in params:
                body["curl_level"] = params["curl"]
            if "color" in params:
                body["hair_color"] = params["color"]
            if "bang_style" in params:
                body["bang_style"] = params["bang_style"]

            resp = await client.post(f"{self.base_url}/hairstyle/regenerate", json=body)
            resp.raise_for_status()
            data = resp.json()
            import base64
            return base64.b64decode(data["data"]["result_image"])


meitu_service = MeituService()
```

---

### Task 8: Backend — Generation API

**Files:**
- Create: `backend/app/routers/generation.py`
- Create: `backend/app/services/face.py`

- [ ] **Step 1: Create backend/app/services/face.py**

```python
class FaceService:
    async def detect_and_segment(self, photo_base64: str) -> dict:
        """Stub: In production, call Aliyun SegmentHair API.
        Returns face detection result."""
        return {"face_detected": True, "segment_ok": True}


face_service = FaceService()
```

- [ ] **Step 2: Create backend/app/routers/generation.py**

```python
import base64
import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerateRequest, GenerateResponse, RegenerateRequest, UploadResponse
from app.services.meitu import meitu_service
from app.services.oss import oss_service
from app.services.face import face_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    # 1. Face detection
    face_result = await face_service.detect_and_segment(req.photo_base64)
    if not face_result.get("face_detected"):
        raise HTTPException(status_code=400, detail="No face detected in photo")

    # 2. Call Meitu API
    try:
        image_bytes = await meitu_service.generate_hairstyle(req.photo_base64, req.style_id)
    except Exception as e:
        logger.error(f"Meitu API call failed: {e}")
        raise HTTPException(status_code=502, detail="AI generation failed")

    # 3. Upload to OSS
    url, image_id = oss_service.upload_image(image_bytes)

    return GenerateResponse(image_url=url, image_id=image_id)


@router.post("/regenerate", response_model=GenerateResponse)
async def regenerate(req: RegenerateRequest):
    params = req.model_dump(exclude={"image_id"}, exclude_none=True)
    # In production, retrieve original photo by image_id
    # For MVP, caller must re-send photo
    # This is a placeholder — real implementation needs photo from storage
    raise HTTPException(status_code=501, detail="Regenerate not yet implemented in MVP")
```

---

### Task 9: Backend — Verify full startup

**Files:**
- None (integration check)

- [ ] **Step 1: Start server and test endpoints**

```bash
cd /Users/william.jiang/my-tests/my-fun/hairstyle/backend
uvicorn app.main:app --port 8000 &
sleep 2
echo "=== Root ===" && curl -s http://localhost:8000/
echo ""
echo "=== Templates ===" && curl -s http://localhost:8000/api/templates | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} templates')"
echo "=== Generate (should fail - no face) ===" && curl -s -X POST http://localhost:8000/api/generate -H "Content-Type: application/json" -d '{"photo_base64":"","style_id":"m1"}'
kill %1 2>/dev/null
```

Expected: Root returns ok, templates return 15, generate returns 400 "No face detected".

---

### Task 10: Frontend — API service layer

**Files:**
- Create: `mobile/services/api.ts`
- Create: `mobile/services/generation.ts`
- Create: `mobile/services/templates.ts`

- [ ] **Step 1: Create mobile/services/api.ts**

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: __DEV__ ? 'http://192.168.1.100:8000' : 'https://api.your-domain.com',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

export default api;
```

- [ ] **Step 2: Create mobile/services/templates.ts**

```typescript
import api from './api';
import { Template } from '../types';

export async function fetchTemplates(category?: string): Promise<Template[]> {
  const params = category ? { category } : {};
  const res = await api.get('/api/templates', { params });
  return res.data;
}

export async function fetchTemplate(id: string): Promise<Template> {
  const res = await api.get(`/api/templates/${id}`);
  return res.data;
}
```

- [ ] **Step 3: Create mobile/types.ts**

```typescript
export interface Template {
  id: string;
  name: string;
  category: string;
  tags: string[];
  style_id: string;
  thumbnail: string;
  description: string;
}

export interface GenerateResult {
  image_url: string;
  image_id: string;
}
```

- [ ] **Step 4: Create mobile/services/generation.ts**

```typescript
import api from './api';
import { GenerateResult } from '../types';

export async function generateHairstyle(
  photoBase64: string,
  styleId: string,
): Promise<GenerateResult> {
  const res = await api.post('/api/generate', {
    photo_base64: photoBase64,
    style_id: styleId,
  });
  return res.data;
}
```

---

### Task 11: Frontend — Root layout + tab navigation

**Files:**
- Create: `mobile/app/_layout.tsx`
- Create: `mobile/app/(tabs)/_layout.tsx`
- Modify: `mobile/app/(tabs)/index.tsx` (replace default)

- [ ] **Step 1: Create mobile/app/_layout.tsx**

```typescript
import { Stack } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="capture" options={{ presentation: 'modal' }} />
        <Stack.Screen name="pick-template" />
        <Stack.Screen name="preview" options={{ presentation: 'fullScreenModal' }} />
      </Stack>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 2: Create mobile/app/(tabs)/_layout.tsx**

```typescript
import { Tabs } from 'expo-router';
import { Text } from 'react-native';

export default function TabLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }}>
      <Tabs.Screen
        name="index"
        options={{
          title: '发型',
          tabBarIcon: () => <Text>💇</Text>,
        }}
      />
    </Tabs>
  );
}
```

---

### Task 12: Frontend — Home screen (template grid + categories)

**Files:**
- Modify: `mobile/app/(tabs)/index.tsx`
- Create: `mobile/components/TemplateCard.tsx`
- Create: `mobile/components/TemplateGrid.tsx`
- Create: `mobile/components/CategoryTabs.tsx`

- [ ] **Step 1: Create mobile/components/CategoryTabs.tsx**

```typescript
import React from 'react';
import { ScrollView, TouchableOpacity, Text, StyleSheet } from 'react-native';

const CATEGORIES = [
  { key: '', label: '全部' },
  { key: 'men', label: '男士' },
  { key: 'women', label: '女士' },
];

interface Props {
  selected: string;
  onSelect: (key: string) => void;
}

export default function CategoryTabs({ selected, onSelect }: Props) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.container}>
      {CATEGORIES.map((cat) => (
        <TouchableOpacity
          key={cat.key}
          style={[styles.pill, selected === cat.key && styles.pillActive]}
          onPress={() => onSelect(cat.key)}
        >
          <Text style={[styles.pillText, selected === cat.key && styles.pillTextActive]}>
            {cat.label}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: 16, paddingVertical: 8 },
  pill: { paddingHorizontal: 20, paddingVertical: 8, borderRadius: 20, backgroundColor: '#f0f0f0', marginRight: 8 },
  pillActive: { backgroundColor: '#2563eb' },
  pillText: { fontSize: 14, color: '#666' },
  pillTextActive: { color: '#fff', fontWeight: '600' },
});
```

- [ ] **Step 2: Create mobile/components/TemplateCard.tsx**

```typescript
import React from 'react';
import { TouchableOpacity, Image, Text, View, StyleSheet } from 'react-native';
import { Template } from '../types';

interface Props {
  template: Template;
  onPress: (t: Template) => void;
}

export default function TemplateCard({ template, onPress }: Props) {
  return (
    <TouchableOpacity style={styles.card} onPress={() => onPress(template)}>
      <Image source={{ uri: template.thumbnail }} style={styles.image} />
      <View style={styles.info}>
        <Text style={styles.name} numberOfLines={1}>{template.name}</Text>
        <Text style={styles.desc} numberOfLines={2}>{template.description}</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: { flex: 1, margin: 6, backgroundColor: '#fff', borderRadius: 12, overflow: 'hidden', elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 4 },
  image: { width: '100%', height: 160, resizeMode: 'cover' },
  info: { padding: 10 },
  name: { fontSize: 14, fontWeight: '600' },
  desc: { fontSize: 12, color: '#888', marginTop: 2 },
});
```

- [ ] **Step 3: Create mobile/components/TemplateGrid.tsx**

```typescript
import React from 'react';
import { FlatList, StyleSheet } from 'react-native';
import TemplateCard from './TemplateCard';
import { Template } from '../types';

interface Props {
  templates: Template[];
  onSelect: (t: Template) => void;
}

export default function TemplateGrid({ templates, onSelect }: Props) {
  return (
    <FlatList
      data={templates}
      keyExtractor={(item) => item.id}
      numColumns={2}
      renderItem={({ item }) => <TemplateCard template={item} onPress={onSelect} />}
      contentContainerStyle={styles.list}
      columnWrapperStyle={styles.row}
    />
  );
}

const styles = StyleSheet.create({
  list: { padding: 6 },
  row: { justifyContent: 'space-between' },
});
```

- [ ] **Step 4: Rewrite mobile/app/(tabs)/index.tsx**

```typescript
import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { fetchTemplates } from '../../services/templates';
import CategoryTabs from '../../components/CategoryTabs';
import TemplateGrid from '../../components/TemplateGrid';
import { Template } from '../../types';

export default function HomeScreen() {
  const [category, setCategory] = useState('');
  const router = useRouter();

  const { data: templates = [] } = useQuery({
    queryKey: ['templates', category],
    queryFn: () => fetchTemplates(category || undefined),
  });

  const handleSelect = (template: Template) => {
    router.push({ pathname: '/capture', params: { templateId: template.id } });
  };

  return (
    <View style={styles.container}>
      <CategoryTabs selected={category} onSelect={setCategory} />
      <TemplateGrid templates={templates} onSelect={handleSelect} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
});
```

---

### Task 13: Frontend — Capture screen

**Files:**
- Create: `mobile/app/capture.tsx`
- Create: `mobile/components/PhotoCapture.tsx`

- [ ] **Step 1: Create mobile/components/PhotoCapture.tsx**

```typescript
import React from 'react';
import { View, TouchableOpacity, Text, Image, StyleSheet } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

interface Props {
  photoUri: string | null;
  onPhotoTaken: (base64: string, uri: string) => void;
}

export default function PhotoCapture({ photoUri, onPhotoTaken }: Props) {
  const takePhoto = async () => {
    const result = await ImagePicker.launchCameraAsync({
      base64: true,
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      onPhotoTaken(result.assets[0].base64 || '', result.assets[0].uri);
    }
  };

  const pickPhoto = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      base64: true,
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      onPhotoTaken(result.assets[0].base64 || '', result.assets[0].uri);
    }
  };

  return (
    <View style={styles.container}>
      {photoUri ? (
        <Image source={{ uri: photoUri }} style={styles.preview} />
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>上传正面头像照片</Text>
        </View>
      )}
      <View style={styles.buttons}>
        <TouchableOpacity style={styles.btn} onPress={takePhoto}>
          <Text style={styles.btnText}>📸 拍照</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={pickPhoto}>
          <Text style={[styles.btnText, styles.btnTextOutline]}>🖼️ 相册</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  preview: { width: 300, height: 400, borderRadius: 16, marginBottom: 24 },
  placeholder: { width: 300, height: 400, borderRadius: 16, backgroundColor: '#e5e7eb', alignItems: 'center', justifyContent: 'center', marginBottom: 24 },
  placeholderText: { color: '#999', fontSize: 16 },
  buttons: { flexDirection: 'row', gap: 16 },
  btn: { paddingHorizontal: 32, paddingVertical: 14, borderRadius: 12, backgroundColor: '#2563eb' },
  btnOutline: { backgroundColor: 'transparent', borderWidth: 2, borderColor: '#2563eb' },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  btnTextOutline: { color: '#2563eb' },
});
```

- [ ] **Step 2: Create mobile/app/capture.tsx**

```typescript
import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import PhotoCapture from '../components/PhotoCapture';

export default function CaptureScreen() {
  const { templateId } = useLocalSearchParams<{ templateId: string }>();
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [photoBase64, setPhotoBase64] = useState<string>('');
  const router = useRouter();

  const handlePhotoTaken = (base64: string, uri: string) => {
    setPhotoBase64(base64);
    setPhotoUri(uri);
    // Auto-navigate to pick template (or generate directly if template pre-selected)
    router.replace({ pathname: '/preview', params: { templateId, photoBase64: base64 } });
  };

  return (
    <View style={styles.container}>
      <PhotoCapture photoUri={photoUri} onPhotoTaken={handlePhotoTaken} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
});
```

---

### Task 14: Frontend — Preview screen + result components

**Files:**
- Create: `mobile/app/preview.tsx`
- Create: `mobile/components/LoadingOverlay.tsx`
- Create: `mobile/components/ResultView.tsx`
- Create: `mobile/components/ActionButtons.tsx`

- [ ] **Step 1: Create mobile/components/LoadingOverlay.tsx**

```typescript
import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';

interface Props {
  message?: string;
}

export default function LoadingOverlay({ message = '正在生成效果图...' }: Props) {
  return (
    <View style={styles.overlay}>
      <ActivityIndicator size="large" color="#2563eb" />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(255,255,255,0.92)', alignItems: 'center', justifyContent: 'center', zIndex: 100 },
  text: { marginTop: 16, fontSize: 16, color: '#555' },
});
```

- [ ] **Step 2: Create mobile/components/ResultView.tsx**

```typescript
import React from 'react';
import { Image, StyleSheet, Dimensions } from 'react-native';

const { width } = Dimensions.get('window');

interface Props {
  imageUrl: string;
}

export default function ResultView({ imageUrl }: Props) {
  return (
    <Image
      source={{ uri: imageUrl }}
      style={styles.image}
      resizeMode="contain"
    />
  );
}

const styles = StyleSheet.create({
  image: { width: width, height: width * 1.3, borderRadius: 12 },
});
```

- [ ] **Step 3: Create mobile/components/ActionButtons.tsx**

```typescript
import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';

interface Props {
  imageUrl: string;
  onRetry?: () => void;
}

export default function ActionButtons({ imageUrl, onRetry }: Props) {
  const handleSave = async () => {
    try {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status !== 'granted') return;
      await MediaLibrary.saveToLibraryAsync(imageUrl);
      alert('已保存到相册');
    } catch {
      alert('保存失败，请稍后重试');
    }
  };

  const handleShare = async () => {
    try {
      await Sharing.shareAsync(imageUrl);
    } catch {
      // user cancelled
    }
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity style={styles.btn} onPress={handleSave}>
        <Text style={styles.btnText}>💾 保存</Text>
      </TouchableOpacity>
      <TouchableOpacity style={[styles.btn, styles.btnSecondary]} onPress={handleShare}>
        <Text style={styles.btnText}>📤 分享</Text>
      </TouchableOpacity>
      {onRetry && (
        <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={onRetry}>
          <Text style={[styles.btnText, styles.btnTextOutline]}>🔄 重试</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flexDirection: 'row', justifyContent: 'center', gap: 12, paddingVertical: 16 },
  btn: { paddingHorizontal: 24, paddingVertical: 12, borderRadius: 10, backgroundColor: '#2563eb' },
  btnSecondary: { backgroundColor: '#059669' },
  btnOutline: { backgroundColor: 'transparent', borderWidth: 2, borderColor: '#2563eb' },
  btnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  btnTextOutline: { color: '#2563eb' },
});
```

- [ ] **Step 4: Create mobile/app/preview.tsx**

```typescript
import React, { useState } from 'react';
import { View, StyleSheet, SafeAreaView } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import { generateHairstyle } from '../services/generation';
import LoadingOverlay from '../components/LoadingOverlay';
import ResultView from '../components/ResultView';
import ActionButtons from '../components/ActionButtons';

export default function PreviewScreen() {
  const { templateId, photoBase64 } = useLocalSearchParams<{ templateId: string; photoBase64: string }>();
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: () => generateHairstyle(photoBase64!, templateId!),
    onSuccess: (data) => setResultUrl(data.image_url),
    onError: () => alert('生成失败，请重试'),
  });

  // Auto-start generation on mount
  React.useEffect(() => {
    if (photoBase64 && templateId && !mutation.isIdle) return;
    mutation.mutate();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      {mutation.isPending && <LoadingOverlay message="AI 正在生成发型效果图..." />}

      {resultUrl && (
        <>
          <ResultView imageUrl={resultUrl} />
          <ActionButtons
            imageUrl={resultUrl}
            onRetry={() => mutation.mutate()}
          />
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
});
```

---

### Task 15: Backend — Docker + env config

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`

- [ ] **Step 1: Create backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create backend/.env.example**

```ini
MEITU_API_KEY=your_key_here
MEITU_API_SECRET=your_secret_here
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=your-bucket
OSS_ACCESS_KEY=your_ak
OSS_SECRET_KEY=your_sk
ALI_CLOUD_VISION_KEY=
```

---

### Task 16: Final integration check

**Files:**
- None

- [ ] **Step 1: Start backend and verify endpoints**

```bash
cd /Users/william.jiang/my-tests/my-fun/hairstyle/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 2
echo "=== Health ===" && curl -s http://localhost:8000/ | python3 -m json.tool
echo "=== Templates ===" && curl -s http://localhost:8000/api/templates?category=men | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'  {t[\"id\"]}: {t[\"name\"]}') for t in d]"
kill %1 2>/dev/null
```

- [ ] **Step 2: Update mobile API base URL**

Edit `mobile/services/api.ts` to point to your actual backend IP when testing on device.

```typescript
// Use your computer's LAN IP for device testing
baseURL: 'http://192.168.x.x:8000',
```
