# ComfyUI 发型合成 — 模型与 Workflow 准备

> **状态**: v1 模型已确认可行 | v2 架构不兼容  
> **日期**: 2026-07-17

---

## 1. 环境现状

| 项目 | 状态 |
|------|------|
| ComfyUI 版本 | v0.27.1 (macOS MPS, via Pinokio) |
| 模型存储路径 | `/Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621/` |
| SD1.5 Checkpoints | `photon_v1.safetensors` ✅, `realisticVisionV60B1_v60B1VAE.safetensors` ✅ |
| SDXL Checkpoints | `juggernautXL_ragnarokBy`, `realvisxlV50` 等 (不用于当前方案) |
| PhotoMaker 节点 | ✅ 内置 (`PhotoMakerEncode`, `PhotoMakerLoader`) |
| PhotoMaker v1 模型 | ⬜ 待下载 (photomaker-v1.bin, ~470MB) |
| PhotoMaker v2 模型 | ❌ 已下载但**不兼容** (1.7GB, 存在 `qformer_perceiver` 架构差异) |

---

## 2. ⚠️ PhotoMaker v2 不可用

`photomaker-v2.bin` 包含额外的 `qformer_perceiver` 组件，ComfyUI v0.27.1 内置的 `PhotoMakerIDEncoder` 无法加载:

```
RuntimeError: Error(s) in loading state_dict for PhotoMakerIDEncoder:
Unexpected key(s) in state_dict: "qformer_perceiver.*"
```

**必须使用 `photomaker-v1.bin`** (SD1.5 架构，ComfyUI 原生支持)。

---

## 3. 唯一需要下载的模型

### photomaker-v1.bin (~470MB)

```bash
BASE="/Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621"
curl -L -o "$BASE/photomaker/photomaker-v1.bin" \
  "https://huggingface.co/TencentARC/PhotoMaker/resolve/main/photomaker-v1.bin"
```

> 你已有 SD1.5 checkpoint (`photon_v1.safetensors`, ~2GB)，无需额外下载底模。

---

## 4. PhotoMaker 工作流

### 4.1 节点连接

```
LoadImage (用户照片)
    │
CheckpointLoaderSimple (photon_v1.safetensors) ──→ MODEL, CLIP, VAE
    │
PhotoMakerLoader (photomaker-v1.bin) ──→ PHOTOMAKER
    │
PhotoMakerEncode (photomaker + image + clip + prompt text)
    │                               ↑ 含 "img" 触发词
    ├──→ CONDITIONING (positive)
    │
CLIPTextEncode (negative prompt) ──→ CONDITIONING (negative)
    │
EmptyLatentImage (512×768) ──→ LATENT
    │
KSampler (model, positive, negative, latent) ──→ LATENT
    │  steps=25, cfg=6.5, denoise=0.85
    │
VAEDecode ──→ IMAGE
    │
SaveImage ──→ output/
```

### 4.2 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| checkpoint | `photon_v1.safetensors` | SD1.5 写实底模 |
| photomaker_model | `photomaker-v1.bin` | v1 架构 |
| width × height | 512 × 768 | SD1.5 标准尺寸 |
| steps | 25 | 推理步数 |
| cfg | 6.5 | 引导强度 |
| denoise | 0.8–0.85 | 发型变化程度 |
| trigger word | `img` | 代码自动追加到 prompt 末尾 |

### 4.3 调试

| 现象 | 调整 |
|------|------|
| 人脸不像原图 | 降低 `denoise` 到 0.7–0.75 |
| 发型没变化 | 提高 `denoise` 到 0.9，检查 prompt 是否具体 |
| 画面模糊 | 增加 `steps` 到 30，或换 `realisticVisionV60B1` |
| 生成太慢 | MPS 下 SD1.5 约 30–60s/张，正常 |

---

## 5. 测试命令

```bash
cd backend
python3 scripts/test_comfyui.py
```

或指定真实照片:

```bash
python3 scripts/test_comfyui.py --photo ~/Desktop/my_face.jpg --style w1
```

---

## 6. 后端 API

```
POST /api/comfyui/generate
{"photo_base64": "...", "style_id": "w1"}
→ {"image_url": "...", "image_id": "..."}
```

`/api/generate` (Meitu) 保持不变。
