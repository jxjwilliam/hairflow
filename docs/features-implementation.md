# 待办功能实现文档 — P1 Local MVP

> **目标**：在 MacBook 本地环境（ComfyUI + FastAPI + Expo）集中实现 P1 待办功能。
> **原则**：需要数据库时用 SQLite，避免外部依赖；先跑通功能，再考虑部署。
> **状态**：Plan · 2026-07-17

---

## 总览

| 功能 | 涉及端 | 数据库需求 | 复杂度 | 依赖关系 |
|------|--------|-----------|--------|---------|
| 发型参数调整（长度/卷曲/颜色） | 前端 + 后端 + ComfyUI | 无 | ⭐⭐⭐ | A |
| 多角度切换 | 前端 + 后端 + ComfyUI | 无 | ⭐⭐⭐ | A |
| 原图对比 | 前端 | 无 | ⭐ | B |
| 用户注册/登录 | 前端 + 后端 | 需要 | ⭐⭐⭐ | C |
| 点数订阅与支付 | 前端 + 后端 | 需要 | ⭐⭐⭐⭐ | C, D |
| 数据库层（SQLite） | 后端 | — | ⭐⭐ | — |

**依赖关系**：
- A: 核心 ComfyUI 交互 → **优先实现**
- B: 纯前端 → 可与 A 并行
- C: 需要数据库 → 先实现数据库层
- D: 依赖登录 → 先实现用户系统

---

## 现有代码基础（已就绪）

### 后端
- `POST /api/comfyui/generate` — 接收 `photo_base64` + `style_id`，调用 ComfyUI PhotoMaker 生成
- `generate_hairstyle()` — 已暴露 `width/height/steps/cfg/denoise/seed` 等全部 KSampler 参数
- `schemas.py` — `RegenerateRequest` 已有 `length`/`curl`/`color`/`bang_style` 字段（未使用）
- 模板数据：`templates_comfyui.json` — 每模板自带 `positive_prompt`/`negative_prompt`/`checkpoint`/`steps`/`cfg`/`denoise`

### 前端
- 页面流：发型库 → `capture.tsx` → `preview.tsx` → 结果
- 组件: `ResultView`、`ActionButtons`（保存/分享/重试/换发型）
- Tab: `(tabs)/history.tsx`（本机试戴历史）
- Session: `SessionContext` 保留用户照片

---

## 一、发型参数调整（长度/卷曲/颜色）

### 目标
用户选定模板生成效果图后，通过滑块调整发型参数（发长、卷曲度、发色），点击"应用"重新生成。

### 实现思路

参数调整的本质是 **修改 prompt + KSampler 参数** 重新提交 ComfyUI。

```
发长 (length):    0.0 (极短) → 1.0 (极长)  → 拼入 prompt "short/medium/long hair"
卷曲度 (curl):    0.0 (直发) → 1.0 (卷发)  → 拼入 prompt "straight/wavy/curly hair"
发色 (color):     预设 5-8 色 → 拼入 prompt "black/brown/red/blonde/blue hair"
```

### 步骤

#### 1.1 后端 — 新增 `POST /api/comfyui/regenerate` 端点

```python
# new endpoint in comfyui_generation.py
class RegenerateRequest(BaseModel):
    photo_base64: str       # 保留原始照片（前端传回或后端缓存）
    style_id: str           # 模板 ID
    length: float = 0.5     # 0.0 ~ 1.0
    curl: float = 0.0       # 0.0 ~ 1.0
    color: str = "black"    # 预设色名
    # 以下可选，覆盖模板默认
    steps: int | None = None
    cfg: float | None = None
    denoise: float | None = None
```

**核心逻辑** — 参数 → prompt 映射函数：

```python
# app/services/prompt_builder.py (new)
def build_adjusted_prompt(base_prompt: str, length: float, curl: float, color: str) -> str:
    """Adjust hairstyle description based on parameter sliders."""
    length_desc = _map_length(length)     # "short" / "medium" / "long"
    curl_desc = _map_curl(curl)           # "straight" / "wavy" / "curly"
    color_desc = _map_color(color)        # "black" / "brown" / ... (Chinese names supported)

    # Replace or inject into base prompt
    # Strategy: inject before "hair" keyword in prompt
    adjusted = f"{length_desc} {curl_desc} {color_desc} hair, {base_prompt}"
    return adjusted
```

