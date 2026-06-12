'use client'

import {useState} from 'react'
import {ContextActions} from './ContextActions'
import {EvidenceTimeline} from './EvidenceTimeline'
import {ScoreHistory} from './ScoreHistory'
import {keywordApi, KeywordLlmAnalysis} from '../lib/api'

type Tone = 'blue' | 'green' | 'amber' | 'red' | 'slate' | 'purple'

const toneClass: Record<Tone, string> = {
  blue: 'border-blue-500/30 bg-blue-500/10 text-blue-200',
  green: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  amber: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  red: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
  slate: 'border-slate-700 bg-slate-900 text-slate-300',
  purple: 'border-purple-500/30 bg-purple-500/10 text-purple-200',
}

const LIFECYCLE_HELP = [
  ['新发现', '刚进入系统或历史状态仍未转译，尚未完成关键词验证。'],
  ['候选', '已具备一定搜索表达，但还需要补证据、转译或等待自动任务。'],
  ['已入库', '已经是正式关键词库对象，后续由自动流程跑 SERP、竞品和机会评分。'],
  ['已生成机会', '已经生成机会卡，后续进入机会页面或机会推进。'],
  ['已过滤', '被判定为噪音、重复、异常或低价值，不继续自动推进。'],
]

const PROCESSING_HELP = [
  ['待补证据', '当前缺少 SERP、竞品、社区或来源证据，需要补充后再判断。'],
  ['等待自动推进', '不需要人工点按钮，等待统一自动任务继续处理。'],
  ['需人工处理', '出现异常、冲突或无法自动判断的场景，需要人工修复。'],
]

const QUALITY_HELP = [
  ['通过', '当前客观检查支持继续推进。'],
  ['观察', '暂未拒绝，但证据或分数不足。'],
  ['拒绝', '质量门不通过，通常是噪音、重复或明确不适合推进。'],
]

function Badge({children, tone = 'slate'}: {children: React.ReactNode; tone?: Tone}) {
  return <span className={`inline-flex rounded-xl border px-3 py-1 text-xs font-semibold ${toneClass[tone]}`}>{children}</span>
}

function HelpTip({items, text}: {items?: string[][]; text?: string}) {
  return (
    <span className="group relative inline-flex align-middle">
      <span className="ml-1 inline-flex h-5 w-5 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-xs text-blue-200">?</span>
      <span className="pointer-events-none absolute left-0 top-7 z-30 hidden w-80 rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs leading-5 text-slate-300 shadow-2xl group-hover:block">
        {text}
        {items?.map(([label, body]) => <span key={label} className="mb-2 block"><b className="text-slate-100">{label}</b>：{body}</span>)}
      </span>
    </span>
  )
}

function fmtDate(value?: string | null) {
  if (!value) return '暂无'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {hour12: false})
}

function scoreValue(value: unknown) {
  const n = Number(value || 0)
  if (!Number.isFinite(n) || n <= 0) return null
  if (n <= 1) return n * 100
  if (n > 100) return Math.min(100, n / 100)
  return n
}

function scoreText(value: unknown) {
  const n = scoreValue(value)
  return n == null ? '待自动评分' : n.toFixed(1)
}

function sourceLabel(raw: string) {
  const map: Record<string, string> = {
    root_combo: '词根组合',
    keyword_engine: '关键词引擎',
    manual: '人工添加',
    'collector:google_suggest': 'Google Suggest',
    'collector:duckduckgo': 'DuckDuckGo Suggest',
    'collector:suggest': '词找词',
    'collector:short_tail_rewrite': '短词改写',
    'collector:sitemap': 'Sitemap',
    'collector:domain_web': '网页内容识别',
    'collector:alternatives': '替代品/对比挖掘',
    'collector:hot_topic': '热点任务补充',
    'collector:advanced_search': 'SERP 搜索',
  }
  if (raw?.startsWith('four_find:')) return `四找 · ${raw.split(':')[1]}`
  return map[raw] || raw || '未知来源'
}

