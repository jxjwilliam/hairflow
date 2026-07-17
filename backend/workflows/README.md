# ComfyUI Workflows — AI 发型试戴

这些 workflow JSON 文件可以直接拖入 ComfyUI Web UI (`http://127.0.0.1:8188`)，与后端 API 使用完全相同的节点结构和参数。

## 文件说明

| 文件 | 模板 | 类别 |
|------|------|------|
| `photomaker_hairstyle_base.json` | 通用基础模板 | — |
| `photomaker_hairstyle_w1_french_wave.json` | 法式大波浪 (w1) | 女 |
| `photomaker_hairstyle_w5_long_straight.json` | 黑长直 (w5) | 女 |
| `photomaker_hairstyle_m1_short.json` | 清爽短发 (m1) | 男 |
| `photomaker_hairstyle_m3_korean.json` | 韩式微分 (m3) | 男 |
| `txt2img_hairstyle_catalog.json` | Catalog thumbnails (all styles) | — |

## Catalog thumbnails (txt2img, no PhotoMaker)

Use `txt2img_hairstyle_catalog.json` to preview catalog-style portraits without uploading a face:

1. Drag the file into ComfyUI Web UI
2. Edit **② Positive prompt** (and negative if needed) using text from `data/templates_comfyui.json`
3. Queue Prompt — no LoadImage step
4. Output prefix: `catalog_thumb`

For batch generation and updating template JSON, run:

```bash
cd backend
python scripts/generate_thumbnails.py
python scripts/generate_thumbnails.py --id m1 --force
```

## 使用方法

1. 打开 ComfyUI: `http://127.0.0.1:8188`
2. 将 `.json` 文件拖入 ComfyUI 窗口（或点 Load → 选择文件）
3. 在 **LoadImage** 节点选择你的正面照片
4. 点击 **Queue Prompt** 生成
5. 结果保存在 ComfyUI 的 `output/` 目录

## 自定义发型

使用 `photomaker_hairstyle_base.json`：
1. 加载后，找到 **PhotoMakerEncode** 节点（节点 ④）
2. 修改 `text` 字段中的 prompt（保留末尾的 `img` 触发词）
3. 调整 KSampler 的 `denoise`（0.75–0.85）控制变化程度
4. Queue Prompt

## 与后端 API 的关系

后端 `POST /api/comfyui/generate` 自动构建相同的工作流，区别仅在于：
- 后端动态上传照片到 ComfyUI 而非用 LoadImage
- 后端从 `templates_comfyui.json` 读取 prompt
- 后端轮询结果并下载

在 Web UI 中测试这些 workflow 等同于手动验证后端效果。

## 所需模型

- **Checkpoint**: `photon_v1.safetensors` (SD1.5)
- **PhotoMaker**: `photomaker-v1.bin`

两个模型需事先下载到 ComfyUI 的 `models/` 对应目录。
