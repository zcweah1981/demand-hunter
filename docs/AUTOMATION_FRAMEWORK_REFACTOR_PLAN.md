# 机会发现统一自动化框架重构方案

## 1. 目标

本方案用于重构机会发现自动化，使系统从当前“旧 daily_run 黑盒流程 + 新 automation_cycle 占位框架”逐步演进为：

```text
统一自动化框架 + 模块独立执行器 + 手动/自动共用同一套后台服务代码
```

最终目标：

- 只有一个统一调度框架负责周期、队列、优先级、预算、锁、重试、异常和运行记录。
- 每个业务模块保留独立执行器，负责自己的业务动作。
- 手动按钮和自动周期不写两套逻辑，最终都创建或触发同一种 action。
- 所有线索、关键词、证据、机会都能追溯到输入对象、来源模型、运行批次和执行结果。
- 页面上的人工按钮必须能看到真实状态：已提交、排队中、运行中、完成、失败。
- 手动或自动执行时，前端必须有明确的运行进度和提示，避免用户不知道系统是否真的在运行。

## 2. 当前状态

当前代码中存在两套自动化逻辑。

### 2.1 新统一周期框架

`backend/app/automation_cycle.py` 已经提供了统一周期框架：

- 收集 `CandidateEntry`。
- 收集 `WatchTarget`。
- 收集 `ActionRequest`。
- 写入 `RunHistory(kind="automation_cycle")`。

但当前 `execute_action()` 主要还是占位逻辑：

- `candidate_entry` 只更新 `next_due_at`。
- `watch_target` 只更新 `last_run_at` 和 `next_due_at`。
- `action_request` 只标记为 executed。

也就是说，新框架有调度概念，但还没有真正接入采集、评分、补证据、SERP、机会生成等业务动作。

### 2.2 旧 daily_run 流程

`backend/app/services.py` 中的 `daily_run()` 仍然是真正产生机会发现结果的核心流程。

它会执行：

- collector autopilot。
- 清洗和导入候选关键词。
- 选择待处理关键词。
- 运行 SERP。
- 执行 SERP 准入判断。
- 生成或更新机会卡。
- 写入 `RunHistory(kind="daily")`。

问题是它是一个大黑盒：

- 难以解释每一步做了什么。
- 难以和线索模型库、线索池、关键词库、证据系统页面形成统一追溯。
- 手动和自动入口容易出现不同执行路径。
- 后续拆分模块和按钮语义会越来越困难。

### 2.3 手动和自动不一致

当前手动点击“运行一轮”会调用：

```text
POST /api/automation-cycle/run
```

接口默认 `run_legacy_daily=true`，因此会先执行旧 `daily_run()`，再执行新周期占位动作。

但后端启动后的后台定时循环调用：

```python
automation_cycle.run_automation_cycle(db, max_seconds=max_seconds)
```

没有显式传入 `run_legacy_daily=true`，因此后台定时运行不一定会跑完整旧机会发现流程。

这是当前自动化最需要修正的边界问题。

## 3. 总体架构

推荐架构分为四层。

```text
触发层
  手动按钮 / 定时器 / 系统状态变化

统一自动化层
  AutomationCycle
  ActionQueue / ActionRequest
  RunHistory / ActionEvent
  锁 / 预算 / 优先级 / 重试 / 异常

模块执行器层
  ClueModelExecutor
  ClueScoringExecutor
  EvidenceExecutor
  KeywordSerpExecutor
  KeywordScoringExecutor
  OpportunityExecutor
  WatchExecutor

业务服务层
  collectors
  clue services
  evidence services
  keyword services
  opportunity services
```

原则：

- 统一自动化层只负责“什么时候做、做哪些、谁先做、做完怎么记”。
- 模块执行器只负责“具体怎么做”。
- 业务服务层只负责可复用的业务能力。
- 页面按钮不直接写业务逻辑，只创建 action 或触发同一个 automation cycle。

## 4. 手动和自动统一原则

手动和自动不应该是两套代码。

区别只在于触发来源：