function rootMeta(rootTerms: unknown) {
  if (rootTerms && typeof rootTerms === 'object' && !Array.isArray(rootTerms)) return rootTerms as Record<string, any>
  if (Array.isArray(rootTerms)) return {terms: rootTerms}
  return {}
}

function inputObject(kw: any, meta: Record<string, any>) {
  if (meta.input_ref?.label) return meta.input_ref.label
  if (meta.source_domain) return `网站 · ${meta.source_domain}`
  if (Array.isArray(meta.terms) && meta.terms.length) return `词根 · ${meta.terms.join(' + ')}`
  if (Array.isArray(kw.root_terms) && kw.root_terms.length) return `词根 · ${kw.root_terms.join(' + ')}`
  return '历史数据缺少输入对象'
}

function statusModel(kw: any, data: any) {
  const hasSerp = Boolean(data.serp?.length)
  const hasCard = Boolean(data.cards?.length)
  const hasEvidence = Boolean(data.social?.length)
  const raw = String(kw.status || '')
  if (['reject', 'rejected', 'block', 'serp_reject', 'rewrite_exhausted'].includes(raw)) {
    return {
      decision: '需人工处理',
      lifecycle: '已过滤',
      processing: '需人工处理',
      quality: '拒绝',
      tone: 'red' as Tone,
      summary: '当前关键词被异常、拒绝或暂停状态拦截。需要先查看失败原因，修复后才能重新进入自动流程。',
      nextTitle: '修复异常',
      nextBody: '处理搜索异常、重复判断或来源冲突，再等待下一轮自动任务重新分析。',
      action: 'repair' as const,
    }
  }
  if (hasCard) {
    return {
      decision: '已生成机会',
      lifecycle: '已生成机会',
      processing: '等待人工查看',
      quality: '通过',
      tone: 'green' as Tone,
      summary: '关键词已经完成搜索分析，并被机会系统转成机会卡。详情页重点查看证据是否充分，以及机会是否值得推进。',
      nextTitle: '查看机会',
      nextBody: '后续判断应在机会页面完成，关键词页只保留来源和评分追溯。',
      action: 'none' as const,
    }
  }
  if (hasSerp && hasEvidence) {
    return {
      decision: '等待机会评分',
      lifecycle: '已入库',
      processing: '等待自动推进',
      quality: '观察',
      tone: 'blue' as Tone,
      summary: '关键词已有搜索结果和部分证据，下一步由自动任务结合证据和竞争弱点判断是否生成机会。',
      nextTitle: '等待自动推进',
      nextBody: '不需要手动运行 SERP；统一自动任务会继续计算机会评分。',
      action: 'none' as const,
    }
  }
  if (hasSerp) {
    return {
      decision: '待补证据后再判断',
      lifecycle: '已入库',
      processing: '待补证据',
      quality: '观察',
      tone: 'amber' as Tone,
      summary: '关键词已有搜索结果，但缺少社区、来源或变化证据。当前只能观察，不能直接生成强结论。',
      nextTitle: '补充客观证据',
      nextBody: '需要补 SERP 以外的证据，例如社区讨论、竞品页面、定价页、changelog 或站点变化。',
      action: 'evidence' as const,
    }
  }
  return {
    decision: '等待自动搜索分析',
    lifecycle: '已入库',
    processing: '等待自动推进',
    quality: '观察',
    tone: 'amber' as Tone,
    summary: '关键词已经入库，但还没有完成自动搜索分析。它不应该依赖手动按钮推进，而是等待统一自动任务运行。',
    nextTitle: '等待自动任务运行 SERP',
    nextBody: '自动任务完成后，这里会出现 SERP、竞品弱点和机会评分依据。',
    action: 'none' as const,
  }
}

