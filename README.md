# Hairstyle — AI 虚拟发型试戴

面向国内理发行业的 AI 虚拟发型试戴 App。用户上传人像照片，选择发型模板，AI 生成发型效果图，辅助理发决策。

> 个人开发者业余项目 · MVP 阶段

---

## 功能

| 功能 | 状态 |
|------|------|
| 发型模板浏览（网格列表 + 男女分类 Tab） | ✅ |
| 拍照 / 相册上传头像 | ✅ |
| AI 生成发型效果图（美图奇想大模型 API） | ✅ |
| 效果图预览 | ✅ |
| 保存到相册 / 分享 | ✅ |
| 发型参数调整（长度、颜色、卷曲度） | ⏳ P1 |
| 脸型适配推荐 | ⏳ P2 |

---

## 架构

```
mobile/  (React Native Expo)  ──HTTP──▶  backend/  (Python FastAPI)  ──▶  美图 API
                                               │
                                               ▼
                                          阿里云 OSS (图片存储)
```

### 前端

- **React Native (Expo SDK 57)** + Expo Router 文件路由
- @tanstack/react-query 管理 API 请求和缓存
- TypeScript

**页面流：** 首页模板浏览 → 拍照/选照片 → AI 生成 → 预览（保存/分享）

**Web 支持：** 保存/分享按钮在 Web 端自动降级为下载链接和 Web Share API，方便开发调试。

### 后端

- **Python FastAPI** + uvicorn
- httpx 调用美图 API
- 阿里云 OSS 存储原图和效果图
- 人脸检测对接阿里云视觉 API（MVP 为 stub）

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
│   │   ├── TemplateCard.tsx   # 发型模板卡片
│   │   ├── TemplateGrid.tsx   # 模板网格列表
│   │   ├── CategoryTabs.tsx   # 分类 Tab
│   │   ├── PhotoCapture.tsx   # 拍照/上传组件
│   │   ├── LoadingOverlay.tsx # AI 生成加载动画
│   │   ├── ResultView.tsx     # 效果图展示
│   │   └── ActionButtons.tsx  # 保存/分享按钮
│   └── services/
│       ├── api.ts            # Axios 实例
│       ├── templates.ts      # 模板 API 封装
│       └── generation.ts     # 生成 API 封装
├── backend/                   # Python FastAPI
│   ├── app/
│   │   ├── main.py           # 入口
│   │   ├── config.py         # 配置 (pydantic-settings)
│   │   ├── routers/
│   │   │   ├── templates.py  # GET /api/templates
│   │   │   └── generation.py # POST /api/generate
│   │   ├── services/
│   │   │   ├── meitu.py      # 美图 API 封装
│   │   │   ├── oss.py        # 阿里云 OSS 上传
│   │   │   └── face.py       # 人脸检测 (stub)
│   │   └── models/
│   │       └── schemas.py    # Pydantic 模型
│   ├── data/
│   │   └── templates.json    # 15 个种子发型模板
│   └── Dockerfile
├── docs/                     # 设计文档
├── README.md
└── AGENTS.md
```

---

## 快速开始

### 前置条件

- Node.js 20+ / npm
- Python 3.12+
- Expo Go（手机测试）或 Xcode / Android Studio
- 美图 API 密钥（[申请地址](https://open.mtlab.meitu.com/)）
- 阿里云 OSS Bucket

### 后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 复制并填写环境变量
cp .env.example .env

# 启动开发服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证：

```bash
curl http://localhost:8000/              # → {"status":"ok"}
curl http://localhost:8000/api/templates  # → 15 个模板
```

### 前端

```bash
cd mobile

# 安装依赖
npm install

# 启动 Expo 开发服务
npx expo start
```

> 扫码或用模拟器打开。确保手机和电脑在同一局域网，修改 `mobile/services/api.ts` 中的 `baseURL` 为电脑局域网 IP。
> 在国内网络环境下，如果扫码后无法连接，尝试 tunnel 模式：`npx expo start --tunnel`

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `MEITU_API_KEY` | 美图 API Key |
| `MEITU_API_SECRET` | 美图 API Secret |
| `OSS_ENDPOINT` | OSS Endpoint（如 `oss-cn-hangzhou.aliyuncs.com`） |
| `OSS_BUCKET` | OSS Bucket 名称 |
| `OSS_ACCESS_KEY` | 阿里云 AccessKey |
| `OSS_SECRET_KEY` | 阿里云 AccessSecret |

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/templates` | 发型模板列表（可选 `?category=men|women`） |
| `GET` | `/api/templates/{id}` | 单个模板详情 |
| `POST` | `/api/generate` | 上传头像 + 选择模板 → 生成效果图 |
| `POST` | `/api/regenerate` | 调整参数后重新生成（MVP stub） |

---

## 部署

- **后端：** `docker build -t hairstyle-api ./backend && docker run -p 8000:8000 hairstyle-api`
- **建议：** 阿里云 ECS 轻量应用服务器 ~¥30/月

---

## 路线图

- **P1：** 发型参数调整（长度/颜色/卷曲度/刘海）、多视角切换、对比图、用户登录、点数消费
- **P2：** 会员订阅、生成历史、模板收藏、脸型适配推荐、切换到 HairPort + ACE++ 自部署

---

## License

MIT
