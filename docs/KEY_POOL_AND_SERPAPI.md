# Key Pool & SerpApi Plan

## SerpApi 有什么用

SerpApi 不是“又一个普通搜索 API”。它的价值是稳定拿到 Google 结构化 SERP 数据：

- organic results
- related searches
- People Also Ask（可后续接）
- Google Trends/Autocomplete 等其他 engine（可后续接）
- 本地化/国家/语言参数
- 避免直接抓 Google 的反爬和 HTML 变化

在 Demand Hunter 中，SerpApi 适合做：

1. SERP 验证：更稳定的 Google SERP。
2. 词找词：related searches / PAA / autocomplete。
3. Advanced Search：allintitle/site/date 等 Google 查询语法。
4. 免费额度轮询：很多账号/服务有免费额度，适合与 SearXNG/Brave/Tavily 共同轮询。

## 真轮询 vs 假轮询

之前的问题：

- 设置页能保存多条 Key。
- 但实际调用层只是简单列表尝试。
- 没有统一 key pool。
- 没有记录每条 key 的成功/失败。
- 没有在所有 provider 上统一应用轮询策略。

现在的方向：

```text
Provider Key Pool
  ↓
按 SERP_ROTATION_STRATEGY 排序
  ↓
调用 provider
  ↓
记录 key success/failure/last_error
  ↓
失败切下一个 key
```

## 当前已接入 Key Pool

- BRAVE_API_KEYS
- TAVILY_API_KEYS
- SERPAPI_API_KEYS

## 轮询策略

使用搜索总控：

- failover：失败后才尝试下一个 key/provider
- round_robin：每次请求从下一个 key/provider 开始

## SerpApi provider

新增 provider：

```text
serpapi
```

默认 provider order：

```text
searxng,serpapi,brave,tavily
```

只有配置了 `SERPAPI_API_KEYS` 时，`serpapi` 才进入 available providers。

## 下一步

1. Key Pool 状态页展示每条 key 的 ok/fail/last_error。
2. 扩展 SerpApi engine：Google Autocomplete、Google Trends、PAA。
3. 把 DataForSEO / Zenserp / Scale SERP 接入相同 Key Pool。
4. 为每个 provider 加每日 quota / cooldown。