```text
auto   = 系统根据周期、状态、缺口自动创建 action
manual = 用户点击按钮创建高优先级 action
system = 系统内部联动创建 next action
```

示例：补证据。

```text
自动发现某线索缺证据
  -> create_action(type="evidence.backfill", trigger_source="auto")

用户点击“补证据”
  -> create_action(type="evidence.backfill", trigger_source="manual")

后台执行
  -> EvidenceExecutor.run(action)
```

页面按钮的作用不是“直接跑一段独立业务代码”，而是：

- 创建 action。
- 显示 action 状态。
- 必要时触发一轮自动化。
- 展示 action 结果和异常。

## 5. Action 数据模型

建议以现有 `ActionRequest` 为基础扩展，而不是重新造一套互不兼容的队列。

建议字段：

```text
id
action_type
target_type
target_id
trigger_source
priority
status
risk_level
run_id
payload_json
result_json
error_json
retry_count
max_retries
created_at
started_at
finished_at
```

字段含义：

- `action_type`：动作类型，例如 `clue_model.run`、`keyword.serp_analysis`。
- `target_type`：作用对象，例如 `clue_model`、`candidate_entry`、`keyword`、`watch_target`。
- `target_id`：具体对象 ID。
- `trigger_source`：`auto`、`manual` 或 `system`。
- `priority`：执行优先级。
- `status`：`pending`、`running`、`success`、`failed`、`skipped`、`retrying`。
- `payload_json`：执行输入。
- `result_json`：执行产出。
- `error_json`：异常详情。
- `run_id`：归属哪一轮自动化运行。

## 6. 执行结果标准

所有执行器返回统一结构，便于页面解释和后续联动。

```text
ok
status
summary
generatedClues
generatedKeywords
generatedEvidence
generatedOpportunities
inputRefs
errors
nextActions
metrics
```

关键要求：

- `inputRefs` 必须说明本轮用了哪些输入对象。
- `generatedClues` 必须说明本轮产生了哪些线索。
- `errors` 必须说明异常发生在哪个输入对象、错误是什么、是否可重试。
- `nextActions` 用于创建后续动作，例如补证据、SERP、生成机会。

示例：

```json
{
  "ok": true,
  "summary": "Google Suggest 产生 6 条线索",
  "inputRefs": [
    {
      "type": "keyword",
      "id": 12,
      "label": "compliance tracker"
    }
  ],
  "generatedClues": [
    {
      "text": "compliance tracker template",
      "type": "search_keyword",
      "source_model": "google_suggest"
    }
  ],
  "errors": [
    {
      "input": "expiredge.com",
      "message": "timeout",
      "retryable": true
    }
  ]
}
```

## 7. 执行器设计

每个执行器遵循统一接口。

```python
class Executor:
    action_type: str

    def can_run(self, action, db) -> bool:
        ...

    def run(self, action, db) -> ExecutionResult:
        ...
```

统一自动化框架通过 registry 分发：

```text
action_type -> executor
```

如果找不到 executor：

- action 标记为 failed。
- error_json 记录 `executor_not_found`。
- 页面显示异常处理入口。

## 8. 模块执行器清单

### 8.1 线索模型执行器

```text
action_type: clue_model.run
```

职责：

- 运行线索模型。
- 记录本轮输入对象。
- 记录本轮产生的线索。
- 记录异常。
- 将新线索写入线索池。

覆盖模型：

- Google Suggest
- Sitemap
- Domain Web
- Alternative
- Hot Topic
- SERP Search
- 词找词
- 词找站
- 站找词
- 站找站
- Social / Forum / Review
- Docs / Changelog / Pricing Pages
- GitHub / Product Hunt / Steam / arXiv

### 8.2 线索评分执行器

```text
action_type: clue.score
```

职责：

- 给线索池对象评分。
- 计算需求分、趋势分、总评分。
- 更新生命周期状态、处理状态、质量状态。
- 通过质量门后创建关键词入库 action。

评分底座：

```text
总评分 = 需求分 * 65% + 趋势分 * 35%
```

