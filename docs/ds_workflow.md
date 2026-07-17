# DeepSeek Multi-Agent 并发开发工作流

> **目的**: 防止多 Agent（DeepSeek 内部 sub-agent + OpenCode + Cursor + Claude Code 等外部工具）并发开发时的文件冲突。  
> **关联规划文档**: [ds_spec.md](./ds_spec.md) | [ds_plan.md](./ds_plan.md)  
> **适用环境**: macOS 本地开发 + 阿里云 Ubuntu 部署

---

## 1. 文件所有权约定

### 1.1 前缀命名规范

| 来源 | 前缀 | 示例 | 说明 |
|------|------|------|------|
| DeepSeek (本工具) | `ds_` | `ds_spec.md`, `ds_plan.md` | 规划文档、架构决策、workflow 文件 |
| OpenCode | `oc_` | `oc_auth_service.py` | 按服务/模块拆分 |
| Cursor | `cursor_` | — | 由其用户自行约定 |
| Claude Code | `claude_` | — | 由其用户自行约定 |
| 共享文件 | 无前缀 | `docker-compose.yml`, `main.py` | 所有工具共享，修改前检查 [OWNERS](#2-文件所有权注册表-ownersmd) |

### 1.2 目录级隔离（推荐策略）

更好的做法是每个工具/Agent 只写自己的目录，共享区通过 PR/MR 合入：

```
hairstyle/
├── backend/                 # 共享区 — 最终产出
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── services/
│   │   └── tasks/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── mobile/                  # 共享区 — 最终产出
│   └── (React Native 项目)
├── docs/                    # 共享区
│   ├── ds_spec.md
│   ├── ds_plan.md
│   ├── ds_workflow.md       # 本文件
│   └── OWNERS.md            # 文件所有权注册表
└── .gitignore
```

所有开发直接在 `backend/`、`mobile/`、`docs/` 目录进行，通过 Git 分支隔离。

---

## 2. 文件所有权注册表 (OWNERS.md)

每次开始在一个文件上工作时，Agent 必须先在 `docs/OWNERS.md` 注册所有权。注册表格式：

```markdown
# 文件所有权注册表

| 文件路径 | 当前 Owner | 工具 | 状态 | 开始时间 | 预计完成 |
|----------|-----------|------|------|----------|----------|
| backend/app/routers/auth.py | deepseek-agent-3 | DeepSeek | in_progress | 2026-07-15 14:00 | 2026-07-15 16:00 |
| backend/app/services/payment_service.py | opencode | OpenCode | pending | — | — |
| mobile/screens/Home.tsx | cursor | Cursor | completed | 2026-07-15 10:00 | — |
```

**规则**:
- 写入前必须注册；读取无需注册
- 状态: `pending` → `in_progress` → `completed`
- 超过预计完成时间 30 分钟未更新 → 视为超时，其他 Agent 可抢占
- `completed` 的文件在 5 分钟后释放所有权

---

## 3. Git 分支策略

```
main
├── ds/phase-1-infra          # DeepSeek: 基础设施
├── ds/phase-2-backend        # DeepSeek: 后端核心
├── ds/phase-3-ai-pipeline     # DeepSeek: AI 管线
├── ds/phase-4-mobile          # DeepSeek: 移动端
├── oc/auth-service            # OpenCode: 认证服务
├── cursor/home-screen         # Cursor: 首页 UI
└── claude/payment-integration # Claude Code: 支付集成
```

**合入规则**:
- 每个工具的每个 Agent 使用独立分支
- 分支命名: `<tool>/<task-slug>`
- 完成 → 推送到远程 → 创建 PR → 人工 review → 合并到 `main`
- 合并后立即删除分支
- 合入前必须确认 `OWNERS.md` 中涉及的文件已释放

**最低要求**（如果团队很小不用 PR 流程）:
- 推送前 `git pull --rebase origin main`
- 提交信息中包含工具和任务标识: `[ds][auth] implement sms login endpoint`

---

## 4. API 契约优先 (Contract-First)

这是防止后端/前端 Agent 各自为战的关键策略。

**流程**:
1. 先定义 OpenAPI 3.0 规范文件: `docs/openapi.yaml`
2. 提交到 `main` 分支并 lock（标记为 `CONTRACT_LOCKED`）
3. 后端 Agent 按契约实现 API
4. 前端 Agent 按契约生成类型和调用代码
5. 修改契约需要在独立分支上进行，所有消费者 Agent 确认后才能合入

**OpenAPI 文件所有权**:
- `docs/openapi.yaml` 是共享文件
- 修改需要跨工具协商（在 OWNERS.md 中标注为 `needs_approval`）
- 建议由 DeepSeek 作为规划者维护初始版本

---

## 5. 数据库迁移串行化

多个 Agent 创建 Alembic 迁移文件会导致版本号冲突。

**规则**:
- 迁移文件编号严格串行 — 同一时刻只能有一个 Agent 创建迁移
- 需要新迁移时，在 `OWNERS.md` 申请 `alembic/versions/` 写入权
- 申请到写入权后，执行 `alembic revision --autogenerate -m "描述"`
- 完成后立即推送迁移文件，释放写入权
- 手动编号冲突时：保留先合入的，后合入的 rebase 后重新生成

**替代方案（推荐）**: 指定一个 Agent 或人负责所有迁移创建，其他 Agent 只编写 SQLAlchemy 模型，发 PR 请求迁移创建者生成迁移文件。

---

## 6. Docker Compose 共享

`docker-compose.yml` 是共享文件，冲突风险高。

**规则**:
- 初始版本由 DeepSeek 在 Phase 1 创建并提交
- 后续修改在 OWNERS.md 中申请
- 修改原则：只改自己负责的 service 定义
- 新 service 添加时放在文件末尾
- 端口映射冲突检测: 新增 service 前检查已占用端口

---

## 7. DeepSeek Sub-Agent 并发策略

### 7.1 并行批次规划（如果按 ds_plan.md 实施）

实施 ds_plan.md 时，我会如下分派 sub-agents：

**Batch 1 — Phase 1: 基础设施 (4 agents, 全并行)**
```
Agent 1: FastAPI 项目骨架 + config + database.py + dependencies.py
Agent 2: Dockerfile + docker-compose.yml + Nginx 配置
Agent 3: GitHub Actions CI/CD (.github/workflows/deploy.yml)
Agent 4: Alembic 配置 + 初始 migration
```

**Batch 2 — Phase 2/3: 后端 (5 agents, 全并行)**
```
Agent 1: Auth 模块 (routers/auth.py + services/auth_service.py + SMS/微信/支付宝)
Agent 2: User 模块 (routers/user.py + services/user_service.py + 点数逻辑)
Agent 3: Payment 模块 (routers/payment.py + services/payment_service.py + wechatpy/alipay)
Agent 4: Template 模块 (routers/template.py + services/template_service.py + OSS 导入)
Agent 5: AI Generation 模块 (routers/generation.py + tasks/ai_tasks.py + Celery 任务)
```

**Batch 3 — Phase 4: 移动端 (4 agents, 全并行)**
```
Agent 1: 认证页面 (登录/注册) + 微信/支付宝 SDK 集成
Agent 2: 首页模板库 + 分类/搜索
Agent 3: 相机/上传 + 生成结果页 + 4 角度预览
Agent 4: 参数编辑面板 + 我的/充值页面
```

**Batch 4 — 集成测试 (2 agents, 全并行)**
```
Agent 1: 后端 API 集成测试 (pytest)
Agent 2: 前端 E2E 测试
```

**总计: ~15 sub-agents, 4 批次**。每批次内全并行，批次间有依赖。

### 7.2 并发上限

DeepSeek sub-agent 默认上限 10 个并发（可在 `config.toml` 调整）。Batch 2 的 5 个 agents 和 Batch 3 的 4 个 agents 都在安全范围内。

### 7.3 Sub-Agent 间协调

DeepSeek 的 sub-agents 通过我（主 Agent）来协调。流程：

```
主 Agent 分解任务 → spawn 多个 sub-agent → 等待全部完成 →
逐个验证产出 → 合成到共享文件 → 更新 OWNERS.md → 提交
```

Sub-agent 通过主 Agent 中转写入共享区文件。

---

## 8. 与外部工具（OpenCode / Cursor / Claude Code）的协调

### 8.1 冲突检测机制

每个工具在开始工作前，执行：

```bash
# 1. 拉取最新
git pull origin main

# 2. 检查是否有冲突
grep "in_progress" docs/OWNERS.md

# 3. 检查目标文件是否被占用
grep "<target-file>" docs/OWNERS.md
```

### 8.2 通信协议

- **OWNERS.md** 是唯一真实来源（Single Source of Truth）
- 如果一个 Agent 需要等待另一个，在 OWNERS.md 中将状态设为 `blocked`，备注栏写清等待哪个文件/哪个 Agent
- 完成工作后立即更新 OWNERS.md 为 `completed`

### 8.3 合并冲突处理

当 `git merge` 产生冲突时：
1. 查看冲突文件的 OWNERS.md 记录，找到当前 owner
2. 如果是你自己 → 解决冲突
3. 如果是其他工具 → 联系其操作者（或等待其完成 `completed` 状态后自行解决）
4. 不确定时 → 保留双方改动，标记 `# CONFLICT_RESOLUTION_NEEDED`，提交后协商

---

## 9. .gitignore 建议

```gitignore
# Python
__pycache__/
*.pyc
.venv/
venv/

# React Native
mobile/node_modules/
mobile/.expo/
mobile/ios/Pods/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 环境变量
.env
.env.local

# Docker
*.log

# macOS
.DS_Store
```

---

## 10. 快速启动检查清单

一个新 Agent（无论来自哪个工具）开始工作前：

- [ ] `git pull origin main`
- [ ] 阅读 `docs/ds_spec.md` 了解整体架构
- [ ] 阅读 `docs/ds_plan.md` 了解当前阶段
- [ ] 检查 `docs/OWNERS.md` 确认目标文件未被占用
- [ ] 在 `docs/OWNERS.md` 注册你的工作
- [ ] 创建独立分支: `git checkout -b <tool>/<task>`
- [ ] 在独立分支上开发；合入时才写共享区
- [ ] 完成 → 更新 OWNERS.md → 推送分支 → 创建 PR

---

*本文件由 DeepSeek 创建并维护，随项目复杂度增长持续更新。*
