# P2 实现计划 — 面部推荐 + 多级会员

> **日期**: 2026-07-17
> **状态**: Plan
> **前置**: P1 全部完成（数据库、Auth、ComfyUI 生成）

---

## 总览

| 功能 | 涉及端 | 数据库 | 前置依赖 | 预估工时 |
|------|--------|--------|----------|---------|
| 面部推荐 | 后端 (MediaPipe Face Mesh) + 前端 | 模板 tags 增强 | P1 人脸检测 | 4-6h |
| 多级会员 | 后端 (User model) + 前端 | User 表扩充 | P1 登录/点数 | 3-4h |

---

## 一、面部推荐（Face Shape Hairstyle Recommendation）

### 目标

用户上传照片后，自动检测脸型（椭圆/圆/方/心形/菱形/长脸），推荐最匹配的发型模板。在捕获页和模板列表页展示推荐结果。

### 1.1 脸型检测算法

使用 MediaPipe **Face Mesh**（非当前 `mp.solutions.face_detection`），获取 468 个面部关键点，提取以下测量值：

```
测量维度:
- 脸宽 (FW): 左右颧骨点距离 (landmark #234 → #454)
- 下颌宽 (JW): 左右下颌角距离 (landmark #58 → #288)
- 脸长 (FL): 额头中心到下巴尖距离 (landmark #10 → #152)
- 额头宽 (TW): 左右太阳穴点距离 (landmark #162 → #389)

比例:
- FW/FL ratio → 判断长脸 vs 短脸
- JW/FW ratio → 判断方脸 vs 尖脸
- TW/JW ratio → 判断心形脸 vs 菱形脸
```

**脸型分类阈值（初始值，可根据实测调整）**：

| 脸型 | 判定条件 |
|------|---------|
| 椭圆脸 (Oval) | FW/FL ≈ 0.85-0.95, JW/FW < 0.92 |
| 圆脸 (Round) | FW/FL ≥ 0.95, JW/FW ≥ 0.92 |
| 方脸 (Square) | JW/FW ≥ 0.95, FW/FL 0.85-0.95 |
| 心形脸 (Heart) | TW/JW ≥ 1.15, FW/FL ≤ 0.90 |
| 菱形脸 (Diamond) | TW/JW ≤ 1.05, FW/FL < 0.90 |
| 长脸 (Long) | FW/FL ≤ 0.80 |

### 1.2 后端实现

#### 新增文件: `app/services/face_shape.py`

```python
class FaceShapeDetector:
    """Analyze face shape using MediaPipe Face Mesh landmarks."""

    SHAPE_LANDMARKS = {
        "forehead_center": 10,
        "chin": 152,
        "left_jaw": 58,
        "right_jaw": 288,
        "left_cheek": 234,
        "right_cheek": 454,
        "left_temple": 162,
        "right_temple": 389,
    }

    def __init__(self):
        self._face_mesh = None

    @property
    def face_mesh(self):
        if self._face_mesh is None:
            import mediapipe as mp
            self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                min_detection_confidence=0.5,
            )
        return self._face_mesh

    async def detect_shape(self, photo_base64: str) -> dict:
        """Return face shape classification + confidence."""
        # decode → process → extract landmarks → compute ratios → classify
        ...

    def _classify(self, ratios: dict) -> str:
        """Map ratios to face shape label."""
        ...
```

**输出格式**:
```json
{
    "face_shape": "oval",
    "confidence": 0.85,
    "ratios": {"fw_fl": 0.90, "jw_fw": 0.88, "tw_jw": 1.10},
    "shape_label": "椭圆脸"
}
```

#### 新增端点: `GET /api/recommend/by-shape`

或作为 `POST /api/recommend/by-photo`，接收照片 → 检测脸型 → 返回推荐的模板列表。