所有评分统一为 0-100，禁止出现 `8010.0` 这类比例错误。

### 8.3 证据执行器

```text
action_type: evidence.backfill
action_type: evidence.monitor
```

职责：

- 为线索、关键词、机会补充客观证据。
- 执行 sitemap、changelog、pricing、community、SERP 等监控。
- 将证据关联到服务对象。
- 新发现的词回流到线索池。

原则：

- 证据是客观事实。
- 证据不直接等于评分。
- 证据要说明为谁服务。

### 8.4 关键词 SERP 执行器

```text
action_type: keyword.serp_analysis
```

职责：

- 关键词入库后自动运行 SERP。
- 分析搜索意图。
- 分析竞争弱点。
- 分析 SERP 可切入度。
- 产出关键词阶段的机会判断依据。

原则：

- SERP 不应该依赖人工点击。
- 关键词库只展示已入库关键词。
- 已入库关键词应等待自动搜索分析，而不是人工逐个推进。

### 8.5 关键词评分执行器

```text
action_type: keyword.rescore
```

职责：

- 复用线索池统一评分底座。
- 补充关键词阶段指标。

关键词阶段可展示：

- SERP 可切入度。
- 竞争弱点。
- 商业承接度。
- 证据新鲜度。
- 机会生成状态。

### 8.6 机会生成执行器

```text
action_type: opportunity.generate
```

职责：

- 根据关键词、SERP、证据、质量门生成机会。
- 记录机会来源链路。
- 写入机会状态。

前置条件：

- 关键词已入库。
- SERP 已分析。
- 质量门通过。
- 证据足够或风险可接受。

### 8.7 监控执行器

```text
action_type: watch.run
```

职责：

- 运行变化监控。
- 监控 sitemap、changelog、pricing、社区、竞品、趋势实体。
- 发现新线索后写回线索池。

数据流：

```text
监控发现新词 -> generatedClues -> 线索池 -> 评分 -> 入库
```

## 9. 自动化周期执行流程

每一轮自动化应按以下步骤执行：

```text
1. 创建 automation_run
2. 收集 due actions
3. 按优先级和 due_at 排序
4. 根据预算分配执行
5. 分发给对应 executor
6. executor 写入结果
7. 写 ActionEvent / RunHistory
8. 根据 nextActions 创建后续 action
9. 更新目标对象状态
10. 生成本轮摘要
```

典型一轮：

```text
自动周期开始
  -> 运行到期线索模型
  -> 新线索进入线索池
  -> 到期线索评分
  -> 通过质量门的线索进入关键词库
  -> 入库关键词自动 SERP 分析
  -> SERP 通过后生成机会
  -> 证据和监控结果回流
  -> 写完整运行记录
```

## 10. 状态体系

系统统一采用三类状态。

### 10.1 生命周期状态

```text
新发现
候选
已入库
已生成机会
已过滤
```

### 10.2 处理状态

```text
等待自动推进
待补证据
需人工处理
运行中
异常待处理
```

### 10.3 质量状态

```text
通过
观察
拒绝
```

不同页面展示语境不同：

- 线索池：这个线索是否能进入关键词库。
- 关键词库：这个关键词是否完成 SERP，是否能生成机会。
- 机会页：这个机会是否值得继续推进。

## 11. 页面按钮原则

按钮不应过多，也不应绕过自动化框架。

### 11.1 线索模型库

- 运行模型
- 查看异常

### 11.2 线索池

- 补证据
- 重新评分

### 11.3 关键词库

- 补证据
- 重新计算

### 11.4 关键词详情

- 补证据
- 重新计算
- 运行 LLM 研判

### 11.5 机会页

- 重新评分
- 补证据
- 推进机会

按钮点击后必须有状态反馈：

```text
已提交任务
排队中
运行中
完成
失败
```

不能只在前端显示提示文字。

## 12. 运行进度与页面提示

手动或自动执行时，系统必须让用户清楚知道当前发生了什么。

### 12.1 全局运行提示

