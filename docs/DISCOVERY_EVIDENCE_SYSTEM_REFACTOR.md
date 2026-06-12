# damand-hunter 发现与论证系统重构方案 V1

> 状态：设计稿 / 待实施  
> 目标分支：`refactor/discovery-evidence-system`  
> 原则：先理清系统逻辑，再逐步重构；不影响线上 `main/latest` 部署。

---

## 1. 一句话定位

damand-hunter 不是简单的关键词采集器，而是一个从 **成熟搜索需求、趋势实体、工具生态、竞品证据** 中持续发现、转译、论证、评分和推进机会的系统。

核心链路：

```text
边界与机会偏好
  ↓
候选入口发现
  ↓
候选入口池 candidate_entries
  ↓
机会验证 / 趋势转译
  ↓
候选关键词池 candidate_keywords
  ↓
成熟词 / 趋势实体双评分
  ↓
关键词库 keywords
  ↓
SERP 分析
  ↓
机会卡 opportunity_cards
  ↓
证据循环 / 竞品与趋势监控 / 重评分
  ↓
机会推进 / PRD-first 论证
```

---

## 2. 核心认知修正

### 2.1 不再把系统理解成单线条

旧理解：

```text
采集器 → 关键词 → SERP → 机会卡
```

新理解：

```text
搜索需求 + 新趋势 + 证据源 + 监控变化
  ↓
候选入口
  ↓
转译/验证/评分
  ↓
关键词与机会
  ↓
持续重评
```

### 2.2 来源不是固定角色

同一个来源在不同场景下可以承担不同任务：

- 发现成熟搜索需求；
- 捕捉新趋势实体；
- 验证候选词/机会/PRD；
- 持续监控竞品和趋势变化；
- 作为副产物补充新候选词。

---

## 3. 用户可理解的来源命名

避免使用“常规找词源 / 趋势实体源 / 论证源 / 监控源”这类抽象工程词。

推荐面向用户的命名：

| 旧名 | 新名 | 用户理解 |
|---|---|---|
| 常规找词源 | 搜索需求发现 | 找用户已经开始搜索的需求 |
| 趋势实体源 | 新趋势捕捉 | 抓刚火的新工具、新项目、新游戏、新模型、新平台变化 |
| 论证源 | 机会验证 | 判断候选词/趋势/机会是否真有价值 |
| 监控源 | 变化监控 | 持续看竞品、趋势、价格、文档、社区是否变化 |

推荐菜单短名：

```text
机会发现
  - 总览
  - 搜索需求
  - 新趋势
  - 机会验证
  - 变化监控
  - 候选入口
  - 关键词库
  - 来源表现
```

---

## 4. 边界与机会偏好

### 4.1 不设置“要找什么”

不要让用户一开始选择：

```text
我要找 SaaS / 跨境电商 / B2B
```

因为这会限制系统探索。

### 4.2 设置“不能碰什么”和“机会偏好”

#### 禁止范围

默认禁止：

```text
成人
赌博
灰产
违法
金融投资建议
医疗诊断
加密投机
政治操纵
重硬件
重线下交付
纯内容搬运
纯新闻资讯
低质量 AI 聊天壳
```

#### 机会偏好

默认偏好：

```text
工具类
小团队可做
可快速 MVP
有明确使用场景
有明确变现路径
可 SEO / 社区 / 开源生态获客
可做模板 / 计算器 / 插件 / 自动化 / 数据库 / 监控 / 目录
B2B / 跨境电商 / SaaS / 工具生态 / 新趋势衍生机会优先
```

这些不是硬限制，而是评分加权和质量门条件。

---

## 5. 候选入口池 candidate_entries

### 5.1 为什么需要 candidate_entries

现在系统太依赖 `keyword`，但很多早期机会一开始并不是搜索词。

例如：

```text
OpenClaw
nano banana
某个 GitHub repo
某个新游戏
某个 Shopify 新 API
某个竞品域名
```

这些是“入口对象”，不是最终关键词。

### 5.2 entry 类型

第一版支持：

```text
search_keyword       搜索词
trend_entity         趋势实体
github_repo          GitHub 项目
tool_name            工具名
game                 游戏
domain               网站/竞品域名
product_name         产品名
feature              新功能
platform_update      平台/API 更新
```

### 5.3 建议字段

```text
id
entry_type
name
source
source_role
source_url
raw_context_json
trend_score
maturity_type
status
created_at
updated_at
```

建议状态：

```text
new
needs_evidence
evidence_ready
translated
rejected
promoted
```

---

## 6. 搜索需求发现

目标：发现已经接近搜索需求的成熟词。

来源：

```text
Google Suggest
Short-tail Rewrite
Hot Topic
Roots Combo
Advanced Search
```

适合发现：

```text
shopify sales tax calculator
quickbooks paypal reconciliation
clinic no show reminder
invoice automation tool
compliance checklist template
```

输出：

```text
candidate_entries(entry_type=search_keyword)
candidate_keywords
```

