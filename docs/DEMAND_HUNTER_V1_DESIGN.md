# Demand Hunter v1 设计方案

> 目标：用“搜索需求入口 + SERP 缺口 + 弱竞品 + 快速 MVP + 匹配变现方式”的方法，替代现阶段 Hunter 里不稳定、泛痛点化、Action 标准过宽的问题。

生成时间：2026-06-05  
适用范围：Hunter 新系统原型 / 旧 Hunter 重构评估

---

## 0. 结论先行

现阶段不建议直接重构旧 Hunter。

推荐策略：

1. **新建 Demand Hunter v1 原型**，与旧 Hunter 并行影子运行 7-14 天。
2. 旧 Hunter 暂时降级为：
   - 社区痛点采集器；
   - social proof provider；
   - 不直接发布正式 Action 卡。
3. 新 Demand Hunter 负责：
   - 搜索词发现；
   - SERP 缺口分析；
   - 竞品弱点拆解；
   - 变现方式分型；
   - MVP 可执行性判断；
   - 生成最终机会卡。
4. 如果 Demand Hunter 影子运行质量稳定，再决定：
   - 替换旧 Hunter；或
   - 将旧 Hunter 融合为 Demand Hunter 的 social signal collector。

核心公式：

```text
Opportunity = 搜索需求 × SERP 缺口 × 弱竞品 × 快速 MVP × 匹配变现方式
```

不是：

```text
有人抱怨 = 机会
```

---

## 1. 背景：现有 Hunter 的核心问题

### 1.1 搜索池老化严重

最近 Hunter run 表现出：

- 新 URL 率持续偏低；
- fixed / query_family / keyword_engine / card_driven 等来源消耗大量预算但新内容少；
- feedback 写回后仍容易回到旧关键词；
- 系统更像是在抓“熟悉的词”，不是在找“市场正在出现的新搜索需求”。

### 1.2 痛点聚类与机会判断混在一起

旧 Hunter 大致流程：

```text
抓网页 → 抽 pain signal → 聚类 → 生成机会卡
```

这个流程只能说明“有人提到/抱怨过”，不能证明“值得做”。

缺失关键判断：

- 用户会不会主动搜索？
- 搜索词是什么？
- Google SERP 是否有缺口？
- 竞品是否弱？
- 能不能当天做 MVP？
- 适合广告、联盟、工具站，还是 SaaS？
- 这个机会能不能变成一个页面、站点或产品入口？

### 1.3 Action 卡标准过宽

旧 Action 往往基于：

- evidence 数；
- strength；
- LLM 判断；
- tags；
- cluster。

但新方法要求 Action 至少满足：

- 有明确搜索词；
- SERP 有缺口；
- 竞品有短板；
- MVP 可快速上线；
- 变现方式明确；
- 能被数据验证。

### 1.4 fallback / recovery 容易污染结果

近期已出现：fallback 把 HN 无关文章、Reddit 社区首页当作 Shopify checkout 证据。

结论：

- fallback 不能生成正式 Action；
- fallback 只能输出候选线索；
- 正式卡必须经过搜索入口、SERP、竞品、MVP、变现验证。

### 1.5 机会类型混乱

旧 Hunter 混合了至少四类机会：

1. SEO 新词工具站；
2. 广告流量站；
3. Affiliate / leadgen 站；
4. Workflow SaaS。

这些类型判断标准不同，不能混用同一 Action 逻辑。

---

## 2. 方法论来源与抽象

基于两篇文章总结出的核心方法：

### 2.1 搜索词就是 C 端需求表达

用户大量需求会通过搜索行为显性表达。把搜索词研究透，很多需求会自然浮现。

### 2.2 四找框架

```text
词找站 → 站找词 → 词找词 → 站找站
```

#### 词找站

用关键词去 Google 搜索，找 SERP 前排正在吃这个需求的网站。

看：

- 是否有工具站；
- 是否有论坛/文章占位；
- 是否有强品牌；
- 是否有低质量 AI 站；
- 结果是否不丰富；
- 是否存在可切入缺口。

