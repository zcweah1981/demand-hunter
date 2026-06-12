# Demand Hunter Web PRD

> 固定 Web 系统，用于基于“词根 → 关键词 → SERP → 竞品 → 社媒证据 → 变现方式 → MVP 可行性”的流程，稳定发现、评估、复盘出海需求机会。

版本：v1.0  
状态：Draft  
创建时间：2026-06-05  
关联文档：`DEMAND_HUNTER_V1_DESIGN.md`

---

## 1. 背景

当前 Hunter 系统效果差且不稳定，主要原因不是单点 bug，而是方法论与系统目标混杂：

- 既想找社区痛点，又想找 SEO 新词，又想找 SaaS 机会；
- Action 卡标准过宽，经常缺少搜索入口、SERP 缺口、竞品弱点与可执行 MVP；
- 搜索池老化，新 URL 率持续低；
- fallback/recovery 容易将低质量证据包装成机会；
- 结果主要以 Markdown 日报呈现，不利于人工复盘、反馈写回和系统持续优化。

基于近期研究的两篇出海复盘文章，新的需求发现方法应围绕：

```text
词根 → 词找词 → 词找站 → 站找词 → 站找站 → SERP 缺口 → 弱竞品 → MVP → 变现
```

核心公式：

```text
Opportunity = 搜索需求 × SERP 缺口 × 弱竞品 × 快速 MVP × 匹配变现方式
```

Demand Hunter Web 的目标是把这套流程固化为可操作、可观察、可复盘的 Web 系统。

---

## 2. 产品目标

### 2.1 核心目标

建立一个内部 Web 操作台，帮助用户系统化发现和评估出海需求机会。

系统应能：

1. 管理词根库与 seed roots；
2. 自动扩展关键词；
3. 自动采集 SERP 结果；
4. 自动识别 SERP 缺口；
5. 自动拆解竞品页面弱点；
6. 自动追溯 Reddit / YouTube / Twitter / HN 等社媒证据；
7. 判断适合的变现方式；
8. 判断 MVP 可执行性；
9. 生成 Action / Watch / Reject 机会卡；
10. 支持人工复核和反馈写回。

### 2.2 阶段目标

#### v0.1：可观察版本

目标：先让数据和判断过程可见。

必须实现：

- 词根库；
- 关键词列表；
- SERP top 10；
- 简单 SERP gap 标签；
- scoring 展示；
- 人工标注。

#### v0.2：机会卡版本

目标：生成结构化机会卡。

新增：

- 竞品拆解；
- 社媒证据；
- 变现方式分型；
- MVP 可行性评分；
- Demand Card 详情页。

#### v0.3：反馈闭环版本

目标：让系统能从人工反馈中学习。

新增：

- seed / 词根 cooldown；
- blocked terms；
- source health；
- daily run report；
- 旧 Hunter social proof 接入。

---

## 3. 用户与使用场景

### 3.1 目标用户

内部用户：

- 产品机会研究者；
- SEO/出海项目操盘者；
- 独立开发者；
- Hunter 系统维护者；
- 负责每日机会复盘的人。

### 3.2 典型使用场景

#### 场景 1：每日查看机会雷达

用户打开 Dashboard，查看：

- 今日新增关键词；
- 今日 Action / Watch / Reject；
- Top SERP gap；
- Top 弱竞品；
- Top 高分机会；
- 系统健康状态。

#### 场景 2：评估一个关键词是否值得做

用户进入 Keyword Detail 页面，查看：

- 词来源；
- 词根组成；
- SERP 前 10；
- SERP 缺口；
- 竞品弱点；
- 社媒证据；
- 变现方式；
- MVP 方案；
- 系统评分。

然后人工标为：

- Action；
- Watch；
- Reject；
- Block；
- Add to seed；
- Generate MVP Brief。

#### 场景 3：管理词根库

用户进入 Root Library 页面，管理：

- 工具词根；
- 行业词根；
- 痛点词根；
- 商业意图词根；
- 地区词根；
- 排除词；
- 词根组合规则。

#### 场景 4：复盘系统推荐质量

用户进入 Review Queue，对系统推荐逐条标注：

- 好机会；
- 垃圾；
- 太泛；
- SERP 太强；
- 没有变现；
- 只是短期热点；
- 适合广告，不适合 SaaS；
- 适合 SaaS，不适合广告。

反馈写回系统，用于后续 scoring 和 seed selection。

---

## 4. 产品范围

### 4.1 v1 必须包含

1. Dashboard；
2. Root Library 词根库；
3. Keyword Discovery 关键词发现；
4. Keyword List；
5. Keyword Detail；
6. SERP Results；
7. Competitor Pages；
8. Opportunity Cards；
9. Review Queue；
10. Feedback；
11. Run History；
12. Settings。