---

## 7. 新趋势捕捉

目标：发现新工具、新项目、新游戏、新模型、新平台功能带来的早期机会入口。

### 7.1 第一版来源

优先：

```text
GitHub Trending / GitHub Search
Product Hunt
Hacker News / Reddit
Steam / SteamDB / 游戏趋势
```

后续：

```text
Hugging Face / Replicate / AI 模型趋势
平台 Changelog / Developer Docs
Twitch / YouTube Gaming
X / Discord
```

### 7.2 趋势实体不直接进 keywords

趋势实体需要先转译成工具词/任务词/商机词。

例如：

```text
OpenClaw
  ↓
OpenClaw skills marketplace
OpenClaw workflow templates
OpenClaw plugin directory
OpenClaw hosting
OpenClaw monitoring dashboard
```

```text
nano banana
  ↓
nano banana prompt templates
nano banana batch editor
nano banana API wrapper
nano banana for Shopify product photos
nano banana workflow automation
```

```text
新游戏
  ↓
[game] item database
[game] build planner
[game] gear calculator
[game] interactive map
[game] quest tracker
[game] market tracker
[game] drop rate calculator
[game] wiki
[game] server status
```

---

## 8. 机会验证

目标：验证候选入口是否有价值，把趋势实体转译成商机词，给机会卡/PRD 补证。

来源：

```text
四找
SERP
Domain Web
Sitemap
Alternatives / Compare
Social / Forum / Review
Docs / Changelog
Pricing Pages
```

### 8.1 四找定位

四找不是独立模块，也不只是找词工具。

它是：

```text
机会验证 + 扩展 + 趋势转译
```

四个动作：

```text
词找词：扩展需求表达
词找站：找承接该需求的网站 / 竞品 / 内容占位
站找词：从成熟站反查关键词
站找站：扩展竞品池 / 相邻赛道
```

### 8.2 四找的用途

候选词验证：

```text
candidate keyword
  ↓
词找站
  ↓
判断 SERP 里是强竞品、弱内容、工具空白，还是无需求
```

趋势实体转译：

```text
OpenClaw
  ↓
词找词 / 词找站 / 站找词
  ↓
OpenClaw skills / templates / hosting / plugin directory
```

机会卡补证：

```text
opportunity card
  ↓
四找
  ↓
找相邻竞品、替代方案、蓝海切口
```

机会推进：

```text
PRD
  ↓
提取产品关键词 / 竞品域名
  ↓
四找
  ↓
验证 PRD 假设、找竞品词、找未覆盖场景
```

---

## 9. 变化监控

目标：对已进入机会池或机会推进的竞品、工具、趋势实体做持续监控。

监控对象：

```text
已采纳机会的竞品站
Action / Watch 机会的核心 SERP 站点
趋势实体的 GitHub repo
新游戏的社区 / wiki / Steam 页面
平台 changelog
产品 pricing / changelog / docs 页面
```

监控结果：

```text
新页面
新功能
新定价
新集成
新用户问题
新教程/模板
新替代品
新讨论热度
```

触发：

```text
机会重新评分
PRD 改进建议
新候选关键词
竞品商业模式更新
```

---

## 10. candidate_keywords

candidate_keywords 是候选搜索词池，不是最终关键词库。

来源包括：

```text
搜索需求发现直接生成
新趋势转译生成
机会验证副产物生成
竞品站反查生成
机会推进中 PRD 分析生成
```

状态：

```text
new
needs_evidence
evidence_pending
scored
promoted_to_keywords
rejected
watch
```

进入 keywords 前必须经过：

```text
去重
禁区过滤
成熟词 / 趋势实体分类
机会验证证据补充
评分体系
质量门
```

---

## 11. 评分体系 V1

前期不要复杂化，只分两类：

```text
成熟词 Mature Keyword
趋势实体 Trend Entity
```

后续再根据反馈自我优化。

### 11.1 成熟词评分

适用对象：已经接近搜索需求的词。

维度：

```text
需求明确度
商业意图
SERP 缺口
MVP 可执行性
变现路径
```

每项 0-20，总分 100。

### 11.2 趋势实体评分

适用对象：新工具 / 新项目 / 新游戏 / 新模型 / 新功能 / 新平台。

维度：

```text
热度/增长
用户问题密度
生态空白
可工具化程度
衍生关键词质量
```

每项 0-20，总分 100。

### 11.3 关键规则

```text
趋势实体不能直接进 keywords。
趋势实体必须先转译成衍生关键词。
衍生关键词再按成熟词评分。
```

---

## 12. Keywords 关键词库

关键词库只存：

```text
已经通过质量门、值得正式跑 SERP 的搜索词。
```

它不是垃圾池，不应该直接接收所有候选词。

Keywords 进入后做：

```text
SERP 分析
竞品弱点分析
生成机会卡
```

---

## 13. Opportunity Evidence Loop

机会卡生成后不结束，进入证据循环。