function scoreModel(data: any) {
  const card = data.cards?.[0]
  const serp = data.serp || []
  const competitors = data.competitors || []
  const demand = scoreValue(card?.demand_score)
  const trend = scoreValue(data.keyword?.score)
  const serpGap = scoreValue(card?.serp_gap_score)
  const weakness = scoreValue(card?.competitor_weakness_score)
  const total = demand != null && trend != null ? demand * 0.65 + trend * 0.35 : scoreValue(card?.score ?? data.keyword?.score)
  return {
    demand,
    trend,
    total,
    serpGap,
    weakness,
    hasUnified: demand != null && trend != null,
    notes: [
      demand == null ? '需求分：缺少候选词统一评分或机会需求分，等待自动评分补齐。' : `需求分：${demand.toFixed(1)}，来自机会/关键词需求评估。`,
      trend == null ? '趋势分：缺少线索池趋势信号，等待来源模型回补。' : `趋势分：${trend.toFixed(1)}，暂用关键词当前分作为趋势/热度近似。`,
      serp.length ? `SERP：已有 ${serp.length} 条搜索结果。` : 'SERP：尚未完成自动搜索分析。',
      competitors.length ? `竞品弱点：已有 ${competitors.length} 条竞品页面记录。` : '竞品弱点：尚未形成记录。',
    ],
  }
}

