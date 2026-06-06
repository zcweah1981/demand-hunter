# 四找方法论 — Demand Hunter 核心找词框架

> 基于"搜索需求入口 + SERP 缺口 + 弱竞品 + 快速 MVP + 匹配变现方式"的系统化找词方法。

## 核心公式

Opportunity = 搜索需求 × SERP 缺口 × 弱竞品 × 快速 MVP × 匹配变现方式

这个公式不是口号，而是 Demand Hunter 的过滤器。一个词是否值得进入机会池，不能只看搜索量，也不能只看竞品弱。它必须同时具备明确入口、可被验证的需求、现有结果的缺口、可快速上线的 MVP，以及合理的变现方式。

四找方法论的目标是把“灵感找机会”变成“链路找机会”：从一个 seed keyword 出发，沿着搜索词、网站、竞品、类似站不断扩散，再用评分体系收敛。

## 核心判断原则

1. 先找入口，再谈产品。入口通常是搜索词、SERP、竞品页面、Reddit/HN 帖子、工具导航站或广告落地页。
2. 先看现有结果，再判断缺口。没有看 SERP 的想法只是猜想。
3. 先判断用户任务，再设计 MVP。用户真正要完成的动作比关键词字面意思更重要。
4. 先找弱点，再找定位。强品牌占满 SERP 时，除非长尾有空位，否则不要硬打。
5. 先匹配变现，再投入建设。不同需求适合广告、联盟、SaaS、Leadgen 或 Freemium 工具。

## 四找框架

四找包括：词找站、站找词、词找词、站找站。四者不是线性一次性动作，而是循环扩展网络。

### 词找站 (Keyword → Site)

用关键词搜 Google/SearXNG，找 SERP 前排正在吃需求的网站。

- 判断是否有工具站
- 判断是否有论坛/文章占位
- 判断是否有强品牌
- 判断是否存在低质量 AI 站
- 判断结果是否不丰富
- 判断是否存在可切入缺口

词找站回答的问题是：这个搜索入口现在被谁占着？用户搜这个词时，Google 认为哪些页面最能满足需求？如果结果里已经有强品牌的高质量工具，并且没有明显长尾缺口，机会会变弱。如果结果里是论坛、过时文章、模板 PDF、低质量目录站，机会会变强。

#### 词找站的观察维度

- SERP 前 10 名域名结构：强品牌、论坛、内容站、工具站、目录站各占多少。
- 页面类型：用户是被导向文章、工具、SaaS、模板、视频、商品页还是论坛讨论。
- 意图匹配：标题和摘要是否真的覆盖 seed keyword，还是只是泛泛相关。
- 可替代性：现有结果是否能被更快、更专、更清晰的工具替代。
- 新鲜度：结果是否依赖最新数据，但页面内容明显过时。
- 体验弱点：是否有广告过多、输入流程繁琐、移动端差、结果不可下载、无多语言等问题。

#### 词找站示例

Seed keyword：`invoice late fee calculator`

可能的 SERP：

- 会计博客解释 late fee policy
- PDF 模板下载站
- 强品牌 accounting SaaS 的帮助文档
- 一个老旧 calculator 页面
- Reddit/Quora 上关于 late fee 的讨论

判断：如果前排缺少清晰、快速、可导出结果的 calculator，就存在 tool_gap。MVP 可以是一个输入 invoice amount、due date、interest rate、jurisdiction note 的轻工具。

#### 词找站实现提示

- 调用 SearXNG 搜索 seed keyword。
- 解析 URL domain，去重。
- 按 domain、title、snippet 分类站点类型。
- 记录工具站、SaaS、内容站、论坛、强品牌、目录站。
- 对弱结果打标签，例如 `forum_heavy`、`thin_snippet`、`weak_content_or_template`。
- 把可疑竞品域名送入站找词与站找站。

### 站找词 (Site → Keyword)

找到竞品后，反查它靠哪些页面、哪些关键词拿流量。