映射表（`prompt_builder.py`）：

| 参数 | 值 | Prompt 片段 |
|------|----|------------|
| length 0.0-0.3 | short | `short` |
| length 0.3-0.6 | medium | `medium length` |
| length 0.6-1.0 | long | `long` |
| curl 0.0-0.2 | straight | `straight` |
| curl 0.2-0.6 | wavy | `wavy` |
| curl 0.6-1.0 | curly | `curly` |
| color black | 黑色 | `black` |
| color brown | 棕色 | `brown` |
| color red | 红色 | `red` |
| color blue | 蓝色 | `blue` |
| color purple | 紫色 | `purple` |
| color blonde | 金色 | `blonde` |
| color gray | 灰色 | `gray` |

**提示词注入策略**：PhotoMaker 依赖 `img` 触发词保留在 prompt 中。

#### 1.2 前端 — 参数面板组件（ResultView 扩展）

新建 `mobile/components/ParamPanel.tsx`：

```
┌──────────────────────────────┐
│  发型参数调整                  │
│                              │
│  发长 ─────●────────  (0.7)  │
│  卷曲 ─●───────────  (0.2)   │
│                              │
│  发色:                        │
│  ⚫ 🟤 🔴 🔵 🟣 💛 ⚪      │
│                              │
│  [  重新生成 (消耗 1 点)  ]    │
└──────────────────────────────┘
```

- 使用 `@react-native-community/slider` (Expo 57 自带)
- 发色用圆形 `TouchableOpacity` 色板
- 点击"重新生成" → 调用 `POST /api/comfyui/regenerate`

#### 1.3 前端 — 更新 `generation.ts`

```typescript
// new function
export async function regenerateHairstyle(
  photoBase64: string,
  styleId: string,
  params: { length: number; curl: number; color: string },
): Promise<GenerateResult> {
  const res = await api.post('/api/comfyui/regenerate', {
    photo_base64: photoBase64,
    style_id: styleId,
    ...params,
  });
  return res.data;
}
```

#### 1.4 更新 `preview.tsx`

- 在 `ResultView` 下方渲染 `ParamPanel`
- 用户调整参数后调用 `regenerateHairstyle` mutation
- 结果替换当前显示

---

## 二、多角度切换

### 目标
生成多个角度的发型效果图（正面/左侧/右侧/后面），用户可滑动切换查看。

### 实现思路

**方案 A（推荐）**：一次 generate 请求同时生成多角度图（通过 ComfyUI 多 batch 或多 KSampler 节点）

**方案 B（备选）**：修改 prompt 中的角度词，多次调用 ComfyUI

推荐 **方案 B** 作为起始实现（不需要修改 ComfyUI 工作流 JSON），后续可升级为方案 A。

#### 2.1 后端 — 修改 generate_hairstyle 支持多角度

```python
ANGLES = ["front", "left", "right", "back"]
ANGLE_PROMPTS = {
    "front": "front view, looking at camera",
    "left": "left side view, head turned slightly left",
    "right": "right side view, head turned slightly right",
    "back": "back view, showing back of head",
}
```

新端点 `POST /api/comfyui/generate-multi`：

```python
@router.post("/generate-multi", response_model=MultiAngleResponse)
async def comfyui_generate_multi(req: GenerateRequest, request: Request):
    """Generate hairstyle preview from 4 angles, return image_urls dict."""
    # Same face detection + crop as single generate
    # Then for each angle:
    results = {}
    for angle in ANGLES:
        angle_prompt = f"{template['positive_prompt']}, {ANGLE_PROMPTS[angle]}"
        image_bytes = await comfyui_service.generate_hairstyle(
            photo_base64=photo_for_generation,
            prompt=angle_prompt,
            ...  # same params
        )
        url, image_id = _save_locally(image_bytes, base_url=base_url)
        results[angle] = {"url": url, "id": image_id}
    return MultiAngleResponse(images=results)
```

> **性能注意**：4 次串行调用约 4× 耗时（~60-80s）。优化方向：用 `asyncio.gather` 并行调用，或改造 ComfyUI 工作流单次生成多图。

