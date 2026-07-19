# FLUX 管线集成（含 FLUX.2 Klein 原生编辑工作流）

> **状态**：已实现，已验证（2026-07-17），2026-07-18 同步更新  
> **范围**：`flux_klein`（FLUX.2 Klein 4B）GGUF 管线，仅 img2img 可用；FLUX.1 Schnell 已从前端选项移除。  
> **原因**：开发环境为 macOS CPU-only（2.2GB 可用 RAM），FLUX.1 Schnell（12GB GGUF）无法加载，`flux_klein` txt2img（8GB qwen CLIP）OOM。

本文档描述**现行**实现。早期方案（`generate-v2` 端点 + HairstyleParams 滑条）已被下文的分发式架构取代。

## 架构

`ComfyUIService.generate(pipeline, method, ...)`（`backend/app/services/comfyui.py`）按 `pipeline` + `method` 分发到对应 workflow builder：

| pipeline | method | builder | 说明 |
|----------|--------|---------|------|
| `photomaker` | `photomaker` | `_build_photomaker_workflow` | SD1.5 + PhotoMaker v1 人脸嵌入（默认，保脸） |
| `sd15` | `txt2img` / `img2img` | `_build_sd15_*_workflow` | RealisticVision；img2img 已加 ImageScale 防高分辨率耗时 |
| `flux_klein` | `img2img` | **`_build_flux_klein_edit_workflow`** | **官方原生编辑工作流（保脸）** — 前端的唯一入口 |

> `flux_klein` txt2img 沿用 DualCLIP(clip_l+qwen, type=flux) 布局，但加载 8GB qwen_3_4b 在 CPU 环境 OOM，已从 options 隐藏。FLUX.1 Schnell 因 12GB 模型无法加载，完全移除。

模型文件名由 `_flux_unet_for / _flux_clip_for / _flux_vae_for(pipeline)` 决定：

| pipeline | UNET (GGUF) | 文本编码器 | VAE |
|----------|-------------|-----------|-----|
| `flux_klein` | `flux-2-klein-4b-Q8_0.gguf` | `qwen_3_4b.safetensors`（CLIPLoader, type=flux2） | `flux2-vae.safetensors` |

## flux_klein img2img = 原生编辑工作流（保脸关键）

通用 img2img（VAEEncode → KSampler 高 denoise 重采样）会把大部分画面重新生成，**自拍者脸部特征丢失**（"模特脸"）。FLUX.2 Klein 是指令编辑模型，现行实现采用 ComfyUI 官方模板 **"Image Edit (Flux.2 Klein 4B Distilled)"**（Comfy-Org/workflow_templates）：

```
LoadImage(自拍)
  → ImageScaleToTotalPixels(nearest-exact, 1.0MP, resolution_steps=1)
  → VAEEncode → ReferenceLatent(注入正条件) + ReferenceLatent(注入负条件)
CLIPLoader(qwen_3_4b.safetensors, type="flux2")
  → CLIPTextEncode(编辑指令) → 正条件；ConditioningZeroOut → 负条件
UnetLoaderGGUF(flux-2-klein-4b-Q8_0.gguf)
GetImageSize → EmptyFlux2LatentImage(与输入同尺寸) + Flux2Scheduler(steps, w, h)
CFGGuider(cfg=1.0) + KSamplerSelect(euler) + RandomNoise(seed)
  → SamplerCustomAdvanced → VAEDecode → SaveImage
```

要点：

- **ReferenceLatent** 把自拍作为参考条件注入（正/负条件都注入），模型按指令做局部编辑而非整体重采样 → 保留脸部特征，只换发型。
- 提示词在 `generate()` 内自动包装为编辑指令：
  `Give the person in the image this hairstyle: {template_prompt}. Keep the person's face, facial features, expression, skin tone, head pose, background, clothing and lighting exactly the same. Only change the hair.`
- 蒸馏模型：`cfg=1.0`、`euler`、`Flux2Scheduler`；**steps 建议 4**（前端选 FLUX 时步数默认已修正为 4；过多步数会"烤糊"）。
- `denoise` 参数在该路径不参与（编辑由参考条件驱动）。
- `ImageScaleToTotalPixels` 需要 `resolution_steps` 入参（ComfyUI 0.27 新增，缺省会 400）。

