'use client'

import {useEffect, useMemo, useState} from 'react'
import {ContextActions} from './ContextActions'
import {discoveryApi} from '../lib/api'
import type {ClueLlmAnalysis, CluePoolItem, CluePoolResponse} from '../lib/api'

function fmtScore(value:number|undefined|null) {
  if (typeof value !== 'number') return '-'
  return value.toFixed(1)
}

function fmtDate(value?:string|null) {
  if (!value) return '-'
  try { return new Date(value).toLocaleString('zh-CN', {hour12:false}) } catch { return value }
}

function uniqueOptions(items:CluePoolItem[], key:(item:CluePoolItem)=>string) {
  return Array.from(new Set(items.map(key).filter(Boolean))).sort()
}

function toneForStatus(status:string) {
  if (status === 'generated_opportunity' || status === 'in_library' || status === 'pass') return 'text-emerald-300'
  if (status === 'filtered') return 'text-amber-300'
  if (status === 'needs_review' || status === 'reject') return 'text-rose-300'
  return 'text-blue-200'
}

const LIFECYCLE_STATUSES = [
  {key:'new', label:'新发现', text:'系统刚发现的线索，还没有进入候选、关键词库或机会链路。'},
  {key:'candidate', label:'候选', text:'线索已经像一个可搜索需求，但还在等待质量门、补证或自动推进。'},
  {key:'in_library', label:'已入库', text:'线索已经进入正式关键词库，后续主要看关键词验证和机会生成。'},
  {key:'generated_opportunity', label:'已生成机会', text:'线索已经生成机会对象，可以继续看机会评估和产品分析。'},
  {key:'filtered', label:'已过滤', text:'线索被判定为重复、噪音、低质量或不适合推进。'},
]

const PROCESSING_STATUSES = [
  {key:'needs_evidence', label:'待补证据', text:'当前证据或分数不足，需要补 SERP、竞品、社区、站点变化等证据。'},
  {key:'waiting_auto', label:'等待自动推进', text:'当前不需要立即人工处理，等待下一轮自动任务继续评分、入库或生成机会。'},
  {key:'needs_review', label:'需人工处理', text:'系统无法继续自动判断，通常需要人工修复来源、确认过滤或处理异常。'},
]

const QUALITY_STATUSES = [
  {key:'pass', label:'通过', text:'质量门通过，当前分数和规则检查支持继续推进。'},
  {key:'observe', label:'观察', text:'暂未拒绝，但证据或分数不足，需要更多运行结果或补证后再判断。'},
  {key:'reject', label:'拒绝', text:'质量门拒绝，通常是噪音、重复、低分或明确不适合推进。'},
]

function gateClass(status:string) {
  if (status === 'passed') return 'badge badge-action'
  if (status === 'blocked') return 'badge badge-reject'
  return 'badge'
}

function checkClass(status:string) {
  if (status === 'passed') return 'border-emerald-900/70 bg-emerald-950/20 text-emerald-200'
  if (status === 'blocked') return 'border-amber-900/80 bg-amber-950/20 text-amber-200'
  return 'border-slate-800 bg-slate-950 text-slate-200'
}

function clueActions(item:CluePoolItem) {
  if (item.lifecycle_status === 'filtered') {
    return [{label:'修正关联' as const, actionType:'clue.restore', targetType:'clue', targetId:item.id, variant:'secondary' as const}]
  }
  if (item.processing_status === 'needs_evidence') {
    return [{label:'补证据' as const, actionType:'clue.collect_evidence', targetType:'clue', targetId:item.id}]
  }
  if (item.lifecycle_status === 'candidate') {
    return [{label:'推送到关键词库' as const, actionType:'clue.promote_keyword', targetType:'clue', targetId:item.id}]
  }
  return [{label:'重新计算' as const, actionType:'clue.rescore', targetType:'clue', targetId:item.id, variant:'secondary' as const}]
}

function HelpTip({text}:{text:string}) {
  return (
    <span className="group relative inline-flex align-middle">
      <button type="button" className="ml-1 inline-flex h-5 w-5 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-xs text-blue-200">?</button>
      <span className="pointer-events-none absolute left-0 top-7 z-20 hidden w-72 rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs leading-5 text-slate-300 shadow-2xl group-hover:block">
        {text}
      </span>
    </span>
  )
}

function Stat({label,value,help}:{label:string;value:number|string;help?:string}) {
  return <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4"><div className="text-sm text-slate-400">{label}{help&&<HelpTip text={help}/>}</div><div className="mt-2 text-3xl font-black text-white">{value}</div></div>
}