建议在页面顶部提供一个全局运行提示区，可以是浮动栏、顶部状态条或固定通知区域。

提示区用于展示：

- 当前是否有自动化任务正在运行。
- 正在执行哪一类动作。
- 当前阶段，例如排队中、运行中、写入结果、完成、失败。
- 本轮已处理数量、成功数量、失败数量。
- 最近一次异常或需要人工处理的问题。
- 可点击进入运行明细。

示例：

```text
正在运行：关键词 SERP 分析
已处理 8 / 20 · 成功 6 · 失败 1 · 需人工处理 1
查看运行明细
```

### 12.2 手动动作反馈

用户点击按钮后，页面不能只显示一次性提示，而要绑定真实 action 状态。

状态变化建议：

```text
已提交任务 -> 排队中 -> 运行中 -> 完成
已提交任务 -> 排队中 -> 运行中 -> 失败
```

失败时必须能查看：

- 哪个 action 失败。
- 作用对象是什么。
- 错误原因。
- 是否可重试。
- 下一步建议。

### 12.3 自动周期反馈

自动周期运行时，也需要在相关页面展示运行状态。

例如：

- 线索模型库：显示当前是否正在抓取线索模型。
- 线索池：显示是否有线索正在评分或补证据。
- 关键词库：显示是否有关键词正在 SERP 分析。
- 证据系统：显示是否有证据补充或监控任务正在执行。
- 机会页：显示是否有机会正在重评分或生成。

### 12.4 运行明细

全局提示和局部提示都应能进入运行明细。

运行明细至少展示：

- 运行批次。
- 触发来源：自动 / 手动 / 系统联动。
- 当前 action。
- 输入对象。
- 产出对象。
- 异常。
- 开始时间。
- 结束时间。
- 下一步动作。

这部分数据来自统一 action、executor result、RunHistory 和 ActionEvent，不允许每个页面自行拼接一套独立状态。

## 13. API 设计

### 13.1 Action API

```text
POST /api/actions
GET  /api/actions
GET  /api/actions/{id}
POST /api/actions/{id}/retry
POST /api/actions/{id}/cancel
```

创建 action 示例：

```json
{
  "action_type": "keyword.serp_analysis",
  "target_type": "keyword",
  "target_id": "123",
  "trigger_source": "manual",
  "priority": 80
}
```

### 13.2 Automation Cycle API

```text
POST /api/automation-cycle/run
GET  /api/automation-cycle/due
GET  /api/automation-cycle/runs
GET  /api/automation-cycle/runs/{id}
```

手动按钮可采用两种方式：

```text
方式 A：创建 action，等待周期执行
方式 B：创建 action 后立即触发一轮 cycle
```

无论哪种方式，业务执行代码都只走 executor。

## 14. 追溯要求

每个执行器必须记录：

```text
inputRef
generatedClues / generatedKeywords / generatedEvidence / generatedOpportunities
errors
```

系统必须能回答：

- 这个词从哪里来？
- 哪轮自动化产生？
- 哪个模型产生？
- 哪个输入对象产生？
- 后续进入了哪里？
- 为什么被拒绝？
- 为什么生成机会？
- 异常发生在哪个输入对象？
- 是否可以重试？

## 15. 迁移计划

### 阶段 1：统一入口

目标：

- 手动和自动都走 `automation_cycle`。
- 先不破坏现有可运行能力。

实施：

- 后台定时运行也进入完整 automation cycle。
- 将 `daily_run` 包装成 `LegacyDailyExecutor`。
- 手动运行和后台定时都通过 action / executor 触发旧流程。

结果：

```text
automation_cycle -> LegacyDailyExecutor -> daily_run
```

### 阶段 2：建立 Action / Executor 底座

目标：

- 建立 executor registry。
- 建立统一 ExecutionResult。
- ActionRequest 支持运行状态、结果、异常、重试和 run_id。

实施：

- 新增或扩展 action 状态字段。
- 实现 dispatcher。
- 实现通用 action 执行记录。
- API 返回用户能理解的状态。