#### 2.2 前端 — 多角度切换 UI

更新 `preview.tsx` 结果显示区域：

```
┌──────────────────────────────┐
│                              │
│        [ 大图显示区域 ]       │
│                              │
│  ○ 正面  ○ 左侧  ● 右侧  ○ 后 │  ← 角度缩略图切换栏
│                              │
│  [ 参数调整 ] [ 保存/分享 ]    │
└──────────────────────────────┘
```

- 新建 `mobile/components/AngleSelector.tsx`
- 底部 4 个圆形缩略图按钮
- 大图使用 `expo-image` 切换 `source={{ uri: images[angle].url }}`

#### 2.3 更新 types.ts

```typescript
export interface MultiAngleResult {
  images: {
    front: { url: string; id: string };
    left: { url: string; id: string };
    right: { url: string; id: string };
    back: { url: string; id: string };
  };
}
```

---

## 三、原图对比

### 目标
在效果结果页，用户可以通过滑动条或点击切换"原图 vs 效果图"，直观对比。

### 实现思路
纯前端实现，不需要后端改动。

#### 3.1 新建 `mobile/components/BeforeAfterSlider.tsx`

使用左右并排或滑动遮罩实现：

```
┌──────────────────────────────┐
│  ┌──────┬───────┐            │
│  │ 原图  │ 效果图 │            │
│  └──────┴───────┘            │
│       ◀─── ● ───▶            │  ← 滑动条
│    原照         生成效果       │
└──────────────────────────────┘
```

**实现方式**：

1. **并排对比**（简单）：左右两张图并排，带标签
2. **滑动遮罩对比**（更好）：使用 `react-native-gesture-handler` 的 PanResponder 做一个可拖动的分割线

对于 Expo Web + Native 兼容，采用 **方案 1（并排）** + 一个切换按钮"原图/效果图"模式。

#### 3.2 更新 preview.tsx

- `preview.tsx` 中保留 session photo 的 base64（已通过 `SessionContext` 持有）
- 在 ResultView 区域增加"原图对比"按钮
- 点击后进入对比模式，显示原照 vs 生成图

---

## 四、数据库层（SQLite）

### 目标
为登录、点数、支付功能引入持久化存储。本地开发使用 SQLite，零配置。

### 实现思路

使用 `SQLAlchemy`（async）+ `aiosqlite`，与现有 FastAPI 架构一致，未来迁移到 PostgreSQL 只需改连接 URL。

#### 4.1 新增依赖

```txt
# backend/requirements.txt 追加
aiosqlite==0.20.0
sqlalchemy[asyncio]==2.0.35
alembic==1.13.0
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
```

#### 4.2 数据库配置

```python
# backend/app/database.py (new — replaces placeholder)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./hairstyle.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with async_session() as session:
        yield session
```

#### 4.3 数据模型

```python
# backend/app/models/user.py
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    phone = Column(String(11), unique=True, nullable=True)
    nickname = Column(String(64))
    avatar_url = Column(String(512))
    wechat_openid = Column(String(128), unique=True)
    alipay_user_id = Column(String(128), unique=True)
    points_balance = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# backend/app/models/order.py
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_no = Column(String(32), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)      # 实付金额（元）
    points = Column(Integer, nullable=False)     # 购买点数
    channel = Column(String(16))                # "wechat" / "alipay" / "mock"
    status = Column(String(16), default="pending")  # pending / paid / failed / refunded
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

# backend/app/models/points_ledger.py
class PointsLedger(Base):
    __tablename__ = "points_ledger"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)    # + 充值 / - 消费
    type = Column(String(16))                   # "recharge" / "generate" / "regenerate" / "bonus"
    balance_after = Column(Integer)
    created_at = Column(DateTime, default=func.now())
```

#### 4.4 初始化时机

在 `app/main.py` 的 `startup` 事件中调用 `init_db()`：

```python
@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("Database initialized (SQLite: hairstyle.db)")
```

> **未来迁移到 PostgreSQL**：只需改为 `postgresql+asyncpg://user:pass@host/dbname`，模型无需改动。

---

## 五、用户注册/登录

### 目标
支持手机号+短信验证码登录（本地开发用万能码），为点数/支付系统提供用户身份。

