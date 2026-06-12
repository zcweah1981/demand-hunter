# damand-hunter 发现与证据系统重构方案 V2

> 状态：方案确认稿  
> 日期：2026-06-11  
> 基础：`docs/Messageinfo/messages.html` 讨论记录 + 当前 main 代码结构  
> 原则：完整规划、分阶段实施；不再设计“最小范围”作为目标，但实现必须可拆步推进。

## 1. 系统定位

`damand-hunter` 是一个证据驱动的自提升机会系统。

它的目标不是做采集器 Dashboard，也不是把 Four-Find 做成独立工作台，而是持续完成：

```text
发现入口
  ↓
候选入口池
  ↓
转译 / 验证 / 监控
  ↓
候选关键词
  ↓
质量评分
  ↓
关键词库
  ↓
SERP / 竞品 / MVP / 变现分析
  ↓
机会卡
  ↓
证据时间线与自动重评分
  ↓
机会推进
```

### 1.1 模型先行闭环

本轮确认后的核心原则：

```text
先有模型
  ↓
按模型去找证据
  ↓
证据产生入口 / 候选关键词 / 关键词 / 机会
  ↓
机会结果和人工反馈回到模型表现
  ↓
模型边界、权重、来源预算和运行策略持续调整
```

所以系统不是：

```text
来源 / 采集器 → 关键词 → 机会
```

而是：

```text
业务模型 / 四找模型
  ↓
证据采集与监控方式
  ↓
客观证据
  ↓
候选入口、候选关键词、关键词库、机会卡
  ↓
模型产出闭环
```

模型是闭环主体，证据是客观材料，机会是模型产出的业务结果。

### 1.2 四找模型归属

四找模型必须保留，但不再作为“机会发现”下的独立旧工作台，也不放进“来源表现”里解释。

四找属于 `证据系统 > 证据模型` 的核心模型：

```text
词找词：从 seed keyword 扩展更多用户表达
词找站：用关键词找到承接需求的网站 / 竞品 / 内容占位
站找词：从竞品站、sitemap、页面标题和内容反查关键词
站找站：从竞品和替代品扩展相邻站点与赛道
```

四找每一段都要能看到：

```text
使用了哪些证据来源
产生了哪些证据
产生了哪些入口
产生了哪些候选关键词
哪些进入关键词库
哪些生成机会卡
哪些被排除或需要补证
```

### 1.3 来源表现边界

`来源表现` 只看效果，不承载模型说明。

它回答：

```text
哪个来源 / 模型最近带来多少线索
多少入口、候选关键词、关键词和机会
有效 / 拒绝 / 异常分别是多少
哪些来源正在制造噪音
哪些来源值得增加预算
```

它不回答：

```text
Sitemap 是什么
网页内容识别是什么
四找模型是什么
哪个模型应该看哪里
```

这些统一放到 `证据系统 > 证据模型`。

## 2. 一级信息架构

采用四个一级模块：

```text
机会发现
证据系统
机会猎手
系统维护
```

### 2.1 机会发现

职责：

- 发现需求入口和趋势入口；
- 管理候选入口池；
- 管理候选关键词；
- 管理正式关键词库；
- 查看来源表现。

建议页面：

```text
总览
需求入口
趋势入口
候选入口
候选关键词
关键词库
来源表现
```

### 2.2 证据系统

证据系统独立成一级模块，但不是封闭模块。它是双向证据总线：

- 给候选入口、关键词、机会卡、推进项目补证据；
- 在验证和监控过程中发现新词、新页面、新实体、新域名；
- 把新发现回流到 `candidate_entries`。

建议页面：

```text
证据总览
证据任务
证据验证
变化追踪
证据记录
衍生入口
异常与修复
```

### 2.3 机会猎手

职责：

- 展示机会卡；
- 自动重评分；
- 展示证据时间线；
- 支持人工判断 Action / Watch / Reject / Adopted；
- Adopted 后进入机会推进。

建议页面：

```text
总览
机会
机会推进
```

### 2.4 系统维护

全局设置放在系统维护，不放在业务主流程里。

建议页面：

```text
运行历史
边界与偏好
API Key
自动化
来源预算
质量控制
高风险建议
异常修复
```

## 3. 核心对象

### 3.1 candidate_entries

候选入口池，承接所有入口对象。它不是关键词库。

入口类型：

```text
search_keyword
trend_entity
github_repo
tool_name
game
domain
product_name
feature
platform_update
```

状态：

```text
new
needs_evidence
scored
translated
rejected
promoted
```