```text
机会卡
  ↓
定期调用机会验证 / 变化监控
  ↓
四找 / SERP refresh / Domain Web / Sitemap / Alternatives / Social / Review
  ↓
生成 support / weaken / neutral 证据
  ↓
重新评分
  ↓
更新状态 / 分组 / PRD 建议
```

触发条件：

```text
新机会卡生成
机会进入 Action / Watch
机会被 Adopted
竞品有变化
趋势实体热度变化
PRD 上传或修改
定期验证周期到期
```

---

## 14. 机会推进中的验证

机会推进以 PRD 为主事实源。

```text
PRD
  ↓
提取核心需求 / ICP / 功能假设 / 竞品
  ↓
机会验证 / 变化监控
  ↓
找证据
  ↓
support / weaken / neutral
  ↓
PRD 改进建议
  ↓
商业模式判断
  ↓
MVP 决策
```

---

## 15. 来源表现 / ROI

所有来源都要记录 ROI，但不能简单比数量。

### 搜索需求 ROI

```text
产生候选词数
进入 keywords 数
生成机会卡数
Action 数
Reject 数
噪音率
```

### 新趋势 ROI

```text
发现趋势实体数
成功转译出关键词数
衍生关键词进入 keywords 数
生成机会卡数
趋势实体后续热度
```

### 机会验证 ROI

```text
验证候选数
support / weaken / neutral 证据数
推动重评分次数
发现新竞品数
补充衍生词数
推动机会状态变化次数
```

### 变化监控 ROI

```text
监控对象数
发现变化数
变化有效率
触发 PRD 改进数
触发机会重评分数
```

---

## 16. 自动化边界

系统自动做：

```text
抓趋势实体
抓成熟词
生成 candidate_entries
生成 candidate_keywords
机会验证补证
转译趋势实体
评分
入库 keywords
SERP 分析
生成机会卡
定期重评分
来源 ROI 统计
低风险修复
```

人必须做：

```text
设置不能碰的边界
设置机会偏好
确认高风险清理
决定 Adopted
决定是否进入产品推进
确认 PRD 方向
确认 MVP 投入
```

高风险动作只给建议，不自动执行：

```text
删除数据
批量 Block
永久屏蔽词/域名/来源
大规模降权
清空 rejected
修改已采纳机会状态
覆盖有效 PRD/评分
```

---

## 17. 推荐菜单结构

```text
机会发现
  - 总览
  - 搜索需求
  - 新趋势
  - 机会验证
  - 变化监控
  - 候选入口
  - 关键词库
  - 来源表现

机会猎手
  - 总览
  - 机会
  - 机会推进

系统维护
  - 运行历史
  - 边界与偏好
  - 高风险清理建议
```

---

## 18. 阶段实施建议

### Phase 1：信息架构与解释层

目标：先把现有功能按新逻辑解释清楚，不大改算法。

做：

```text
重排菜单
新增机会发现总览说明
把四找标注为机会验证/扩展能力
把 Keywords 解释为通过质量门后的词库
新增边界与偏好设置 UI 占位
来源表现按“搜索需求 / 新趋势 / 机会验证 / 变化监控”分组
```

### Phase 2：candidate_entries + 新趋势捕捉

目标：系统开始支持非关键词入口。

做：

```text
新增 candidate_entries 表
接入 GitHub Trending / Steam 趋势第一版
趋势实体转译成 candidate_keywords
```

### Phase 3：机会验证编排

目标：四找 / domain_web / sitemap / alternatives 统一服务候选词、机会卡、PRD。

做：

```text
四找结果进入 candidate_keywords
四找写 source_roi
Domain Web/Sitemap/Alternatives 输出 evidence_items
Opportunity Evidence Loop 初版
```

### Phase 4：评分与自学习

目标：成熟词 / 趋势实体双评分体系上线，并根据反馈迭代。

做：

```text
成熟词评分
趋势实体评分
质量门
来源 ROI
反馈回流
自动调权
高风险清理建议
```

---

## 19. 第一版最小可执行 MVP

建议第一版只做：

```text
1. 边界与偏好设置
2. candidate_entries 表
3. GitHub Trending + Steam 趋势实体源
4. 趋势实体 → 衍生关键词模板
5. 四找接入 candidate_keywords
6. 成熟词 / 趋势实体双评分
7. 来源表现按角色展示
```

暂时不做：

```text
复杂机器学习模型
复杂行业 taxonomy
全量社媒抓取
大规模自动清理
多层 PRD 自动改写
```

---

## 20. 成功标准

系统能回答：

```text
今天发现了哪些成熟搜索需求？
今天捕捉了哪些新趋势？
哪些趋势被转译成了可做的工具机会？
哪些候选入口通过了质量门？
哪个来源贡献了真正机会？
哪个验证源提供了关键证据？
哪些机会因为新证据需要重评分？
哪些竞品值得持续监控？
哪个 PRD 假设被支持或削弱？
```
