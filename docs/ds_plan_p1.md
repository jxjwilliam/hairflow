# P1 本地实现方案 — 发型试戴

> **版本**: v1.0  
> **日期**: 2026-07-18  
> **状态**: Draft  
> **前提**: MacBook 本地开发（ComfyUI + FastAPI + Expo Web），忽略阿里云部署  
> **关联**: [README.md](../README.md) · [AGENTS.md](../AGENTS.md) · [ds_comfyui_setup.md](./ds_comfyui_setup.md)

---

## 0. 目标

在现有 ComfyUI MVP 基础上，于 MacBook 本地实现所有 P1 功能：

- 发型参数滑条（长度、卷曲度、发色、刘海）
- 多角度切换 / 伪 3D 预览
- 原图对比（Before / After）
- 用户注册 / 登录
- 点数充值 / 消费（Mock 支付）
- 数据库用 **SQLite**（零配置、单文件）

---

## 1. 架构变更

```
现有：Mobile ──→ FastAPI ──→ ComfyUI
                                        无状态，无用户

新增：Mobile ──→ FastAPI ──→ ComfyUI
                │
                ├── SQLite (aiosqlite)  ← 新增
                ├── JWT Auth            ← 新增
                ├── 点数系统             ← 新增
                ├── Mock 支付            ← 新增
                ├── 参数→prompt 映射     ← 新增
                └── 多角度生成            ← 新增
```

- 无新增外部依赖
- 无需 Docker / Redis / Celery
- SQLite 文件落于 `backend/data/hairstyle.db`
- 所有 ComfyUI 调用保持同步（本地单用户，无需任务队列）

---

## 2. Phase 分拆（6 个阶段）

| Phase | 内容 | 后端 | 前端 |
|-------|------|------|------|
| 1 | 数据库 + 用户系统 | SQLAlchemy + JWT + Auth API | 登录/注册页 + AuthContext |
| 2 | 点数 + Mock 支付 | 点数模型 + 支付 API | 余额展示 + 充值页 |
| 3 | 发型参数滑条 | 参数→prompt 映射 | ParameterPanel 组件 |
| 4 | 多角度 / 伪 3D | 多角度生成 API | AngleSwitcher 组件 |
| 5 | 原图对比 | 无后端改动 | BeforeAfter 组件 |
| 6 | 全链路集成 + 文档 | 无 | 页面串联 + 文档更新 |

---

## 3. Phase 1：数据库 + 用户系统

### 3.1 技术选型

- **ORM**: SQLAlchemy 2.0 (async) + aiosqlite
- **Auth**: python-jose (JWT), bcrypt 或 hashlib (密码/Mock SMS)
- **SMS**: Mock 实现 — 验证码固定 `123456`，控制台打印

### 3.2 数据模型（5 张表）