- 抓 sitemap / title / meta
- 抓 URL path 反推关键词
- site:domain keyword 查询
- 页面标题转 keyword
- 找长尾页面

站找词回答的问题是：这个站实际覆盖了哪些搜索需求？很多机会不是直接从 seed keyword 发现的，而是从竞品的页面结构里发现的。竞品往往已经帮我们做了一轮市场验证：它愿意为某类页面建内容，说明这些页面可能有流量或转化价值。

#### 站找词的输入

- 从词找站得到的工具站或 SaaS 域名。
- 从站找站得到的类似站。
- 从用户反馈或人工研究得到的竞品域名。

#### 站找词的方法

1. `site:domain.com` 搜索，抓前排页面 title。
2. 从 title 中去掉品牌后缀，把标题转成 keyword。
3. 从 URL path 中提取最后一个语义段，例如 `/tools/invoice-late-fee-calculator` → `invoice late fee calculator`。
4. 搜索品牌名，观察别人如何描述该站。
5. 如果允许进一步扩展，可抓 sitemap.xml、robots.txt 暴露的 sitemap index。

#### 站找词示例

Competitor：`calculator.net`

可能发现：

- `paycheck calculator`
- `sales tax calculator`
- `margin calculator`
- `loan payoff calculator`
- `time duration calculator`

这些词不一定都适合做，但可以进入候选池，再用 SERP gap 和 monetization 评分。

#### 站找词实现提示

- 不要只抓首页。长尾机会通常藏在工具页、模板页、对比页、行业页。
- title 清洗要去掉品牌后缀，例如 `Keyword Tool - Brand` 只保留前半段。
- URL path 要过滤日期、纯数字、无意义目录名。
- 同一个 domain 下发现的 keyword 应保留 source_url，方便后续人工复核。
- 发现的 keyword 先进入 discovery 表，人工或按钮导入主 keyword 表。

### 词找词 (Keyword → Keyword)

围绕一个词继续扩展相关词、新词、长尾词。

- Google Suggest / Autocomplete
- Related Searches
- SERP title 中反复出现的 modifiers
- People Also Ask
- Trends rising queries
- existing keyword 的 long-tail variants

词找词回答的问题是：一个搜索入口附近还有哪些入口？主词通常竞争强，但 modifier 后的长尾词可能更弱、更具体、更容易做 MVP。词找词的价值在于把一个宽泛词拆成多个用户任务。

#### 常见 modifier 类型

- 价格：free、cheap、pricing、cost、calculator。
- 格式：template、pdf、excel、spreadsheet、csv。
- 行业：for dentists、for contractors、for Shopify、for landlords。
- 地区：US、UK、California、EU、Singapore。
- 对比：vs、alternative、compared、best。
- 工作流：workflow、automation、tracker、dashboard、generator。
- 痛点：late、failed、refund、chargeback、compliance、reconciliation。

#### 词找词示例

Seed：`shopify checkout`

扩展可能包括：

- `shopify checkout customization`
- `shopify checkout extensibility migration`
- `shopify checkout upsell app`
- `shopify checkout validation rules`
- `shopify checkout one page vs three page`

然后每个长尾词再进入词找站，观察 SERP 是否被官方文档、论坛或弱工具占据。

#### 词找词实现提示

- 当前系统可从 SERP title 中抽取 modifier，生成 `seed + modifier`。
- 可额外搜索 `seed vs`、`seed alternative`、`seed compared` 发现相邻需求。
- 需要去重，并保留 expansion_type：suggest、related、modifier、paa。
- 不要把噪音词直接变成机会；先进入 discovery expansion 表。
- 被导入主 keyword 表后，再进入原有 scoring pipeline。

### 站找站 (Site → Site)

从一个站找到类似站、竞品站、同类型高流量站。

- "alternative to X" 查询
- SimilarWeb 类似站
- Product Hunt / 工具导航站
- Reddit 推荐帖
- 竞品图谱