function LlmSection({keywordId}: {keywordId: number}) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<KeywordLlmAnalysis | null>(null)
  const [error, setError] = useState('')
  async function run() {
    setOpen(true)
    setLoading(true)
    setError('')
    try {
      setResult(await keywordApi.llmAnalysis(keywordId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'LLM 研判失败')
    } finally {
      setLoading(false)
    }
  }
  return (
    <section className="panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white">LLM 客观研判 <HelpTip text="LLM 只作为独立客观打分项，不使用系统已有分数反向论证。当前按需运行，不长期保存。" /></h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">默认收起。需要时基于关键词、SERP、竞品弱点、证据和机会记录做一次独立语义判断。</p>
        </div>
        <button className="btn" disabled={loading} onClick={run}>{loading ? '研判中...' : '运行 LLM 研判'}</button>
      </div>
      {!open && <button type="button" className="mt-4 w-full rounded-2xl border border-slate-800 bg-slate-950 p-4 text-left text-sm font-bold text-slate-200 hover:border-blue-900" onClick={() => setOpen(true)}>▸ 展开完整分析</button>}
      {open && (
        <div className="mt-4 space-y-3">
          {error && <div className="rounded-xl border border-rose-900/70 bg-rose-950/20 p-3 text-sm text-rose-200">{error}</div>}
          {!result && !error && <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">尚未运行 LLM 研判。</div>}
          {result && !result.ok && <div className="rounded-xl border border-amber-900/70 bg-amber-950/20 p-4 text-sm leading-6 text-amber-100">{result.message || 'LLM 当前不可用。'}</div>}
          {result?.ok && result.analysis && (
            <div className="space-y-3">
              <div className="rounded-2xl border border-blue-900/70 bg-blue-950/20 p-4">
                <div className="text-sm text-blue-200">LLM 判断</div>
                <div className="mt-2 text-2xl font-black text-white">{result.analysis.verdict}</div>
                <p className="mt-3 text-sm leading-6 text-slate-300">{result.analysis.summary}</p>
                <p className="mt-3 text-sm leading-6 text-slate-400">需求解释：{result.analysis.demand_interpretation || '暂无'}</p>
                <div className="mt-3 text-xs text-slate-500">长期关注匹配度：{result.analysis.long_term_fit}</div>
              </div>
              <ListBlock title="风险" items={result.analysis.risks} />
              <ListBlock title="建议补证和下一步" items={result.analysis.evidence_to_collect.concat(result.analysis.next_actions)} />
            </div>
          )}
          <button type="button" className="w-full rounded-2xl border border-slate-800 bg-slate-950 p-4 text-left text-sm font-bold text-slate-200 hover:border-blue-900" onClick={() => setOpen(false)}>▾ 收起完整分析</button>
        </div>
      )}
    </section>
  )
}

export function KeywordDetailContent({data, compact = false}: {data: any; compact?: boolean}) {
  const kw = data.keyword
  const id = Number(kw.id)
  const meta = rootMeta(kw.root_terms)
  const state = statusModel(kw, data)
  const score = scoreModel(data)
  const input = inputObject(kw, meta)
  const source = sourceLabel(kw.source)
  const cards = data.cards || []
  const serp = data.serp || []
  const social = data.social || []
  const headerClass = compact ? 'rounded-2xl border border-slate-800 bg-slate-950/50 p-5' : 'rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl'

  return (
    <div className="space-y-5">
      <section className={headerClass}>
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Keyword Detail</p>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className={compact ? 'break-words text-3xl font-black text-white' : 'break-words text-4xl font-black text-white'}>{kw.query}</h1>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Badge tone={state.tone}>{state.decision}</Badge>
              <Badge tone={state.quality === '通过' ? 'green' : state.quality === '拒绝' ? 'red' : 'amber'}>{state.quality}</Badge>
              <Badge>{source}</Badge>
            </div>
          </div>
          <div className="grid min-w-[260px] grid-cols-2 gap-3">
            <Info label="总评分" value={score.total == null ? '待自动评分' : score.total.toFixed(1)} />
            <Info label="入库时间" value={fmtDate(kw.created_at)} />
          </div>
        </div>

        <div className="mt-5 rounded-3xl border border-slate-800 bg-slate-950/60 p-5">
          <div className="grid gap-5 xl:grid-cols-[1fr_0.9fr]">
            <div>
              <div className="text-sm font-semibold text-blue-300">关键词研判</div>
              <p className="mt-3 text-sm leading-7 text-slate-300">{state.summary}</p>
              <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <h3 className="font-bold text-white">{state.nextTitle}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">{state.nextBody}</p>
                {state.action === 'repair' && <div className="mt-3"><ContextActions actions={[{label: '修复异常', actionType: 'keyword.repair', targetType: 'keyword', targetId: id}]} /></div>}
                {state.action === 'evidence' && <div className="mt-3"><ContextActions actions={[{label: '补证据', actionType: 'keyword.collect_evidence', targetType: 'keyword', targetId: id}]} /></div>}
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
              <StatusBox title="生命周期" value={state.lifecycle} help={LIFECYCLE_HELP} />
              <StatusBox title="处理状态" value={state.processing} help={PROCESSING_HELP} />
              <StatusBox title="质量状态" value={state.quality} help={QUALITY_HELP} />
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="panel">
          <h2 className="text-2xl font-bold text-white">评分与质量门 <HelpTip text="关键词库会逐步统一到线索池评分体系。需求分用于判断是否像真实搜索需求，趋势分用于判断近期关注强度，总评分用于排序，不直接替代机会结论。" /></h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Info label="总评分" value={score.total == null ? '待自动评分' : score.total.toFixed(1)} />
            <Info label="SERP 缺口" value={score.serpGap == null ? '待机会评分' : score.serpGap.toFixed(1)} />
            <Info label="竞品弱点" value={score.weakness == null ? '待机会评分' : score.weakness.toFixed(1)} />
            <Info label="评分版本" value={score.hasUnified ? '统一评分' : '历史/待补齐'} />
          </div>
          <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
            <p>{score.hasUnified ? `总评分 = 需求分 * 65% + 趋势分 * 35%。当前总评分为 ${score.total?.toFixed(1)}。` : '当前关键词缺少完整统一评分字段，页面只展示已有信号，不用 0 分冒充结论。'}</p>
            <ul className="mt-3 space-y-1 text-slate-400">{score.notes.map((note, index) => <li key={index}>{note}</li>)}</ul>
          </div>
        </div>
        <div className="panel">
          <h2 className="text-2xl font-bold text-white">来源与搜索状态</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-center">
            <Info label="输入对象" value={input} />
            <span className="hidden text-slate-500 md:block">→</span>
            <Info label="来源模型" value={source} />
            <span className="hidden text-slate-500 md:block">→</span>
            <Info label="关键词" value={kw.query} />
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Info label="来源标识" value={kw.source || '未知'} mono />
            <Info label="最近自动分析" value={fmtDate(serp[0]?.fetched_at || cards[0]?.created_at)} />
          </div>
          {!serp.length && (
            <div className="mt-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4">
              <Badge tone="amber">等待统一自动任务</Badge>
              <p className="mt-3 text-sm leading-6 text-slate-300">关键词入库后应由统一自动任务跑 SERP，这里只展示状态，不提供手动搜索按钮。</p>
            </div>
          )}
        </div>
      </section>

      {serp.length > 0 && (
        <section className="panel">
          <h2 className="text-2xl font-bold text-white">自动搜索分析</h2>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {serp.slice(0, 8).map((row: any) => (
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4" key={row.id}>
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span>#{row.rank}</span>
                  <span>{row.domain}</span>
                  {row.weakness_score != null && <span className="text-amber-300">弱点 {scoreText(row.weakness_score)}</span>}
                </div>
                <a className="mt-2 block text-sm font-semibold text-blue-200 hover:underline" href={row.url} target="_blank" rel="noreferrer">{row.title}</a>
                {row.snippet && <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-400">{row.snippet}</p>}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="panel">
          <h2 className="text-2xl font-bold text-white">客观证据</h2>
          {social.length ? (
            <div className="mt-4 space-y-2">
              {social.slice(0, 8).map((row: any) => (
                <a className="block rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-blue-200 hover:border-blue-500/40" href={row.url} target="_blank" rel="noreferrer" key={row.id}>
                  <span className="text-xs text-slate-500">{row.platform}</span>
                  <span className="ml-2">{row.title || row.snippet || row.url}</span>
                </a>
              ))}
            </div>
          ) : <p className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm leading-6 text-slate-400">暂无社区、社交或外部证据。证据只是客观事实，后续应能说明它服务于关键词评分、机会判断或监控。</p>}
        </div>
        <div className="panel">
          <h2 className="text-2xl font-bold text-white">机会关联</h2>
          {cards.length ? (
            <div className="mt-4 space-y-3">
              {cards.slice(0, 4).map((card: any) => (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4" key={card.id}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={card.verdict === 'Action' ? 'green' : card.verdict === 'Reject' ? 'red' : 'blue'}>{card.verdict}</Badge>
                    <span className="font-mono text-sm text-blue-300">评分 {scoreText(card.score)}</span>
                  </div>
                  <h3 className="mt-3 font-bold text-slate-100">{card.title}</h3>
                  {card.mvp_plan && <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-400">{card.mvp_plan}</p>}
                </div>
              ))}
            </div>
          ) : <p className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm leading-6 text-slate-400">暂未生成机会。正常路径是关键词完成自动搜索分析和证据补齐后，由机会系统自动判断是否生成。</p>}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="panel">
          <h2 className="mb-4 text-2xl font-bold text-white">证据时间线</h2>
          <EvidenceTimeline targetType="keyword" targetId={id} />
        </div>
        <ScoreHistory title="关键词权重历史" events={data.weight_events || []} />
      </section>

      <LlmSection keywordId={id} />
    </div>
  )
}

function StatusBox({title, value, help}: {title: string; value: string; help: string[][]}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <div className="text-sm text-slate-500">{title}<HelpTip items={help} /></div>
      <div className="mt-2 font-bold text-slate-100">{value}</div>
    </div>
  )
}

function Info({label, value, mono = false}: {label: string; value: React.ReactNode; mono?: boolean}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`mt-2 break-words font-semibold text-slate-100 ${mono ? 'font-mono text-xs' : ''}`}>{value}</div>
    </div>
  )
}

function ListBlock({title, items}: {title: string; items: string[]}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <h3 className="font-bold text-white">{title}</h3>
      <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
        {(items.length ? items : ['暂无']).map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
      </ul>
    </div>
  )
}