```python
@router.post("/by-photo")
async def recommend_by_photo(req: RecommendByPhotoRequest):
    # 1. Detect face shape
    shape_result = await face_shape_detector.detect_shape(req.photo_base64)
    # 2. Match against template face_shape tags
    templates = _load_comfyui_templates()
    scored = []
    for t in templates:
        compatible = t.get("face_shapes", [])
        score = 1.0 if shape_result["face_shape"] in compatible else 0.3
        scored.append({**t, "match_score": score})
    # 3. Sort by score, return top N
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return {"face_shape": shape_result, "recommendations": scored[:6]}
```

#### 修改: `backend/data/templates_comfyui.json`

为每个模板添加 `face_shapes` 字段，列出适合的脸型：

```json
{
  "id": "m1",
  "name": "清爽短发",
  "face_shapes": ["oval", "square", "heart"],
  ...
}
```

**15 个模板的脸型匹配表（初始版）**：

| 模板 | 适合脸型 |
|------|---------|
| m1 清爽短发 | oval, square |
| m2 纹理碎发 | oval, round, diamond |
| m3 韩式微分 | oval, heart, diamond |
| m4 美式寸头 | oval, square, long |
| m5 侧分油头 | oval, square, heart |
| m6 蓬松中分 | oval, round, diamond |
| m7 飞机头 | oval, square |
| w1 法式大波浪 | oval, heart, round |
| w2 锁骨发 | oval, square, heart |
| w3 长直发 | oval, long, diamond |
| w4 公主切 | oval, heart, diamond |
| w5 大波浪卷 | oval, round, heart |
| w6 羊毛卷 | oval, round, diamond |
| w7 韩系短发 | oval, heart, square |
| w8 丸子头 | oval, round, heart |

#### 修改: `backend/app/routers/templates.py`

返回模板列表时附带 face_shapes 字段（已包含，但需确认 `TemplateOut` schema）。

### 1.3 前端实现

#### 新增: `services/recommendation.ts`

```typescript
export async function recommendByPhoto(photoBase64: string): Promise<{
  face_shape: { face_shape: string; shape_label: string; confidence: number };
  recommendations: Template[];
}> {
  const res = await api.post('/api/recommend/by-photo', { photo_base64 });
  return res.data;
}
```

#### 修改: `mobile/app/capture.tsx`

照片上传／拍摄完成后，增加：

1. 自动请求 `/api/recommend/by-photo`
2. 显示 "已检测到你的脸型: **椭圆脸**"
3. 显示 2-4 个 "为你推荐" 的发型卡片
4. 点击直接进入该模板的生成流程

```
┌──────────────────────────────┐
│                              │
│        [ 照片预览 ]           │
│                              │
│  🔍 检测到脸型: 椭圆脸        │
│                              │
│  ┌─为你推荐───────────────┐   │
│  │ ┌────┐┌────┐┌────┐    │   │
│  │ │ 发1 ││ 发2 ││ 发3 │    │   │
│  │ └────┘└────┘└────┘    │   │
│  └───────────────────────┘   │
│                              │
│  [ 更多发型 ↗ ]              │
│                              │
│  [  使用此照片生成  ]         │
└──────────────────────────────┘
```

### 1.4 模板 Schema 更新

`backend/app/models/schemas.py` → `TemplateOut` 追加 `face_shapes` 字段：
```python
class TemplateOut(BaseModel):
    id: str
    name: str
    category: str
    tags: list[str]
    style_id: str = ""
    thumbnail: str
    description: str
    face_shapes: list[str] = []  # NEW
```

`mobile/types.ts` → `Template` 接口追加：
```typescript
export interface Template {
  // ... existing fields
  face_shapes?: string[];
}
```

---

## 二、多级会员系统（Membership Tiers）

### 目标

Free / Pro / Premium 三级会员体系，不同等级享有不同点数上限、每日生成次数、折扣等权益。

### 2.1 会员等级定义

| 等级 | 月费 | 点数上限 | 每日免费生成 | 点数单价折扣 | 权益标识色 |
|------|------|---------|------------|------------|----------|
| Free | ¥0 | 50 | 2 次/天 | — | 灰 |
| Pro | ¥19.90 | 200 | 10 次/天 | 9折 | 蓝 |
| Premium | ¥49.90 | 1000 | 不限 | 8折 | 金 |