### 阶段 3：接入线索模型执行器

目标：

- 线索模型库运行模型不再是假动作。
- 每个模型统一写 `generatedClues`、`inputRef`、`errors`。

实施：

- 将 collector autopilot 和单模型运行迁移到 `ClueModelExecutor`。
- 模型明细页读取 action run 和 source run。
- 输入对象效果只展示聚合后的对象，不重复显示同一对象。

### 阶段 4：接入线索评分执行器

目标：

- 线索池使用统一评分规则。
- 通过质量门后创建关键词入库 action。

实施：

- 统一需求分、趋势分、总评分。
- 修复评分比例错误。
- 状态体系统一为生命周期、处理、质量三类。

### 阶段 5：接入关键词 SERP 执行器

目标：

- 已入库关键词自动跑 SERP。
- 关键词库不再依赖人工 SERP 按钮。

实施：

- 关键词入库后创建 `keyword.serp_analysis` action。
- SERP 结果写入关键词详情。
- 失败时写异常，并允许重试。

### 阶段 6：接入证据执行器

目标：

- 补证据成为真实 action。
- 证据能服务线索、关键词、机会。

实施：

- 点击补证据创建 `evidence.backfill` action。
- 证据产生的新词写回线索池。
- 证据时间线能显示服务对象和影响。

### 阶段 7：接入机会生成执行器

目标：

- 关键词满足条件后自动生成机会。

实施：

- 根据 SERP、评分、证据、质量门创建 `opportunity.generate` action。
- 机会卡记录来源链路。
- 机会详情展示生成依据。

### 阶段 8：废弃 legacy daily 黑盒

目标：

- `daily_run` 不再作为核心自动化入口。
- 自动化完全由 action + executor 驱动。

实施：

- 将 daily_run 中剩余逻辑拆分到 executor。
- 保留兼容入口一段时间。
- 页面和 API 全部迁移到新执行器。

当前落地要求：

- `POST /api/automation-cycle/run` 默认不再执行 `daily_run`。
- 后台定时循环默认不再执行 `daily_run`。
- `daily_run` 仅通过 `run_legacy_daily=true` 作为兼容回退入口保留。
- 默认自动化周期由 `clue_model.run -> clue.score -> keyword.serp_analysis -> opportunity.generate` 等 executor 联动推进。
- 自动化周期必须写入 `RunHistory(status="running")` 并在每个 action 后刷新进度摘要，供页面顶部运行提示读取。
- 手动或自动触发后，前端必须立即提示“已提交/运行中”，并从 `ActionRequest` 与 `RunHistory` 的同一套状态数据刷新顶部状态栏，不能只依赖按钮旁的一次性文案。

## 16. 成功标准

完成后系统应满足：

- 后台定时和手动按钮调用同一套执行逻辑。
- 每个模块有独立 executor。
- 所有 action 有状态、运行记录、异常、结果。
- 手动和自动运行都有明确的前端进度提示。
- 手动按钮和自动周期必须共用同一套进度数据源，页面顶部需要有全局浮动/固定提示，关键页面需要能看到相关动作的排队、运行、完成、失败状态。
- 线索、关键词、证据、机会之间可追溯。
- 页面按钮不再是假动作。
- 关键词入库后自动 SERP。
- 证据监控产生的新词回到线索池。
- 旧 `daily_run` 不再是核心黑盒。
- 自动化周期能解释这一轮做了什么、为什么做、产出了什么、下一步是什么。

## 17. 推荐实施顺序

推荐按以下顺序落地：

1. 统一 Action / Executor 框架。
2. 将 `daily_run` 包成 `LegacyDailyExecutor`。
3. 接入真实线索模型执行器。
4. 接入关键词自动 SERP 执行器。
5. 接入证据执行器。
6. 接入机会生成执行器。
7. 最后拆掉 `daily_run` 黑盒。

这个顺序可以先修正手动和自动不一致的问题，同时保留当前可运行能力，再逐步把旧流程拆成可解释、可追溯、可复用的模块执行器。