### 4.2 v1 暂不包含

- 多用户复杂权限；
- 对外开放；
- 自动建站；
- 自动购买域名；
- 自动发布文章；
- 复杂爬虫集群；
- 完整 LLM agent 编排；
- 全自动 Action 发布。

---

## 5. 信息架构

```text
Demand Hunter Web
├── Dashboard
├── Root Library
│   ├── Root Groups
│   ├── Roots
│   ├── Root Combinations
│   ├── Blocked Roots
│   └── Root Performance
├── Keywords
│   ├── Keyword List
│   ├── Keyword Detail
│   ├── SERP Results
│   ├── Competitor Analysis
│   └── Social Proof
├── Opportunities
│   ├── Cards
│   ├── Action
│   ├── Watch
│   └── Reject
├── Review Queue
├── Runs
├── Reports
└── Settings
```

---

## 6. 核心模块 PRD

---

# 6.1 Dashboard

## 6.1.1 目标

让用户快速了解今日需求发现系统状态。

## 6.1.2 核心指标

展示：

- 今日新增关键词数；
- 今日新词数；
- 今日 SERP 分析数；
- 今日 Action 数；
- 今日 Watch 数；
- 今日 Reject 数；
- 平均机会分；
- Top root groups；
- Top sources；
- Top SERP gap types；
- 低质量来源警告；
- blocked root 命中警告。

## 6.1.3 卡片区

### 今日 Top Action

展示 5 张最高分 Action：

- title；
- target keyword；
- opportunity type；
- score；
- monetization；
- MVP estimate；
- main risk。

### 今日 Top SERP Gap

展示：

- keyword；
- gap type；
- weak competitor count；
- forum result count；
- strong brand count。

### 今日 Root Performance

展示：

- root group；
- generated keywords；
- Action count；
- Watch count；
- Reject count；
- avg score。

---

# 6.2 Root Library 词根库

## 6.2.1 目标

将“找词”从临时搜索变成可管理资产。

词根是 Demand Hunter 的核心输入。

## 6.2.2 词根类型

### A. 功能型词根 Function Roots

用于识别工具型需求。

示例：

```text
generator
converter
calculator
checker
tracker
monitor
analyzer
editor
template
builder
creator
formatter
compressor
extractor
summarizer
translator
scheduler
planner
optimizer
scanner
validator
detector
recovery
sync
automation
integration
dashboard
alert
notifier
```

### B. 内容/数据型词根 Data Roots

用于识别资讯、数据库、查询站机会。

```text
database
wiki
stats
map
list
ranking
leaderboard
price
index
chart
calendar
schedule
update
patch notes
item list
resource list
lookup
catalog
tracker
```

### C. 商业意图词根 Commercial Roots

用于识别 affiliate / SaaS / leadgen 机会。

```text
best
alternative
review
comparison
vs
pricing
coupon
discount
software
app
plugin
service
agency
consultant
solution
platform
provider
```

### D. 痛点型词根 Pain Roots

用于识别工作流痛点。

```text
failed
broken
error
issue
problem
manual
tedious
slow
missing
lost
churn
leakage
reconciliation
exception
discrepancy
delay
blocked
confusing
workaround
```

### E. 行业型词根 Vertical Roots

用于控制赛道。

```text
shopify
woocommerce
wordpress
quickbooks
xero
bookkeeping
accounting
tax
invoice
freelancer
contractor
hvac
plumber
dentist
real estate
restaurant
ecommerce
logistics
warehouse
inventory
game
pdf
image
video
resume
seo
marketing
email
ads
social media
```

### F. 用户角色词根 Persona Roots

用于细化场景。

```text
store owner
bookkeeper
accountant
freelancer
creator
marketer
agency
developer
designer
teacher
student
recruiter
founder
solo business
small business
contractor
```

### G. 地区/语言词根 Geo Roots

用于地区化机会。

```text
US
UK
Canada
Australia
near me
for small business
for freelancers
for contractors
for Shopify stores
for WooCommerce stores
```

### H. 排除词根 Blocked Roots

用于过滤不适合做的方向。

```text
celebrity
movie
election
politics
war
adult
gambling
casino
torrent
crack
piracy
brand impersonation
login
account hack
```

## 6.2.3 词根字段

每个 root 应有：

- root_id；
- root_text；
- root_type；
- group_name；
- language；
- region；
- priority；
- status：active / candidate / cooldown / blocked；
- reason；
- created_at；
- updated_at。

## 6.2.4 词根组合规则

系统应支持 root combination。