```sql
-- user
CREATE TABLE user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    phone         TEXT UNIQUE NOT NULL,
    phone_verified INTEGER DEFAULT 0,
    points_balance INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

-- sms_code
CREATE TABLE sms_code (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    phone      TEXT NOT NULL,
    code       TEXT NOT NULL,
    used       INTEGER DEFAULT 0,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- generation (替代 AsyncStorage 本地历史)
CREATE TABLE generation (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES user(id),
    template_id   TEXT NOT NULL,
    template_name TEXT,
    source_photo  TEXT,          -- base64，可选存储
    result_images TEXT,          -- JSON: {"front": "url", ...}
    params        TEXT,          -- JSON: {"length":3,"curl":4,...}
    angles        TEXT,          -- JSON: ["front","side-left",...]
    status        TEXT DEFAULT 'completed',
    created_at    TEXT DEFAULT (datetime('now'))
);

-- points_ledger
CREATE TABLE points_ledger (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES user(id),
    amount        INTEGER NOT NULL,
    type          TEXT NOT NULL,   -- 'earn' | 'spend'
    source        TEXT,            -- 'register_bonus' | 'purchase' | 'generation'
    balance_after INTEGER,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- order
CREATE TABLE "order" (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no        TEXT UNIQUE NOT NULL,
    user_id         INTEGER NOT NULL REFERENCES user(id),
    package_id      TEXT,
    amount          REAL NOT NULL,
    points          INTEGER NOT NULL,
    channel         TEXT,          -- 'mock' | 'wechat' | 'alipay'
    status          TEXT DEFAULT 'pending',
    paid_at         TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### 3.3 API 端点

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | `/api/auth/sms/send` | 无 | 发送验证码 (Mock: 控制台打印) |
| POST | `/api/auth/sms/login` | 无 | 手机号 + 验证码登录，返回 JWT |
| GET | `/api/user/profile` | JWT | 用户信息 + 点数余额 |
| GET | `/api/user/generations` | JWT | 生成历史列表 |

### 3.4 JWT 实现

- **签发**: `python-jose`，access token 有效期 2h（无 refresh token，MVP 简化）
- **中间件**: FastAPI `Depends(get_current_user)` 从 `Authorization: Bearer <token>` 解析 user_id
- **前端**: `AuthContext` + axios interceptor 自动附加 token

### 3.5 SMS Mock 策略

```
POST /api/auth/sms/send  {"phone": "13800138000"}
→ 200 {"message": "验证码已发送（开发模式：123456）"}
→ 控制台: [DEV SMS] Phone: 13800138000, Code: 123456
```

本地开发用固定验证码 `123456`，生产替换为阿里云 SMS SDK 即可。

### 3.6 前端新增页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录 | `app/auth/login.tsx` | 手机号输入 + 验证码输入 + 登录按钮 |

`AuthContext` 保存 `{ token, user }` 状态。已登录则在首页 header 显示点数余额；未登录则在点击生成时引导登录。

---

## 4. Phase 2：点数 + Mock 支付

### 4.1 点数模型

| 规则 | 说明 |
|------|------|
| 注册赠送 | 新用户首次登录赠送 **3 点** |
| 生成消耗 | 每次生成（含多角度）消耗 **1 点** |
| 余额不足 | 返回 `402 Payment Required`，前端引导充值 |

### 4.2 套餐定义

| 套餐 ID | 名称 | 点数 | 价格 (¥) |
|---------|------|------|----------|
| `basic` | 基础包 | 10 | 9.9 |
| `plus` | 进阶包 | 30 | 19.9 |
| `premium` | 畅享包 | 100 | 49.9 |

套餐定义在 `backend/data/packages.json`（硬编码，无需 DB）。

### 4.3 Mock 支付流程

```
1. 前端选套餐 → POST /api/payment/order  {package_id: "basic"}
   ← 200 {order_no: "20260718...", amount: 9.9}

2. 前端 → POST /api/payment/mock-pay/{order_no}
   ← 200 {message: "支付成功", points_added: 10, balance: 13}

3. 后端: order.status → 'paid', user.points_balance += 10, 记录 points_ledger
```

真实微信/支付宝接入时，只需：
- 将 `POST /api/payment/order` 改为调用 `wechatpy` / `alipay-sdk-python` 下单
- 将 `POST /api/payment/mock-pay/{order_no}` 替换为微信/支付宝异步回调端点
- 接口契约不变

### 4.4 API 端点

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/payment/packages` | 无 | 套餐列表 |
| POST | `/api/payment/order` | JWT | 创建订单 |
| POST | `/api/payment/mock-pay/{order_no}` | JWT | Mock 支付（本地开发） |
| GET | `/api/user/points/ledger` | JWT | 点数流水 |

### 4.5 生成接口改造

在 `POST /api/comfyui/generate` 开头插入：

```
1. 校验 JWT → 获取 current_user
2. 检查 user.points_balance >= 1 → 否则返回 402
3. user.points_balance -= 1 → 写入 points_ledger (type='spend')
4. 执行 ComfyUI 生成
5. 成功 → 记录 generation 表
6. 失败 → 回补点数 + 记录 points_ledger (type='earn', source='generation_refund')
```

### 4.6 前端新增/改造

| 页面 | 路由 | 说明 |
|------|------|------|
| 个人中心 | `app/account.tsx` | 点数余额 + 快捷充值 + 生成历史 |
| 充值 | `app/account/recharge.tsx` | 套餐选择 + Mock 支付确认 |
| 首页 header | 改造 | 已登录显示点数 badge |

---

## 5. Phase 3：发型参数滑条

### 5.1 核心思路

**不改 ComfyUI workflow，只改 prompt。** 参数值通过映射表拼接到 `positive_prompt`。

### 5.2 参数→Prompt 映射表

实现文件：`backend/app/services/param_prompt.py`