### 3.2 candidate_keywords

候选搜索词池。包括：

- 需求入口直接产生的词；
- 趋势实体转译后的衍生词；
- 证据系统回流的新词；
- 竞品和 sitemap 监控产生的新词。

状态：

```text
new
needs_evidence
evidence_ready
scored
watch
rejected
promoted_to_keywords
```

### 3.3 keywords

正式关键词库。只存通过质量门、值得正式跑 SERP 的词。

### 3.4 evidence_items

客观证据本体。证据只记录事实，不直接表达结论。

建议字段：

```text
id
source_type
source_name
url
title
summary
raw_excerpt
captured_at
confidence
content_hash
raw_json
```

证据本体不记录：

```text
让谁涨分
让谁降分
应该修改哪个状态
```

### 3.5 evidence_links

证据服务关系。说明一条客观证据为谁服务。

建议字段：

```text
id
evidence_id
target_type
target_id
relation_type
relation_reason
created_by
created_at
```

同一条证据可以服务多个对象：

```text
candidate_entry
candidate_keyword
keyword
opportunity_card
mvp_project
progress_hypothesis
watch_target
```

### 3.6 source_runs

记录每次来源运行：

```text
source
source_role
run_kind
inputs_json
outputs_json
candidates_created
evidence_created
keywords_promoted
cards_generated
errors
duration_ms
```

### 3.7 watch_targets

变化追踪对象：

```text
competitor_page
pricing_page
changelog
docs_page
github_repo
game_wiki
steam_page
community_thread
sitemap
```

### 3.8 action_requests / action_events

人工按钮统一落到 `action_requests`，执行结果写入 `action_events`。

字段示例：

```text
action_type
target_type
target_id
risk_level
status
requested_by
reason
result_json
created_at
executed_at
```

## 4. 需求与趋势双评分链

需求入口和趋势入口不能共用同一条评分链。

### 4.1 需求入口链路

```text
需求入口
  ↓
搜索需求评分
  ↓
关键词质量门
  ↓
keywords
```

评分维度：

```text
需求明确度
商业意图
SERP 缺口
弱竞品
MVP 可执行性
变现路径
```

### 4.2 趋势入口链路

```text
趋势入口
  ↓
趋势实体评分
  ↓
趋势转译
  ↓
衍生候选关键词
  ↓
搜索需求评分
  ↓
关键词质量门
  ↓
keywords
```

趋势实体评分维度：

```text
热度增长
用户问题密度
生态空白
可工具化程度
可转译潜力
```

关键规则：

```text
趋势分不能替代关键词分。
趋势实体不能直接进入 keywords。
趋势实体只能决定是否值得投入转译和补证据预算。
衍生关键词必须重新按搜索需求质量门评估。
```

## 5. 证据系统的双向回流

证据系统输出两类结果：

```text
1. evidence_items + evidence_links
   为已有对象补证据。

2. derived entries
   把验证和监控过程中发现的新入口回流到 candidate_entries。
```

示例：

```text
Sitemap 监控一个新游戏
  ↓
发现 /builds、/items、/drop-rate、/market 页面
  ↓
写入 evidence_items
  ↓
建立 evidence_links，说明这些证据服务哪些对象
  ↓
同时生成衍生入口：
    [game] build planner
    [game] item database
    [game] drop rate calculator
    [game] market tracker
  ↓
回流 candidate_entries
  ↓
重新走需求评分或趋势评分
```

## 6. 证据时间线

证据是客观事实，不直接等同评分。

不同页面按语境解释证据：

### 6.1 关键词页面

展示：

- 新增证据；
- 来源贡献；
- 权重提升或降低；
- 为什么该词更值得或不值得进入 keywords。

### 6.2 机会页面

展示：

- 新增证据；
- 自动重评分；
- 每次评分变化前后对比；
- 本次重评分依据；
- SERP 缺口、竞品弱点、MVP、变现路径变化。

### 6.3 机会推进页面

展示：

- 新增证据；
- 它影响哪个 PRD 假设；
- 竞品、定价、MVP、SEO 方向变化；
- 下一步建议。

## 7. 证据驱动自提升

证据让每个环节都能改善：

```text
发现层：调整来源预算和优先级
趋势转译层：优化转译模板和衍生规则
质量门：调整成熟词 / 趋势衍生词阈值
关键词层：更新权重、待补证状态、优先级
机会层：自动重评分并记录依据
推进层：影响 PRD 假设、竞品追踪、MVP、定价、SEO
自动化层：调整运行周期、来源预算、监控频率、补证优先级
```