function Select({label,value,onChange,options}:{label:string;value:string;onChange:(value:string)=>void;options:[string,string][]}) {
  return (
    <label className="flex items-center gap-2 text-sm text-slate-300">
      <span>{label}</span>
      <select className="input min-w-[140px]" value={value} onChange={event=>onChange(event.target.value)}>
        {options.map(([v,t]) => <option key={v} value={v}>{t}</option>)}
      </select>
    </label>
  )
}

function ClueDrawer({item,onClose}:{item:CluePoolItem;onClose:()=>void}) {
  const [llmAnalysis,setLlmAnalysis] = useState<ClueLlmAnalysis|null>(null)
  const [llmLoading,setLlmLoading] = useState(false)
  const [llmError,setLlmError] = useState('')
  const [llmOpen,setLlmOpen] = useState(false)
  const downstream = [
    {label:'关键词库', value:item.keyword ? `#${item.keyword.id} ${item.keyword.query}` : item.keyword_status},
    {label:'机会', value:item.opportunity ? `#${item.opportunity.id} ${item.opportunity.title}` : item.opportunity_status},
    {label:'系统动作', value:item.assessment.next_step},
  ]
  async function runLlmAnalysis() {
    setLlmLoading(true)
    setLlmError('')
    try {
      setLlmAnalysis(await discoveryApi.clueLlmAnalysis(item.id))
    } catch (error) {
      setLlmError(error instanceof Error ? error.message : 'LLM 研判失败')
    } finally {
      setLlmLoading(false)
    }
  }
  return (
    <div className="fixed inset-0 z-50">
      <button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/>
      <aside className="absolute right-0 top-0 h-full w-full max-w-5xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-[0.28em] text-blue-300">Clue Detail</div>
            <h2 className="mt-2 text-3xl font-black text-white">{item.value}</h2>
            <div className="mt-3 grid gap-2 text-sm text-slate-300 sm:grid-cols-3">
              <span>{item.clue_type_label}</span>
              <span>{item.source_model}</span>
              <span>{fmtDate(item.created_at)}</span>
            </div>
          </div>
          <button className="btn-secondary" onClick={onClose}>关闭</button>
        </div>

        <section className="mt-5 panel">
          <div className="grid gap-5 xl:grid-cols-[1.4fr_0.75fr]">
            <div className="space-y-4">
              <div className="text-sm font-semibold text-blue-300">线索研判</div>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <span className="rounded-2xl border border-blue-800 bg-blue-950/40 px-4 py-2 text-2xl font-black text-white">{item.assessment.recommendation}</span>
                <span className={gateClass(item.quality_gate.status)}>{item.quality_gate.label}</span>
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-300">{item.assessment.summary}</p>
              <div className="grid gap-4 lg:grid-cols-3">
                <JudgementBlock title="为什么这样判断" lines={item.assessment.reasons}/>
                <JudgementBlock title="还缺什么证据" lines={item.assessment.evidence_gaps}/>
                <JudgementBlock title="风险提示" lines={item.assessment.risks}/>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-bold text-white">下一步</div>
                    <div className="mt-2 text-lg font-black text-white">{item.assessment.next_step}</div>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{item.assessment.next_step_reason}</p>
                  </div>
                  <ContextActions actions={clueActions(item)} />
                </div>
              </div>
            </div>
            <div className="grid gap-3">
              <StatusInfo item={item}/>
              <Info label="总评分" value={fmtScore(item.total_score)}/>
              <Info label="候选质量分" value={item.record_type === 'candidate_entry' ? '待转译' : fmtScore(item.scoring?.candidate_quality_score ? item.scoring.candidate_quality_score * 100 : 0)}/>
              <Info label="入池判断" value={item.scoring?.gate === 'pass' ? '通过' : item.scoring?.gate === 'reject' ? '拒绝' : '观察'}/>
            </div>
          </div>
        </section>

        <section className="mt-5 panel">
          <h3 className="text-xl font-bold">评分来源 <HelpTip text="现在所有候选词统一走同一套评分框架。候选质量分决定能否进入线索池；需求分、趋势分是同一评分框架下拆出来的两个信号，不再来自两套互不一致的算法。"/></h3>
          <div className="mt-4 grid gap-3 md:grid-cols-5">
            <Info label="需求分" value={fmtScore(item.demand_score)}/>
            <Info label="趋势分" value={fmtScore(item.trend_score)}/>
            <Info label="候选质量" value={item.record_type === 'candidate_entry' ? '待转译' : fmtScore((item.scoring?.candidate_quality_score || 0) * 100)}/>
            <Info label="来源可信" value={fmtScore(item.scoring?.source_confidence_score)}/>
            <Info label="噪音风险" value={fmtScore(item.scoring?.noise_risk_score)}/>
          </div>
          <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
            <p>{item.scoring?.formula || '候选质量分用于入池判断；需求分和趋势分用于后续排序和研判。'}</p>
            <p className="mt-2">总评分 = 需求分 * 65% + 趋势分 * 35%。当前总评分为 {fmtScore(item.total_score)}。</p>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {(item.scoring?.breakdown || []).slice(0, 8).map((part,index) => (
              <div key={`${part.label}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <b className="text-slate-100">{part.label}</b>
                  <span className="font-mono text-blue-200">{part.delta > 0 ? '+' : ''}{part.delta}</span>
                </div>
                <p className="mt-2 leading-6 text-slate-400">{part.reason}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-5 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="panel">
            <h3 className="text-xl font-bold">客观检查 <HelpTip text="这里展示规则化检查项。它们不是 LLM 判断，而是基于分数、词形、来源、输入对象和噪音原因的客观规则。"/></h3>
            <div className="mt-4 grid gap-3">
              {item.quality_checks.map(check => (
                <div key={check.name} className={`rounded-xl border p-3 text-sm ${checkClass(check.status)}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <b>{check.name}</b>
                    <span>{check.label}</span>
                  </div>
                  <p className="mt-2 leading-6 text-slate-300">{check.reason}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="panel">
            <h3 className="text-xl font-bold">来源链路</h3>
            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm">
              <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-center">
                <Info label="输入对象" value={item.input_ref?.label || '未记录'}/>
                <span className="hidden text-slate-500 md:block">→</span>
                <Info label="来源模型" value={item.source_model}/>
                <span className="hidden text-slate-500 md:block">→</span>
                <Info label="运行批次" value={item.source_run_id ? `#${item.source_run_id}` : '暂无批次记录'}/>
              </div>
            </div>
            <h3 className="mt-5 text-xl font-bold">后续去向</h3>
            <div className="mt-4 grid gap-3">
              {downstream.map(row => (
                <div key={row.label} className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm">
                  <div className="text-slate-500">{row.label}</div>
                  <div className="mt-1 break-words font-semibold text-slate-100">{row.value}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mt-5 panel">
          <h3 className="text-xl font-bold">状态时间线</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {item.timeline.map((event,index) => (
              <div key={`${event.label}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm">
                <div className="flex flex-wrap justify-between gap-2">
                  <b className="text-slate-100">{event.label}</b>
                  <span className="text-slate-500">{fmtDate(event.at)}</span>
                </div>
                <p className="mt-1 text-slate-400">{event.reason}</p>
                <p className="mt-1 text-xs text-blue-300">{event.by}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-5 panel">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold">LLM 研判 <HelpTip text="这里是按需调用 LLM 后得到的综合判断。未点击运行时不会消耗模型，也不会把规则结论伪装成 LLM 结论。"/></h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">用于补充规则评分无法覆盖的语义判断。默认收起，避免长内容干扰线索详情。当前研判只保存在本次页面状态中，刷新或关闭详情后不会保留。</p>
            </div>
            <div className="flex items-center gap-2">
              <button className="btn" disabled={llmLoading} onClick={()=>{ setLlmOpen(true); runLlmAnalysis() }}>{llmLoading ? '研判中...' : '运行 LLM 研判'}</button>
            </div>
          </div>
          {!llmOpen && (
            <button type="button" className="mt-4 w-full rounded-2xl border border-slate-800 bg-slate-950 p-4 text-left text-sm font-bold text-slate-200 hover:border-blue-900 hover:bg-blue-950/20" onClick={()=>setLlmOpen(true)}>
              ▸ 展开完整 LLM 研判
            </button>
          )}
          {llmOpen && (
            <div className="mt-4">
              {llmError && <div className="rounded-xl border border-rose-900/70 bg-rose-950/20 p-3 text-sm text-rose-200">{llmError}</div>}
              {!llmAnalysis && !llmError && <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">尚未运行 LLM 研判。</div>}
              {llmAnalysis && !llmAnalysis.ok && <div className="rounded-xl border border-amber-900/70 bg-amber-950/20 p-4 text-sm leading-6 text-amber-100">{llmAnalysis.message || 'LLM 当前不可用。'}</div>}
              {llmAnalysis?.ok && llmAnalysis.analysis && (
                <div className="space-y-3">
                  <div className="rounded-2xl border border-blue-900/70 bg-blue-950/20 p-4">
                    <div className="text-sm text-blue-200">LLM 判断</div>
                    <div className="mt-2 text-2xl font-black text-white">{llmAnalysis.analysis.verdict}</div>
                    <p className="mt-3 text-sm leading-6 text-slate-300">{llmAnalysis.analysis.summary}</p>
                    <div className="mt-3 text-xs text-slate-500">长期关注匹配度：{llmAnalysis.analysis.long_term_fit}</div>
                  </div>
                  <LlmList title="判断依据" items={llmAnalysis.analysis.reasoning}/>
                  <LlmList title="风险" items={llmAnalysis.analysis.risks}/>
                  <LlmList title="建议补证" items={llmAnalysis.analysis.evidence_to_collect.concat(llmAnalysis.analysis.next_actions)}/>
                </div>
              )}
              <button type="button" className="mt-4 w-full rounded-2xl border border-slate-800 bg-slate-950 p-4 text-left text-sm font-bold text-slate-200 hover:border-blue-900 hover:bg-blue-950/20" onClick={()=>setLlmOpen(false)}>
                ▾ 收起 LLM 研判
              </button>
            </div>
          )}
        </section>
      </aside>
    </div>
  )
}

function Info({label,value}:{label:string;value:string}) {
  return <div className="rounded-xl border border-slate-800 bg-slate-950 p-3"><dt className="text-slate-500">{label}</dt><dd className="mt-1 break-words font-semibold text-slate-100">{value}</dd></div>
}

function JudgementBlock({title,lines}:{title:string;lines:string[]}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <h3 className="font-bold text-white">{title}</h3>
      <ul className="mt-3 max-h-40 space-y-2 overflow-y-auto text-sm leading-6 text-slate-300">
        {lines.map((line,index) => <li key={index}>{line}</li>)}
      </ul>
    </div>
  )
}

function LlmList({title,items}:{title:string;items:string[]}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <h4 className="font-bold text-white">{title}</h4>
      <ul className="mt-3 max-h-64 space-y-2 overflow-y-auto text-sm leading-6 text-slate-300">
        {(items.length ? items : ['暂无']).map((line,index) => <li key={`${title}-${index}`}>{line}</li>)}
      </ul>
    </div>
  )
}

function StatusLegendTip({statuses}:{statuses:{key:string;label:string;text:string}[]}) {
  return (
    <span className="group relative inline-flex align-middle">
      <button type="button" className="ml-1 inline-flex h-5 w-5 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-xs text-blue-200">?</button>
      <span className="pointer-events-none absolute right-0 top-7 z-20 hidden w-96 rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs leading-5 text-slate-300 shadow-2xl group-hover:block">
        {statuses.map(status => (
          <span key={status.key} className="mb-2 block">
            <b className="text-slate-100">{status.label}</b>：{status.text}
          </span>
        ))}
      </span>
    </span>
  )
}

function StatusInfo({item}:{item:CluePoolItem}) {
  return (
    <div className="grid gap-3">
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
        <div className="text-slate-500">生命周期 <StatusLegendTip statuses={LIFECYCLE_STATUSES}/></div>
        <div className={`mt-1 font-semibold ${toneForStatus(item.lifecycle_status)}`}>{item.lifecycle_status_label}</div>
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
        <div className="text-slate-500">处理状态 <StatusLegendTip statuses={PROCESSING_STATUSES}/></div>
        <div className={`mt-1 font-semibold ${toneForStatus(item.processing_status)}`}>{item.processing_status_label}</div>
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
        <div className="text-slate-500">质量状态 <StatusLegendTip statuses={QUALITY_STATUSES}/></div>
        <div className={`mt-1 font-semibold ${toneForStatus(item.quality_status)}`}>{item.quality_status_label}</div>
      </div>
    </div>
  )
}

export function CluePoolPage({data}:{data:CluePoolResponse}) {
  const [status,setStatus] = useState('all')
  const [type,setType] = useState('all')
  const [source,setSource] = useState('all')
  const [sort,setSort] = useState('score_desc')
  const [page,setPage] = useState(1)
  const [pageSize,setPageSize] = useState(25)
  const [selected,setSelected] = useState<CluePoolItem|null>(null)
  const items = data.items || []
  const types = uniqueOptions(items, item=>item.clue_type_label)
  const sources = uniqueOptions(items, item=>item.source_model)
  const filtered = useMemo(() => {
    const rows = items.filter(item => {
      if (status !== 'all' && item.lifecycle_status !== status) return false
      if (type !== 'all' && item.clue_type_label !== type) return false
      if (source !== 'all' && item.source_model !== source) return false
      return true
    })
    return rows.sort((a,b) => {
      if (sort === 'demand_desc') return b.demand_score - a.demand_score
      if (sort === 'trend_desc') return b.trend_score - a.trend_score
      if (sort === 'recent_desc') return String(b.last_seen_at || '').localeCompare(String(a.last_seen_at || ''))
      if (sort === 'value_asc') return a.value.localeCompare(b.value)
      return b.total_score - a.total_score
    })
  }, [items,status,type,source,sort])

  useEffect(() => {
    setPage(1)
  }, [status,type,source,sort,pageSize])

  const pages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const safePage = Math.min(page, pages)
  const start = filtered.length ? (safePage - 1) * pageSize + 1 : 0
  const end = Math.min(filtered.length, safePage * pageSize)
  const paged = filtered.slice((safePage - 1) * pageSize, safePage * pageSize)

  const candidateCount = items.filter(item=>item.lifecycle_status === 'candidate').length
  const keywordCount = items.filter(item=>item.keyword).length
  const opportunityCount = items.filter(item=>item.opportunity).length

  return (
    <div className="space-y-6">
      <section className="panel">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Clue Pool</p>
            <h1 className="mt-2 text-3xl font-black text-white">线索池</h1>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">这里看每条机会线索本身：来自哪个模型、哪个输入对象、需求分和趋势分是多少、是否通过质量门，以及后续是否进入关键词库或机会分析。</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <Stat label="线索" value={items.length}/>
        <Stat label="候选关键词" value={candidateCount}/>
        <Stat label="已入关键词库" value={keywordCount}/>
        <Stat label="已生成机会" value={opportunityCount}/>
      </section>

      <section className="panel">
        <div className="flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3">
          <Select label="生命周期" value={status} onChange={setStatus} options={[['all','全部'],['new','新发现'],['candidate','候选'],['in_library','已入库'],['generated_opportunity','已生成机会'],['filtered','已过滤']]}/>
          <Select label="类型" value={type} onChange={setType} options={[['all','全部'],...types.map(value=>[value,value] as [string,string])]}/>
          <Select label="来源模型" value={source} onChange={setSource} options={[['all','全部'],...sources.map(value=>[value,value] as [string,string])]}/>
          <Select label="排序" value={sort} onChange={setSort} options={[['score_desc','总评分高到低'],['demand_desc','需求分高到低'],['trend_desc','趋势分高到低'],['recent_desc','最近发现'],['value_asc','线索 A-Z']]}/>
          <span className="ml-auto self-center text-sm text-slate-500">本页 {start}-{end} · 过滤后 {filtered.length} · 全部 {items.length}</span>
        </div>

        <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-800">
          <table className="w-full min-w-[860px] text-sm">
            <thead className="table-head">
              <tr>
                <th className="py-3 text-left">线索</th>
                <th className="py-3 text-left">来源模型</th>
                <th className="py-3 text-left">输入对象</th>
                <th className="py-3 text-left">总评分</th>
                <th className="py-3 text-left">产生时间</th>
              </tr>
            </thead>
            <tbody>
              {paged.map(item => (
                <tr key={item.id} className="border-t border-slate-800">
                  <td className="max-w-[260px] truncate py-3 font-semibold text-slate-100"><button className="text-left text-blue-200 hover:text-blue-100" onClick={()=>setSelected(item)}>{item.value}</button></td>
                  <td className="max-w-[160px] truncate py-3 text-slate-300">{item.source_model}</td>
                  <td className="max-w-[220px] truncate py-3 text-slate-400">{item.input_ref?.label || '-'}</td>
                  <td className="py-3 font-mono text-white">{fmtScore(item.total_score)}</td>
                  <td className="py-3 text-slate-400">{fmtDate(item.created_at)}</td>
                </tr>
              ))}
              {!filtered.length && <tr><td colSpan={5} className="py-8 text-center text-slate-500">暂无线索。</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm">
          <span className="text-slate-500">第 {safePage} / {pages} 页</span>
          <div className="flex flex-wrap items-center gap-2">
            <Select label="每页" value={String(pageSize)} onChange={value=>setPageSize(Number(value))} options={[['10','10'],['25','25'],['50','50'],['100','100']]}/>
            <button type="button" className="btn-secondary" disabled={safePage <= 1} onClick={()=>setPage(safePage - 1)}>上一页</button>
            <button type="button" className="btn-secondary" disabled={safePage >= pages} onClick={()=>setPage(safePage + 1)}>下一页</button>
          </div>
        </div>
      </section>
      {selected && <ClueDrawer item={selected} onClose={()=>setSelected(null)}/>}
    </div>
  )
}