### 组合模式 1：Vertical + Function

```text
shopify + monitor
woocommerce + recovery
pdf + converter
invoice + generator
game + database
```

### 组合模式 2：Vertical + Pain + Function

```text
shopify failed payment recovery
woocommerce subscription error checker
bookkeeping reconciliation exception tracker
inventory sync monitor
```

### 组合模式 3：Persona + Task + Tool

```text
bookkeeper client document tracker
freelancer invoice generator
store owner checkout monitor
contractor quote follow-up template
```

### 组合模式 4：Commercial Modifier + Tool

```text
best invoice generator
shopify app alternative
woocommerce plugin pricing
quickbooks integration review
```

### 组合模式 5：Trend + Tool

```text
[new game] item database
[new AI feature] prompt generator
[new product] alternative
```

## 6.2.5 词根表现统计

每个 root group 需要统计：

- generated_keywords；
- searched_keywords；
- SERP gaps；
- Action count；
- Watch count；
- Reject count；
- avg score；
- spam rate；
- duplicate rate；
- last_success_at；
- cooldown_until。

## 6.2.6 词根操作

支持：

- Add root；
- Edit root；
- Block root；
- Cooldown root；
- Promote root；
- Merge duplicate roots；
- Add to combination rule；
- View generated keywords；
- View performance。

---

# 6.3 Keyword Discovery

## 6.3.1 目标

基于词根库自动生成候选关键词。

## 6.3.2 来源

关键词来源包括：

- root combinations；
- Google Trends；
- Google Suggest；
- Google Related Searches；
- SearXNG / Google SERP；
- GSC；
- competitor pages；
- social mentions；
- old Hunter pain signals。

## 6.3.3 生成流程

```text
Select active roots
  ↓
Generate root combinations
  ↓
Expand by suggest / related searches
  ↓
Deduplicate
  ↓
Filter blocked terms
  ↓
Classify intent
  ↓
Queue SERP collection
```

## 6.3.4 关键词字段

- keyword_id；
- keyword；
- normalized_keyword；
- source；
- source_detail；
- root_ids；
- root_combination；
- intent_type；
- region；
- language；
- status；
- first_seen_at；
- last_seen_at；
- score_latest。

---

# 6.4 Keyword List

## 6.4.1 目标

让用户快速浏览、筛选、排序所有关键词。

## 6.4.2 列表字段

- keyword；
- source；
- root combination；
- intent type；
- trend status；
- SERP gap score；
- competitor weakness score；
- monetization type；
- total score；
- verdict；
- first seen；
- last analyzed。

## 6.4.3 筛选条件

- source；
- root group；
- intent type；
- opportunity type；
- score range；
- verdict；
- region；
- language；
- date；
- trend status；
- has social proof；
- has competitor weakness；
- has SERP gap。

## 6.4.4 操作

- View detail；
- Mark Action；
- Mark Watch；
- Reject；
- Block keyword；
- Add root；
- Run SERP again；
- Generate card。

---

# 6.5 Keyword Detail

## 6.5.1 目标

这是系统核心页面，用于判断一个词是否值得做。

## 6.5.2 页面结构

### A. Header

展示：

- keyword；
- total score；
- verdict；
- opportunity type；
- intent type；
- monetization type。

### B. Keyword Origin

展示：

- 来源；
- 词根组合；
- first seen；
- related keywords；
- generated by which rule。

### C. Trend Panel

展示：

- 7d trend；
- 30d trend；
- breakout status；
- rising related queries；
- trend lifespan；
- decay risk。

### D. SERP Panel

展示 SERP 前 10：

- rank；
- title；
- url；
- domain；
- snippet；
- result type；
- weak signal；
- strong brand；
- has tool；
- has forum；
- has ads。

### E. SERP Gap Panel

展示：

- gap types；
- gap score；
- weak result count；
- strong brand count；
- forum-only ratio；
- tool missing flag。

### F. Competitor Panel

展示前 3-5 个竞品：

- 页面 title；
- core function；
- monetization；
- weakness；
- UI quality；
- data freshness；
- AI smell；
- improve angle。

### G. Social Proof Panel

展示：

- Reddit / YouTube / Twitter / HN 证据；
- 用户原话；
- 时间；
- 信号类型；
- strength。

### H. Scoring Panel

展示六项评分：

- Search Demand；
- SERP Gap；
- Competitor Weakness；
- Social Proof；
- Monetization Fit；
- MVP Feasibility。

### I. MVP Panel

展示：

- MVP type；
- first screen；
- must-have；
- nice-to-have；
- do-not-build；
- estimated shipping time；
- data source；
- maintenance burden。