#### 站找词

找到竞品后，反查它靠哪些页面、哪些关键词拿流量。

看：

- 高流量页面；
- 长尾词；
- 页面标题和 URL 结构；
- 竞品覆盖不足的词。

#### 词找词

围绕一个词继续扩展相关词、新词、长尾词。

工具：

- Google Trends；
- Google Suggest；
- Google Related Searches；
- Google Keyword Planner；
- Google Ads；
- GSC；
- Gemini DeepResearch / LLM 辅助。

#### 站找站

从一个站找到类似站、竞品站、同类型高流量站。

工具：

- SimilarWeb；
- Ahrefs；
- Semrush；
- Google “alternative to X”；
- Product Hunt；
- Reddit 推荐帖；
- 工具导航站。

---

## 3. Demand Hunter v1 的目标

### 3.1 系统定位

Demand Hunter 不是“痛点猎人”，而是“需求入口猎人”。

它的核心工作是：

```text
发现搜索需求入口 → 判断 SERP 缺口 → 拆竞品弱点 → 判断变现方式 → 输出可执行 MVP 机会卡
```

### 3.2 输出目标

每天输出：

- Top candidate keywords；
- Top SERP gaps；
- Top competitor weakness pages；
- Top opportunity cards；
- Reject reasons；
- 与旧 Hunter 的对比。

### 3.3 成功标准

7-14 天影子运行期间，满足：

- 每天 ≥ 3 个可执行候选；
- Action 垃圾率 < 30%；
- 每张 Action 有明确 target keyword；
- 每张 Action 有 SERP gap；
- 每张 Action 有 MVP plan；
- 每张 Action 有 monetization type；
- 不依赖 fallback 生成正式卡。

---

## 4. 系统架构

建议新建目录：

```text
demand-hunter/
  demand_hunter.sqlite
  pipeline.py
  collectors/
    trends.py
    suggest.py
    serp.py
    competitor.py
    social.py
    gsc.py
  analyzers/
    keyword_classifier.py
    serp_gap.py
    competitor_weakness.py
    monetization_fit.py
    mvp_fit.py
    scorer.py
  reports/
    daily_demand_report.py
  output/
    demand_cards_latest.md
    daily_demand_report.txt
```

### 4.1 旧 Hunter 与新 Demand Hunter 的关系

```text
旧 Hunter
  └── social pain signal / forum evidence

Demand Hunter
  ├── keyword discovery
  ├── SERP analysis
  ├── competitor analysis
  ├── social proof validation
  ├── monetization fit
  ├── MVP fit
  └── final opportunity card
```

长期目标：旧 Hunter 降级为 Demand Hunter 的 social collector。

---

## 5. Pipeline DAG

```text
[Seed Discovery]
      ↓
[Keyword Classification]
      ↓
[SERP Collection]
      ↓
[SERP Gap Analysis]
      ↓
[Competitor Tear-down]
      ↓
[Social Proof Validation]
      ↓
[Monetization Fit]
      ↓
[MVP Feasibility]
      ↓
[Scoring + Verdict]
      ↓
[Opportunity Cards + Daily Report]
      ↓
[Human Feedback]
```

---

## 6. Stage 1：Seed Discovery 找初始词

目标：每天产生一批新的候选词，不再依赖旧 fixed queries。

### 6.1 Google Trends / Rising Queries

字段：

- keyword；
- topic；
- region；
- timeframe；
- growth；
- trend_type；
- related_queries；
- related_topics。

优先：

- 7 天上涨；
- 30 天上涨；
- 起势晚；
- 非新闻热点；
- 有工具、查询、模板、数据属性。

### 6.2 Google Suggest / Related Searches

围绕 seed roots 扩展长尾词。

常用词根：

```text
generator, converter, calculator, checker, tracker, monitor,
analyzer, editor, template, app, plugin, alternative, database,
map, guide, recovery, automation, dashboard, integration,
pricing, comparison, review, best, free, online
```

### 6.3 SERP Mining