安全边界：

```text
低风险可自动：
来源预算微调、运行频率微调、关键词权重、补证优先级、转译模板排序。

中风险保守执行或只建议：
质量门阈值、来源降权、监控范围扩张。

高风险必须人工确认：
删除数据、Block、永久屏蔽、Adopted 状态变化、PRD 覆盖、MVP 投入。
```

## 8. 统一自动运行周期

V1 采用统一自动运行周期，不为每个模块或项目创建独立定时器。

规则：

```text
系统只有一个统一调度器。
所有对象只记录 next_due_at、priority、action_type。
统一周期触发后收集所有 due actions。
统一排序、预算分配、执行、记录结果、生成下一轮动作。
```

对象可以有 `next_due_at`，但不拥有自己的定时器。

后期如果某类任务证明需要不同频率、隔离失败、独立预算或更高实时性，再拆专用周期。

可能后期拆分：

```text
高频价格监控
GitHub repo watch
长耗时竞品抓取
PRD 深度验证
高频社区趋势监控
```

## 9. 页面语境按钮

人工按钮按页面语境分配，不强求统一文案。

原则：

```text
每页只保留 1-2 个主按钮。
异常时才出现“修复异常”。
高风险动作不放主按钮。
低频动作进入“更多”或详情页。
按钮是否显示由对象状态决定。
```

页面按钮建议：

```text
机会发现 / 候选入口：
手动抓取
推送到候选词

候选关键词 / 关键词库：
重新计算
补证据 / 推送到关键词库

证据系统：
重新验证
修正关联 / 补证据

机会页面：
重新计算
补证据 / 推送到机会推进

机会推进：
上传 / 更新 PRD
重新验证

系统维护：
运行一轮
修复异常
```

按钮底层仍统一写入 `action_requests`。

## 10. 完整实施阶段

### Phase 1：信息架构与导航

目标：

- 建立四个一级模块；
- 调整页面归属；
- 保留现有能力，不大改算法。

完成后系统应看起来是一套机会系统，而不是 Advanced / Collectors / Roots / Keywords 的松散组合。

### Phase 2：入口与候选池

目标：

- 新增 `candidate_entries`；
- 扩展 `candidate_keywords`；
- 明确入口、候选词、正式关键词库边界。

### Phase 3：需求与趋势双评分

目标：

- 成熟需求评分；
- 趋势实体评分；
- 趋势转译；
- 衍生词再过关键词质量门。

### Phase 4：证据系统 V1

目标：

- 新增 `evidence_items`；
- 新增 `evidence_links`；
- 证据任务和证据时间线；
- 证据服务对象可追踪。

### Phase 5：证据双向回流

目标：

- Sitemap、Domain Web、Four-Find、SERP、Alternatives 等证据过程可以生成衍生入口；
- 衍生入口统一回流 `candidate_entries`。

### Phase 6：自提升事件

目标：

- 关键词权重事件；
- 机会评分事件；
- 推进假设事件；
- 来源预算和质量门反馈事件。

### Phase 7：统一自动化周期

目标：

- 建立统一调度器；
- 全部对象通过 `next_due_at` 和 `action_type` 进入队列；
- 自动执行发现、趋势、证据、监控、评分、推进动作。

### Phase 8：页面语境按钮

目标：

- 每页 1-2 个主按钮；
- 异常时出现修复；
- 高风险动作进入更多或确认流程；
- 按钮统一落到 `action_requests`。

### Phase 9：机会推进整合

目标：

- PRD-first 验证；
- 证据时间线服务 PRD 假设；
- 竞品、定价、MVP、SEO 持续更新；
- 推进项目纳入统一自动周期。

### Phase 10：安全、审计与生产化

目标：

- 高风险动作确认；
- 操作审计；
- 数据一致性修复；
- 自动化异常恢复；
- 部署和回滚检查。

## 11. 验证标准

完整重构后，系统必须能回答：

```text
今天发现了哪些成熟需求入口？
今天捕捉了哪些趋势入口？
哪些趋势被转译成了候选关键词？
哪些候选关键词通过了质量门？
哪些证据服务了哪个入口、关键词、机会或 PRD 假设？
证据系统产生了哪些新入口并回流？
哪个来源真正贡献了有效机会？
关键词权重为什么变化？
机会为什么自动重评分？
PRD 假设被哪些证据支持或削弱？
统一自动周期本轮执行了哪些动作？
哪些异常需要人工修复？
哪些高风险动作等待人工确认？
```
