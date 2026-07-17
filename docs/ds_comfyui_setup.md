# ComfyUI 发型合成 — 模型与 Workflow 准备

> **目标**: 手动下载所需模型，在 ComfyUI Web UI 中验证换发效果，然后对接到后端 API。

---

## 1. 你的环境现状

| 项目 | 状态 |
|------|------|
| ComfyUI 版本 | v0.27.1 (macOS MPS, via Pinokio) |
| 模型存储路径 | `/Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621/` |
| 已有 Checkpoints | `juggernautXL_ragnarokBy`, `realvisxlV50_v50LightningBakedvae`, `xxmix9realisticsdxl_v10`, `illustriousXL_v01` 等 (全部 SDXL) |
| PhotoMaker 节点 | ✅ 已内置（`PhotoMakerEncode`, `PhotoMakerLoader`） |
| PhotoMaker 模型 | ❌ 未下载 |
| LoRA | ❌ 无 |
| ControlNet | ❌ 无 |

---

## 2. 方案选择：PhotoMaker（推荐）

**PhotoMaker**（腾讯 ARC 实验室）是专门为人脸身份保持 + 风格变换设计的模型。输入一张人脸照片 + 文字 prompt，输出同一人物的不同风格图片——包括换发型。

### 为什么不用 IP-Adapter / Reactor / InstantID？
你的 ComfyUI 当前没有这些 custom node。PhotoMaker 是 ComfyUI 内置节点，无需额外安装。

### PhotoMaker 工作流原理

```
用户照片 ──→ PhotoMakerEncode (编码人脸身份)
                  │
SDXL Checkpoint ──┤
                  │
正面 Prompt ──────┤ ──→ KSampler ──→ VAEDecode ──→ 结果图
负面 Prompt ──────┘    "一个留着法式大波浪的女生"
```

PhotoMaker 保证人脸像你，Prompt 控制发型样式。

---

## 3. 需要下载的模型

### 3.1 必选：PhotoMaker 模型文件

**下载到**: `photomaker/` 目录（即 `/Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621/photomaker/`）

```
# 方式一：直接下载（推荐）
cd /Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621/photomaker/
rm -f put_photomaker_models_here  # 删除占位文件

# PhotoMaker v2
BASE="/Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621"
curl -L -o "$BASE/photomaker/photomaker-v2.bin" \
  "https://huggingface.co/TencentARC/PhotoMaker-V2/resolve/main/photomaker-v2.bin"
```

> **注意**: PhotoMaker v1 是为 SD1.5 设计的。你的 checkpoints 全是 SDXL。有两种方案：
> - **方案 A**（推荐）: 额外下载一个 SD1.5 写实底模 + PhotoMaker v1 → 效果最稳定
> - **方案 B**: 尝试 PhotoMaker v1 配合 SDXL checkpoints（新版本 ComfyUI 可能支持，但不保证）

### 3.2 方案 A：下载 SD1.5 Checkpoint（推荐）

**下载到**: `checkpoints/` 目录

```
cd /Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621/checkpoints/

# realisticVision V6.0 (最流行的写实人像 SD1.5 底模, ~2GB)
curl -L -o realisticVisionV60B1_v60B1VAE.safetensors \
  "https://civitai.com/api/download/models/294706?type=Model&format=SafeTensor"
```

> Civitai 需要 API key。更简单的方式是用 HuggingFace 上的替代品：
> ```
> curl -L -o photon_v1.safetensors \
>   "https://huggingface.co/andite/photon/resolve/main/photon_v1.safetensors"
> ```

### 3.3 可选：SD1.5 VAE（如果 checkpoint 不带 VAE）

`realisticVisionV60B1` 自带 VAE，一般不需要单独下载。如果遇到画面发灰，下载：

```
cd /Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621/vae/
curl -L -o vae-ft-mse-840000-ema-pruned.safetensors \
  "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors"
```

### 3.4 可选：发型 LoRA（提升特定发型效果）