### J. Review Actions

按钮：

- Mark Action；
- Mark Watch；
- Reject；
- Block keyword；
- Cooldown root；
- Add to seed；
- Generate MVP Brief；
- Add feedback。

---

# 6.6 SERP Analysis

## 6.6.1 目标

自动判断一个搜索结果页是否有切入机会。

## 6.6.2 SERP Result Type

分类：

- tool；
- content；
- forum；
- video；
- official；
- ecommerce；
- SaaS；
- marketplace；
- directory；
- unknown。

## 6.6.3 Weak SERP Signals

判断：

- no_tool_result；
- forum_heavy；
- outdated_title；
- thin_content；
- ai_generated_page；
- weak_ui；
- no_structured_data；
- no_fresh_data；
- weak_domain；
- longtail_low_competition。

## 6.6.4 Strong SERP Signals

判断：

- strong_brand_dominance；
- official_docs_dominance；
- mature_tool_many；
- high_authority_sites；
- ads_competition_high；
- no_clear_gap。

---

# 6.7 Competitor Analysis

## 6.7.1 目标

拆解竞品弱点，判断是否能“比弱竞品强一点”。

## 6.7.2 分析维度

- 内容深度；
- 工具完成度；
- UI/UX；
- 数据新鲜度；
- 页面速度；
- mobile 体验；
- 广告/订阅/联盟；
- 是否 AI 味；
- 是否有真实数据；
- 是否有多页面结构。

## 6.7.3 输出

每个竞品输出：

```json
{
  "url": "...",
  "domain": "...",
  "page_type": "tool/content/forum",
  "core_function": "...",
  "weaknesses": ["data_old", "ui_poor"],
  "improve_angle": "做更新的数据表 + 更清晰筛选器",
  "risk": "竞品域名权重较强"
}
```

---

# 6.8 Opportunity Cards

## 6.8.1 目标

生成可执行机会卡，不生成泛泛想法卡。

## 6.8.2 卡片字段

- title；
- target_keyword；
- opportunity_type；
- intent_type；
- monetization_type；
- total_score；
- verdict；
- search_demand_summary；
- serp_gap_summary；
- competitor_weakness_summary；
- social_proof_summary；
- mvp_plan；
- do_not_build；
- risks；
- next_step。

## 6.8.3 卡片状态

- Draft；
- Action；
- Watch；
- Reject；
- Archived。

---

# 6.9 Review Queue

## 6.9.1 目标

让用户每天快速复核系统推荐，形成反馈闭环。

## 6.9.2 队列来源

- 今日 Top Action；
- 高分但证据不足；
- 分数分歧大的候选；
- 新 root group 产出的候选；
- 系统不确定候选。

## 6.9.3 反馈选项

正向：

- good opportunity；
- actionable；
- strong SERP gap；
- weak competitor confirmed；
- monetization fit confirmed；
- add similar seeds。

负向：

- garbage；
- too generic；
- no search intent；
- no monetization；
- SERP too strong；
- short-lived trend；
- legal/brand risk；
- duplicate；
- hallucinated evidence。

---

## 7. 数据模型草案

### 7.1 root_terms

```sql
CREATE TABLE root_terms (
  root_id INTEGER PRIMARY KEY AUTOINCREMENT,
  root_text TEXT NOT NULL,
  root_type TEXT NOT NULL,
  group_name TEXT,
  language TEXT DEFAULT 'en',
  region TEXT DEFAULT 'global',
  priority REAL DEFAULT 1.0,
  status TEXT DEFAULT 'active',
  reason TEXT,
  created_at TEXT,
  updated_at TEXT,
  UNIQUE(root_text, root_type, language, region)
);
```

### 7.2 root_combinations

```sql
CREATE TABLE root_combinations (
  combination_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  pattern TEXT,
  root_types_json TEXT,
  example TEXT,
  priority REAL DEFAULT 1.0,
  status TEXT DEFAULT 'active',
  created_at TEXT,
  updated_at TEXT
);
```

### 7.3 generated_keywords

```sql
CREATE TABLE generated_keywords (
  keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword TEXT NOT NULL,
  normalized_keyword TEXT NOT NULL,
  source TEXT,
  root_ids_json TEXT,
  root_combination_id INTEGER,
  intent_type TEXT,
  region TEXT,
  language TEXT,
  status TEXT DEFAULT 'candidate',
  first_seen_at TEXT,
  last_seen_at TEXT,
  UNIQUE(normalized_keyword, region, language)
);
```

### 7.4 serp_results

