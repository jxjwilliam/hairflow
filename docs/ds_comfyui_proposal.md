# AI 发型试戴 — 本地 AI 管线替代方案

> **版本**: v1.0  
> **日期**: 2026-07-17  
> **状态**: Proposal  
> **背景**: Meitu API 需要付费订阅（¥6700+/年），免费 Key 无法调用 `portrait_edit`。  
> **前提**: 你已有 LLM tokens（DeepSeek 等）、本地 ComfyUI（Pinokio）、本地 Ollama。

---

## 1. 当前实现分析

### 1.1 现有架构

```
Mobile (React Native)
    │  POST /api/generate  {photo_base64, style_id}
    ▼
FastAPI Backend
    │  ① detect_hair()    → Meitu hairclassifier    → 人脸检测
    │  ② segment_hair()   → Meitu hair_segment      → 头发遮罩
    │  ③ generate_hair()  → Meitu portrait_edit     → AI 合成
    │  ④ upload           → Alibaba OSS              → 存储
    ▼
Result URL → Mobile
```

### 1.2 阻塞点

| 接口 | 状态 | 错误 |
|------|------|------|
| `hairclassifier` | 部分可用 | `Empty media_data`（免费 Key 权限受限） |
| `hair_segment` | 不可用 | 连接异常 |
| `portrait_edit` | **致命** | `[90002] GATEWAY_AUTHORIZED_ERROR`（需付费） |

付费路径：美图开放平台要求企业认证 + 按量计费最低充值 ¥8000 余额。你在海外，调试时 IP 也会被拦截。

### 1.3 受影响的代码

- `backend/app/services/meitu.py` — 整个 MeituService（约 180 行）
- `backend/app/routers/generation.py` — 依赖 meitu_service 的三个步骤
- `backend/app/services/face.py` — 目前是 stub
- `backend/data/templates.json` — `style_id` 字段指向 Meitu 内部 ID
- `mobile/services/api.ts` — 前端调用不变（接口契约可保持）

---

## 2. 新方案：ComfyUI 本地 AI 管线

### 2.1 核心思路

用 **ComfyUI Workflow API** 完全替代 Meitu 的三个接口。ComfyUI 已经通过 Pinokio 在你的机器上运行，通过 HTTP REST API（默认 `http://127.0.0.1:8188`）接收任务、返回图片。

```
Mobile (React Native)       ← 不变
    │
    ▼
FastAPI Backend
    │  ① detect_face()     → mediapipe (Python)       → 人脸检测 + 头发遮罩
    │  ② generate_hair()   → ComfyUI workflow API     → AI 合成
    │  ③ upload            → Alibaba OSS              → 存储（不变）
    ▼
Result URL → Mobile
```

### 2.2 为什么可行

| 组件 | Meitu（旧） | ComfyUI（新） | 优势 |
|------|------------|---------------|------|
| 人脸检测 | hairclassifier API | mediapipe (本地) | 零延迟、免费、离线 |
| 头发分割 | hair_segment API | mediapipe / rembg | 免费、可调优 |
| AI 合成 | portrait_edit API | ComfyUI workflow | 免费、完全可控 |
| 模板风格 | Meitu style_id | LoRA + reference image | 无限扩展、自行训练 |

### 2.3 你需要启动的服务

| 服务 | 地址 | 用途 |
|------|------|------|
| **ComfyUI** (via Pinokio) | `http://127.0.0.1:8188` | 发型合成核心引擎 |
| **FastAPI** | `http://127.0.0.1:8000` | 业务后端（不变） |
| **Ollama** (可选) | `http://127.0.0.1:11434` | 自然语言模板搜索、prompt 优化 |

Ollama 不参与图像生成管线，但可以用于：
- 根据用户描述推荐发型模板（"适合圆脸的短发"）
- 自动生成 ComfyUI 的 positive/negative prompt
- 模板标签自动分类

---

## 3. ComfyUI 发型合成工作流设计

### 3.1 工作流原理