### 本地开发简化
- **不集成真实 SMS 服务**（阿里云 SMS 需要审核和多步配置）
- 本地使用 **万能验证码 `888888`**，任何手机号输入此码即可登录
- 同时保留 SMS 接口结构，后续接入阿里云 SMS 只需替换发送逻辑

### 实现步骤

#### 5.1 后端 — 用户路由

```python
# backend/app/routers/auth.py (new)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# POST /api/v1/auth/sms/send
# - 本地环境: 直接返回成功，控制台打印验证码
# - 生产环境: 调用阿里云 SMS

# POST /api/v1/auth/sms/login
# - 本地: 验证码为 888888 即通过
# - 生成 JWT token，返回 user_id + token + expires_in

# POST /api/v1/auth/wechat/login  (stub for now)
# - 本地环境返回 mock，保留接口结构

# POST /api/v1/auth/alipay/login  (stub for now)
# - 同上

# GET /api/v1/user/profile  (需鉴权)
# - 返回用户信息 + points_balance

# POST /api/v1/auth/register
# - 手机号 + 验证码注册
# - 新用户赠送 3 点
```

**JWT 配置**（开发用简单密钥）：

```python
# app/config.py 追加
JWT_SECRET_KEY = "hairstyle-dev-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24
```

**鉴权依赖**：

```python
# app/dependencies.py
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    # decode JWT → user_id → query user
    # raise 401 if invalid
```

#### 5.2 前端 — 登录页面

新建 `mobile/app/(auth)/login.tsx`：

```
┌──────────────────────────────┐
│                              │
│       发型试戴                │
│                              │
│  ┌──────────────────────┐   │
│  │ 手机号输入              │   │
│  └──────────────────────┘   │
│  ┌──────────────────────┐   │
│  │ 验证码 (888888)       │   │
│  └──────────────────────┘   │
│  ┌──────────────────────┐   │
│  │ 获取验证码            │   │
│  └──────────────────────┘   │
│                              │
│  ┌──────────────────────┐   │
│  │ 登录 / 注册           │   │
│  └──────────────────────┘   │
│                              │
│  --- 或 ---                  │
│  [ 微信登录 ] [ 支付宝登录 ]  │
│                              │
│  < 跳过，先浏览 >             │
└──────────────────────────────┘
```

**逻辑**：
- 免登录可浏览模板（当前行为保持不变）
- 点击"生成预览"时，如果未登录则引导登录
- 登录后 JWT 存储到 `AsyncStorage`，每次请求自动带 Token

**Token 管理**：

```typescript
// mobile/services/auth.ts (new)
import AsyncStorage from '@react-native-async-storage/async-storage';

const TOKEN_KEY = 'auth_token';

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY);
}
```

**API 拦截器**（更新 `api.ts`）：

```typescript
// Axios interceptor 自动带 Token
api.interceptors.request.use(async (config) => {
  const token = await getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

#### 5.3 更新导航流

- 新建 `mobile/app/(auth)/` 路由组
- 使用 Expo Router 的 `before` 或条件判断控制未登录用户的访问
- 简单方案：在 `_layout.tsx` 添加全局 `AuthContext`，未登录用户在生成页显示登录引导

---

## 六、点数订阅与支付

### 目标
用户购买点数套餐，每次生成消耗点数。本地开发使用 mock 支付（模拟支付成功回调）。

### 点数模型

| 套餐 | 点数 | 价格 (¥) |
|------|------|----------|
| 新用户赠送 | 3 | 免费 |
| 基础包 | 10 | 9.90 |
| 进阶包 | 30 | 19.90 |
| 畅享包 | 100 | 49.90 |

消费：1 次生成（或重新生成）= 1 点

### 实现步骤

#### 6.1 后端 — 支付路由

```python
# backend/app/routers/payment.py (new)
router = APIRouter(prefix="/api/v1/payment", tags=["payment"])

# 套餐列表 (硬编码或 config)
# GET /api/v1/payment/packages
PACKAGES = [
    {"id": "basic", "name": "基础包", "points": 10, "price": 9.90},
    {"id": "advanced", "name": "进阶包", "points": 30, "price": 19.90},
    {"id": "unlimited", "name": "畅享包", "points": 100, "price": 49.90},
]

