# Four-Find × SEO Demand Keyword Method

目标：四找不是替代 SEO 找词，而是扩词框架；SEO 找词方法负责判断需求价值。

## 核心公式

```text
SEO 机会 = 搜索词真实需求 × 明确搜索任务 × 可打 SERP × SEO 指标价值 × 可执行轻量页面 × 变现路径
```

## 两类词都要找

### 新词 / 上升词
- 30 天内出现或明显上升
- 竞争小，拼速度
- 需要 Google Trends / rising queries / 最近 SERP 新站确认
- 适合 Fast Action，但要警惕不可持续

### 老词 / 常青词
- 长期存在，搜索需求稳定
- 竞争更强，但市场更大
- 需要周期性复查，Watch/Reject 可能变 Action
- 适合长期 SEO 工具页

## 四找如何融合

1. 词找词：从 seed/root 扩展长尾任务词，例如 calculator → board feet calculator。
2. 词找站：搜索关键词，找正在承接该词的工具站/模板站。
3. 站找词：反查竞品站标题、URL、页面任务，找更多可承接词。
4. 站找站：从竞品找相似站，继续扩展词和品类。

## SEO 判断字段

当前已纳入 LLM 提示词，缺失时必须标记为待补证据：

- keyword_type: new / rising / old / evergreen / unknown
- seo_fit: high / medium / low / unknown
- search volume
- CPC
- keyword difficulty / KD
- country distribution，尤其 US 或高变现国家占比
- Google Trends 上升趋势
- recent SERP entrant / 新站
- SERP top results 是否是弱内容、模板、目录、论坛、过时页面

## Action / Watch / Reject

### Action
- 搜索意图清楚
- SERP 有缺口
- 竞品/现有结果弱
- 能定义很小的工具页/模板页 MVP
- 变现路径明确：Ads / Affiliate / Paid export / Subscription
- 不缺关键 SEO 证据，或证据足够强

### Watch
- 方向可能有价值
- 但缺 search volume / CPC / KD / trend / country / pay trigger 等证据
- 需要补证后再决定

### Reject
- SERP 跑偏
- 意图混乱
- 强品牌/强站过多
- 无法定义明确搜索任务
- 缺口弱或不可变现

## 系统实现状态

- Four-Find 仍负责扩词。
- 自动运行已支持新词发现 + 老词复查。
- LLM 机会卡提示词已加入 SEO 找词方法，不再只套模板。
- 机会卡 business evidence 已增加 keyword_type / seo_fit / missing_evidence。

## 下一步

- 接 Google Trends / rising queries。
- 接 SEO metrics provider：volume / CPC / KD / country。
- 检测 exact-match domain 和最近新站。
- Action 门槛加入 SEO metrics。 