### 2.2 后端实现

#### 修改: `backend/app/models/user.py`

追加字段：
```python
class User(Base):
    ...
    membership_tier: Mapped[str] = mapped_column(
        String(16), default="free"
    )  # free / pro / premium
    membership_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    daily_generations: Mapped[int] = mapped_column(Integer, default=0)
    daily_generations_date: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default=None
    )  # "2026-07-17"
```

#### 新增: `backend/app/services/membership_service.py`

```python
class MembershipService:
    """Membership tier enforcement and benefits."""

    TIERS = {
        "free": {
            "label": "免费用户",
            "max_points": 50,
            "daily_free": 2,
            "price_discount": 1.0,  # no discount
        },
        "pro": {
            "label": "Pro 会员",
            "max_points": 200,
            "daily_free": 10,
            "price_discount": 0.9,
        },
        "premium": {
            "label": "Premium 会员",
            "max_points": 1000,
            "daily_free": 999,  # unlimited
            "price_discount": 0.8,
        },
    }

    async def check_generation_quota(self, user: User) -> bool:
        """Check if user can generate today."""
        today = date.today().isoformat()
        tier_config = self.TIERS[user.membership_tier]
        if user.daily_generations_date != today:
            user.daily_generations = 0  # reset for new day
        return user.daily_generations < tier_config["daily_free"]

    async def record_generation(self, session: AsyncSession, user: User):
        """Increment daily generation count."""
        today = date.today().isoformat()
        if user.daily_generations_date != today:
            user.daily_generations_date = today
            user.daily_generations = 0
        user.daily_generations += 1
        await session.commit()

    def get_discounted_price(self, tier: str, original_price: float) -> float:
        discount = self.TIERS.get(tier, self.TIERS["free"])["price_discount"]
        return round(original_price * discount, 2)
```

#### 新增: `backend/app/routers/membership.py`

```python
router = APIRouter(prefix="/api/v1/membership", tags=["membership"])

# GET /api/v1/membership/tiers  — 查看所有等级及权益
# POST /api/v1/membership/upgrade  — 升级会员（mock 支付，类似 payment mock）
# GET /api/v1/membership/my-status  — 查看自己的会员状态
```

**端点详情**:

```
GET /api/v1/membership/tiers
Response:
{
  "tiers": [
    {"id": "free", "label": "免费用户", "max_points": 50, "daily_free": 2},
    {"id": "pro", "label": "Pro 会员", "max_points": 200, "daily_free": 10, "price": 19.90},
    {"id": "premium", "label": "Premium 会员", "max_points": 1000, "daily_free": -1, "price": 49.90},
  ]
}

POST /api/v1/membership/upgrade  (需鉴权)
Body: {"tier": "pro", "channel": "mock"}
Response: {"tier": "pro", "status": "active", "expires_at": "2026-08-17T..."}

GET /api/v1/membership/my-status  (需鉴权)
Response: {"tier": "free", "expires_at": null, "daily_left": 2, "points_balance": 3, "max_points": 50}
```

#### 修改: `backend/app/main.py`

注册新路由：
```python
from app.routers import membership
app.include_router(membership.router)
```

#### 修改: `backend/app/routers/comfyui_generation.py`

在 generate/regenerate/generate-multi 端点中增加会员权益检查（如果 `skip_points_check` 未开启）：

```python
# 在生成前检查
if not settings.skip_points_check:
    quota_ok = await membership_service.check_generation_quota(user)
    if not quota_ok:
        raise HTTPException(status_code=403, detail="已达每日生成上限，升级会员可增加次数")
    await membership_service.record_generation(session, user)
```

### 2.3 前端实现

#### 新增: `services/membership.ts`