```python
LENGTH_MAP = {
    1: "very short hair, buzz cut",
    2: "short hair",
    3: "medium length hair",
    4: "long hair",
    5: "very long hair, flowing long hair",
}

CURL_MAP = {
    1: "completely straight hair, sleek",
    2: "slightly wavy hair, soft waves",
    3: "wavy hair",
    4: "curly hair, defined curls",
    5: "very curly hair, voluminous tight curls",
}

COLOR_MAP = {
    1: "black hair",
    2: "dark brown hair",
    3: "brown hair",
    4: "light brown hair, caramel hair",
    5: "fashion hair color, highlighted hair",
}

BANGS_MAP = {
    1: "no bangs, forehead visible",
    2: "wispy bangs, air bangs, see-through bangs",
    3: "blunt bangs, full bangs, straight bangs",
    4: "side-swept bangs, side parted bangs",
    5: "short baby bangs, cropped bangs",
}
```

### 5.3 API 变更

`GenerateRequest` 增加可选 `params` 字段：

```json
{
  "photo_base64": "...",
  "style_id": "w1",
  "params": {
    "length": 3,
    "curl": 4,
    "color": 2,
    "bangs": 1
  }
}
```

后端处理：
1. 加载模板 `positive_prompt`
2. 遍历 `params`，调用映射表追加修饰词
3. 最终 prompt = `原prompt + , length_modifier + , curl_modifier + , color_modifier + , bangs_modifier + , img`

### 5.4 前端 ParameterPanel 组件

| 元素 | 实现 |
|------|------|
| 容器 | `BottomSheet`（react-native-reanimated）从底部滑出 |
| 发长 | `Slider` 5 档，标签：超短 / 短 / 中 / 长 / 超长 |
| 卷曲 | `Slider` 5 档，标签：直 / 微卷 / 波浪 / 卷 / 爆炸卷 |
| 发色 | 5 个圆形色块（黑 / 深棕 / 棕 / 浅棕 / 潮色），点击选择 |
| 刘海 | `Slider` 5 档，标签：无 / 空气 / 齐 / 侧分 / 眉上 |
| 应用 | 「生成预览」按钮，提交生成请求 |

### 5.5 前端页面流调整

```
现有：capture → preview（自动生成）
新：  capture → params（参数编辑）→ preview（自动生成）
```

`params.tsx`：显示选定模板 + 照片缩略图 + ParameterPanel + 生成按钮。

---

## 6. Phase 4：多角度切换 / 伪 3D

### 6.1 方案

对每个角度发起 **独立的 ComfyUI 生成请求**，返回多张图。
前端通过手势滑动 4 个角度模拟 3D 旋转感。

### 6.2 角度定义

| angle | 说明 | prompt 修饰词 |
|-------|------|--------------|
| `front` | 正面（默认） | `front view, facing camera, looking at viewer` |
| `side-left` | 左侧 45° | `left profile view, head turned to the left, side angle` |
| `side-right` | 右侧 45° | `right profile view, head turned to the right, side angle` |
| `back` | 背面 | `back view, from behind, showing back of head and hairstyle` |

### 6.3 API 变更

`POST /api/comfyui/generate` 增加 `angles` 参数：

```json
{
  "photo_base64": "...",
  "style_id": "w1",
  "params": { "length": 3, "curl": 4, "color": 2, "bangs": 1 },
  "angles": ["front", "side-left", "side-right", "back"]
}
```

- 默认值：`["front"]`（不传则仅正面）
- 返回 `result_images`：`{"front": "url1", "side-left": "url2", ...}`
- 后端串行生成各角度（Mac MPS 下并行易 OOM，串行更稳定）
- 单个角度约 30-60s，4 角度约 2-4 min

### 6.4 模板数据扩展

`templates_comfyui.json` 每条模板增加 `angle_prompt_modifiers`：

```json
{
  "id": "w1",
  "angle_prompt_modifiers": {
    "front": ", front view, facing camera, looking at viewer",
    "side-left": ", left profile view, head turned to the left, 45 degree side angle",
    "side-right": ", right profile view, head turned to the right, 45 degree side angle",
    "back": ", back view, from behind, showing back of head and hairstyle"
  }
}
```

### 6.5 后端生成逻辑

```python
# comfyui_generation.py 伪代码
async def comfyui_generate(req: GenerateRequest, current_user: User):
    angles = req.angles or ["front"]
    results = {}
    for angle in angles:
        # 构建 angle-specific prompt
        angle_modifier = template.get("angle_prompt_modifiers", {}).get(angle, "")
        final_prompt = base_prompt + angle_modifier
        # 调用 ComfyUI
        image_bytes = await comfyui_service.generate_hairstyle(
            photo_base64=req.photo_base64,
            prompt=final_prompt,
            ...
        )
        url = save_and_get_url(image_bytes)
        results[angle] = url
    return {"result_images": results, ...}
```

### 6.6 前端 AngleSwitcher 组件

