# SEO Demand Method Integration

基于 11 篇“网站出海每日分享”文章，对 Demand Hunter / Four-Find 的融合方案。

## 方法论总览

这些文章可以归纳成一个完整闭环：

```text
词根 → 扩词 → 找站 → 反查词 → 监控新页面/新词 → 补 SEO 指标 → SERP 验证 → LLM 机会判断 → Action/Watch/Reject
```

Four-Find 仍然是主框架：

- 词找词
- 词找站
- 站找词
- 站找站

文章补充的是数据源和判断标准。

## 适合直接融入现有 Four-Find 的方法

### 1. 词根找需求
来源：通过词根找需求

方法：
- 从工具/输出型词根出发，例如 calculator/generator/template/checker/converter/analyzer 等。
- 用 Google Trends 相关查询、Google Related Search、搜索下拉、Semrush/SimilarWeb 继续扩词。

已融合：
- tool roots 已加入词根库。
- Four-Find quality score 已扩展 SEO 工具词根。

还需增强：
- Google Suggest / Related Search 独立数据源。
- Google Trends rising queries。
- Semrush/SimilarWeb keyword enrichment。

### 2. 词找站 / 站找词 / 站找站
来源：找词找站找需求

方法：
- 词找站：用关键词搜索 Google，找承接该需求的网站。
- 站找词：用 GSC/SimilarWeb/Semrush/AI TDK 查网站关键词。
- 站找站：SimilarWeb similar sites、PubSpy 同 Adsense ID 找同类站。

已融合：
- Four-Find 已有 Keyword→Site、Site→Keyword、Site→Site。

还需增强：
- query.domains 作为词找站来源。
- SimilarWeb site keywords / similar sites API。
- sitemap 监控到的新页面进入 Site→Keyword。
- PubSpy/Adsense ID 做站找站。

### 3. Bing 关键词研究
来源：Bing 关键词研究

方法：
- Bing Webmaster 关键词研究可以看到：搜索量、国家分布、每日搜索量、相关词、Top 10 站点。
- 不够实时，适合老词/稳定词，不适合抢新词。

适合融入：
- SEO Metrics enrichment。
- 老词复查模块。

可做字段：
- bing_volume
- country_distribution
- daily_volume
- related_keywords
- bing_top10_domains

### 4. 高级搜索找需求
来源：高级搜索找需求

方法：
- Google 搜索语法 + 时间过滤。
- allintitle + 词根：发现新上的页面。
- site + 关注站点：发现竞争对手新页面。

适合融入：
- SERP variant generator。
- 新词/新站发现。

可实现查询：
- `allintitle:"{root}" after:{date}`
- `site:{domain} {root} after:{date}`
- `{keyword} -site:.gov -site:wikipedia.org after:{date}`

### 5. Google Trends + AI 扩词根
来源：新版 Google Trends，用 AI 扩词根

方法：
- Google Trends 新版“建议搜索字词”可根据词根推荐不完全包含原词的新词。
- 适合找相关概念和上升趋势。

适合做独立模块：
- Trends Discovery Module。

输出：
- rising_queries
- suggested_terms
- trend_score
- top_country
- keyword_type: rising/new/unknown

### 6. Sitemap 监控
来源：sitemap 使用小技巧

方法：
- 监控竞争对手 sitemap。
- 对比新增 URL，发现新页面、新游戏、新工具、新长尾词。

适合做独立模块：
- Sitemap Watcher。

输出：
- new_urls
- url_to_keyword
- first_seen_at
- source_domain
- competitor_reaction_speed

### 7. 信息溯源
来源：信息溯源，快速找到新词

方法：
- 找到新词的一手信息源，例如 Hugging Face、arXiv、X 早期发布者。
- 关注源头，而不是等 Google Trends 起来。

适合做独立模块：
- Source Radar / Early Signal Radar。

数据源：
- Hugging Face trending / papers
- arXiv new papers
- X/Twitter accounts
- ProductHunt
- GitHub trending
- Hacker News

### 8. 出站流量找产品
来源：出站流量找到受关注的产品

方法：
- 用 SimilarWeb 看 AI 导航站/工具站的 outgoing traffic。
- 找大家正在点击的产品。
- 也可找竞争对手外链哪里导流多。

适合做独立模块：
- Outbound Traffic Discovery。

数据源：
- SimilarWeb outgoing traffic
- Toolify / traffic.cv / AI directories
- YouTube / Reddit mentions

### 9. 插件差评找需求
来源：收集插件抱怨找需求

方法：
- Chrome 插件：高下载、低评分、差评多 = 需求强但供给差。
- 用户差评就是痛点原话。

适合做独立模块：
- Extension Complaint Miner。

数据源：
- Chrome Web Store
- Firefox Add-ons
- Edge Add-ons

输出：
- installs
- rating
- review_count
- complaint_topics
- opportunity_gap

### 10. AI Tool Requests
来源：一个看需求的 AI 导航站

方法：
- theresanaiforthat.com/requests/ 里用户提交 AI 工具诉求。
- 可按最新/投票最多查看。

适合融入：
- Social / Request evidence。
- 新词候选。

数据源：
- TheresAnAIForThat Requests
- Futurepedia requests 如有
- ProductHunt discussions

### 11. SimilarWeb 着落页找词
来源：Similarweb 着落页找词