拿候选词查 Google/SearXNG，记录 SERP 前 10。

字段：

- query；
- rank；
- title；
- url；
- domain；
- snippet；
- result_type；
- has_tool；
- has_forum；
- has_video；
- has_ads；
- has_strong_brand；
- weak_result_count。

### 6.4 Competitor Reverse Discovery

从弱竞品反查更多词。

来源：

- sitemap；
- title/meta；
- URL path；
- SimilarWeb；
- Ahrefs/Semrush；
- indexed pages；
- `site:domain keyword`。

### 6.5 GSC / 自家站数据

优先利用 Search Console：

- impressions 上升但 CTR 低的词；
- ranking 11-30 的词；
- 新出现 query；
- 页面拿到意外曝光的词。

### 6.6 社媒追溯种子

对候选词去这些平台验证：

- Reddit；
- Twitter/X；
- YouTube；
- HN；
- Quora。

验证：

- 为什么突然出现？
- 用户在问什么？
- 是否多人讨论？
- 是不是短期事件？
- 有没有真实数据或素材？

---

## 7. Stage 2：Keyword Classification 关键词分型

每个词必须先分型，不同类型走不同评分。

### 7.1 Tool Intent 工具意图

关键词特征：

```text
generator, converter, calculator, checker, editor,
template, analyzer, tracker, monitor
```

适合：

- 工具站；
- 免费工具 + 广告；
- freemium；
- 轻 SaaS。

### 7.2 Info / Database Intent 信息数据库意图

关键词特征：

```text
guide, list, database, map, stats, wiki,
item, price, ranking, schedule, update
```

适合：

- 内容站；
- 数据库站；
- 广告；
- affiliate。

### 7.3 Commercial Intent 商业意图

关键词特征：

```text
best, alternative, pricing, review, comparison,
software, app, plugin
```

适合：

- affiliate；
- leadgen；
- SaaS；
- 产品页。

### 7.4 Workflow Pain 工作流痛点

关键词特征：

```text
automation, monitor, recovery, dashboard, integration,
alerts, sync, reconciliation, exception, failed payment
```

适合：

- SaaS；
- plugin；
- vertical workflow product。

### 7.5 Event / Trend Intent 热点事件

关键词特征：

- 游戏更新；
- 新产品发布；
- 名人/影视；
- 政治；
- 新闻；
- meme。

适合：

- 短期流量；
- 广告；
- 不能直接作为长期 SaaS Action。

---

## 8. Stage 3：SERP Gap Analysis 搜索结果缺口分析

### 8.1 Result Type Mix

统计 SERP 前 10：

- 工具站数量；
- 内容站数量；
- 论坛数量；
- 视频数量；
- 官方站数量；
- 强品牌数量；
- 广告数量。

### 8.2 Weakness Signals

弱竞品信号：

- 页面单薄；
- 纯 AI 文；
- UI 差；
- 无真实数据；
- 数据过时；
- 页面速度慢；
- mobile 差；
- title/meta 不匹配；
- 没有结构化数据；
- 没有工具功能；
- 只有教程没有工具；
- 只有论坛没有解决方案。

### 8.3 SERP Gap Types

缺口类型：

- `tool_gap`：用户需要工具，但结果没有工具；
- `fresh_data_gap`：用户需要最新数据，但结果过时；
- `ui_gap`：竞品功能有但体验差；
- `longtail_gap`：主词竞争强，但长尾弱；
- `localization_gap`：结果没有多语言/地区化；
- `comparison_gap`：用户要比较，但缺清晰对比；
- `workflow_gap`：用户要完成流程，但结果只是文章。

---

## 9. Stage 4：Competitor Tear-down 竞品拆解

对 SERP 前 3-5 个页面做拆解。

### 9.1 竞品字段

- domain；
- page_url；
- page_type；
- title；
- h1；
- core_function；
- user_intent_served；
- monetization；
- ads_present；
- pricing_present；
- content_depth；
- data_freshness；
- ui_quality；
- ai_smell_score；
- mobile_quality；
- weakness_summary；
- clone_or_improve_angle。