| 元素 | 实现 |
|------|------|
| 大图区 | 当前选中角度的结果图，居中全宽 |
| 角度条 | 底部横向缩略图列表：正 / 左 / 右 / 后，当前选中高亮 |
| 手势 | `FlatList` 横向滑动切换角度；左右箭头按钮辅助 |
| 伪 3D | 快速连续滑动时产生旋转动画感（可选 `Animated.spring`） |

### 6.7 ResultView 改造

`ResultView` 原来接收单个 `imageUrl: string`，改造为：

```typescript
interface ResultViewProps {
  images: Record<string, string>;  // { front: url, side-left: url, ... }
}
```

---

## 7. Phase 5：原图对比

### 7.1 方案

纯前端实现，无后端改动。用户原始照片已在 `SessionContext` 中。

### 7.2 BeforeAfter 组件

两种模式，按钮切换：

**模式 1：并排对比（默认）**
```
┌──────────┬──────────┐
│  原图     │  生成图    │
│          │          │
└──────────┴──────────┘
```

**模式 2：滑块对比**
```
┌──────────────────────┐
│  原图 ←──┫──→ 生成图   │  ← 可拖动竖线分界
└──────────────────────┘
```

滑块模式实现：`react-native-reanimated` 手势 + `overflow: hidden` + `translateX` 分界线。

### 7.3 接入点

- `preview.tsx`：生成完成后 toolbar 增加「对比原图」按钮，点击弹 BeforeAfter
- `result-view.tsx`（历史详情）：同样增加对比按钮
- `params.tsx`：参数编辑页也可在照片缩略图左侧放「预览原图」入口

---

## 8. Phase 6：全链路集成

### 8.1 完整用户流程

```
打开 App
  │
  ├─ 浏览模板（无需登录）
  │    │
  │    └─ 选模板 → 拍照/上传
  │         │
  │         ├─ 未登录 → 跳登录页 → 登录成功 → 继续
  │         │
  │         └─ 参数编辑页（长度/卷曲/颜色/刘海 + 角度选择）
  │              │
  │              └─ 生成 → 扣点 → 等待 → 预览页
  │                   │
  │                   ├─ 角度切换（正/左/右/后）
  │                   ├─ 原图对比
  │                   ├─ 重试（再扣 1 点）
  │                   ├─ 换发型（回发型库，保留照片）
  │                   └─ 保存/分享
  │
  ├─ 效果 Tab（历史列表，云端数据）
  │    └─ 点击 → 详情（多角度 + 对比）
  │
  └─ 个人中心
       ├─ 点数余额
       ├─ 充值
       ├─ 点数流水
       └─ 生成历史
```

### 8.2 完整页面路由表

| 路由 | 页面 | 变更类型 |
|------|------|----------|
| `(tabs)/index` | 发型库 | 改造：header 加登录状态 + 点数 badge |
| `(tabs)/history` | 效果历史 | 改造：从云端 API 获取，替代 AsyncStorage |
| `auth/login` | 登录/注册 | **新增** |
| `capture` | 拍照/上传 | 改造：完成后跳 params 而非 preview |
| `params` | 参数编辑 | **新增** |
| `preview` | 生成预览 | 改造：多角度 + 原图对比 |
| `result-view` | 历史详情 | 改造：多角度 + 对比 |
| `account` | 个人中心 | **新增** |
| `account/recharge` | 充值 | **新增** |

### 8.3 后端文件清单

```
backend/
├── app/
│   ├── main.py                       # 改造：注册新 router + startup 建表
│   ├── config.py                     # 改造：增加 SQLITE_PATH
│   ├── database.py                   # 新增：async engine + session
│   ├── models/
│   │   ├── __init__.py               # 新增
│   │   ├── user.py                   # 新增
│   │   ├── sms_code.py               # 新增
│   │   ├── generation.py             # 新增
│   │   ├── points_ledger.py         # 新增
│   │   └── order.py                  # 新增
│   ├── schemas/
│   │   ├── auth.py                   # 新增
│   │   ├── user.py                   # 新增
│   │   └── payment.py                # 新增
│   ├── routers/
│   │   ├── auth.py                   # 新增
│   │   ├── user.py                   # 新增
│   │   ├── payment.py                # 新增
│   │   ├── templates.py              # 已有，不改
│   │   ├── generation.py             # 已有，不改（Meitu 遗留）
│   │   └── comfyui_generation.py     # 改造
│   ├── services/
│   │   ├── auth_service.py           # 新增
│   │   ├── payment_service.py        # 新增
│   │   ├── param_prompt.py           # 新增
│   │   ├── face.py                   # 已有，不改
│   │   ├── comfyui.py                # 已有，不改
│   │   ├── meitu.py                  # 已有，不改
│   │   └── oss.py                    # 已有，不改
│   └── middleware/
│       └── jwt_auth.py               # 新增
├── data/
│   ├── hairstyle.db                  # 新增（SQLite 文件，gitignore）
│   ├── packages.json                 # 新增（点数套餐定义）
│   └── templates_comfyui.json        # 改造
├── requirements.txt                  # 改造：增加 sqlalchemy, aiosqlite, python-jose, bcrypt
└── tests/                            # 新增测试
```

