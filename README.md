# Hairstyle — AI 虚拟发型试戴

面向国内理发行业的 AI 虚拟发型试戴 App。用户上传人像照片，选择发型模板，本地 ComfyUI（PhotoMaker）生成发型效果图，辅助理发决策。

> 个人开发者业余项目 · MVP 阶段  
> **当前 AI 后端：本地 ComfyUI + PhotoMaker v1**（美图 API 代码仍保留为遗留路径，App 默认不再调用）

---

## 功能

| 功能 | 状态 |
|------|------|
| 发型模板浏览（网格列表 + 男女分类 Tab + 本地 catalog 缩略图） | ✅ |
| 拍照 / 相册上传头像 | ✅ |
| AI 生成发型效果图（本地 ComfyUI PhotoMaker） | ✅ |
| 效果图预览 | ✅ |
| 保存到相册 / 分享 | ✅ |
| 发型参数调整（长度、颜色、卷曲度） | ⏳ P1 |
| 脸型适配推荐 | ⏳ P2 |

---

## 架构

```
mobile/  (React Native Expo)
    │  HTTP
    ▼
backend/  (Python FastAPI)
    ├── GET  /api/templates          → templates_comfyui.json + /static/thumbnails
    ├── POST /api/comfyui/generate   → Face (MediaPipe) + ComfyUI PhotoMaker
    └── POST /api/generate           → 遗留 Meitu 路径（未接入前端）
              │
              ▼
         ComfyUI :8188  (Pinokio / 本机)
              │
              ▼
         backend/output/  +  backend/static/thumbnails/
```

开发阶段生成结果默认落盘到 `backend/output/`，经 `/api/comfyui/output/{filename}` 提供；模板缩略图在 `backend/static/thumbnails/`。阿里云 OSS / 美图 API 仍可作为可选遗留能力保留在代码中。

### 前端

- **React Native (Expo SDK 57)** + Expo Router 文件路由
- @tanstack/react-query 管理 API 请求和缓存
- TypeScript
- `mobile/services/generation.ts` → **`POST /api/comfyui/generate`**

**页面流：** 首页模板浏览 → 拍照/选照片 → AI 生成 → 预览（保存/分享）

**Web 支持：** 保存/分享按钮在 Web 端自动降级为下载链接和 Web Share API，方便开发调试。

### 后端

- **Python FastAPI** + uvicorn
- **ComfyUI** HTTP API（PhotoMaker v1 + SD1.5 `photon_v1`）
- MediaPipe 本地人脸检测（`app/services/face.py`）
- 模板数据：`backend/data/templates_comfyui.json`（含 prompt / checkpoint 参数）
- 遗留：美图 API（`meitu.py`）、OSS（`oss.py`）

---

## 项目结构

```
hairstyle/
├── mobile/                   # React Native (Expo) 前端
│   ├── app/
│   │   ├── (tabs)/
│   │   │   ├── _layout.tsx   # Tab 导航
│   │   │   └── index.tsx     # 首页模板浏览
│   │   ├── capture.tsx       # 拍照/相册上传
│   │   ├── preview.tsx       # AI 生成预览
│   │   └── _layout.tsx       # 根布局 (QueryClientProvider)
│   ├── components/
│   └── services/
│       ├── api.ts            # Axios 实例
│       ├── templates.ts      # 模板 API
│       └── generation.ts     # → /api/comfyui/generate
├── backend/                   # Python FastAPI
│   ├── app/
│   │   ├── main.py           # 入口 + /static 挂载
│   │   ├── config.py         # 含 COMFYUI_URL
│   │   ├── routers/
│   │   │   ├── templates.py         # GET /api/templates
│   │   │   ├── comfyui_generation.py # POST /api/comfyui/generate
│   │   │   └── generation.py        # 遗留 Meitu POST /api/generate
│   │   ├── services/
│   │   │   ├── comfyui.py    # ComfyUI HTTP 客户端
│   │   │   ├── face.py       # MediaPipe 人脸检测
│   │   │   ├── meitu.py      # 遗留美图客户端
│   │   │   └── oss.py        # 可选 OSS
│   │   └── models/
│   ├── data/
│   │   ├── templates_comfyui.json  # 主模板（prompts + 缩略图路径）
│   │   └── templates.json          # 遗留 Meitu style_id 对照
│   ├── workflows/            # 可拖入 ComfyUI Web UI 的 JSON
│   ├── scripts/
│   │   ├── generate_thumbnails.py  # catalog 缩略图批生成
│   │   └── test_comfyui.py
│   ├── static/thumbnails/    # 模板展示图
│   ├── output/               # 生成结果（本地）
│   └── tests/
├── docs/
├── README.md
└── AGENTS.md
```

