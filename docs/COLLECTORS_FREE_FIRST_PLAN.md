# Collectors Free-First Plan

目标：先从免费/公开数据源跑通完整闭环，再接付费 API。

```text
免费采集器 → 候选池 → Four-Find 扩展 → 免费 SEO/SERP 验证 → LLM 机会分析 → Action/Watch/Reject
```

## 免费 / 基本免费的数据源

### P0：最先做

#### 1. Sitemap Watcher
- 费用：免费
- 是否需要 Key：否
- 数据源：robots.txt、sitemap.xml、sitemap index
- 作用：监控竞品新页面，从 URL/title 抽长尾词
- 对应方法：sitemap 使用小技巧、站找词
- 优先级：最高

#### 2. Google/Bing/SearXNG SERP + 搜索语法
- 费用：当前可用 SearXNG 免费；Google/Bing 官方 API 可选
- 是否需要 Key：SearXNG 不需要；Bing Webmaster 仅用于站长关键词数据，非通用搜索
- 数据源：SearXNG、现有 Brave/Tavily、Google 高级搜索语法
- 作用：allintitle、site、after/date、新页面发现、SERP 验证
- 对应方法：高级搜索找需求
- 优先级：最高

#### 3. Google Suggest / Bing Suggest / Related Search
- 费用：基本免费
- 是否需要 Key：通常不需要；也可用 SearXNG/SerpApi/DataForSEO 增强
- 作用：词找词，扩展长尾词
- 对应方法：通过词根找需求
- 优先级：最高

#### 4. Hacker News Algolia
- 费用：免费
- 是否需要 Key：否
- 数据源：HN Algolia API
- 作用：早期技术/产品讨论、新工具名词
- 对应方法：信息溯源
- 优先级：高

#### 5. arXiv API
- 费用：免费
- 是否需要 Key：否
- 作用：AI/技术新词源头
- 对应方法：信息溯源
- 优先级：高

#### 6. GitHub Trending / GitHub Search
- 费用：免费；Token 可提高限额
- 是否需要 Key：可选 GITHUB_TOKENS
- 作用：新项目、新工具、新技术词
- 对应方法：信息溯源
- 优先级：高

#### 7. Hugging Face public APIs/pages
- 费用：免费；Token 可提高限额/访问更多接口
- 是否需要 Key：可选 HUGGINGFACE_TOKENS
- 作用：AI 模型/Space/数据集新词
- 对应方法：信息溯源
- 优先级：高

#### 8. ProductHunt
- 费用：基础 API 免费但需要 Token
- 是否需要 Key：PRODUCTHUNT_TOKENS
- 作用：新产品、新品类、AI 工具趋势
- 对应方法：信息溯源 / 请求找需求
- 优先级：中高

#### 9. Firefox Add-ons API
- 费用：免费
- 是否需要 Key：否
- 作用：插件评分、评论、用户抱怨
- 对应方法：插件差评找需求
- 优先级：中

#### 10. Chrome Web Store 抓取
- 费用：免费但需谨慎限速；无稳定官方 API
- 是否需要 Key：否
- 作用：高下载低评分插件、评论抱怨
- 对应方法：插件差评找需求
- 优先级：中

#### 11. TheresAnAIForThat Requests 页面抓取
- 费用：免费/公开页面
- 是否需要 Key：否，除非未来用官方/第三方 API
- 作用：AI 工具请求
- 对应方法：AI Tool Requests
- 优先级：中

## 付费或强依赖商业 API 的数据源

### P1：免费闭环跑通后再接

#### 1. DataForSEO
- 费用：付费
- 需要填写：DATAFORSEO_CREDENTIALS
- 价值：最高；覆盖 volume、CPC、KD、SERP、Trends、Suggest、Ads、国家数据
- 建议：第一个付费 API

#### 2. SimilarWeb
- 费用：付费
- 需要填写：SIMILARWEB_API_KEYS
- 价值：站找词、站找站、出站流量、着陆页新点击量
- 建议：第二优先

#### 3. Semrush
- 费用：付费
- 需要填写：SEMRUSH_API_KEYS
- 价值：关键词、KD、CPC、域名关键词

#### 4. Ahrefs
- 费用：付费
- 需要填写：AHREFS_API_KEYS
- 价值：KD、volume、traffic、top pages

#### 5. SerpApi / Zenserp / Scale SERP
- 费用：付费或有限免费额度
- 需要填写：SERPAPI_API_KEYS / ZENSERP_API_KEYS / SCALESERP_API_KEYS
- 价值：稳定 Google SERP、PAA、related search

#### 6. Bing Webmaster API
- 费用：免费/账号权限，但需要接入站点或账号权限
- 需要填写：BING_WEBMASTER_API_KEYS
- 价值：Bing 搜索量、国家、每日量、Top10

#### 7. YouTube Data API
- 费用：免费额度 + quota
- 需要填写：YOUTUBE_API_KEYS
- 价值：视频关注度、评论/产品热度

#### 8. X / Twitter API
- 费用：通常付费或限制较多
- 需要填写：X_BEARER_TOKENS
- 价值：一手信息源、早期传播

#### 9. Wappalyzer / BuiltWith
- 费用：付费 API
- 需要填写：WAPPALYZER_API_KEYS / BUILTWITH_API_KEYS
- 价值：技术栈、广告网络、站找站辅助

## 免费优先实施顺序

### Phase 1：无 Key 也能做
1. Candidate Pool 表
2. Sitemap Watcher
3. Suggest / Related Search Collector
4. Advanced Search Collector：allintitle/site/date variants
5. HN + arXiv Source Radar

### Phase 2：可选免费 Token
6. GitHub Collector
7. Hugging Face Collector
8. ProductHunt Collector
9. Firefox Add-ons Collector
10. Chrome Web Store Complaint Miner
11. AI Request Miner

### Phase 3：付费增强
12. DataForSEO
13. SimilarWeb
14. Semrush/Ahrefs
15. SerpApi/Zenserp/ScaleSERP
16. Wappalyzer/BuiltWith

## 设置页 Key 管理状态

设置页已新增“采集器 API”，但免费优先阶段可以先不填大部分 Key。

优先需要用户填写的顺序：

```text
可先不填 → Sitemap / Suggest / HN / arXiv 先跑
可选填写 → GitHub Token / HuggingFace Token / ProductHunt Token
付费后填写 → DataForSEO / SimilarWeb / Semrush / Ahrefs
```

## 决策

先做免费闭环，不等付费 API：

```text
Sitemap Watcher + Suggest Collector + Advanced Search Collector
```

这三块最贴近文章方法、成本最低、能最快让采集器真正产出候选词。


## API 可用性校验

- Bing Search APIs：已于 2025-08-11 退役，不再作为配置项。
- Bing Webmaster API：保留，但只用于 Bing Webmaster/Keyword Research，不作为通用搜索 API。
- Google Custom Search / Programmable Search：不使用，限制多且与本系统通用找词/SERP 入口不匹配。


## API 可用性校验补充

- Google Custom Search / Programmable Search：不使用。原因：PSE/CX 配置和搜索范围限制较多，不适合作为本系统通用找词/SERP 入口。
- 如需稳定 Google SERP / PAA / Related Search，后续使用明确付费源：DataForSEO / SerpApi / Zenserp / Scale SERP。
