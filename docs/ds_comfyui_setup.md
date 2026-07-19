# ComfyUI 发型合成 — 模型与 Workflow 准备

> **状态**: v1 模型已确认可行 | v2 架构不兼容  
> **日期**: 2026-07-17 (2026-07-18 补充 CPU 约束说明)  
> **开发环境**：macOS CPU-only (2.2GB 可用 RAM) — FLUX.1 Schnell (12GB GGUF) 无法加载，FLUX.2 Klein txt2img (8GB CLIP) OOM。前端 options 已移除不可用选项。

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

## 6. 后端 API（主路径）

App 前端（`mobile/services/generation.ts`）只调用 ComfyUI 路径：

```
POST /api/comfyui/generate
{"photo_base64": "...", "style_id": "w1"}   # style_id = 模板 id（m1/w1…），不是 meitu_style_*
→ {"image_url": "http://…/api/comfyui/output/{uuid}.png", "image_id": "..."}
```

模板列表来自 `data/templates_comfyui.json`，缩略图经 `/static/thumbnails/` 提供。

遗留：`POST /api/generate`（Meitu）仍在代码中，**前端未接入**。美图 Key 无 `portrait_edit` 权限时不可用。

Catalog 缩略图批生成（txt2img，无 PhotoMaker）：

```bash
python3 scripts/generate_thumbnails.py
python3 scripts/generate_thumbnails.py --id m1 --force --seed 42
```

Workflow 说明见 `backend/static/workflows/README.md`。

---

## 7. FLUX 管线（可选，2026-07-17 新增）

除 PhotoMaker 外，后端还支持 3 条 GGUF 管线（前端「生成选项」可选）：

| pipeline | 模型文件（ComfyUI `models/` 下） | 说明 |
|----------|------|------|
| `sd15` | `realisticVisionV60B1_v60B1VAE.safetensors`（checkpoints） | SD1.5 真实风格 |
| `flux` | `flux1-schnell-Q8_0.gguf`（unet）+ `clip_l.safetensors` + `t5xxl_fp16.safetensors`（clip）+ `ae.safetensors`（vae） | FLUX.1 Schnell（最快，但 12GB 模型 CPU 环境无法加载，已从前端隐藏） |
| `flux_klein` | `flux-2-klein-4b-Q8_0.gguf`（unet）+ `qwen_3_4b.safetensors`（text_encoders）+ `flux2-vae.safetensors`（vae） | FLUX.2 Klein 4B，细节最好 |

**前置**：GGUF 加载需要 [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) 自定义节点（`UnetLoaderGGUF` / `DualCLIPLoaderGGUF`）。

**flux_klein 要点**：

- img2img 走**官方原生编辑工作流**（ReferenceLatent 注入自拍参考），保留自拍者脸部特征，只换发型；详见 `docs/oc_flux2_klein_integration.md`。
- 蒸馏模型：`cfg=1.0`、`euler`、**steps=4**（前端已默认）；步数过多会"烤糊"。
- 文本编码器是 `qwen_3_4b.safetensors`（~8GB），**不是** clip_l/t5xxl；VAE 是 `flux2-vae.safetensors`，**不能**用 FLUX.1 的 `ae.safetensors`。

> ⚠️ **Pinokio 共享盘坑**：模型下载到 Pinokio 共享盘（`drive/drives/peers/<id>/text_encoders/`）时 ComfyUI 扫不到——`extra_model_paths.yaml` 的 `pinokio_drive` 段只映射 `clip:` 未映射 `text_encoders:`。把文件放进 ComfyUI 应用自己的 `models/text_encoders/` 即可（无需重启即被扫描）。

**排错**：后端会把 ComfyUI 的 400 校验详情透传到 502 响应（如 `clip_name2: 'qwen_3_4b.safetensors' not in [...]`），按提示补齐模型文件即可。