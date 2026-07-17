# 发型试戴 — AI 虚拟发型试戴

面向国内理发行业的 AI 虚拟发型试戴 App。用户上传人像照片，选择发型模板，本地 ComfyUI（PhotoMaker）生成发型效果图，辅助理发决策。

> 个人开发者业余项目 · MVP 阶段  
> **App 名称：** 发型试戴  
> **当前 AI 后端：本地 ComfyUI + PhotoMaker v1**（美图 API 代码仍保留为遗留路径，App 默认不再调用）

---

## 功能

| 功能 | 状态 |
|------|------|
| 发型模板浏览（响应式网格 + 男女分类 + catalog 缩略图） | ✅ |
| 拍照 / 相册上传头像 | ✅ |
| AI 生成发型效果图（本地 ComfyUI PhotoMaker） | ✅ |
| 效果图预览（保存 / 分享 / 重试） | ✅ |
| 换发型并保留照片继续试戴 | ✅ |
| 「效果」页：本机试戴历史对比 | ✅ |
| 品牌 Logo / Favicon（Web + App） | ✅ |
| 发型参数调整（长度、颜色、卷曲度） | ⏳ P1 |
| 脸型适配推荐 | ⏳ P2 |

---

## 架构

```
mobile/  (React Native Expo · 发型试戴)
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

### 生成结果在哪里？

| 位置 | 说明 |
|------|------|
| App **「效果」** Tab | 本机 AsyncStorage 记录的试戴历史，方便对比 |
| `backend/output/{uuid}.png` | 服务端落盘的生成图 |
| `http://localhost:8000/api/comfyui/output/{filename}` | 上述文件的 HTTP 访问地址 |
| `backend/static/thumbnails/{id}.png` | 发型库 catalog 预览图（非用户试戴结果） |

### 前端

- **React Native (Expo SDK 57)** + Expo Router
- 响应式布局：手机 2 列 / 平板 3 列 / 桌面 Web 4 列；缩略图保持 **2:3**
- @tanstack/react-query；`generation.ts` → **`POST /api/comfyui/generate`**
- Session：保留上次照片，换发型可跳过重新上传
- 品牌资源：`mobile/assets/`（icon / favicon / logo）+ `mobile/public/`（Web 静态）

**页面流：** 发型库 → 上传照片 → AI 生成预览 → 换发型 / 返回 / 效果历史

**Web：** `npx expo start --web`；保存降级为下载，分享用 Web Share API 或复制链接。

### 后端

- **Python FastAPI** + uvicorn
- **ComfyUI** HTTP API（PhotoMaker v1 + SD1.5 `photon_v1`）
- MediaPipe 本地人脸检测
- 模板：`backend/data/templates_comfyui.json`
- 遗留：美图 API（`meitu.py`）、OSS（`oss.py`）

---

## 项目结构

```
hairstyle/
├── mobile/                      # Expo 前端（发型试戴）
│   ├── app/
│   │   ├── (tabs)/
│   │   │   ├── index.tsx        # 发型库
│   │   │   └── history.tsx      # 我的效果（历史对比）
│   │   ├── capture.tsx          # 上传照片
│   │   ├── preview.tsx          # 生成预览
│   │   ├── result-view.tsx      # 历史详情（不重新生成）
│   │   ├── +html.tsx            # Web title / favicon
│   │   └── _layout.tsx
│   ├── assets/                  # icon、favicon、logo、splash
│   ├── public/                  # Web 静态 favicon.ico 等
│   ├── components/
│   ├── constants/theme.ts       # 设计 token
│   ├── context/SessionContext.tsx
│   ├── hooks/useLayout.ts       # 响应式列数
│   └── services/
│       ├── generation.ts        # → /api/comfyui/generate
│       └── history.ts           # 本机试戴历史
├── backend/
│   ├── app/…                    # FastAPI + ComfyUI / 遗留 Meitu
│   ├── data/templates_comfyui.json
│   ├── workflows/               # ComfyUI 可拖入 JSON
│   ├── scripts/generate_thumbnails.py
│   ├── static/thumbnails/       # catalog 预览
│   └── output/                  # 生成结果
├── docs/
├── README.md
└── AGENTS.md
```

---

## 快速开始

### 前置条件

- Node.js 20+ / npm
- Python 3.12+
- Expo Go 或模拟器 / 浏览器
- **本机 ComfyUI**（推荐 Pinokio），`http://127.0.0.1:8188`
  - Checkpoint: `photon_v1.safetensors`
  - PhotoMaker: `photomaker-v1.bin`（**不要用 v2**）
- 详见 [`docs/ds_comfyui_setup.md`](docs/ds_comfyui_setup.md)、[`backend/workflows/README.md`](backend/workflows/README.md)

### 1. ComfyUI

```bash
curl -s http://127.0.0.1:8188/system_stats | head -c 200
```

### 2. 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/templates
```

### 3. 前端

```bash
cd mobile
npm install
npx expo start          # 扫码 / 模拟器
npx expo start --web    # 浏览器（可见品牌 favicon）
```

> API 主机由 `mobile/services/api.ts` 按平台自动探测。国内网络可试 `--tunnel`。

### 可选：重建 catalog 缩略图

```bash
cd backend
python scripts/generate_thumbnails.py
python scripts/generate_thumbnails.py --id m1 --force --seed 42
```

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `COMFYUI_URL` | 默认 `http://127.0.0.1:8188` |
| `MEITU_*` | 遗留美图路径（前端未使用） |
| `OSS_*` | 可选；当前生成默认写 `backend/output/` |
| `ALI_CLOUD_VISION_KEY` | 未使用（MediaPipe） |

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | Health |
| `GET` | `/api/templates` | 模板列表；缩略图为绝对 URL |
| `GET` | `/api/templates/{id}` | 详情 |
| `POST` | `/api/comfyui/generate` | **主路径**（`style_id` = 模板 id，如 `w1`） |
| `GET` | `/api/comfyui/output/{filename}` | 生成结果图 |
| `POST` | `/api/generate` | 遗留 Meitu |
| `POST` | `/api/regenerate` | Stub（501） |

---

## 部署

- **开发：** 本机 FastAPI + ComfyUI  
- **后端：** `docker build -t hairstyle-api ./backend && docker run -p 8000:8000 hairstyle-api`（需可达的 ComfyUI）  
- **建议：** 阿里云 ECS；GPU 跑 ComfyUI，或本机 Pinokio 调试

---

## 路线图

- **P1：** 发型参数滑条、多视角、原图对比、登录、点数
- **P2：** 会员、云端生成历史、收藏、脸型推荐、工作流升级（HairPort / ACE++）

---

## 相关文档

| 文档 | 内容 |
|------|------|
| [`AGENTS.md`](AGENTS.md) | Agent / 开发约定 |
| [`docs/ds_comfyui_setup.md`](docs/ds_comfyui_setup.md) | ComfyUI 模型与调试 |
| [`docs/ds_comfyui_proposal.md`](docs/ds_comfyui_proposal.md) | ComfyUI 方案说明 |
| [`backend/workflows/README.md`](backend/workflows/README.md) | Workflow 使用 |
| [`docs/superpowers/specs/2026-07-17-comfyui-catalog-thumbnails-design.md`](docs/superpowers/specs/2026-07-17-comfyui-catalog-thumbnails-design.md) | Catalog 缩略图设计 |

---

## License

MIT