```typescript
export async function fetchTiers(): Promise<TierInfo[]>
export async function upgradeMembership(tier: string, channel: string): Promise<UpgradeResult>
export async function fetchMembershipStatus(): Promise<MembershipStatus>
```

#### 新增: `mobile/app/membership.tsx`

会员中心页面：

```
┌──────────────────────────────┐
│        会员中心               │
│                              │
│  当前: 免费用户               │
│  点数: 3/50                  │
│  今日剩余: 2/2 次            │
│                              │
│  ┌────────────────────────┐  │
│  │  Pro · ¥19.90/月       │  │
│  │  200点上限 · 日10次 · 9折│  │
│  │  [ 升级 ]               │  │
│  ├────────────────────────┤  │
│  │  Premium · ¥49.90/月   │  │
│  │  1000点 · 不限 · 8折   │  │
│  │  [ 升级 ]               │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

#### 修改: 点数相关 UI

- `recharge.tsx`: 根据会员等级显示折扣后价格
- `history.tsx` / `_layout.tsx`: 显示会员徽章
- `preview.tsx`: 生成前检查配额并提示

---

## 三、文件变更清单

### 新增文件

| 文件 | 归属 |
|------|------|
| `backend/app/services/face_shape.py` | 面部推荐 |
| `backend/app/routers/recommend.py` | 面部推荐 |
| `backend/app/services/membership_service.py` | 会员 |
| `backend/app/routers/membership.py` | 会员 |
| `mobile/services/recommendation.ts` | 面部推荐 |
| `mobile/services/membership.ts` | 会员 |
| `mobile/app/membership.tsx` | 会员 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `backend/app/models/user.py` | 追加 membership_tier, membership_expires_at, daily_generations, daily_generations_date |
| `backend/app/models/schemas.py` | TemplateOut 追加 face_shapes, 新增会员相关 schema |
| `backend/data/templates_comfyui.json` | 每个模板追加 face_shapes 字段 |
| `backend/app/main.py` | 注册 recommend + membership 路由 |
| `backend/app/routers/templates.py` | 返回 face_shapes 字段 |
| `backend/app/routers/comfyui_generation.py` | 插入会员检查 |
| `mobile/app/capture.tsx` | 集成面部推荐 UI |
| `mobile/app/(tabs)/index.tsx` | 可能显示推荐标签 |
| `mobile/app/recharge.tsx` | 显示会员折扣价 |
| `mobile/app/(tabs)/history.tsx` | 显示会员徽章 |
| `mobile/app/_layout.tsx` | 注册 membership 路由 |
| `mobile/types.ts` | 追加会员相关类型 |
| `mobile/constants/theme.ts` | 追加会员等级色 (pro/premium) |

---

## 四、实现顺序

```
Phase 1: 面部推荐（数据准备）
  1.1 给 15 个模板打脸型标签（face_shapes）
  1.2 Template schema 更新 + 返回 face_shapes

Phase 2: 面部推荐（算法）
  2.1 FaceMesh 集成 + 脸型检测算法
  2.2 /api/recommend/by-photo 端点
  2.3 capture.tsx 推荐 UI

Phase 3: 会员（后端）
  3.1 User model 追加字段
  3.2 membership_service.py
  3.3 memberships 路由
  3.4 生成端点的检查集成

Phase 4: 会员（前端）
  4.1 membership.ts 服务
  4.2 membership.tsx 页面
  4.3 各页面的会员信息展示
```

---

## 五、关键决策记录

| 决策 | 选项 | 选择 |
|------|------|------|
| 脸型检测方案 | Face Mesh vs OpenCV dlib vs 第三方API | **Face Mesh**（复用 MediaPipe 依赖，无新增外部依赖） |
| 推荐时机 | 上传照片后自动 vs 手动点击 | **自动检测 + 显示推荐**（无感体验） |
| 会员有效期 | 永不过期 vs 30天 vs 自然月 | **30天**（从支付日起算，简单明确） |
| 配额重置 | 自然日 vs 滚动24h | **自然日**（reset 逻辑简单，用户体验好理解） |