### 9.2 核心问题

1. 它解决了什么第一痛点？
2. 它没解决什么？
3. 它为什么能排上去？
4. 它靠内容、工具、数据还是品牌？
5. 我们能不能在 1 天内做一个更好的版本？
6. 它适合复制吗，还是太强不能碰？

---

## 10. Stage 5：Social Proof / Demand Proof 社媒追溯

对高潜词做社媒验证。

来源：

- Reddit；
- Twitter/X；
- YouTube；
- HN；
- Quora；
- TikTok，如可用。

提取：

- 用户原话；
- 需求触发原因；
- 是否多人重复；
- 是求推荐、抱怨、教程、购买、迁移，还是故障；
- 是否有商业损失；
- 是否有时间损耗；
- 是否有人提到付费；
- 是否存在替代方案不满。

作用：

- 防止 SEO 假信号；
- 判断趋势来龙去脉；
- 区分短期热点与长期需求；
- 为机会卡提供真实 evidence。

---

## 11. Stage 6：Monetization Fit 变现方式判断

每条候选必须明确变现类型。

### 11.1 Ads Fit

适合：

- 高流量；
- 低付费意愿；
- 查询/娱乐/资讯；
- 游戏/工具/指南。

判断字段：

- search_volume_potential；
- session_duration_potential；
- pageviews_per_user；
- topic_ad_rpm；
- evergreen_or_short_lived。

### 11.2 Affiliate Fit

适合：

- best / alternative / review / comparison；
- 工具推荐；
- 软件购买；
- 高客单。

判断字段：

- has_affiliate_programs；
- buyer_intent；
- product_ecosystem；
- commission_potential。

### 11.3 SaaS Fit

适合：

- 高频工作流；
- 明确 ROI；
- 用户痛点持续；
- 数据/集成/自动化粘性；
- 可以收月费。

判断字段：

- workflow_frequency；
- economic_loss；
- integration_need；
- willingness_signal；
- existing_paid_competitors。

### 11.4 Leadgen Fit

适合：

- 服务型需求；
- 高客单；
- 用户需要人工服务；
- 地区/行业明确。

### 11.5 Tool Freemium Fit

适合：

- 单次任务；
- 工具可免费用；
- 可加限制、批量、高级功能。

---

## 12. Stage 7：MVP Feasibility MVP 可执行性

防止“想法很好但做不了”。

### 12.1 MVP 评分字段

- can_ship_in_3h；
- can_ship_in_1d；
- needs_backend；
- needs_auth；
- needs_api；
- needs_scraping；
- needs_user_upload；
- needs_realtime_data；
- legal_risk；
- data_availability；
- maintenance_burden。

### 12.2 MVP 类型

- Static SEO page；
- Calculator；
- Converter；
- Checker；
- Database page；
- Simple API wrapper；
- Dashboard mock + waitlist；
- Chrome extension；
- Shopify/WooCommerce plugin；
- Template library；
- Comparison page。

---

## 13. Stage 8：Opportunity Card 输出

新版卡片必须是“可执行卡”，不是“想法卡”。

### 13.1 卡片字段

#### 1. Opportunity Type

- SEO Tool；
- Ads Content Site；
- Affiliate Page；
- Workflow SaaS；
- Leadgen；
- Data/Database Site；
- Plugin/App。

#### 2. Target Keyword

- 主词；
- 长尾词；
- 相关词；
- 词来源。

#### 3. Search Demand

- Google Trends 状态；
- SERP 结果概况；
- 是否新词；
- 是否持续。

#### 4. SERP Gap

- 当前前 10 结果；
- 缺口类型；
- 弱竞品证据。

#### 5. Competitor Weakness

- 竞品 1 弱点；
- 竞品 2 弱点；
- 竞品 3 弱点。

#### 6. Social Proof

- Reddit/Twitter/YouTube 证据；
- 用户原话；
- 需求来龙去脉。

#### 7. MVP Plan

- 第一天做什么；
- 第一屏功能；
- 页面结构；
- 数据来源；
- 不做什么。

