# AGENTS.md

## 规范类

- 始终使用简体中文回复。
- 修改代码前先阅读相关文件，遵循现有项目结构和风格。
- 不要删除或回滚用户未提交的文件、文档、数据和本地配置。
- 不要把业务流程、页面规划、重构方案写进本文件；业务方案应写入 `docs/`。
- 手工编辑文件优先使用补丁方式，避免无关格式化和大范围重排。

### 提交规范

使用 Conventional Commits：

- `feat:` 新功能
- `fix:` Bug 修复
- `refactor:` 重构
- `test:` 测试
- `docs:` 文档
- `chore:` 工具链 / 构建

示例：

```text
feat: add brand run scheduler
fix: handle perplexity timeout gracefully
refactor: extract report summary formatter
```

### 编码前思考

不要假设。不要隐藏困惑。呈现权衡。

- 明确说明假设：如果不确定，询问而不是猜测。
- 呈现多种解释：当存在歧义时，不要默默选择。
- 适时提出异议：如果存在更简单的方法，说出来。
- 困惑时停下来：指出不清楚的地方并要求澄清。

### 简洁优先

用最少的代码解决问题。不要过度推测。

- 不要添加要求之外的功能。
- 不要为一次性代码创建抽象。
- 不要添加未要求的“灵活性”或“可配置性”。
- 不要为不可能发生的场景做错误处理。
- 如果 200 行代码可以写成 50 行，重写它。

检验标准：资深工程师会觉得这过于复杂吗？如果是，简化。

### 精准修改

只碰必须碰的。只清理自己造成的混乱。

- 不要“改进”相邻的代码、注释或格式。
- 不要重构没坏的东西。
- 匹配现有风格，即使你更倾向于不同的写法。
- 如果注意到无关的死代码，提一下，不要删除它。
- 删除因你的改动而变得无用的导入、变量、函数。
- 不要删除预先存在的死代码，除非被要求。

检验标准：每一行修改都应该能直接追溯到用户的请求。

### 数据表格规范

面向用户的数据表格必须优先让人看懂和追溯，不直接暴露原始 JSON 作为主要内容。

- 表格应提供必要的过滤、分类、筛选和排序能力。
- 表格默认应支持可分类、可排序、可过滤、可筛选；如果某项暂时无法实现，需要在页面或方案中说明原因。
- 运行记录、明细记录、效果矩阵类表格必须展示用户能理解的数量、状态、时间、去向和判断依据。
- 原始记录只可作为调试辅助，不应放在默认用户视图中。
- 表格列名使用业务语言，避免内部字段名直接暴露。
- 表格应能和上游输入对象、下游线索/关键词/机会形成可理解的关联。
- 表格数据量过多要进行分页处理。

### 目标驱动执行

定义成功标准。循环验证直到达成。

- “添加验证”应转化为：为无效输入编写测试，然后让它们通过。
- “修复 bug”应转化为：编写重现 bug 的测试，然后让它通过。
- “重构 X”应转化为：确保重构前后测试都能通过。
- 对于多步骤任务，说明简短计划，并为每一步给出验证方式。

示例：

```text
1. [步骤] → 验证: [检查]
2. [步骤] → 验证: [检查]
3. [步骤] → 验证: [检查]
```

### 工作仪式规范

修改前：

- 所有参与者必须了解 `AGENTS.md`。
- 禁止直接在 `main` 分支开发。
- 分支命名规范：
  - `feat/<desc>`
  - `fix/<desc>`
  - `refactor/<desc>`
  - `chore/<desc>`

修改中：

- Claude / Codex 在响应任何任务前，必须先检查是否有适用的 superpowers skill。
- 只要有可能适用，就必须先读取并遵循对应 skill，再进行澄清、规划、编码或验证。
- 创意、功能、组件、行为变更类任务必须先使用 `superpowers:brainstorming`。
- 执行已有计划时必须使用对应执行类 skill，例如 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development`。
- 完成、提交或声称通过前必须使用验证类 skill，例如 `superpowers:verification-before-completion`。

修改原则：

- 小步修改，避免大范围 PR。
- 禁止“顺手重构”，除非明确说明。
- 禁止引入未说明的新依赖。

## 项目类

- 项目根目录：`D:\Projects\damand-hunter`
- 本地开发以源码方式运行，不使用 Docker。
- 本地前端默认端口：`3100`。
- 本地部署脚本：`deploy-local.bat`，应支持指定前端端口；如果端口被占用，可以先结束占用进程再启动。
- 本地后端通常运行在：`http://127.0.0.1:8100`
- 本地前端通常运行在：`http://localhost:3100`

### 项目介绍与架构

- `damand-hunter` 是机会发现与验证系统，采用前后端分离架构。
- 后端提供 API、数据模型、自动化运行、采集/发现、证据和机会分析能力。
- 前端提供管理界面、发现/证据/机会/设置等页面。
- 本地开发时前端通过 API 访问本地后端服务。

### 技术栈约束

- 后端：
  - Python
  - FastAPI
  - SQLAlchemy
  - Alembic
  - Pydantic
  - SQLite 本地数据
- 前端：
  - Next.js App Router
  - React
  - TypeScript
  - Tailwind CSS
