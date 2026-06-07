# Collectors Roadmap & API Key Plan

## 总原则

采集器不是机会生成器。采集器只负责发现候选词、候选站、候选页面、请求、抱怨和早期信号。所有候选必须统一进入：

```text
Collectors → Candidate Pool → Four-Find Expansion → SEO Validation → LLM Opportunity Analysis → Action/Watch/Reject
```

一句话：所有入口都可以找词，但所有词都必须过 SEO。

## 模块规划

### 1. 搜索联想 / 相关搜索 Collector
用途：词找词。

来源：
- Google Suggest / Autocomplete
- Google Related Search
- People Also Ask
- Bing Suggest
- SearchSuggest.tips

输出：
- candidate_keyword
- source_query
- suggestion_type
- source_url/provider

需要 Key：
- 可无 key：部分 suggest 可直接请求或走 SearXNG。
- Google Custom Search / Programmable Search 不使用。
- 可选：SerpApi / Zenserp / Scale SERP / DataForSEO。

### 2. Trends Collector
用途：新词、上升词、趋势词。

来源：
- Google Trends / pytrends
- Google Trends suggested terms
- Exploding Topics
- Glimpse
- Treendly

输出：
- keyword_type: new/rising/old/evergreen/unknown
- trend_score
- top_country
- related_rising_queries
- first_seen_at

需要 Key：
- pytrends 可无官方 key，但稳定性有限。
- Exploding Topics / Glimpse / Treendly 视服务而定。
- DataForSEO 可作为趋势/关键词数据统一源。

### 3. Sitemap Watcher
用途：站找词；监控竞品新页面。

来源：
- robots.txt
- sitemap.xml
- sitemap index
- competitor domains

输出：
- source_domain
- new_url
- title/path_keyword
- first_seen_at
- extracted_keyword

需要 Key：
- 不需要 key。

### 4. SimilarWeb Collector
用途：站找词 / 站找站 / 出站流量找产品 / 着陆页找词。

来源：
- SimilarWeb site keywords
- SimilarWeb similar sites
- SimilarWeb outgoing traffic
- SimilarWeb landing pages / new clicks

输出：
- discovered_keyword
- competitor_domain
- similar_domain
- outgoing_domain
- landing_page
- traffic_delta

需要 Key：
- SimilarWeb API Key。

### 5. SEO Metrics Collector
用途：给所有候选补 SEO 指标，是 Action 门槛的关键。

来源：
- DataForSEO
- Semrush
- Ahrefs
- Bing Webmaster
- SimilarWeb

输出：
- search_volume
- cpc
- keyword_difficulty
- country_distribution
- daily_volume
- top_serp_domains
- ads_presence

需要 Key：
- DataForSEO credentials（推荐优先）
- Semrush API Key
- Ahrefs API Key
- Bing Webmaster API Key
- SimilarWeb API Key

### 6. Extension Complaint Miner
用途：从插件差评和低评分高下载产品中找需求。

来源：
- Chrome Web Store
- Firefox Add-ons
- Edge Add-ons

输出：
- extension_name
- installs/users
- rating
- review_count
- complaint_topic
- candidate_keyword

需要 Key：
- Firefox Add-ons API 可公开。
- Chrome Web Store 多数需抓取/第三方 API，通常不需要自有 key，但要控制频率。

### 7. AI Request Miner
用途：从用户主动提交的 AI 工具请求里找需求。

来源：
- TheresAnAIForThat Requests
- ProductHunt discussions
- AI directories request/wishlist

输出：
- request_text
- votes
- category
- candidate_keyword

需要 Key：
- ProductHunt Token。
- 其他目录视是否有 API。

### 8. Source Radar
用途：信息溯源，抢新词。

来源：
- Hugging Face
- arXiv
- GitHub Trending
- Hacker News Algolia
- X/Twitter accounts
- ProductHunt

输出：
- early_signal
- source_author/domain
- first_seen_at
- extracted_keyword
- related_terms

需要 Key：
- GitHub Token（可选，提高限额）
- Hugging Face Token（可选）
- X Bearer Token
- ProductHunt Token
- HN Algolia/arXiv 通常不需要 key

### 9. Tech / Ads / Domain Intelligence
用途：站找站、竞争验证、域名/广告网络识别。

来源：
- Wappalyzer
- BuiltWith
- query.domains
- PubSpy
- Namebeta / domain availability

输出：
- tech_stack
- adsense_id
- related_sites
- domain_status
- newly_registered_domain_signal

需要 Key：
- Wappalyzer API Key
- BuiltWith API Key
- PubSpy 视服务是否支持 API
- query.domains 需确认 API

## 设置页统一管理

新增设置分组：采集器 API。

统一用多条 Key/Token/凭证列表管理，支持：
- 新增
- 保存新增密钥
- 保存密钥
- 显示/隐藏
- 删除
- 清空

当前配置项：

- - BING_WEBMASTER_API_KEYS
- DATAFORSEO_CREDENTIALS
- SEMRUSH_API_KEYS
- AHREFS_API_KEYS
- SIMILARWEB_API_KEYS
- SERPAPI_API_KEYS
- ZENSERP_API_KEYS
- SCALESERP_API_KEYS
- YOUTUBE_API_KEYS
- REDDIT_CREDENTIALS
- PRODUCTHUNT_TOKENS
- GITHUB_TOKENS
- HUGGINGFACE_TOKENS
- X_BEARER_TOKENS
- WAPPALYZER_API_KEYS
- BUILTWITH_API_KEYS

## 推荐用户优先填写

### P0：最推荐
1. DATAFORSEO_CREDENTIALS
   - 覆盖 SERP / keyword volume / CPC / KD / trends / suggest。
2. SIMILARWEB_API_KEYS
   - 站找词、站找站、着陆页、出站流量。
3. SERPAPI_API_KEYS / DATAFORSEO_CREDENTIALS / ZENSERP_API_KEYS / SCALESERP_API_KEYS
   - 如需稳定 Google SERP / related / PAA，使用明确付费源。

### P1
4. SEMRUSH_API_KEYS 或 AHREFS_API_KEYS
   - SEO 指标和竞品词。
5. BING_WEBMASTER_API_KEYS
   - 老词 volume / 国家 / daily volume。
6. PRODUCTHUNT_TOKENS
   - 新产品和请求。

### P2
7. GITHUB_TOKENS
8. HUGGINGFACE_TOKENS
9. X_BEARER_TOKENS
10. YOUTUBE_API_KEYS
11. WAPPALYZER_API_KEYS / BUILTWITH_API_KEYS

## 实施顺序

1. 设置页统一 Key 管理（已完成第一版）。
2. Candidate Pool 数据表。
3. Sitemap Watcher（无需 key，优先落地）。
4. Google Suggest / Related Search Collector。
5. SEO Metrics provider 抽象，优先 DataForSEO。
6. SimilarWeb Collector。
7. Trends Collector。
8. Extension Complaint Miner / AI Request Miner / Source Radar。


## API 可用性校验

- Bing Search APIs：已于 2025-08-11 退役，不再作为配置项。
- Bing Webmaster API：保留，但只用于 Bing Webmaster/Keyword Research，不作为通用搜索 API。
- Google Custom Search / Programmable Search：不使用，限制多且与本系统通用找词/SERP 入口不匹配。


## API 可用性校验补充

- Google Custom Search / Programmable Search：不使用。原因：PSE/CX 配置和搜索范围限制较多，不适合作为本系统通用找词/SERP 入口。
- 如需稳定 Google SERP / PAA / Related Search，后续使用明确付费源：DataForSEO / SerpApi / Zenserp / Scale SERP。