站找站回答的问题是：这个站所在的竞争集合是什么？单个竞品可能只是冰山一角。通过 alternative、sites like、best alternatives、vs 等查询，可以发现一个工具类别里更多玩家。

#### 站找站的价值

- 找到更多竞品，再做站找词。
- 判断市场是否已经成熟。
- 发现竞品共同弱点。
- 找到目录站和推荐帖，理解用户如何比较工具。
- 找到 affiliate 生态，判断变现可能。

#### 站找站示例

Seed domain：`typeform.com`

搜索：

- `alternative to typeform`
- `sites like typeform.com`
- `typeform vs`
- `best typeform alternatives`

可能发现：Jotform、Tally、Fillout、Google Forms、Paperform、Formstack。接着对这些域名做站找词，会发现 form builder、survey maker、quiz maker、lead capture form 等关键词簇。

#### 站找站实现提示

- 过滤 Google、YouTube、Wikipedia、Reddit 等泛域名。
- 记录 discovery_method：alternative_to、directory、reddit。
- 记录 source_url 和 title，方便判断来源质量。
- 类似站不一定都是直接竞品；可能是目录页、评论页、替代品聚合页。
- 对高质量 similar_domain 继续执行站找词，形成扩展循环。

## 完整链路

词根 → 词找词 → 词找站 → 站找词 → 站找站 → SERP 缺口 → 弱竞品 → MVP → 变现

完整链路可以拆成以下阶段：

1. 输入词根：来自 root library、用户灵感、竞品、趋势、社媒痛点。
2. 词找词：扩展长尾、对比、替代、地区、行业、格式词。
3. 词找站：检查 SERP 前排，识别站点类型和缺口。
4. 站找词：从竞品页面结构反推更多词。
5. 站找站：发现更多同类站和替代方案。
6. SERP 缺口：判断结果页是否有可切入空位。
7. 弱竞品：识别 UX、内容、新鲜度、定位、价格、功能缺陷。
8. MVP：定义能在短时间内验证的最小工具或页面。
9. 变现：匹配 ads、affiliate、SaaS、leadgen 或 freemium。
10. 评分：用统一权重决定 Action / Watch / Reject。

## SERP Gap Types

- tool_gap：用户需要工具，但结果没有工具
- fresh_data_gap：用户需要最新数据，但结果过时
- ui_gap：竞品功能有但体验差
- longtail_gap：主词竞争强，但长尾弱
- localization_gap：结果没有多语言/地区化
- comparison_gap：用户要比较，但缺清晰对比
- workflow_gap：用户要完成流程，但结果只是文章

### tool_gap

用户搜索的是可完成任务的词，例如 calculator、generator、checker、converter、tracker，但 SERP 主要是文章或 PDF。此时最小 MVP 通常是单页工具。

### fresh_data_gap

用户需要当前数据，例如法规、价格、平台政策、API 变化，但 SERP 页面更新时间很旧。MVP 可以是带更新时间、引用来源、自动刷新机制的数据页。

### ui_gap

竞品已有功能，但体验差：广告遮挡、加载慢、输入字段多、移动端不可用、结果不可复制。MVP 不需要功能更多，只要更快更清晰。

### longtail_gap

主词被强品牌占据，但长尾词没有专门页面。例如 `invoice template` 很难，但 `invoice template for roofing contractor` 可能可做。

### localization_gap

SERP 全是英文或美国语境，但用户需要本地法规、货币、格式或语言。适合做地区化页面或多语言工具。

### comparison_gap

用户搜索 vs、alternative、best，说明处于选择阶段。如果结果都是泛 listicle，缺少结构化对比表、价格更新和适用场景，就有机会。

### workflow_gap

用户要完成一个流程，但现有结果只解释概念。例如 `chargeback evidence template` 不只是文章需求，而是收集证据、生成文档、导出 PDF 的 workflow。

## 变现分型