## 防御性行为

- **checkpoint 覆盖守卫**：模板 JSON 的 `checkpoint` 是 SD1.5（`photon_v1.safetensors`）。flux 管线只接受 `.gguf` 结尾的覆盖值，否则忽略并回退到管线默认 UNET（避免 SD1.5 checkpoint 被当作 UNET 提交导致 400）。
- **400 错误透传**：`_submit_workflow` 不再裸 `raise_for_status()`；ComfyUI 的 `node_errors` 详情会写日志并包含在 502 响应中（例如 `clip_name2: 'qwen_3_4b.safetensors' not in [...]`），缺什么模型一目了然。

## 模型文件（用户环境，Pinokio @ /Volumes/SamsungT7）

| 文件 | 大小 | 位置（ComfyUI 应用 models/ 下） |
|------|------|------|
| `flux-2-klein-4b-Q8_0.gguf` | ~4.5 GB | `unet/`（GGUF 节点扫描） |
| `qwen_3_4b.safetensors` | ~8 GB | `text_encoders/` |
| `flux2-vae.safetensors` | ~320 MB | `vae/` |
| `flux1-schnell-Q8_0.gguf` / `clip_l.safetensors` / `t5xxl_fp16.safetensors` / `ae.safetensors` | — | flux (schnell) 路径所需 |

> ⚠️ **Pinokio 共享盘坑**：模型若下载到 Pinokio 共享盘（`drive/drives/peers/<id>/text_encoders/`），ComfyUI 默认扫不到——`extra_model_paths.yaml` 的 `pinokio_drive` 段只映射了 `clip:` 未映射 `text_encoders:`。最稳妥：把文件放进 ComfyUI 应用自己的 `models/text_encoders/`（无需重启即可被扫描）。

## 前端

- `mobile/app/options.tsx`：模型选择（PhotoMaker v1 / Realistic Vision / FLUX.2 Klein 4B）+ 方式（保持人脸/文本生成/图生图）+ 变化程度 + 步数（flux_klein 默认 15，范围 2–30；flux 管线和 txt2img 方法对 flux_klein 已隐藏因 CPU OOM）。
- `mobile/services/generation.ts`：`generateHairstyle(photo, styleId, options)` → `POST /api/comfyui/generate`，携带 `pipeline`/`method`/`denoise`/`steps`/`cfg`。
- 每次生成的参数随效果图存入本机历史（`services/history.ts` 的 `HistoryItem.options`），详情页（`result-view.tsx`）展示参数卡片。

## 测试

`backend/tests/test_comfyui_bugfixes.py`（7 项全绿）覆盖：

- RGBA PNG 上传导致 `crop_face` JPEG 失败（`cannot write mode RGBA as JPEG`）
- 400 校验错误透传（node_errors 详情进入 ComfyUIError）
- flux_klein 使用 `flux2-vae.safetensors`；flux (schnell) 保持 `ae.safetensors`
- SD1.5 checkpoint 不泄漏进 flux 管线；`.gguf` 覆盖仍生效
- flux_klein img2img 原生编辑布局（CLIPLoader flux2 / 双 ReferenceLatent / CFGGuider 1.0 / euler / Flux2Scheduler / 指令式提示词）

另对本机 ComfyUI 做过端到端实测：flux_klein img2img 全链路生成成功（M3 Pro CPU-only **约 157-163s/张**；M3 Pro GPU 约 131s/张）。

## 已知边界 / 后续

- `flux_klein` txt2img — 加载 8GB qwen_3_4b 在 CPU 环境 OOM（Pinokio 以 CPU-only 模式运行 ComfyUI），已从前端隐藏。有 GPU 时可恢复。
- `flux` (schnell) — 12GB GGUF 模型在 CPU 环境完全无法加载，已从前端移除。有 GPU 时可恢复。
- 多角度（generate-multi）逐角度串行调用，flux_klein 下 4 张约 10–11 分钟。
