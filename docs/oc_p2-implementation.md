# P2 实现文档 — 脸型推荐 + 多级会员

> **日期**: 2026-07-17
> **状态**: 已实现，已验证
> **前置**: P1 全部完成（数据库、JWT 认证、ComfyUI 生成、点数系统）

---

## 功能总览

P2 在 P1 基础上新增两个核心功能：

| 功能 | 后端 | 前端 | 说明 |
|------|------|------|------|
| 脸型推荐 | MediaPipe Face Mesh 分类 + 推荐接口 | capture.tsx 推荐 UI（预留） | 上传照片后自动检测脸型并推荐匹配发型 |
| 多级会员 | User model 扩充 + 限额检查 | membership.tsx 会员页面 | Free / Pro / Premium 三级，每日限额、折扣 |

---

## 一、脸型推荐系统

### 1.1 脸型分类算法

**文件**: `backend/app/services/face_shape.py`

使用 MediaPipe **Face Mesh**（468 个关键点），提取以下测量维度：

| 测量 | 关键点 | 说明 |
|------|--------|------|
| 脸高 (FH) | 10 → 152 | 额头中心到下巴尖 |
| 脸宽 (FW) | 172 → 397 | 左右颧骨最外点 |
| 下颌宽 (JW) | 58 → 288 | 左右下颌角 |
| 额头宽 (HW) | 109 → 338 | 左右太阳穴 |

**分类逻辑**（基于比例阈值）：

| 脸型 | 判定条件 |
|------|---------|
| 椭圆脸 (Oval) | FH/FW ≈ 1.25–1.5, 整体均衡 |
| 圆脸 (Round) | FH/FW < 1.25, JW/FW < 0.88 |
| 方脸 (Square) | JW/FW > 0.88, FH/FW < 1.5 |
| 心形脸 (Heart) | 额头显著宽于下颌, FH/FW > 1.25 |
| 菱形脸 (Diamond) | 颧骨最宽, 额头和下颌收窄 |
| 长脸 (Long) | FH/FW > 1.5, 整体偏窄 |

**输出格式**:
```json
{
  "face_detected": true,
  "face_shape": "oval",
  "confidence": 0.7,
  "landmarks": {
    "face_height": 0.4321,
    "face_width": 0.3218,
    "aspect_ratio": 1.343,
    "jaw_to_cheek_ratio": 0.812,
    ...
  }
}
```

### 1.2 推荐接口

**端点**: `POST /api/recommend/by-photo`

**文件**: `backend/app/routers/face_recommend.py`

```
Request:  { photo_base64: string, category?: "men" | "women" }
Response: {
  face_shape: "oval",
  face_confidence: 0.7,
  templates: TemplateOut[],   // 匹配的模板列表
  total: 15
}
```

- 检测脸型 → 匹配模板的 `face_shapes` 字段 → 返回排序结果
- 未检测到人脸时返回全部模板作为 fallback

### 1.3 模板脸型标签

**文件**: `backend/data/templates_comfyui.json`

15 个模板均添加了 `face_shapes` 字段：

| 模板 | 适合脸型 |
|------|---------|
| m1 清爽短发 | oval, square |
| m2 纹理碎发 | oval, round |
| m3 韩式微分 | oval, round, diamond |
| m4 美式寸头 | oval, square |
| m5 复古油头 | oval, square, heart |
| m6 侧分纹理 | oval, round, long |
| m7 飞机头 | oval, round, square |
| w1 法式大波浪 | oval, round, heart |
| w2 及肩锁骨发 | oval, square, long |
| w3 蛋蛋卷 | oval, round, diamond |
| w4 公主切 | oval, heart, diamond |
| w5 黑长直 | oval, long, heart |
| w6 羊毛卷 | oval, round, diamond |
| w7 波波头 | oval, square, heart |
| w8 木马卷 | oval, round, heart |

---

## 二、多级会员系统

### 2.1 会员等级

| 等级 | 月费 | 点数上限 | 每日免费生成 | 点数折扣 | 标识色 |
|------|------|---------|------------|---------|-------|
| Free | ¥0 | 50 | 2 次/天 | — | 灰 `#6b7280` |
| Pro | ¥19.90 | 200 | 10 次/天 | 9折 | 蓝 `#2563eb` |
| Premium | ¥49.90 | 1000 | 不限 | 8折 | 金 `#d97706` |

### 2.2 后端实现

#### User 模型扩充

**文件**: `backend/app/models/user.py`

新增字段：
| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `membership_tier` | String(16) | `"free"` | free / pro / premium |
| `membership_expires_at` | DateTime | None | 到期时间（upgrade 后 30 天） |
| `daily_generations` | Integer | 0 | 当日已生成次数 |
| `daily_generations_date` | String(10) | None | 重置日期 (YYYY-MM-DD) |

#### 会员服务

**文件**: `backend/app/services/membership_service.py`

```python
class MembershipService:
    async def check_generation_quota(user) -> bool   # 检查每日限额
    async def record_generation(session, user)         # 记录生成次数
    def get_discounted_price(tier, price) -> float     # 计算折扣价
    def tier_daily_left(user) -> int                   # 当日剩余次数
    def get_all_tiers() -> list[dict]                  # 所有等级信息
```

#### 会员接口

