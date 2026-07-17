# AI 发型试戴 App — MVP 产品规格说明书

> **版本**: v2.0 (MVP)  
> **状态**: Draft（长期规划；**现行 MVP 实现以 README / AGENTS 为准**）  
> **变更**: 技术栈切换为 React Native + Python FastAPI 全栈  
> **2026-07-17 实现注记**: AI 引擎已落地为本地 **ComfyUI + PhotoMaker**，而非下文表格中的「美图奇想为主」。美图为遗留代码路径。  
> **目标**: 面向中国大陆美发消费场景的移动端 AI 虚拟发型预视工具

---

## 1. 产品概述

### 1.1 产品定位

一款适配手机、平板双端的 AI 虚拟发型试戴应用。用户上传或拍摄正面人像照片，一键融合海量发型模板，生成逼真的发型预览效果图，支持发长、发色等基础参数调节，帮助用户在理发前直观选定心仪造型。

### 1.2 MVP 目标

验证核心假设：**用户愿意为"提前看到自己的发型效果"付费。**

MVP 只保留能验证这一假设的最小功能集，不做 3D 全景旋转、不做实时渲染、不做社交分享。

### 1.3 MVP 功能边界

| 包含 | 不包含（后续版本） |
|------|-------------------|
| 手机号 / 微信 / 支付宝登录 | 3D 全景实时旋转 |
| 相册上传 + 相机拍照 | 实时渲染编辑 |
| ~100 款发型模板库 | 社交分享 / 社区 |
| AI 合成 4 角度预览图（正/侧/后/顶） | 用户 UGC 上传发型 |
| 发长、发色参数调节 | 发型师端 / 门店管理端 |
| 点数充值与消耗（微信/支付宝支付） | 会员订阅制 |
| 消费记录查询 | 个性化推荐算法 |

---

## 2. 技术架构

### 2.1 技术栈决策

| 层 | 选型 | 理由 |
|----|------|------|
| **移动端** | React Native (Expo) + TypeScript | 你的 TS 技能直接复用；Expo 屏蔽原生配置；相机/相册插件成熟；一套代码双端 + 平板自适应 |
| **后端** | Python 3.12 + FastAPI | 你的 Python 技能复用；异步高性能（uvicorn，单机 5000+ QPS）；生态覆盖 SMS/支付/OSS/AI 全部需求 |
| **异步任务** | Celery + Redis | AI 生成任务入队、重试、回调；Python 原生支持 |
| **AI 引擎** | 美图奇想大模型 API（主）+ YouCam API（备） | 亚洲人发型适配好；接入快；按调用付费，前期零 GPU 成本 |
| **数据库** | PostgreSQL 15（阿里云 RDS）+ Redis 7.x | SQLAlchemy async 对 PostgreSQL 支持最佳（asyncpg）；JSON 字段原生支持；阿里云 RDS 成熟托管 |
| **对象存储** | 阿里云 OSS + CDN | 用户照片、生成效果图、模板资源 |
| **部署** | 阿里云 ECS（Ubuntu 22.04）+ Docker Compose | 单机部署满足 MVP；Ansible/脚本一键部署；后期可平滑升级到 ACK |

### 2.2 为什么不再需要 Java/Spring Boot

原 v1.0 架构中 Java 做业务（Auth/User/Payment/Template）、Python 做 AI——两套服务需要两套 CI、两套 Dockerfile、两层鉴权。统一为 FastAPI 后：

- **代码量减少 ~40%**：一个 `requirements.txt`、一个 `Dockerfile`、一个 `docker-compose.yml`
- **不再需要 API Gateway**：FastAPI 中间件直接做 JWT 鉴权和限流；MVP 阶段 Nginx 反代足够
- **鉴权统一**：从前端到后端全程 JWT，不再有 Java↔Python 服务间调用的二次鉴权问题
- **运维简化**：一个 `git push` → 一个 CI 流程 → 一个容器 → 部署完成

### 2.3 系统架构图