ComfyUI 的核心是一个 JSON 格式的工作流（workflow），定义节点和连线。发型合成的本质是 **图像到图像的风格迁移 + 局部重绘（inpainting）**。

流程如下：

```
Load User Photo ──→ Face Detection (mediapipe) ──→ Generate Hair Mask
                                                         │
Load Hairstyle Reference Image ──→ CLIP Encode ──────────┤
                                                         │
                              ┌──────────────────────────┤
                              │   IP-Adapter (Face ID)   │
                              │   + ControlNet (Edge)    │
                              │   + Inpaint (Hair Area)  │
                              └──────────────────────────┤
                                                         ▼
                                              Generated Image
```

### 3.2 需要的模型（推荐）

这些模型需要下载到 ComfyUI 的 `models/` 目录：

```
comfyui/
├── models/
│   ├── checkpoints/
│   │   └── realisticVisionV60B1_v60B1VAE.safetensors   # 写实人像底模
│   ├── controlnet/
│   │   └── control_v11p_sd15_canny.pth                  # ControlNet Canny 边缘
│   ├── ipadapter/
│   │   └── ip-adapter-plus-face_sd15.safetensors        # IP-Adapter 人脸保持
│   ├── loras/
│   │   ├── hair_short.safetensors                       # 短发 LoRA
│   │   ├── hair_long_wave.safetensors                   # 长发波浪 LoRA
│   │   └── ...（按模板数量扩展）
│   └── ...
```

### 3.3 工作流 JSON（核心）

下面是一个简化的 node 结构（完整 JSON 由代码动态生成）：

```
Node 1: LoadImage (user photo)       → output: IMAGE
Node 2: LoadImage (hair reference)   → output: IMAGE
Node 3: CLIPTextEncode (positive)    → output: CONDITIONING
Node 4: CLIPTextEncode (negative)    → output: CONDITIONING
Node 5: ControlNetApply (canny)      → input: IMAGE(from 1) → output: CONDITIONING
Node 6: IPAdapterApplyFaceID         → input: IMAGE(from 1) → output: MODEL
Node 7: VAEDecode                    → ... 
Node 8: KSampler                     → latent → VAE → SaveImage
```

### 3.4 Python 调用 ComfyUI 的方式

```python
import httpx
import uuid
import json

COMFYUI_URL = "http://127.0.0.1:8188"

async def call_comfyui(workflow: dict) -> bytes:
    """Submit a ComfyUI workflow and return the result image bytes."""
    client_id = str(uuid.uuid4())
    
    # 1. Submit workflow
    async with httpx.AsyncClient(timeout=120) as client:
        payload = {"prompt": workflow, "client_id": client_id}
        resp = await client.post(f"{COMFYUI_URL}/prompt", json=payload)
        prompt_id = resp.json()["prompt_id"]
    
    # 2. Poll for result via WebSocket or GET /history
    #    (ComfyUI writes results to output/ dir, poll /history/{prompt_id})
    #    ...
    
    # 3. Download result image
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{COMFYUI_URL}/view", params={"filename": result_filename}
        )
        return resp.content
```

---

## 4. 后端代码变更计划

### 4.1 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/services/comfyui.py` | ComfyUI HTTP 客户端，替代 `meitu.py` |
| `backend/app/services/face_detector.py` | mediapipe 人脸检测 + 头发遮罩 |
| `backend/data/comfyui_workflow.json` | 基础工作流模板 |

### 4.2 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/services/face.py` | 从 stub 升级为真实 mediapipe 实现 |
| `backend/app/routers/generation.py` | 替换 meitu 调用为 comfyui 调用 |
| `backend/app/config.py` | 添加 `COMFYUI_URL` 配置项 |
| `backend/data/templates.json` | `style_id` 替换为 `lora_name` + `reference_image` + `prompt` |
| `backend/requirements.txt` | 添加 `mediapipe`, `opencv-python-headless`, `rembg` |
| `backend/.env.example` | 添加 ComfyUI 相关环境变量 |

### 4.3 可删除/弃用

| 文件 | 原因 |
|------|------|
| `backend/app/services/meitu.py` | 完全不再使用（保留为参考或删除） |