- 不要在未说明的情况下引入新框架、新状态管理库或新 UI 组件库。
- 不要绕过既有 API/服务层直接在前端硬编码业务数据。
- 数据结构变更必须同步考虑模型、迁移、API、前端类型和测试。

### 目录架构规范

- `backend/`：后端服务。
  - `backend/app/models.py`：SQLAlchemy 数据模型。
  - `backend/app/api/v1/endpoints/`：API 路由。
  - `backend/app/services.py` 及独立服务模块：业务逻辑。
  - `backend/alembic/`：数据库迁移。
  - `backend/tests/`：后端测试。
- `frontend/`：前端应用。
  - `frontend/app/`：Next.js App Router 页面。
  - `frontend/components/`：可复用组件。
  - `frontend/lib/`：API 客户端、工具和前端公共逻辑。
  - `frontend/types/`：前端类型定义。
- `docs/`：业务方案、架构说明、交接和实施计划。
- `deploy/`：正式部署相关文件。
- `data/`、`local-data/`、`output/`：本地数据或运行输出，修改前先确认是否属于用户数据。
- `.worktrees/`、`.superpowers/`：本地工作辅助目录，不作为业务代码入口。

## 正式部署

- 对外访问域名：`tools.biztint.com`
- VPS：`root@64.186.232.231:22`
- SSH key：`D:\DMIT-ZCWEAH-id_rsa\id_rsa.pem`
- VPS 项目目录：`/opt/projects/damand-hunter/`
- VPS 使用 Docker Compose 部署。
- Preview 不部署在 VPS；Preview 只在本机运行。

### 公网路由 / Caddy

- 公网地址：`https://tools.biztint.com`
- Caddy 配置：`/opt/edge/caddy/Caddyfile`
- 正确 upstream：
  - `damand-hunter-backend:8100`
  - `damand-hunter-frontend:3100`
- 错误旧 upstream，会导致 502：
  - `demand-hunter-backend:8100`
  - `demand-hunter-frontend:3100`

验证 / reload：

```bash
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

健康检查：

```bash
curl -sS https://tools.biztint.com/api/health
```

### 正式部署流程

部署前必须备份数据。

生产 DB 使用 SQLite，并可能存在 WAL/SHM 文件。部署前必须备份三者：

```bash
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p /opt/damand-hunter/backups
cp -a /opt/damand-hunter/shared/data/demand_hunter.sqlite \
  /opt/damand-hunter/backups/demand_hunter.sqlite.pre-deploy-$TS

[ -f /opt/damand-hunter/shared/data/demand_hunter.sqlite-wal ] && \
cp -a /opt/damand-hunter/shared/data/demand_hunter.sqlite-wal \
  /opt/damand-hunter/backups/demand_hunter.sqlite-wal.pre-deploy-$TS || true

[ -f /opt/damand-hunter/shared/data/demand_hunter.sqlite-shm ] && \
cp -a /opt/damand-hunter/shared/data/demand_hunter.sqlite-shm \
  /opt/damand-hunter/backups/demand_hunter.sqlite-shm.pre-deploy-$TS || true
```

最近一次重要备份：

```text
/opt/damand-hunter/backups/demand_hunter.sqlite.pre-main-deploy-20260611-012319
/opt/damand-hunter/backups/demand_hunter.sqlite-wal.pre-main-deploy-20260611-012319
/opt/damand-hunter/backups/demand_hunter.sqlite-shm.pre-main-deploy-20260611-012319
```

等待 GitHub Actions 成功。

检查 main 最新 run：

```bash
curl -sL "https://api.github.com/repos/zcweah1981/damand-hunter/actions/runs?per_page=1&branch=main"
```

必须确认最新 commit：

```text
status = completed
conclusion = success
```

部署正式。

方式 A：直接 Docker Compose：

```bash
cd /opt/damand-hunter
docker compose pull
docker compose up -d --remove-orphans
docker compose ps
```

方式 B：使用仓库脚本：

```bash
cd /opt/projects/damand-hunter
APP_DIR=/opt/damand-hunter deploy/deploy-from-ghcr.sh latest main
```

注意：部署脚本会更新 compose 中的镜像 tag，但不会处理 DB 备份；DB 备份必须部署前单独执行。

写入部署版本：

```bash
cat > /opt/damand-hunter/.deploy-version <<EOF
repo=zcweah1981/damand-hunter
ref=main
sha=<commit_sha>
tag=latest
deployed_at=$(date -Is)
EOF
```

验证：

```bash
curl -sS https://tools.biztint.com/api/health
```

期望：

```json
{"ok":true,"settings":...,"keywords":...,"cards":...}
```

页面验证：

```bash
curl -I https://tools.biztint.com/
curl -I https://tools.biztint.com/login
```

未登录页面通常会 `307 /login`，这是正常的。

### 回滚流程

代码 / 镜像回滚：

- 使用上一个可用 GHCR tag。
- 修改 `/opt/damand-hunter/docker-compose.yml` 后执行：

```bash
cd /opt/damand-hunter
docker compose pull
docker compose up -d --remove-orphans
```

DB 回滚：

- 仅在确认数据损坏时执行。
- 先停止服务：

```bash
cd /opt/damand-hunter
docker compose stop frontend backend
```

- 恢复同一批次的 sqlite / wal / shm 备份后启动：

```bash
docker compose up -d
```

- 启动后立即验证 counts。