```
┌──────────────────────────────────────────────────────────┐
│              移动端: React Native (Expo) + TypeScript      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌───────┐ │
│  │ 登录   │ │ 首页   │ │ 拍照   │ │ 预览   │ │ 编辑  │ │
│  │ (手机/ │ │ 模板库 │ │ 上传   │ │ 4角度  │ │ 发长/ │ │
│  │ 微信/  │ │ 分类   │ │ 引导框 │ │ 切换   │ │ 发色  │ │
│  │ 支付宝)│ │        │ │        │ │        │ │       │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └───────┘ │
│  状态管理: Zustand  •  路由: React Navigation            │
│  网络: Axios + JWT 拦截器  •  相机: expo-camera          │
│  微信 SDK: react-native-wechat-lib                       │
│  支付宝 SDK: @alipay/react-native-alipay                 │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTPS (REST JSON + JWT)
                     ▼
┌──────────────────────────────────────────────────────────┐
│              阿里云 ECS (Ubuntu 22.04)                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Nginx (TLS 终结 + 反代)                │  │
│  └────────────────────┬───────────────────────────────┘  │
│                       │                                   │
│  ┌────────────────────▼───────────────────────────────┐  │
│  │          FastAPI 应用 (Uvicorn + Gunicorn)          │  │
│  │                                                     │  │
│  │  /auth  — 认证模块 (SMS/微信/支付宝 OAuth)          │  │
│  │  /user  — 用户模块 (资料/点数/历史)                 │  │
│  │  /pay   — 支付模块 (套餐/下单/微信回调/支付宝回调)   │  │
│  │  /tmpl  — 模板模块 (分类/列表/详情)                 │  │
│  │  /gen   — AI 生成模块 (提交→Celery→轮询→返回)      │  │
│  └────────────────────┬──────────────────────────────┘  │
│                       │                                   │
│  ┌────────────────────▼───────────────────────────────┐  │
│  │            Celery Workers (异步 AI 任务)             │  │
│  │  - 人脸质检 → AI 合成 → 结果上传 OSS → 回调通知     │  │
│  │  - 失败重试 + 点数回补                              │  │
│  └────────────────────┬───────────────────────────────┘  │
│                       │                                   │
│  ┌────────────────────┴───────────────────────────────┐  │
│  │            阿里云 PaaS 服务                          │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │  │
│  │  │ RDS  │ │Redis │ │ OSS  │ │ SMS  │              │  │
│  │  │(PG)  │ │      │ │+CDN  │ │      │              │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  外部 API: 美图奇想 (主) • YouCam (备)                    │
└──────────────────────────────────────────────────────────┘
```

### 2.4 后端项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置（环境变量 / .env）
│   ├── database.py          # SQLAlchemy async engine + session
│   ├── dependencies.py      # 公共依赖注入（get_db, get_current_user）
│   ├── middleware/
│   │   └── jwt_auth.py      # JWT 鉴权中间件
│   ├── models/              # SQLAlchemy ORM 模型
│   │   ├── user.py
│   │   ├── sms_code.py
│   │   ├── hair_template.py
│   │   ├── generation.py
│   │   ├── order.py
│   │   └── points_ledger.py
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── routers/             # 路由（按模块拆分）
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── payment.py
│   │   ├── template.py
│   │   └── generation.py
│   ├── services/            # 业务逻辑层
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── payment_service.py
│   │   ├── template_service.py
│   │   └── ai_service.py
│   └── tasks/               # Celery 异步任务
│       ├── celery_app.py    # Celery 配置
│       └── ai_tasks.py      # AI 生成任务定义
├── alembic/                 # 数据库迁移
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 3. 核心功能详述

（本节与 v1.0 完全兼容，仅技术实现细节有变化）

### 3.1 用户登录与注册

**支持的登录方式（MVP）：**
1. **手机号 + 短信验证码**：阿里云 SMS SDK（`aliyun-python-sdk-dysmsapi`），60 秒有效，同号每日上限 10 条
2. **微信授权登录**：OAuth 2.0 授权码模式，后端用 `wechatpy` 库获取 access_token 和 openid
3. **支付宝授权登录**：OAuth 2.0，后端用 `alipay-sdk-python` 官方 SDK

**MVP 策略：先体验，后注册。** 免登录可浏览模板；首次点击"生成预览"时引导登录。

### 3.2 发型模板库

MVP 规模 ≥ 100 款。分类：性别 / 长度 / 风格 / 热度。
模板来源：开源资源（Meshy AI 等）→ 美图/YouCam 内置模板 → 后续定制。
存储：缩略图存 OSS + CDN，元数据存 PostgreSQL。

### 3.3 头像采集与预处理

流程：拍摄/选取 → 前端引导框 → 上传至后端 → 人脸质检（美图/阿里云 API）→ 分割预处理 → OSS 存储。
MVP 限制：仅单人正面照。

### 3.4 AI 发型合成

美图奇想（主）+ YouCam（备），Celery 异步处理。
流程：用户选择模板 → 扣点 → 入队 → API 合成 → 4 角度预览图 → OSS → 返回 URL。
SLA：≤ 10s；失败自动重试 1 次，仍失败回补点数。

