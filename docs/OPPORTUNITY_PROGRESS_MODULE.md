# 机会推进模块 / Opportunity Progress Module

## 目标

机会推进模块用于处理已经被用户确认采纳的机会（Adopted），把机会从“发现/判断”推进到“PRD 验证、竞品追踪、Sitemap 监控、SERP 补证、商业策略、定价策略、SEO/推广/迭代建议”。

它不是机会发现模块，也不是复核模块；它是 Action/Adopted 之后的持续验证与推进系统。

## 硬规则

1. 只有 `Adopted` 机会组可以创建机会推进项目。
2. 上传或填写 PRD 后，才允许启动竞品/Sitemap/SERP/商业策略挖掘。
3. PRD 是推进系统的边界来源：竞品、关键词、Sitemap、SEO、定价和推广建议都必须围绕 PRD 与机会组证据生成。
4. 如果可行性降低，系统必须明确提示并给出 PRD 调整建议。
5. 如果机会继续成立，系统必须进一步给出 MVP、定价、SEO、推广、迭代策略。
6. 不做最小实现；模块第一版就要形成完整闭环，只是每个能力可以先用现有采集器/搜索/LLM 能力实现。

## PRD 输入方式

### 页面编辑 / 上传

用户在机会推进详情页上传或编辑 PRD 内容。

### 文件落盘

同时保存到：

```text
demand-hunter/prds/<project_slug>/PRD.md
```

这样 PRD 可版本化、可导出、可持续迭代。

## 页面结构

一级仍在“机会猎手”下，新增二级菜单：

```text
总览
机会
机会推进
```

路径：

```text
/hunter/progress
/hunter/progress/[id]
```

## 机会推进项目

每个项目绑定一个 opportunity group：

- opportunity_group_id
- canonical_keyword
- representative_card_id
- PRD path/content/version
- feasibility score
- risk level
- status
- last validated at
- next action

## 验证流程

### 1. PRD 审核

LLM 读取 PRD + 机会组证据，检查：

- ICP 是否明确
- 痛点是否具体
- MVP 范围是否过大
- 首个付费触发是否明确
- 第一笔钱测试是否存在
- 定价是否可验证
- SEO 入口是否对应机会关键词
- 风险与待补证据

输出：

- PRD 可行性评分
- PRD 缺口
- 风险项
- 修改建议
- 下一步验证计划

### 2. 竞品发现

从 PRD 和机会组生成竞品搜索 query，使用现有采集器和 SERP 能力寻找：

- 直接竞品
- 替代方案
- 模板/工具/计算器竞品
- SaaS / API / marketplace / directory 页面

保存 tracked competitors。

### 3. Sitemap / 页面监控

对竞品追踪：

- sitemap.xml
- pricing
- docs
- blog
- templates
- calculators/tools
- changelog
- integrations

记录新增页面、页面变化、内容 hash、摘要。

### 4. SERP 补证

围绕 PRD 生成：

- 核心词
- 长尾词
- 替代词
- 价格词
- 模板词
- calculator/checker/generator 词
- 竞品 alternative 词

跑搜索验证：

- SERP 是否仍有缺口
- 是否被强竞品占据
- 是否有付费/工具/模板需求
- 是否有搜索意图错配

### 5. 商业策略与定价

输出：

- MVP 范围调整
- 首个功能优先级
- 定价策略
- 免费/付费边界
- SEO 页面策略
- 推广渠道
- 用户验证动作
- 后续迭代路线

## 自动通知条件

### 可行性降低

- 强竞品占据 SERP
- 竞品推出免费工具
- 搜索意图变弱或偏信息词
- PRD 范围过大
- 找不到付费触发
- Sitemap 发现竞品快速扩张同类页面

### 可继续推进

- 发现新弱竞品
- SERP 缺口增强
- 竞品定价高且体验弱
- 搜索证据变强
- 出现明确社区痛点
- PRD 范围可控且第一笔钱测试明确

## 数据模型

### MvpProject

- id
- opportunity_group_id
- canonical_keyword
- representative_card_id
- status
- prd_path
- prd_version
- prd_content
- feasibility_score
- risk_level
- next_action
- created_at
- updated_at
- last_validated_at

### MvpValidationRun

- id
- project_id
- kind
- status
- summary_json
- score_delta
- started_at
- finished_at

### TrackedCompetitor

- id
- project_id
- domain
- name
- url
- pricing_url
- sitemap_url
- status
- notes
- last_seen_at
- created_at

### CompetitorSnapshot

- id
- competitor_id
- snapshot_type
- url
- title
- content_hash
- summary_json
- created_at

### MvpStrategyRecommendation

- id
- project_id
- type
- title
- content
- confidence
- status
- created_at

## 第一版实现范围

第一版直接完整打通闭环：

1. Adopted 机会创建推进项目。
2. PRD 上传/编辑并保存到 `prds/<slug>/PRD.md`。
3. PRD LLM 审核。
4. 竞品发现 query 生成并跑搜索。
5. 保存竞品与 Sitemap 监控目标。
6. SERP 补证。
7. 输出可行性评分、风险变化、PRD 修改建议、MVP/定价/SEO/推广/迭代策略。
8. 页面展示项目列表、项目详情、验证记录、竞品、策略建议。

## 与现有模块关系

- 机会页：只有 Adopted 机会显示“创建推进项目”。
- 采集器：推进项目会提供竞品域名、关键词、Sitemap 目标作为采集目标。
- 自动运行记录：后续增加“推进项目验证”任务。
- 通知：可行性降低或增强时推送用户。