#### 8. Monetization

- Ads / SaaS / Affiliate / Leadgen；
- 为什么匹配；
- 验证指标。

#### 9. Risk

- 趋势短命；
- 竞品太强；
- 数据不可得；
- 合规风险；
- 品牌风险；
- 维护成本。

#### 10. Verdict

- Action；
- Watch；
- Reject。

### 13.2 Action 必备条件

Action 必须满足：

- 有目标词；
- 有 SERP 缺口；
- 有竞品弱点；
- 有可执行 MVP；
- 有明确变现方式。

---

## 14. Scoring System 评分体系

总分：100。

### 14.1 Search Demand Score：20 分

- Trends 上涨：0-5；
- 搜索意图明确：0-5；
- 非短期热点：0-5；
- 长尾扩展空间：0-5。

### 14.2 SERP Gap Score：20 分

- 弱结果数量：0-5；
- 工具/数据缺口：0-5；
- 强品牌少：0-5；
- 结果不够丰富：0-5。

### 14.3 Competitor Weakness Score：15 分

- UI 差：0-3；
- 数据旧：0-3；
- 内容薄：0-3；
- AI 味重：0-3；
- 功能缺口：0-3。

### 14.4 Social Proof Score：15 分

- 多平台讨论：0-4；
- 用户原话强：0-4；
- 多人重复：0-4；
- 有明确损失/动机：0-3。

### 14.5 Monetization Fit Score：15 分

- 广告/联盟/订阅匹配：0-5；
- 有竞品变现证据：0-5；
- 变现闭环短：0-5。

### 14.6 MVP Feasibility Score：15 分

- 3h/1d 可上线：0-5；
- 数据易得：0-4；
- 技术简单：0-3；
- 维护低：0-3。

---

## 15. Verdict 规则

### 15.1 Action

条件：

- 总分 ≥ 70；
- SERP Gap ≥ 12；
- MVP Feasibility ≥ 10；
- Monetization Fit ≥ 8；
- 必须有目标词。

### 15.2 Watch

条件：

- 总分 50-69；或
- 缺一项关键验证；或
- 趋势强但社媒/竞品证据不足。

### 15.3 Reject

条件：

- 总分 < 50；或
- 品牌/黑灰/合规风险高；或
- SERP 强垄断；或
- 无明确搜索词；或
- 无可执行 MVP。

---

## 16. Database Schema 草案

### 16.1 demand_keywords

```sql
CREATE TABLE demand_keywords (
  keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword TEXT NOT NULL,
  normalized_keyword TEXT NOT NULL,
  source TEXT,
  source_detail TEXT,
  region TEXT,
  language TEXT,
  intent_type TEXT,
  trend_status TEXT,
  first_seen_at TEXT,
  last_seen_at TEXT,
  created_at TEXT,
  updated_at TEXT,
  UNIQUE(normalized_keyword, source, region)
);
```

### 16.2 trend_signals

```sql
CREATE TABLE trend_signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword_id INTEGER,
  provider TEXT,
  timeframe TEXT,
  growth_score REAL,
  breakout BOOLEAN,
  related_queries_json TEXT,
  related_topics_json TEXT,
  captured_at TEXT
);
```