---

## 快速开始

### 前置条件

- Node.js 20+ / npm
- Python 3.12+
- Expo Go（手机测试）或 Xcode / Android Studio
- **本机 ComfyUI**（推荐 Pinokio），默认 `http://127.0.0.1:8188`
  - Checkpoint: `photon_v1.safetensors`（SD1.5）
  - PhotoMaker: `photomaker-v1.bin`（**不要用 v2**）
- 详见 [`docs/ds_comfyui_setup.md`](docs/ds_comfyui_setup.md) 与 [`backend/workflows/README.md`](backend/workflows/README.md)

### 1. 启动 ComfyUI

确保 Pinokio / ComfyUI 已启动，并确认：

```bash
curl -s http://127.0.0.1:8188/system_stats | head -c 200
```

### 2. 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 至少可保留默认；COMFYUI_URL 默认为本机 8188
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证：

```bash
curl http://localhost:8000/                 # → {"status":"ok"}
curl http://localhost:8000/api/templates    # → 15 个模板（缩略图为绝对 URL）
```

### 3. 前端

```bash
cd mobile
npm install
npx expo start
```

> `mobile/services/api.ts` 会按平台自动探测后端（web=localhost，Android 模拟器=10.0.2.2，真机=Expo LAN IP）。  
> 国内网络扫码连不上时可试：`npx expo start --tunnel`

### 可选：重新生成模板缩略图

```bash
cd backend
python scripts/generate_thumbnails.py              # 全部（已有则跳过）
python scripts/generate_thumbnails.py --id m1 --force --seed 42
```

手动测试 workflow：把 `backend/workflows/*.json` 拖入 ComfyUI Web UI。

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `COMFYUI_URL` | ComfyUI 地址，默认 `http://127.0.0.1:8188` |
| `MEITU_API_KEY` / `MEITU_API_SECRET` / `MEITU_API_APPID` | 遗留美图路径（前端未使用） |
| `OSS_*` | 可选阿里云 OSS（当前 ComfyUI 路径默认本地落盘） |
| `ALI_CLOUD_VISION_KEY` | 未使用（人脸检测已切 MediaPipe） |

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | Health check |
| `GET` | `/api/templates` | 发型模板列表（可选 `?category=men|women`）；缩略图为绝对 URL |
| `GET` | `/api/templates/{id}` | 单个模板详情 |
| `POST` | `/api/comfyui/generate` | **主路径**：上传头像 + `style_id`（模板 id，如 `w1`）→ ComfyUI 生成 |
| `GET` | `/api/comfyui/output/{filename}` | 本地生成结果图 |
| `POST` | `/api/generate` | 遗留 Meitu 生成（前端未接） |
| `POST` | `/api/regenerate` | Stub（501） |

---

## 部署

- **开发：** 本机 FastAPI + 本机 / 局域网 ComfyUI  
- **后端镜像：** `docker build -t hairstyle-api ./backend && docker run -p 8000:8000 hairstyle-api`（生产还需可达的 ComfyUI 服务）  
- **建议：** 阿里云 ECS 轻量应用服务器；GPU 机器跑 ComfyUI，或继续本机 Pinokio 调试

---

## 路线图

- **P1：** 发型参数调整（长度/颜色/卷曲度/刘海）、多视角切换、对比图、用户登录、点数消费
- **P2：** 会员订阅、生成历史、模板收藏、脸型适配推荐、工作流升级（HairPort / ACE++ 等）

---

## 相关文档

| 文档 | 内容 |
|------|------|
| [`AGENTS.md`](AGENTS.md) | Agent / 开发约定 |
| [`docs/ds_comfyui_setup.md`](docs/ds_comfyui_setup.md) | ComfyUI 模型与调试 |
| [`docs/ds_comfyui_proposal.md`](docs/ds_comfyui_proposal.md) | 切换 ComfyUI 的方案说明 |
| [`backend/workflows/README.md`](backend/workflows/README.md) | Workflow 使用说明 |
| [`docs/superpowers/specs/2026-07-17-comfyui-catalog-thumbnails-design.md`](docs/superpowers/specs/2026-07-17-comfyui-catalog-thumbnails-design.md) | Catalog 缩略图设计 |

---

## License

MIT