### 4.4 模板数据结构变更

```json
{
  "id": "w1",
  "name": "法式大波浪",
  "category": "women",
  "tags": ["长发", "卷发", "优雅"],
  "lora_name": "hair_long_wave.safetensors",
  "reference_image": "templates/w1_reference.jpg",
  "positive_prompt": "beautiful woman with long wavy hair, french wave hairstyle, soft curls, elegant, professional photography",
  "negative_prompt": "ugly, deformed, bad anatomy, blurry, low quality, short hair, straight hair",
  "thumbnail": "https://placehold.co/200x260/EEE/333?text=Wave",
  "description": "浪漫法式大波浪"
}
```

### 4.5 新版 `generation.py` 伪代码

```python
@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    # 1. 加载模板
    template = _load_template(req.style_id)
    
    # 2. 人脸检测 + 头发遮罩（mediapipe，本地毫秒级）
    face_info = face_service.detect_and_segment(req.photo_base64)
    if not face_info["face_detected"]:
        raise HTTPException(400, "No face detected")
    
    # 3. 构建 ComfyUI 工作流
    workflow = comfyui_service.build_workflow(
        user_photo=req.photo_base64,
        template=template,
        hair_mask=face_info["hair_mask"],
    )
    
    # 4. 提交到 ComfyUI 并等待结果
    image_bytes = await comfyui_service.submit_and_wait(workflow)
    
    # 5. 上传 OSS（不变）
    url, image_id = oss_service.upload_image(image_bytes)
    
    return GenerateResponse(image_url=url, image_id=image_id)
```

---

## 5. 前端变更

### 5.1 不变的部分

- API 接口路径不变（`POST /api/generate`、`GET /api/templates`）
- 请求和响应 schema 不变（`GenerateRequest`、`GenerateResponse`）
- 相机、相册、图片选择逻辑不变
- 结果展示页不变

### 5.2 可能的小调整

- 生成等待时间可能不同（本地 ComfyUI 比远程 API 可预测性更高）
- 后续可添加实时进度条（ComfyUI 有 WebSocket 进度推送）

---

## 6. 实施计划

### Phase 1: 环境准备（0.5-1 天）

| # | 任务 | 产出 |
|---|------|------|
| 1.1 | 确认 ComfyUI 运行正常（访问 `http://127.0.0.1:8188`） | ComfyUI 就绪 |
| 1.2 | 下载必需模型：写实底模、ControlNet Canny、IP-Adapter Face | 模型就绪 |
| 1.3 | 在 ComfyUI 中手动测试一次 "换发" 工作流 | 手动验证通过 |
| 1.4 | 安装 Python 依赖：`mediapipe`, `opencv-python-headless` | 依赖就绪 |

### Phase 2: 后端改造（1-2 天）

| # | 任务 | 产出 |
|---|------|------|
| 2.1 | 实现 `FaceService.detect_and_segment()`（mediapipe） | 人脸检测可用 |
| 2.2 | 实现 `ComfyUIService`（submit + poll + download） | ComfyUI 客户端 |
| 2.3 | 修改 `generation.py` 替换 Meitu → ComfyUI | generate 接口可用 |
| 2.4 | 更新 `templates.json`（添加 lora_name, prompt 等） | 模板数据就绪 |
| 2.5 | 更新 `config.py` + `.env` | 配置就绪 |
| 2.6 | 端到端测试：上传照片 → 合成 → 返回图片 URL | 全链路通 |

### Phase 3: 调优与扩展（1-3 天）

| # | 任务 | 产出 |
|---|------|------|
| 3.1 | 为每种发型模板准备 LoRA 或调整 prompt | 15 款模板可用 |
| 3.2 | 优化工作流参数（denoise strength、CFG scale 等） | 效果达标 |
| 3.3 | 添加 Ollama 集成（可选：智能模板推荐） | 搜索增强 |
| 3.4 | 性能测试：单张生成耗时 | < 30s（本地 GPU） |

---

## 7. ComfyUI 工作流示例 JSON