### 3.5 参数编辑

MVP 支持：发长（5 档滑块）、发色（5 色色板）。
点击「应用」→ 扣点 → 重新生成。支持「撤销」回到上次结果（不扣点）。
不支持实时预览、挑染、卷度调节。

### 3.6 点数与支付

点数模型：1 次生成 = 1 点，新用户赠送 3 点。

| 套餐 | 点数 | 价格 (¥) |
|------|------|----------|
| 体验包 | 3 | 注册赠送 |
| 基础包 | 10 | 9.9 |
| 进阶包 | 30 | 19.9 |
| 畅享包 | 100 | 49.9 |

支付流程：用户选套餐 → 后端创建订单 → 调用微信/支付宝统一下单 API → 前端拉起收银台 → 异步回调验签 → 更新点数余额。
**Python 支付库**: `wechatpy`（微信支付 V3）+ `alipay-sdk-python`（支付宝）。
每日 Celery 定时任务对账。

---

## 4. 数据模型

与 v1.0 一致，数据库从 MySQL 切换为 PostgreSQL。`JSON` 列使用 PostgreSQL 原生 `JSONB` 类型，`ENUM` 使用 PostgreSQL 原生 `ENUM` 或 `VARCHAR` + CHECK 约束。

```sql
-- 核心表（PostgreSQL）
CREATE TABLE "user" (
  id            BIGSERIAL PRIMARY KEY,
  nickname      VARCHAR(64),
  avatar_url    VARCHAR(512),
  phone         VARCHAR(11) UNIQUE,
  phone_verified BOOLEAN DEFAULT FALSE,
  wechat_openid VARCHAR(128) UNIQUE,
  wechat_unionid VARCHAR(128),
  alipay_user_id VARCHAR(128) UNIQUE,
  points_balance INTEGER DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sms_code (
  id         BIGSERIAL PRIMARY KEY,
  phone      VARCHAR(11),
  code       VARCHAR(6),
  used       BOOLEAN DEFAULT FALSE,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sms_phone_expires ON sms_code (phone, expires_at);

CREATE TABLE hair_template (
  id              BIGSERIAL PRIMARY KEY,
  name            VARCHAR(128) NOT NULL,
  gender          VARCHAR(16) DEFAULT 'unisex',
  length          VARCHAR(16),
  style           VARCHAR(64),
  thumbnail_url   VARCHAR(512),
  api_template_id VARCHAR(128),
  sort_order      INTEGER DEFAULT 0,
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE generation (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL REFERENCES "user"(id),
  template_id      BIGINT NOT NULL REFERENCES hair_template(id),
  source_image_url VARCHAR(512),
  result_images    JSONB,
  params           JSONB,
  status           VARCHAR(16) DEFAULT 'queued',
  points_cost      INTEGER DEFAULT 0,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_generation_user ON generation (user_id);

CREATE TABLE "order" (
  id              BIGSERIAL PRIMARY KEY,
  order_no        VARCHAR(32) UNIQUE NOT NULL,
  user_id         BIGINT NOT NULL REFERENCES "user"(id),
  package_id      BIGINT,
  amount          DECIMAL(10,2) NOT NULL,
  points          INTEGER NOT NULL,
  payment_channel VARCHAR(16),
  status          VARCHAR(16) DEFAULT 'pending',
  paid_at         TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_order_user ON "order" (user_id);

CREATE TABLE points_ledger (
  id            BIGSERIAL PRIMARY KEY,
  user_id       BIGINT NOT NULL REFERENCES "user"(id),
  amount        INTEGER NOT NULL,
  type          VARCHAR(16),
  source        VARCHAR(64),
  balance_after INTEGER,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_points_user ON points_ledger (user_id);
```

---

## 5. API 设计（核心端点）

与 v1.0 相同，以下为核心端点概览：

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Auth | `POST` | `/api/v1/auth/sms/send` | 发送验证码 |
| Auth | `POST` | `/api/v1/auth/sms/login` | 手机号登录 |
| Auth | `POST` | `/api/v1/auth/wechat/login` | 微信登录 |
| Auth | `POST` | `/api/v1/auth/alipay/login` | 支付宝登录 |
| Auth | `POST` | `/api/v1/auth/refresh` | 刷新 Token |
| User | `GET/PUT` | `/api/v1/user/profile` | 用户信息 |
| User | `GET` | `/api/v1/user/points/ledger` | 点数流水 |
| User | `GET` | `/api/v1/user/generations` | 生成历史 |
| Template | `GET` | `/api/v1/templates` | 模板列表 |
| Generate | `POST` | `/api/v1/generate` | 提交生成任务 |
| Generate | `GET` | `/api/v1/generate/{id}/status` | 查询结果 |
| Payment | `GET` | `/api/v1/payment/packages` | 套餐列表 |
| Payment | `POST` | `/api/v1/payment/order` | 创建订单 |
| Payment | `POST` | `/api/v1/payment/wechat/notify` | 微信回调 |
| Payment | `POST` | `/api/v1/payment/alipay/notify` | 支付宝回调 |