方法：
- SimilarWeb → Keyword Research → Landing Pages。
- 看“新点击量”上涨页面。
- 右侧热搜关键词 → Google Trends 验证。

适合做独立模块：
- Landing Page Growth Miner。

输出：
- growing_landing_pages
- hot_keywords
- traffic_delta
- domain
- trend_validation

## 适合直接扩展现有系统的部分

优先级 P0/P1：

1. Google Suggest / Related Search
   - 直接补 Four-Find 词找词。
   - 技术成本低。

2. 高级搜索语法 + 时间过滤
   - 补新页面/新词发现。
   - 可通过现有 SERP provider 实现。

3. Sitemap Watcher
   - 补站找词，特别适合监控竞品新页面。
   - 技术成本低。

4. Bing Keyword Research
   - 补老词 volume/country/top10。
   - 需要评估 API/抓取可行性。

5. SimilarWeb landing pages / site keywords
   - 对站找词和站找站最有价值。
   - 需要 API 或手动导入。

## 适合做单独模块的部分

### A. Trends Discovery Module
职责：发现 rising/new keywords。
来源：Google Trends、Trends suggested terms、rising queries。

### B. Sitemap Watcher
职责：监控目标站/竞品站新增页面，从 URL/title 抽词。

### C. Extension Complaint Miner
职责：从插件商店高下载低评分产品里找痛点。

### D. Source Radar
职责：监控 HuggingFace/arXiv/X/GitHub/ProductHunt/HN 等一手源。

### E. SimilarWeb Miner
职责：site keywords、similar sites、outgoing traffic、landing pages。

### F. AI Request Miner
职责：AI 工具请求平台、目录站 requests、社区愿望单。

## 可接 API / 数据源清单

### 搜索词 / SEO 指标
- Google Custom Search API / Programmable Search API：SERP。
- Bing Webmaster Tools / Bing Search APIs：关键词研究、搜索量、国家分布、SERP。
- DataForSEO API：Google Suggest、SERP、Trends、Search Volume、Keyword Difficulty、Ads/CPC（付费，最适合系统化）。
- Semrush API：关键词、KD、CPC、竞品词、域名关键词（付费）。
- Ahrefs API：KD、volume、traffic、top pages（付费）。
- SimilarWeb API：site keywords、similar sites、outgoing traffic、landing pages（付费）。
- SerpApi / Zenserp / Scale SERP：SERP + related searches + PAA。

### Trends / 新词
- Google Trends unofficial pytrends：趋势、related/rising queries（不稳定但可用）。
- Glimpse / Exploding Topics / Treendly：趋势词（部分有 API/付费）。
- ProductHunt API：新产品。
- Hacker News Algolia API：新讨论。
- GitHub Trending 无官方 API，可抓取。
- Hugging Face API：models/datasets/spaces trending 或最近更新。
- arXiv API：新论文。

### 站点 / 竞品
- Sitemap XML：公开，无需 API。
- robots.txt sitemap discovery：公开。
- query.domains：需确认是否有 API；无 API 可作为外部手动/抓取源。
- PubSpy：同 Adsense ID/广告网络找站，需确认 API。
- BuiltWith / Wappalyzer：技术栈/广告代码，部分有 API。

### 评论 / 抱怨 / 请求
- Chrome Web Store：非官方抓取或第三方 API。
- Firefox Add-ons API：可查插件和评论。
- Reddit API：社区痛点。
- YouTube Data API：视频/评论/产品关注度。
- TheresAnAIForThat Requests：需确认 API；无 API 可抓页面。

## 融合后的系统模块建议

### 1. Core Four-Find Engine
继续保留现有四找：
- keyword_to_keyword
- keyword_to_site
- site_to_keyword
- site_to_site

增强点：
- 每个候选记录 discovery_method。
- 每个候选记录 keyword_type / seo_fit / missing_evidence。
- 候选必须进入 SEO validation，而不是直接成卡。

### 2. SEO Metrics Enrichment
新增统一 enrichment 层：
- volume
- CPC
- KD
- country distribution
- trend score
- top SERP domains
- recent page/new site count

### 3. Old/New Keyword Classifier
输出：
- new
- rising
- old
- evergreen
- declining
- unknown

### 4. Evidence Gate
Action 前必须有：
- SERP 任务清楚
- 至少一个 SEO 指标或趋势/竞品增长证据
- 竞品缺口/弱内容证据
- 变现路径

### 5. Discovery Source Modules
按模块异步补充候选：
- Trends Discovery
- Sitemap Watcher
- SimilarWeb Miner
- Extension Complaint Miner
- Source Radar
- AI Request Miner

## 推荐实施顺序

### Phase 1：低成本快速融合
- Google Suggest / Related Search 扩词。
- Google advanced search time filter。
- Sitemap watcher。
- Opportunity prompt 已加入 SEO 方法。

### Phase 2：SEO 指标接入
- DataForSEO 或 Semrush/Ahrefs/SimilarWeb 选一个主源。
- 增加 KeywordSeoMetric 表。
- Action 门槛加入 volume/CPC/KD/country。

### Phase 3：独立发现模块
- Trends Discovery。
- Sitemap Watcher UI。
- SimilarWeb landing pages。
- Extension Complaint Miner。
- Source Radar。

### Phase 4：自动学习闭环
- 用户反馈 Action/Reject 反向调整 root/source 权重。
- 高 Action 来源扩大预算。
- 低质量来源 cooldown。