### 8.4 前端文件清单

```
mobile/
├── app/
│   ├── _layout.tsx                   # 改造：注册新路由
│   ├── auth/
│   │   └── login.tsx                 # 新增
│   ├── account.tsx                   # 新增
│   ├── account/
│   │   └── recharge.tsx              # 新增
│   ├── params.tsx                    # 新增
│   ├── (tabs)/
│   │   ├── index.tsx                 # 改造
│   │   └── history.tsx               # 改造
│   ├── capture.tsx                   # 改造
│   ├── preview.tsx                   # 改造
│   └── result-view.tsx               # 改造
├── context/
│   ├── SessionContext.tsx             # 已有
│   └── AuthContext.tsx                # 新增
├── components/
│   ├── ParameterPanel.tsx             # 新增
│   ├── AngleSwitcher.tsx              # 新增
│   ├── BeforeAfter.tsx                # 新增
│   └── ...                            # 已有
├── services/
│   ├── api.ts                        # 改造：JWT interceptor
│   ├── auth.ts                       # 新增
│   ├── user.ts                       # 新增
│   ├── payment.ts                    # 新增
│   ├── generation.ts                 # 改造
│   ├── history.ts                    # 改造
│   └── templates.ts                  # 已有
└── types.ts                          # 改造
```

---

## 9. 关键设计决策

| 决策 | 理由 |
|------|------|
| **SQLite 而非 PostgreSQL** | 零配置、单文件、Mac 本地开发最快；后续生产换 PG 只需改 `database.py` 连接串 |
| **Mock 支付而非真实接入** | 微信/支付宝需企业资质 + 服务器域名，本地阶段 Mock 即可；接口契约不变，后续替换 endpoint 实现 |
| **参数调整 = 改 prompt** | PhotoMaker workflow 结构固定，prompt 修改灵活零风险；不引入新 ComfyUI 节点 |
| **多角度 = 多次串行生成** | PhotoMaker 无法单次输出多角度；Mac MPS 下串行更稳定（避免 OOM）；4 角度约 2-4min |
| **伪 3D = 多角度滑动连播** | 无 3D 模型可用，4 角度手势切换已能模拟旋转感 |
| **不引入 Celery / Redis** | MVP 本地单用户，同步 ComfyUI 调用已足够 |
| **不引入 Alembic** | SQLite 开发阶段用 `Base.metadata.create_all` 自动建表即可；生产迁移时再引入 |
| **SMS = 固定验证码 123456** | 本地无需真实短信，生产替换阿里云 SMS SDK endpoint |
| **无微信/支付宝 OAuth** | MVP 本地无法回调；仅手机号登录；后续添加 OAuth |

---

## 10. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 多角度生成耗时过长（>5min） | 中 | 中 | 默认只生成 front；多角度为可选开关 |
| 角度 prompt 对 PhotoMaker 效果有限 | 中 | 中 | 先实现 front + side-left 两个角度验证；效果差则降级为仅 front |
| SQLite 并发写入冲突 | 低 | 低 | 单用户本地使用，无并发问题 |
| Expo Web 下某些原生组件不可用 | 低 | 中 | 参数面板/Slider 用纯 RN 组件，不依赖原生模块 |

---

## 11. 预计工时

| Phase | 后端 | 前端 | 合计 |
|-------|------|------|------|
| 1: 数据库 + 用户 | 4h | 3h | 7h |
| 2: 点数 + 支付 | 3h | 3h | 6h |
| 3: 参数滑条 | 2h | 4h | 6h |
| 4: 多角度 | 3h | 4h | 7h |
| 5: 原图对比 | 0h | 3h | 3h |
| 6: 集成 + 文档 | 2h | 3h | 5h |
| **合计** | **14h** | **20h** | **34h** |

约 4-5 个工作日（单人全职）。

---

*本文档随实现推进持续更新。*