```sql
CREATE TABLE serp_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword_id INTEGER,
  query TEXT,
  provider TEXT,
  rank INTEGER,
  title TEXT,
  url TEXT,
  domain TEXT,
  snippet TEXT,
  result_type TEXT,
  weak_signal_json TEXT,
  captured_at TEXT
);
```

### 7.5 opportunity_cards

```sql
CREATE TABLE opportunity_cards (
  card_id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword_id INTEGER,
  target_keyword TEXT,
  title TEXT,
  opportunity_type TEXT,
  monetization_type TEXT,
  verdict TEXT,
  total_score REAL,
  card_json TEXT,
  created_at TEXT,
  updated_at TEXT
);
```

### 7.6 feedback

```sql
CREATE TABLE feedback (
  feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT,
  entity_id INTEGER,
  rating TEXT,
  reason TEXT,
  notes TEXT,
  created_at TEXT
);
```

---

## 8. 评分体系

总分：100。

- Search Demand：20
- SERP Gap：20
- Competitor Weakness：15
- Social Proof：15
- Monetization Fit：15
- MVP Feasibility：15

### Action 规则

- total_score ≥ 70；
- SERP Gap ≥ 12；
- MVP Feasibility ≥ 10；
- Monetization Fit ≥ 8；
- 必须有 target keyword；
- 必须有 SERP evidence；
- 必须有 MVP plan。

### Watch 规则

- total_score 50-69；或
- 缺一项关键证据；或
- 趋势强但社媒/竞品证据不足。

### Reject 规则

- total_score < 50；或
- SERP 太强；或
- 无搜索意图；或
- 黑灰/品牌风险；或
- 无可执行 MVP。

---

## 9. 技术方案

### 9.1 后端

推荐：

- FastAPI；
- SQLite 起步；
- SQLAlchemy / sqlite-utils；
- APScheduler / cron；
- 后续可迁 PostgreSQL。

### 9.2 前端

推荐：

- React + Vite 或 Next.js；
- Tailwind；
- shadcn/ui；
- TanStack Table；
- Recharts。

### 9.3 部署

内部部署：

- VPS / 本机；
- Docker Compose；
- Caddy / Nginx；
- Basic Auth 或 OpenClaw 内部访问。

---

## 10. 里程碑

### Milestone 1：v0.1 可观察版本

周期：2-3 天。

交付：

- Root Library；
- Keyword List；
- Keyword Detail；
- SERP 展示；
- 基础评分；
- 人工反馈。

### Milestone 2：v0.2 机会卡版本

周期：3-5 天。

交付：

- 竞品拆解；
- 社媒证据；
- monetization fit；
- MVP fit；
- opportunity cards。

### Milestone 3：v0.3 闭环版本

周期：5-7 天。

交付：

- root performance；
- feedback writeback；
- daily report；
- old Hunter social proof 接入。

---

## 11. 验收标准

v1 可用标准：

1. 能管理词根；
2. 能基于词根生成关键词；
3. 能采集 SERP；
4. 能展示 SERP gap；
5. 能生成机会卡；
6. 能人工标注；
7. 能按反馈调整 root / keyword 状态；
8. 每天至少产生 3 个可复核候选；
9. Action 卡必须包含 target keyword、SERP gap、MVP plan、monetization type；
10. 连续 3 天人工复核垃圾率低于 30%。

---

## 12. 风险

### 12.1 搜索数据不稳定

缓解：

- 多来源；
- SearXNG fallback；
- 缓存 SERP；
- 限速。

### 12.2 词根爆炸导致噪音

缓解：

- root priority；
- root cooldown；
- blocked roots；
- combination limits。

### 12.3 AI 分析幻觉

缓解：

- LLM 只能基于 URL / quote / SERP evidence；
- 无证据只能 Watch；
- 不允许编竞品数据。

### 12.4 过度追短期热点

缓解：

- trend_lifespan；
- decay risk；
- event dependency；
- 短期热点不能进 SaaS Action。

### 12.5 旧 Hunter 数据污染

缓解：

- 新系统独立 DB；
- 旧 Hunter 只作为 social evidence；
- 不继承旧 Action verdict。

---

## 13. 最终建议

应该开发固定 Web 系统。

推荐路线：

```text
新建 Demand Hunter Web → 先做词根库与关键词/SERP可观察 → 再做机会卡 → 最后接反馈闭环
```

不要直接把旧 Hunter 改成 Web。

旧 Hunter 后续定位：

```text
社区痛点采集器 / social proof provider
```

Demand Hunter Web 定位：

```text
搜索需求入口发现器 / SERP 缺口分析器 / 机会评审台
```

最终目标：

> 每天输出少量但高质量、可执行、可验证、变现方式明确的机会卡，而不是大量泛泛的痛点想法。