**文件**: `backend/app/routers/membership.py`

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/v1/membership/tiers` | ❌ | 查看所有等级及权益 |
| POST | `/api/v1/membership/upgrade` | ✅ | 升级会员（mock 支付） |
| GET | `/api/v1/membership/my-status` | ✅ | 查看自己的会员状态 |

**upgrade 端点**:
```json
POST /api/v1/membership/upgrade
Body: { "tier": "pro", "channel": "mock" }
Response: { "tier": "pro", "status": "active", "expires_at": "2026-08-16T22:14:23+00:00" }
```

**my-status 端点**:
```json
GET /api/v1/membership/my-status
Response: {
  "tier": "pro",
  "label": "Pro 会员",
  "expires_at": "2026-08-16T22:14:23",
  "daily_left": 10,
  "points_balance": 3,
  "max_points": 200
}
```

### 2.3 生成限额检查

**文件**: `backend/app/routers/comfyui_generation.py`

三个生成端点（`/generate`, `/regenerate`, `/generate-multi`）均加入了会员限额检查：

```python
if not settings.skip_points_check and user is not None:
    quota_ok = await membership_service.check_generation_quota(user)
    if not quota_ok:
        raise HTTPException(403, detail="已达每日生成上限，升级会员可增加次数")
    # ... 生成成功后 ...
    await membership_service.record_generation(session, user)
```

- `settings.skip_points_check = True`（开发模式跳过检查）
- 生产环境设为 `False` 后开启限额

### 2.4 前端实现

#### 会员 API 服务

**文件**: `mobile/services/membership.ts`

```typescript
export async function fetchTiers(): Promise<TierInfo[]>
export async function fetchMembershipStatus(): Promise<MembershipStatus>
export async function upgradeMembership(tier: string, channel?: string): Promise<UpgradeResult>
```

#### 会员页面

**文件**: `mobile/app/membership.tsx`

路由: `router.push('/membership')`（Modal 形式）

页面结构：
```
┌──────────────────────────────┐
│        会员中心               │
│                              │
│  ┌────────────────────────┐  │
│  │   [FREE/PRO/PREMIUM]   │  │
│  │   当前: Pro 会员         │  │
│  │   点数: 3/200           │  │
│  │   今日剩余: 10 次        │  │
│  └────────────────────────┘  │
│                              │
│  选择会员方案                 │
│  ┌────────────────────────┐  │
│  │  Free · 免费            │  │
│  │  50点·日2次             │  │
│  │  [当前方案]              │  │
│  ├────────────────────────┤  │
│  │  Pro · ¥19.90/月        │  │
│  │  200点·日10次·9折       │  │
│  │  [升级]                  │  │
│  ├────────────────────────┤  │
│  │  Premium · ¥49.90/月   │  │
│  │  1000点·不限·8折        │  │
│  │  [升级]                  │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

#### 集成点

| 页面 | 改动 | 文件 |
|------|------|------|
| 效果页工具栏 | 添加「会员」按钮 | `mobile/app/(tabs)/history.tsx` |
| 路由注册 | membership 作为 Modal | `mobile/app/_layout.tsx` |

---

## 三、文件变更清单

### 新增文件

| 文件 | 功能 |
|------|------|
| `backend/app/services/face_shape.py` | 脸型检测算法（Face Mesh） |
| `backend/app/routers/face_recommend.py` | 脸型推荐接口 |
| `backend/app/services/membership_service.py` | 会员服务（限额/折扣） |
| `backend/app/routers/membership.py` | 会员 CRUD 接口 |
| `mobile/services/membership.ts` | 前端会员 API 服务 |
| `mobile/app/membership.tsx` | 会员中心页面 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `backend/data/templates_comfyui.json` | 15 个模板追加 `face_shapes` 字段 |
| `backend/app/models/schemas.py` | `TemplateOut` 追加 `face_shapes` |
| `backend/app/models/user.py` | 追加会员字段（tier/expires/daily） |
| `backend/app/routers/comfyui_generation.py` | 生成端点加入限额检查 |
| `backend/app/main.py` | 注册 face_recommend + membership 路由 |
| `mobile/types.ts` | `Template` 接口追加 `face_shapes?` |
| `mobile/constants/theme.ts` | 追加会员等级颜色 token |
| `mobile/app/_layout.tsx` | 注册 membership 路由 |
| `mobile/app/(tabs)/history.tsx` | 添加会员入口 |

---

## 四、已知问题

### 生成效果不理想（用户照片不保留）

PhotoMaker v1 + SD1.5 的身份保持能力有限。原因是：

- 工作流从 **EmptyLatentImage**（纯噪声）开始，本质是 txt2img
- PhotoMakerEncode 的身份特征较弱，易被底模风格覆盖
- `photon_v1.safetensors` 不是为身份保持优化的模型

**后续方向**：
- **近期**：换用更真实的 SD1.5 模型（如 `realisticVisionV51`）
- **中期**：迁移到 ACE++（FLUX-based，身份保持显著更好）
- **远期**：HairPort（SIGGRAPH 2026，3D 感知发型迁移，效果最佳）

详见 `docs/workflow-upgrade.md`（待创建）。

---

## 五、验证结果

| 接口 | 结果 |
|------|------|
| `GET /api/templates` → face_shapes | ✅ 15 个模板均返回 |
| `POST /api/recommend/by-photo` | ✅ 返回脸型 + 匹配模板 |
| `GET /api/v1/membership/tiers` | ✅ 3 个等级信息正确 |
| `POST /api/v1/membership/upgrade` | ✅ Mock 升级（30天有效期） |
| `GET /api/v1/membership/my-status` | ✅ 含 tier/label/expires/daily_left/points |
| TypeScript 编译 | ✅ `tsc --noEmit` 无错误 |