从 Civitai 搜索以下关键词，下载 `.safetensors` LoRA 文件到 `loras/`：

| LoRA 关键词 | 用途 |
|-------------|------|
| `hair style` | 通用发型风格 |
| `long wavy hair` | 长发波浪 |
| `short bob hair` | 波波头短发 |
| `curly hair` | 卷发 |
| `Korean hairstyle` | 韩式发型 |

> 对于 MVP，**LoRA 不是必需的**——PhotoMaker + 好的 prompt 就能改变发型。

---

## 4. 验证 PhotoMaker 工作流

### 4.1 在 ComfyUI Web UI 中手动搭建

打开 `http://127.0.0.1:8188`，按以下步骤搭建：

1. **LoadImage** — 选一张你的正面照
2. **CheckpointLoaderSimple** — 选 `photon_v1.safetensors`（或已下载的 SD1.5 底模）
3. **PhotoMakerLoader** — 选 `photomaker-v1.bin`
4. **PhotoMakerEncode** — 连接：photomaker、image、clip、text
   - text: `photograph of a person with [目标发型描述]`
5. **CLIPTextEncode (Positive)** — `beautiful woman with long wavy hair, french wave hairstyle, professional photography, portrait, detailed hair`
6. **CLIPTextEncode (Negative)** — `ugly, deformed, bad anatomy, blurry, low quality, disfigured`
7. **KSampler** — seed=42, steps=25, cfg=6.5, sampler=euler_ancestral, scheduler=normal, denoise=0.85
   - model → checkpoint
   - positive → PhotoMakerEncode output
   - negative → CLIPTextEncode neg output
   - latent_image → EmptyLatentImage 512×768
8. **VAEDecode** — 连接 KSampler → VAE → SaveImage
9. **SaveImage** — filename_prefix=`hairstyle_test`

### 4.2 预期结果

- 人物面部特征与输入照片一致
- 发型按照 prompt 描述变化
- 皮肤质感写实
- 单张生成时间：30-60 秒（MPS）

### 4.3 调试参数

| 参数 | 默认值 | 效果 |
|------|--------|------|
| `denoise` | 0.85 | 越高变化越大，越低越像原图 |
| `steps` | 25 | 25-30 质量足够 |
| `cfg` | 6.5 | 5-7 之间调整 |
| `style_strength` (PhotoMaker) | 可调整 | 控制风格变化程度 |

---

## 5. 一键下载脚本（macOS）

把以下内容保存为 `download_models.sh`，`chmod +x` 后执行：

```bash
#!/bin/bash
BASE="/Volumes/SamsungT7/pinokio/drive/drives/peers/d1779062027621"

# 1. PhotoMaker model
echo "=== Downloading PhotoMaker model ==="
rm -f "$BASE/photomaker/put_photomaker_models_here"
curl -L -o "$BASE/photomaker/photomaker-v1.bin" \
  "https://huggingface.co/TencentARC/PhotoMaker/resolve/main/photomaker-v1.bin"

# 2. SD1.5 checkpoint (选择 photoin 或 realisticVision)
echo "=== Downloading SD1.5 checkpoint ==="
curl -L -o "$BASE/checkpoints/photon_v1.safetensors" \
  "https://huggingface.co/andite/photon/resolve/main/photon_v1.safetensors"

echo "=== Done! Restart ComfyUI to load new models ==="
```

---

## 6. 后续：对接后端 API

模型就绪并手动验证通过后，后端会通过以下 API 调用 ComfyUI：

```
POST /api/comfyui/generate
{
  "photo_base64": "...",
  "template_id": "w1"
}
```

后端会自动：
1. 上传你的照片到 ComfyUI
2. 构建 PhotoMaker workflow JSON
3. 提交任务，轮询等待结果
4. 下载生成的图片，上传 OSS，返回 URL

**前端和现有 `/api/generate` 完全不受影响。**

---

*下载完成后，在 ComfyUI 中手动测试一次 PhotoMaker 工作流，确认能跑通后告诉我，我开始写后端代码。*