# 创建订单
# POST /api/v1/payment/order
# - 需鉴权
# - 创建 order 记录，返回 order_no + 支付 URL/参数

# Mock 支付回调
# POST /api/v1/payment/mock/notify
# - 模拟支付成功，更新订单状态 + 增加用户点数
# - 本地测试可用

# 查询点数余额
# GET /api/v1/user/points/ledger
```

#### 6.2 后端 — 生成扣点中间件

在 `comfyui_generation.py` 的 `generate` 端点中增加鉴权+扣点：

```python
@router.post("/generate", response_model=GenerateResponse)
async def comfyui_generate(
    req: GenerateRequest,
    request: Request,
    user: User = Depends(get_current_user),  # 要求登录
):
    # 1. 检查点数余额
    if user.points_balance < 1:
        raise HTTPException(status_code=402, detail="点数不足，请充值")

    # 2. 扣点（先扣后生成，防止重复生成）
    user.points_balance -= 1
    # 记录流水
    await points_ledger_service.deduct(user.id, 1, "generate")
    await session.commit()

    # 3. 继续现有生成逻辑...
```

> **本地测试豁免**：可在 `.env` 设置 `SKIP_POINTS_CHECK=true` 跳过扣点验证，方便开发时反复测试。

#### 6.3 前端 — 充值页面

新建 `mobile/app/(tabs)/recharge.tsx`，或作为 Modal：

```
┌──────────────────────────────┐
│         购买点数               │
│                              │
│  当前余额: 12 点              │
│                              │
│  ┌────────────────────────┐  │
│  │ 基础包  10 点  ¥9.90   │  │
│  │                       │  │
│  ├────────────────────────┤  │
│  │ 进阶包  30 点  ¥19.90  │  │
│  │                       │  │
│  ├────────────────────────┤  │
│  │ 畅享包  100 点 ¥49.90  │  │
│  │                       │  │
│  └────────────────────────┘  │
│                              │
│  支付方式:                    │
│  [ 微信支付 ]  [ 支付宝 ]     │
│                              │
│  (本地: Mock 支付 → 立即到账) │
└──────────────────────────────┘
```

- 选择套餐 → 选择支付方式 → 调用 `POST /api/v1/payment/order`
- Mock 支付：前端直接调用 `/mock/notify` 模拟支付成功
- 支付成功后更新本地点数余额

#### 6.4 前端 — 点数字段展示

在 `history.tsx`（"效果"页）顶部增加点数信息：

```
  ┌──────────────────────────┐
  │  💇 我的效果    余额: 12 ⚡│
  │                          │
  │  [ 购买点数 ]             │
  └──────────────────────────┘
```

---

## 七、实现路线图（建议顺序）

```
Phase 1: 数据库层 + 用户系统（基础）
  ├── SQLite 数据库初始化
  ├── User 模型 + auth 路由
  ├── JWT 鉴权中间件
  ├── 前端登录页
  └── 前端 API Token 管理

Phase 2: 发型参数调整（核心 AI 交互）
  ├── prompt_builder.py（参数→prompt 映射）
  ├── POST /api/comfyui/regenerate 端点
  ├── ParamPanel 前端组件
  └── preview.tsx 整合参数面板

Phase 3: 多角度切换（并行）
  ├── POST /api/comfyui/generate-multi 端点
  ├── AngleSelector 前端组件
  └── 多图生成结果管理

Phase 4: 点数与支付
  ├── 点数模型 + payment 路由
  ├── 生成扣点逻辑
  ├── Mock 支付回调
  └── 充值页面

Phase 5: 原图对比（纯前端，独立）
  └── BeforeAfterSlider 组件

Phase 6: 集成联调 + 优化
  ├── 全流程走通（登录→选模板→点生成→参数调整→多角度→对比）
  ├── 错误处理 + loading 状态完善
  └── SQLite 数据验证