### 16.3 serp_results

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
  captured_at TEXT
);
```

### 16.4 serp_gap_analysis

```sql
CREATE TABLE serp_gap_analysis (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword_id INTEGER,
  query TEXT,
  tool_results INTEGER,
  forum_results INTEGER,
  video_results INTEGER,
  strong_brand_results INTEGER,
  weak_results INTEGER,
  gap_types_json TEXT,
  gap_score REAL,
  analysis_json TEXT,
  created_at TEXT
);
```

### 16.5 competitor_pages

```sql
CREATE TABLE competitor_pages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword_id INTEGER,
  url TEXT,
  domain TEXT,
  title TEXT,
  h1 TEXT,
  page_type TEXT,
  core_function TEXT,
  monetization TEXT,
  ads_present BOOLEAN,
  pricing_present BOOLEAN,
  content_depth_score REAL,
  data_freshness_score REAL,
  ui_quality_score REAL,
  ai_smell_score REAL,
  mobile_quality_score REAL,
  weakness_summary TEXT,
  captured_at TEXT
);
```

### 16.6 social_mentions

```sql
CREATE TABLE social_mentions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword_id INTEGER,
  platform TEXT,
  url TEXT,
  title TEXT,
  author TEXT,
  published_at TEXT,
  snippet TEXT,
  quote TEXT,
  signal_type TEXT,
  strength_score REAL,
  captured_at TEXT
);
```

### 16.7 opportunity_scores

```sql
CREATE TABLE opportunity_scores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword_id INTEGER,
  search_demand_score REAL,
  serp_gap_score REAL,
  competitor_weakness_score REAL,
  social_proof_score REAL,
  monetization_fit_score REAL,
  mvp_feasibility_score REAL,
  total_score REAL,
  verdict TEXT,
  reasons_json TEXT,
  created_at TEXT
);
```

### 16.8 demand_cards

```sql
CREATE TABLE demand_cards (
  card_id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword_id INTEGER,
  target_keyword TEXT,
  opportunity_type TEXT,
  title TEXT,
  card_json TEXT,
  verdict TEXT,
  total_score REAL,
  created_at TEXT,
  updated_at TEXT
);
```

### 16.9 human_feedback

```sql
CREATE TABLE human_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id INTEGER,
  keyword_id INTEGER,
  rating TEXT,
  reason TEXT,
  notes TEXT,
  created_at TEXT
);
```

---

## 17. MVP 版本范围

第一版不要做全量系统，只做必要闭环。

### 17.1 MVP 输入

- 100 个 seed roots；
- Google Trends / SearXNG；
- Google Suggest，如可实现；
- SERP top 10；
- Reddit / YouTube / Twitter 搜索追溯；
- 简单竞品页面抓取。

### 17.2 MVP 输出

每天 10 张卡：

- 5 张 SEO tool/content opportunity；
- 3 张 workflow SaaS opportunity；
- 2 张 affiliate/leadgen opportunity。

每张必须有：

- target keyword；
- SERP summary；
- competitor weakness；
- MVP plan；
- monetization type；
- Action / Watch / Reject。

---

## 18. 文章方法的不足与系统补强

### 18.1 不足：过度偏 C 端 SEO

文章方法适合：

- 工具站；
- 广告站；
- 内容站；
- 新词站。

但对 B2B workflow SaaS 不够。

补强：

- 保留 workflow layer；
- 引入 Reddit pain / forum pain；
- 引入损失、频率、付费意愿评分。

### 18.2 不足：容易追短期热点

补强字段：

- trend_lifespan：short / medium / evergreen；
- event_dependency；
- decay_risk。

短期热点只能做 Ads/Content，不进 SaaS Action。

### 18.3 不足：商业验证不严肃

补强：

每个机会必须分型：

- Ads only；
- Affiliate；
- SaaS；
- Leadgen；
- Tool freemium。

### 18.4 不足：没有维护成本估算

补强字段：

- data_freshness_burden；
- update_frequency；
- source_reliability；
- automation_difficulty。

维护成本高的机会降分。

### 18.5 不足：弱竞品可能意味着需求小

补强：

必须结合：

- Trends；
- SimilarWeb；
- GSC；
- SERP breadth；
- related keywords；
- social proof。

### 18.6 不足：AI 分析容易幻觉

补强：

- LLM 只能基于抓取证据输出；
- 无 URL / 无 quote / 无 SERP 证据时，只能 Watch；
- LLM 不允许编市场格局、付费意愿、竞品数据。

---

## 19. 与旧 Hunter 的迁移关系

### 19.1 短期：冻结旧 Hunter 的 Action 发布

旧 Hunter：

- 只出 Watch / Diagnostics；
- fallback 不生成正式 Action；
- quality gate blocked 不上传；
- Action 必须人工复核。

### 19.2 中期：Demand Hunter 影子运行

并行运行 7-14 天。

每天对比：

- 旧 Hunter top cards；
- Demand Hunter top cards；
- 垃圾率；
- 可执行性；
- 是否有明确关键词；
- 是否有明确 MVP。

### 19.3 长期：旧 Hunter 降级为 social collector

旧 Hunter 输出：

- pain evidence；
- forum thread；
- social proof；
- workflow loss signal。

Demand Hunter 负责最终 opportunity verdict。

---

## 20. 7 天落地路线

### Day 1：Schema + seed roots

完成：

- 新建 demand-hunter 目录；
- 创建 SQLite schema；
- 准备 100 个 seed roots；
- 定义 intent classifier 规则。

### Day 2：词找词 + SERP collector

完成：

- SearXNG / web search 查询；
- Google Suggest，如可用；
- SERP top 10 存储；
- result type 粗分类。

### Day 3：SERP gap scorer

完成：

- weak result rule；
- tool_gap / fresh_data_gap / forum_gap；
- SERP gap score；
- reject strong SERP。

### Day 4：竞品拆解

完成：

- 抓 title/h1/meta；
- 页面类型判断；
- AI 味 / 内容薄 / 数据旧粗评分；
- competitor weakness summary。

### Day 5：社媒追溯

完成：

- Reddit 搜索；
- YouTube 搜索；
- Twitter/X 如可用；
- social proof score。

### Day 6：变现与 MVP 评分

完成：

- monetization type classifier；
- MVP feasibility scorer；
- scoring aggregation；
- Action / Watch / Reject。

### Day 7：报告与人工复核

完成：

- demand_cards_latest.md；
- daily_demand_report.txt；
- old Hunter vs Demand Hunter 对比；
- human feedback 写回。

---

## 21. 验收标准

Demand Hunter v1 进入替换/融合阶段前，必须满足：

1. 每天至少 3 个可执行候选；
2. Action 垃圾率 < 30%；
3. 每个 Action 有 target keyword；
4. 每个 Action 有 SERP evidence；
5. 每个 Action 有 competitor weakness；
6. 每个 Action 有 MVP plan；
7. 每个 Action 有 monetization type；
8. Watch / Reject reason 清楚；
9. 不依赖 fallback 生成正式卡；
10. 人工复核后连续 3 天质量稳定。

---

## 22. 报告样例

```markdown
# Demand Hunter Daily Report

