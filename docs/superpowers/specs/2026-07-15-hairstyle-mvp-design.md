# AI 虚拟发型试戴 App — MVP 设计文档

> 2026-07-15
> 个人开发者业余项目，验证 AI 发型生成核心价值

## 1. 产品定位

面向国内理发行业的 AI 虚拟发型试戴工具，手机端（平板适配后续）。用户上传人像即可合成不同发型效果预览，辅助理发决策。

## 2. MVP 范围

### P0（核心必需，先做）
1. 首页发型模板浏览（网格列表 + 分类 Tab）
2. 拍照/相册上传头像
3. AI 生成发型效果图
4. 预览展示效果图
5. 保存到相册 / 分享
6. 加载状态 & 错误提示

### P1（重要但延后）
1. 发型参数调整（长度、颜色、卷曲度、刘海）
2. 多视角切换预览
3. 对比图生成（原图 vs 效果）
4. 用户登录（手机号/微信/支付宝）
5. 点数消费 + 支付

### P2（MVP 后迭代）
1. 会员订阅体系
2. 生成历史记录
3. 发型模板收藏
4. 脸型适配推荐

## 3. 技术架构

```
mobile/  (React Native Expo)  ──HTTP──▶  backend/  (Python FastAPI)  ──▶  美图API
                                              │
                                              ▼
                                         阿里云 OSS (图片存储)
```

### 前端 — React Native (Expo)

**技术栈：**
- Expo SDK 52+
- Expo Router（文件路由）
- TypeScript
- expo-image（高性能图片加载）
- expo-image-picker（拍照/相册）
- expo-media-library（保存相册）
- expo-sharing（分享）
- @tanstack/react-query（API 请求 + 缓存）
- axios（HTTP 客户端）

**页面路由：**
```
mobile/app/
├── (tabs)/
│   ├── _layout.tsx       # Tab 导航
│   └── index.tsx         # 首页 - 模板浏览
├── capture.tsx           # 拍照/选照片
├── pick-template.tsx     # 选发型模板
├── preview.tsx           # AI 生成预览
└── _layout.tsx           # 根布局
```

**组件树：**
```
components/
├── TemplateCard.tsx      # 发型模板卡片
├── TemplateGrid.tsx      # 模板网格列表
├── CategoryTabs.tsx      # 分类 Tab
├── PhotoCapture.tsx      # 拍照/上传组件
├── LoadingOverlay.tsx    # AI 生成加载动画
├── ResultView.tsx        # 效果图展示
└── ActionButtons.tsx     # 保存/分享按钮
```

## 4. 后端 — Python FastAPI

**依赖：**
- fastapi + uvicorn
- httpx（调美图 API）
- Pillow（图片处理）
- python-multipart
- aliyun-oss-python-sdk

**API 接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/generate | 上传头像 + 选择模板 → 生成效果图 |
| POST | /api/regenerate | 调整参数后重新生成 |
| GET | /api/templates | 发型模板列表 |
| GET | /api/templates/{id} | 单个模板详情 |
| POST | /api/upload | 图片上传到 OSS |

**服务结构：**
```
backend/app/
├── main.py               # 入口
├── config.py             # 配置
├── routers/
│   ├── __init__.py
│   ├── generation.py     # 生成相关路由
│   └── templates.py      # 模板相关路由
├── services/
│   ├── __init__.py
│   ├── meitu.py          # 美图 API 封装
│   ├── oss.py            # OSS 上传
│   └── face.py           # 人脸检测(阿里云视觉API)
└── models/
    └── schemas.py        # Pydantic 模型
```

## 5. AI 生成流程

```
拍照/上传 → 人脸检测(SegmentHair) → 美图API融合 → OSS存储 → 返回URL
```

- MVP 直接使用美图奇想大模型 API 的预训练发型模板（通过 style_id 调用）
- 不自行部署 AI 模型
- 后续用户量增长后可切换到 HairPort + ACE++ 开源框架自部署

### 参数调整（P1）
- 前端滑块传参（长度、卷曲度、颜色、刘海样式）
- 后端调美图 API 重新生成
- 5-10 秒返回新效果图，覆盖预览

## 6. 存储方案（MVP）

| 数据 | 方案 | 说明 |
|------|------|------|
| 发型模板 | JSON 文件 | ~100 条，JSON 足够 |
| 用户图片 | 阿里云 OSS | 原图 + 效果图，CDN 加速 |
| 用户数据 | 暂不做 | P1 再加 SQLite → MySQL |

## 7. 部署方案

| 组件 | 方案 | 费用 |
|------|------|------|
| 后端 API | 阿里云 ECS 轻量应用服务器 | ~¥30/月 |
| 图片存储 | 阿里云 OSS（按量付费） | MVP 接近免费 |
| App 测试 | Expo Go 真机扫码 | 免费 |
| 域名 | 阿里云 DNS + 备案 | 视需要 |

## 8. 项目结构（Monorepo）

```
hairstyle/
├── mobile/                 # React Native (Expo)
│   ├── app/               # Expo Router 页面
│   ├── components/        # 可复用组件
│   ├── services/          # API 封装
│   └── assets/            # 静态资源
├── backend/               # Python FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── services/
│   │   └── models/
│   └── tests/
├── docs/                   # 文档
└── .gitignore
```

## 9. 开发顺序

1. **初始化项目** — Expo 脚手架 + FastAPI 骨架
2. **Mock 数据开发 UI** — 模板浏览、拍照、预览页面
3. **后端 API 开发** — 模板接口、生成接口、OSS 上传
4. **美图 API 对接** — 调通核心生成流程
5. **前后端联调** — 完整流程跑通
6. **P1 功能** — 参数调整、多视角等
7. **登录 + 支付**（可选，视需求）