API 文档通过 FastAPI 内置的 OpenAPI/Swagger（`/docs`）自动生成。

---

## 6. UI 页面与交互

（与 v1.0 相同，实现框架从 Flutter 切换到 React Native）

### 6.1 页面结构与技术映射

| 页面 | RN 组件/库 |
|------|-----------|
| 模板浏览（瀑布流） | `FlatList` + `numColumns` 实现瀑布流 |
| 分类 Tab | `react-native-tab-view` 或自定义 `ScrollView` |
| 登录/注册 | 自定义表单 + 微信/支付宝 SDK 唤起 |
| 相机拍照 | `expo-camera` |
| 相册选取 | `expo-image-picker` |
| 4 角度预览切换 | `Animated.View` + `FlatList` 横向滑动 |
| 参数编辑面板 | `react-native-reanimated` 底部上滑面板 |
| 生成等待动画 | `Lottie` 动画 + 进度文字 |

### 6.2 关键交互

**拍照引导**：半透明人形轮廓引导框，使用 `react-native-svg` 绘制。

**角度切换**：结果页底部 4 个角度缩略图按钮（正/左/右/后），点击切换大图。

**参数编辑**：底部上滑面板（`BottomSheet`），发长水平滑块（`@react-native-community/slider`），发色圆形色板。

**手势操作**：双指缩放、滑动旋转使用 `react-native-gesture-handler` + `react-native-reanimated`。

---

## 7. 非功能性需求

（与 v1.0 一致）

| 类别 | 要求 |
|------|------|
| **性能** | AI 生成耗时 P95 < 10s；API 响应 P95 < 200ms |
| **可用性** | ≥ 99.5%；AI 服务故障自动切换备用 API |
| **安全** | HTTPS 全链路；JWT 2h + Refresh 7d；支付验签；人脸照片加密存储、30 天自动清理 |
| **合规** | PIPL 人脸数据明示同意；微信/支付宝 SDK PCI-DSS |
| **兼容** | iOS 15+ / Android 8+；手机 + 平板自适应 |

---

## 8. 部署架构

```
阿里云 - 华北2（北京）Region
│
├── VPC
│   ├── ECS 实例 (Ubuntu 22.04, 4C8G, 按量或包年包月)
│   │   ├── Nginx (TLS 终结, 反代到 FastAPI :8000)
│   │   ├── FastAPI 容器 (Uvicorn, 2+ workers)
│   │   ├── Celery Worker 容器 (2 concurrency)
│   │   └── Celery Beat 容器 (定时对账)
│   │
│   ├── RDS PostgreSQL 15 (2C4G, 高可用)
│   ├── Redis 7.0 (2G, 标准版)
│   └── OSS + CDN
│
├── 阿里云 SMS
├── 美图奇想 API（主）
└── YouCam API（备）
```

部署方式：`docker-compose.yml` + GitHub Actions CI → `rsync` 到 ECS → `docker compose up -d`。MVP 阶段单机足够，后续可平滑升级到 ACK。

---

## 9. 技术风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 美图/YouCam API 效果不达预期 | 中 | 高 | Phase 0 用 20+ 真实照片验证效果 |
| AI API 调用不稳定/限频 | 中 | 高 | 双厂商冗余；Celery 自动重试+回补 |
| RN 微信/支付宝 SDK 兼容问题 | 中 | 中 | 提前在真机验证；备选：前端 H5 收银台 |
| Expo bare workflow 升级问题 | 低 | 低 | 锁定 SDK 版本；prebuild 后按标准 RN 项目维护 |
| FastAPI 单机性能瓶颈 | 低 | 中 | MVP 阶段 Gunicorn 多 worker 足够；瓶颈出现时加 ECS 实例 + Nginx 负载均衡 |
| Python wechatpy 维护不及时 | 低 | 中 | 微信支付 V3 API 有官方 HTTP 文档，可自行封装 |

---

*本文档为 MVP v2.0 规格，随开发推进持续更新。*