```

---

## 文件变更清单

### 后端新增文件

| 文件 | 用途 |
|------|------|
| `app/database.py` | SQLAlchemy async engine + session |
| `app/dependencies.py` | 公共依赖注入（get_db, get_current_user） |
| `app/models/user.py` | User ORM 模型 |
| `app/models/order.py` | Order ORM 模型 |
| `app/models/points_ledger.py` | PointsLedger ORM 模型 |
| `app/models/__init__.py` | 模型聚合，方便 init_db 导入 |
| `app/routers/auth.py` | 认证路由（SMS 登录/JWT 签发） |
| `app/routers/payment.py` | 支付路由（套餐/下单/回调/点数） |
| `app/services/prompt_builder.py` | 参数→prompt 映射逻辑 |
| `app/services/auth_service.py` | 验证码/JWT/密码等逻辑 |
| `app/services/points_service.py` | 点数加减/流水查询 |

### 后端修改文件

| 文件 | 改动 |
|------|------|
| `app/main.py` | 注册新 router，添加 startup 事件 init_db |
| `app/config.py` | 追加 JWT_SECRET、SKIP_POINTS_CHECK 等配置 |
| `app/models/schemas.py` | 追加 RegenerateRequest（已有）、MultiAngleResponse 等 |
| `app/routers/comfyui_generation.py` | 追加 regenerate 端点 + generate-multi 端点 |
| `requirements.txt` | 追加 aiosqlite, sqlalchemy, passlib, python-jose, alembic |

### 前端新增文件

| 文件 | 用途 |
|------|------|
| `app/(auth)/login.tsx` | 登录页 |
| `components/ParamPanel.tsx` | 发型参数调整面板 |
| `components/AngleSelector.tsx` | 多角度切换栏 |
| `components/BeforeAfterSlider.tsx` | 原图对比组件 |
| `services/auth.ts` | Token 管理 + 登录 API |
| `services/payment.ts` | 支付 API |

### 前端修改文件

| 文件 | 改动 |
|------|------|
| `app/preview.tsx` | 集成 ParamPanel + AngleSelector + BeforeAfterSlider |
| `app/(tabs)/history.tsx` | 显示点数余额 + 跳转充值入口 |
| `services/api.ts` | 追加 JWT 拦截器 |
| `services/generation.ts` | 追加 regenerateHairstyle 函数 |
| `types.ts` | 追加 MultiAngleResult 等类型 |
| `constants/theme.ts` | 追加支付相关颜色 token（可选） |

---

## 数据库迁移策略

由于使用 SQLAlchemy ORM + `Base.metadata.create_all()`，开发阶段采用 **自动建表** 而非 Alembic 迁移：

1. 模型定义好后，`init_db()` 自动创建/更新表
2. 模型变更时，手动删除 `hairstyle.db` 重建（开发阶段数据不重要）
3. 上生产（PostgreSQL）时引入 Alembic 管理迁移

```bash
# 重建数据库
rm backend/hairstyle.db
# 重启后端即可自动创建
```

---

## 本地快速测试指南

```bash
# 1. 安装新依赖
cd backend
pip install aiosqlite sqlalchemy passlib python-jose python-multipart

# 2. 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 测试登录（万能验证码）
curl -X POST http://localhost:8000/api/v1/auth/sms/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000"}'
# → 控制台打印验证码，本地可用 888888

curl -X POST http://localhost:8000/api/v1/auth/sms/login \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000", "code": "888888"}'
# → 返回 JWT token

# 4. 查询套餐
curl http://localhost:8000/api/v1/payment/packages

# 5. 启动前端
cd mobile
npx expo start --web
```

---

## 附录：ComfyUI 参数调优策略

### 不同参数的效果预期

| 参数 | 调整范围 | 默认值 | 效果影响 |
|------|---------|--------|---------|
| `steps` | 20-40 | 25 | 步数越高细节越多，但耗时线性增加 |
| `cfg` | 4.0-9.0 | 6.5 | 越高越贴近 prompt，但可能过饱和 |
| `denoise` | 0.6-1.0 | 0.85 | 越低越保留原始人像结构，但发型变化小 |
| `seed` | 任意 | random | 固定 seed 可复现结果，调参时建议固定 |

### 调参建议

- **发长调整**：主要靠 prompt 措辞 + `denoise` 间接控制（denoise 越低，原发型保留越多）
- **发色调整**：PhotoMaker 对发色控制较弱，需要在 prompt 中强调颜色词
- **卷曲调整**：通过 `wavy`/`curly`/`straight` prompt 词控制，可配合 `cfg` 增大 prompt 权重