## Top Action

### 1. Game Item Database for [Keyword]

- Opportunity Type: Ads Content / Database Site
- Target Keyword: xxx item database
- Keyword Source: Google Trends rising + SERP expansion
- Search Demand: 7-day rising, related queries expanding
- SERP Gap: 前 10 中 4 个论坛、2 个旧站、1 个 AI 单页，无实时数据工具
- Competitor Weakness:
  - Competitor A: 数据旧
  - Competitor B: UI 差
  - Competitor C: 只有文章无查询工具
- Social Proof:
  - Reddit / YouTube 有用户讨论最新版本数据
- MVP:
  - 1 天内做道具数据库 + filter + latest update page
  - 第一屏直接搜索/筛选
  - 数据源来自公开 wiki / Reddit 手动种子
- Monetization: AdSense first, affiliate later
- Risks:
  - 热点可能衰减
  - 数据需要持续更新
- Verdict: Action
- Score: 78
```

---

## 23. 最终建议

当前最合理路线：

```text
新建 Demand Hunter v1 → 影子运行 → 人工复核 → 决定替换/融合旧 Hunter
```

不要直接重构旧 Hunter。

原因：

1. 旧系统已被太多历史逻辑、feedback、fallback 污染；
2. 新方法论的核心对象从 pain cluster 变成 demand entry；
3. 直接改旧系统风险高、验证慢；
4. 新建原型可以快速证明方法是否有效；
5. 旧 Hunter 仍有价值，但更适合作为 social proof 采集器。

最终目标：

> 每天输出少量但高质量、可执行、可验证、变现方式明确的机会卡，而不是大量泛泛的“痛点想法”。