- Ads only
- Affiliate
- SaaS
- Leadgen
- Tool freemium

### Ads only

适合高流量、低购买意图、工具简单的页面，例如通用 calculator、converter、template。要求 SEO 流量足够大，MVP 可以很轻。风险是 RPM 低、需要规模。

### Affiliate

适合用户处于比较和购买阶段的词，例如 best、alternative、pricing、software、app。要求能推荐第三方工具或服务，并保持内容可信。

### SaaS

适合重复使用、高痛点、业务流程相关需求，例如 reconciliation、dashboard、automation、compliance、integration。MVP 应验证付费意愿，而不只是搜索点击。

### Leadgen

适合法律、财务、医疗、本地服务、B2B 咨询等需求。页面或工具收集线索，再转给服务商或内部销售。要求合规与信任。

### Tool freemium

适合轻工具入口 + 高级功能升级，例如免费生成一次，付费批量导出、保存历史、团队协作、API、白标。

## 评分权重

- Demand Score: 25 (搜索需求强度)
- SERP Gap Score: 25 (搜索结果缺口)
- Competitor Weakness: 20 (竞品弱点)
- MVP Score: 15 (MVP 可执行性)
- Monetization Score: 15 (变现匹配度)

总分 = Demand × 0.25 + SERP Gap × 0.25 + Competitor Weakness × 0.20 + MVP × 0.15 + Monetization × 0.15。

### Demand Score

Demand Score 衡量是否存在真实搜索需求。可用信号包括 SERP 结果相关性、相关搜索数量、论坛提问、竞品页面数量、趋势上升、广告存在。没有需求信号的词，即使缺口明显，也只能 Watch 或 Reject。

### SERP Gap Score

SERP Gap Score 衡量现有搜索结果是否未充分满足任务。论坛占位、薄内容、过时内容、缺工具、低质量 AI 站、强品牌帮助文档不匹配，都可以提高 gap。强品牌高质量工具占位会降低 gap。

### Competitor Weakness

Competitor Weakness 衡量前排竞品是否可被替代。弱点包括 UI 差、速度慢、广告过多、功能缺失、价格不透明、没有导出、没有本地化、没有长尾页面。

### MVP Score

MVP Score 衡量能否快速做出最小可验证版本。输入输出明确的 calculator、generator、template、checker 得分高；需要复杂数据、资质、双边市场或大量人工运营的需求得分低。

### Monetization Score

Monetization Score 衡量变现方式是否与用户意图匹配。比较词适合 affiliate；流程词适合 SaaS；本地专业服务适合 leadgen；大流量轻工具适合 ads/freemium。

## Action / Watch / Reject 标准

### Action

满足：总分高、SERP 缺口明确、竞品弱、MVP 可在短周期上线、变现路径合理。Action 必须给出具体下一步，例如要做什么页面、输入字段、输出结果、首批长尾词。

### Watch

满足部分条件，但证据不足。例如需求存在但缺口不明显，或缺口存在但变现弱。Watch 应继续收集 SERP、社媒、竞品、趋势证据。

### Reject

不满足核心条件。常见原因：查询意图不匹配、强品牌过多、无明确任务、MVP 过重、变现弱、搜索入口太泛。Reject 不是失败，而是保护系统不被噪音污染。

## 数据表设计说明

四找发现数据应与主 keyword 表分离。原因是发现阶段会产生大量噪音，不能直接污染主机会池。

- discovery_expansions：存词找词结果。
- competitor_keywords：存站找词结果。
- competitor_sites：存站找站结果。
- keywords：只存被人工或规则确认导入的候选词。

每个 discovery row 应包含 status：new、imported、rejected。这样可以保留发现历史，也能避免重复导入。

## API 实现说明

后端应提供以下能力：