这是一个简化版的 ComfyUI workflow（实际使用时代码会动态填充变量）：

```json
{
  "3": {
    "inputs": {
      "seed": 42,
      "steps": 20,
      "cfg": 7.5,
      "sampler_name": "euler_ancestral",
      "scheduler": "normal",
      "denoise": 0.75,
      "model": ["4", 0],
      "positive": ["6", 0],
      "negative": ["7", 0],
      "latent_image": ["5", 0]
    },
    "class_type": "KSampler"
  },
  "4": {
    "inputs": {
      "ckpt_name": "realisticVisionV60B1_v60B1VAE.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 768,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  },
  "6": {
    "inputs": {
      "text": "beautiful woman with long wavy hair, french wave hairstyle, professional photo",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": {
      "text": "ugly, deformed, bad anatomy, blurry, low quality",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "8": {
    "inputs": {
      "samples": ["3", 0],
      "vae": ["4", 2]
    },
    "class_type": "VAEDecode"
  },
  "9": {
    "inputs": {
      "filename_prefix": "hairstyle_result",
      "images": ["8", 0]
    },
    "class_type": "SaveImage"
  }
}
```

> **注意**: 上面是最简文本生图示例。实际的发型转移 workflow 需要加入 LoadImage、IPAdapter、ControlNet、Inpaint 等节点。完整的 workflow 我会在 Phase 1 通过 ComfyUI 手动搭建后导出为 JSON，然后代码动态注入用户照片和模板参数。

---

## 8. 生产部署路线（后续）

### 8.1 本地开发阶段（现在）
```
MacBook Pro (M1/M2/M3 or NVIDIA GPU)
├── Pinokio → ComfyUI :8188
├── FastAPI :8000
└── Mobile Expo
```
- 适合 MVP 开发和测试
- 不需要任何外部 AI API
- 零 API 成本

### 8.2 云部署阶段（MVP 验证后）
```
阿里云 GPU ECS (ecs.gn7i, NVIDIA T4/A10)
├── ComfyUI (Docker 化)
├── FastAPI 应用
└── OSS + CDN
```
- 按需使用 GPU，中国国内用户低延迟访问
- 可选用揽睿星舟、AutoDL 等 GPU 云服务降低成本

---

## 9. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| ComfyUI 发型转移效果不如专用 API | 中 | 高 | 先用 IP-Adapter + ControlNet 方案；若不满意可尝试 Fooocus Inpaint、InstantID、PhotoMaker 等替代 workflow |
| 本地 GPU 性能不足（如果非 NVIDIA） | 低 | 中 | Mac M 系列可用 MPS 后端；CPU 模式较慢但可用；或使用云端 GPU API（如 Replicate） |
| 发型 LoRA 资源少 | 中 | 中 | 可自行训练（10-20 张照片即可训练 LoRA）；使用通用 prompt 描述发型的 text-to-image 方案 |
| ComfyUI workflow 调试复杂 | 中 | 低 | 先在 ComfyUI Web UI 中手动搭好并验证，再导出 JSON 给代码使用 |

---

## 10. 成本对比

| 方案 | 月度成本 | 单次生成成本 | 启动成本 |
|------|----------|-------------|----------|
| **Meitu API**（旧） | ~¥5,000（按 10,000 次） | ~¥0.50 | ¥8,000 充值 |
| **ComfyUI 本地**（新） | ¥0（已有硬件） | ¥0 | ¥0（已有硬件） |
| **ComfyUI 云 GPU** | ~¥600（共享 T4，按需） | ~¥0.02 | ¥0 |

---

## 11. 下一步行动

1. **立即**：确认 ComfyUI (Pinokio) 当前运行状态，检查可用模型
2. **立即**：在 ComfyUI Web UI 中手动搭建一次 "换发" workflow，验证可行性
3. **Phase 1 启动**：安装 mediapipe，实现 `FaceService`
4. **Phase 2 启动**：实现 `ComfyUIService`，对接 generate 接口
5. **测试**：用真实照片生成第一张结果

---

*本文档为技术方案提案，随实施推进持续更新。*