- `/api/discovery/expand`：输入 seed，执行词找词。
- `/api/discovery/find-sites`：输入 seed，执行词找站。
- `/api/discovery/site-keywords`：输入 domain，执行站找词。
- `/api/discovery/similar-sites`：输入 domain，执行站找站。
- `/api/discovery/run`：输入 seed，执行完整四找流水线。
- `/api/discovery/expansions`：列出发现词。
- `/api/discovery/competitor-keywords`：列出竞品词。
- `/api/discovery/similar-sites`：列出类似站。
- `/api/discovery/import-expansion/{id}`：导入词找词结果到主 keyword 表。
- `/api/discovery/import-competitor-keyword/{id}`：导入站找词结果到主 keyword 表。

## 前端实现说明

Discovery 页面应把四找方法呈现为可操作面板，而不只是报表。

- 左侧或上方输入 seed keyword，执行词找词和词找站。
- 另一个输入 domain，执行站找词和站找站。
- 提供完整 pipeline 按钮。
- 展示 Expanded Keywords、Competitor Keywords、Similar Sites 三类结果。
- 对 new 状态的 keyword 提供 Import 操作。
- 页面底部保留方法论卡片，帮助使用者理解当前系统在做什么。

## 质量控制

四找容易扩散出大量垃圾结果，因此必须有质量门槛：

1. 查询意图不匹配时不要导入。
2. 纯目录站、社媒首页、无关论坛帖不能当作强证据。
3. 竞品站必须保留 source_url 以便复核。
4. 导入主 keyword 表前应去重。
5. Action 机会必须有 SERP 证据和 MVP 计划。
6. 如果 SearXNG 返回 error row，不能把 error 当成发现结果。
7. 发现链路可以自动跑，但最终机会判断必须经过评分。

## 实战工作流

1. 从 Root Library 选一个方向，例如 `invoice`、`shopify`、`compliance`。
2. 在 Discovery 输入 seed keyword。
3. 查看词找词结果，挑选具体长尾导入。
4. 查看词找站结果，挑选弱竞品 domain。
5. 对 domain 执行站找词，发现更多竞品覆盖词。
6. 对 domain 执行站找站，扩展竞品集合。
7. 导入高质量 keyword 到主表。
8. 对导入 keyword 跑 SERP 和 card generation。
9. 对 Action / Watch / Reject 做反馈。
10. 把高质量发现沉淀回 roots、blocked terms、方法论。

## 示例：从一个 seed 到机会

Seed：`chargeback evidence template`

词找词可能发现：

- `chargeback rebuttal letter template`
- `stripe chargeback evidence template`
- `paypal chargeback response template`
- `chargeback evidence checklist`

词找站可能发现：

- 支付平台帮助文档
- 律所文章
- PDF 模板站
- Reddit 商家讨论

SERP 缺口：用户想生成 evidence packet，但结果多是文章和静态模板，存在 workflow_gap + tool_gap。

MVP：输入平台、交易信息、客户沟通、物流证据，生成 chargeback rebuttal packet 和 checklist。

变现：freemium 生成一次免费，付费导出 PDF、保存模板、批量处理；也可 leadgen 给支付争议服务。

## 反例：不应推进的词

Seed：`best crm software`

问题：强品牌和高权重 affiliate 站占满 SERP；CPC 高但竞争极强；MVP 不是简单工具；很难快速验证。除非发现具体长尾，如 `crm for dog grooming business`，否则应 Reject 或只做站找词研究。

## 迭代方向

未来四找系统可以继续增强：

- 接入真实 autocomplete API。
- 抓取 sitemap 并批量提取关键词。
- 用 LLM 对 SERP gap 做结构化分类。
- 引入 SimilarWeb / Ahrefs / Semrush 数据。
- 对 discovered keywords 自动跑轻量 scoring。
- 建立竞品图谱和关键词簇。
- 记录每个机会从哪个发现链路产生，方便复盘。

## 最终原则

四找不是为了多生成词，而是为了找到可验证、可执行、可变现的入口。每一次扩展都应该服务于一个判断：这个搜索需求是否能变成一个更好的工具、页面或产品？
