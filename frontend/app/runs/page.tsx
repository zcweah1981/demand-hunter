import {api} from '../../lib/api'
import {RunDailyButton, ExportReportButton, AutoTickButton, RepairActionButton, RollbackRepairButton, ExperimentRepairButton, AbandonExperimentButton, RecommendedExperimentButton} from '../../components/Actions'
import {I18nText} from '../../components/I18nText'

function parseSummary(summary:any){
  if(!summary) return {}
  if(typeof summary==='string'){
    try{return JSON.parse(summary)}catch{return {raw:summary}}
  }
  return summary
}

function Funnel({summary}:{summary:any}){
  const s=parseSummary(summary)
  const q=s.quality_report||{}
  const f=q.funnel||{}
  const diagnosis=s.diagnosis||q.diagnosis
  const bestExperiment=diagnosis?.recommended_experiment
  const collector=q.collector||{}
  const budget=collector.budget_plan||{}
  const sourceRows=Object.entries(q.card_by_source||{}) as any[]
  const steps=[
    ['采集看到', f.collector_seen],
    ['候选保存', f.collector_saved],
    ['清洗扫描', f.clean_scanned],
    ['清洗拒绝', f.clean_rejected],
    ['导入关键词', f.imported_keywords],
    ['SERP 拒绝', f.serp_rejected],
    ['机会卡', f.cards],
    ['Action', f.action],
    ['Watch', f.watch],
  ]
  if(!q.funnel){return <pre className="safe-pre mt-3">{JSON.stringify(s,null,2)}</pre>}
  const severityClass=diagnosis?.severity==='critical'?'border-rose-500/40 bg-rose-500/10':diagnosis?.severity==='warning'?'border-amber-500/40 bg-amber-500/10':'border-slate-800 bg-slate-950'
  return <div className="mt-4 space-y-4">
    {diagnosis&&<div className={`rounded-2xl border p-4 ${severityClass}`}><div className="flex flex-wrap justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">自动诊断</div><b className="mt-1 block text-slate-100">{diagnosis.issues?.[0]?.title||'诊断完成'}</b><p className="mt-1 text-sm text-slate-300">{diagnosis.next_action}</p></div><span className="badge">{diagnosis.severity}</span></div>{!!diagnosis.issues?.length&&<div className="mt-3 grid gap-2 md:grid-cols-2">{diagnosis.issues.slice(0,4).map((i:any)=><div key={i.code} className="rounded-xl bg-slate-950/70 p-3 text-xs"><b className="text-slate-200">{i.title}</b><p className="mt-1 text-slate-500">{i.detail}</p></div>)}</div>}{!!diagnosis.recommended_actions?.length&&<div className="mt-3"><div className="mb-1 text-xs font-semibold text-slate-500">建议动作</div><ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">{diagnosis.recommended_actions.slice(0,4).map((a:string,i:number)=><li key={i}>{a}</li>)}</ul></div>}{bestExperiment&&<div className="mt-3 rounded-2xl border border-blue-500/30 bg-blue-950/30 p-3"><div className="mb-2 text-xs font-semibold text-blue-200">推荐实验</div><div className="flex flex-wrap items-center justify-between gap-3"><div><b className="text-slate-100">运行系统推荐的下一步实验</b><p className="mt-1 text-xs text-slate-400">推荐项：{bestExperiment.label}</p></div><RecommendedExperimentButton action={bestExperiment}/></div></div>}{!!diagnosis.repair_actions?.length&&<details className="mt-3"><summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-300">其它修复动作</summary><div className="mt-2 flex flex-wrap gap-2">{diagnosis.repair_actions.slice(0,5).map((a:any)=><span key={a.id||a.action} className="flex gap-1"><RepairActionButton action={a}/><ExperimentRepairButton action={a}/></span>)}</div></details>}</div>}
    <div className="grid gap-2 md:grid-cols-5">{steps.map(([label,value]:any)=><div key={label} className="rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="text-xs text-slate-500">{label}</div><b className="text-2xl text-slate-100">{value??0}</b></div>)}</div>
    {!!budget.active?.length&&<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="mb-2 text-sm font-bold text-slate-200">采集预算</div><div className="flex flex-wrap gap-2">{budget.active.map((r:any)=><span key={r.key} className="rounded-lg bg-slate-900 px-2 py-1 text-xs text-slate-300">{r.key}: {Math.round((r.share||0)*100)}% · {r.item_limit}</span>)}{!!budget.paused?.length&&<span className="rounded-lg bg-rose-950/40 px-2 py-1 text-xs text-rose-300">paused {budget.paused.length}</span>}</div></div>}
    {!!collector.by_source?.length&&<div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950"><div className="border-b border-slate-800 px-4 py-2 text-sm font-bold text-slate-200">Collector 产出</div><div className="divide-y divide-slate-800">{collector.by_source.map((r:any,i:number)=><div key={i} className="grid gap-2 px-4 py-2 text-xs md:grid-cols-5"><b className="text-slate-200">{r.source}</b><span>seen {r.seen||0}</span><span>saved {r.saved||0}</span><span>new {r.new_urls??'-'} / old {r.old_urls??'-'}</span><span className={r.errors?'text-rose-300':'text-slate-500'}>errors {r.errors||0}</span></div>)}</div></div>}
    {!!Object.keys(q.serp_gate_reasons||{}).length&&<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="mb-2 text-sm font-bold text-slate-200">SERP Gate 拒绝原因</div><div className="flex flex-wrap gap-2">{Object.entries(q.serp_gate_reasons).map(([k,v]:any)=><span key={k} className="rounded-lg bg-slate-900 px-2 py-1 text-xs text-amber-200">{k}: {v}</span>)}</div></div>}
    {!!sourceRows.length&&<div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950"><div className="border-b border-slate-800 px-4 py-2 text-sm font-bold text-slate-200">关键词来源 → 卡片结果</div><div className="divide-y divide-slate-800">{sourceRows.map(([source,row]:any)=><div key={source} className="grid gap-2 px-4 py-2 text-xs md:grid-cols-7"><b className="text-slate-200 md:col-span-2">{source}</b><span>processed {row.processed}</span><span>cards {row.cards}</span><span className="text-emerald-300">Action {row.action}</span><span className="text-blue-300">Watch {row.watch}</span><span className="text-amber-300">SERP reject {row.serp_reject}</span></div>)}</div></div>}
    <details><summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-300">Raw summary</summary><pre className="safe-pre mt-3">{JSON.stringify(s,null,2)}</pre></details>
  </div>
}

export default async function Page(){
  const rows=await api<any[]>('/api/runs')
  const auto=await api<any>('/api/auto/status')
  const repairs=await api<any[]>('/api/autopilot/repairs')
  const experiments=await api<any[]>('/api/autopilot/experiments')
  return <div className="space-y-6">
    <div className="flex flex-wrap justify-between gap-3"><div><h1 className="text-3xl font-bold"><I18nText zh='运行历史' en='Run History'/></h1><p className="mt-2 text-slate-400"><I18nText zh='查看每次自动找词的进度、质量漏斗和错误。' en='Inspect progress, quality funnels, and errors for each automatic discovery run.'/></p></div><div className="flex gap-2"><RunDailyButton/><AutoTickButton/><ExportReportButton/></div></div>
    <section className="panel"><h2 className="mb-3 text-xl font-bold"><I18nText zh='当前自动状态' en='Current Auto Status'/></h2><pre className="safe-pre">{JSON.stringify(auto,null,2)}</pre></section>
    <section className="panel"><div className="flex items-center justify-between gap-3"><h2 className="text-xl font-bold">自动实验</h2><span className="text-xs text-slate-500">最近 {experiments.length} 条</span></div><div className="mt-3 space-y-2">{experiments.length===0&&<p className="text-sm text-slate-500">暂无 experiment 记录。</p>}{experiments.map(x=>{const s=x.summary||{}; const e=x.effect||{}; const g=e.guard||{}; const cls=e.status==='improved'?'text-emerald-300':e.status==='regressed'?'text-rose-300':e.status==='pending'?'text-amber-300':e.status==='abandoned'?'text-slate-500':'text-slate-400'; const active=x.status==='running'||['pending','no_baseline'].includes(e.status); return <div key={x.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-xs"><div className="flex flex-wrap justify-between gap-2"><b className="text-slate-100">#{x.id} {s.action}</b><span className={cls}>{g.label||e.status||x.status}{typeof e.delta==='number'?` · Δ ${e.delta}`:''}</span></div><div className="mt-1 text-slate-500">repair #{s.repair_id} · {x.started_at}</div><p className="mt-2 text-slate-300">{g.recommendation||e.recommendation||e.note||'等待实验后的 daily run 完成。'}</p><div className="mt-2 flex flex-wrap gap-2">{g.rollback_recommended&&s.repair_id&&<RollbackRepairButton id={s.repair_id}/>} {active&&<AbandonExperimentButton id={x.id}/>} {active&&s.repair_id&&<AbandonExperimentButton id={x.id} rollback/>}</div></div>})}</div></section>
    <section className="panel"><div className="flex items-center justify-between gap-3"><h2 className="text-xl font-bold">修复审计 / 回滚</h2><span className="text-xs text-slate-500">最近 {repairs.length} 条</span></div><div className="mt-3 space-y-2">{repairs.length===0&&<p className="text-sm text-slate-500">暂无 repair 记录。</p>}{repairs.map(r=>{const s=r.summary||{}; const e=r.effect||{}; const strategy=e.strategy||{}; const effectClass=e.status==='improved'?'text-emerald-300':e.status==='regressed'?'text-rose-300':e.status==='pending'?'text-amber-300':'text-slate-400'; return <div key={r.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="flex flex-wrap justify-between gap-2"><div><b className="text-slate-100">#{r.id} {s.action}</b>{s.source&&<span className="ml-2 text-xs text-slate-500">source={s.source}</span>}<div className="mt-1 text-xs text-slate-500">{r.started_at} · {r.status}</div></div>{!s.rolled_back&&r.status==='ok'&&<RollbackRepairButton id={r.id}/>}</div><div className="mt-2 rounded-xl bg-slate-900 p-2 text-xs"><div className="flex flex-wrap justify-between gap-2"><b className="text-slate-400">修复效果</b><span className={effectClass}>{e.status||'unknown'}{typeof e.delta==='number'?` · Δ ${e.delta}`:''}{strategy.priority?` · p${strategy.priority}`:''}</span></div>{e.before&&e.after&&<div className="mt-1 text-slate-300">score {e.before.score} → {e.after.score} · cards {e.before.funnel?.cards||0} → {e.after.funnel?.cards||0} · SERP reject {Math.round((e.before.serp_reject_rate||0)*100)}% → {Math.round((e.after.serp_reject_rate||0)*100)}%</div>} {strategy.runs&&<div className="mt-1 text-slate-500">历史：improved {strategy.improved||0} / neutral {strategy.neutral||0} / regressed {strategy.regressed||0} · avg Δ {strategy.avg_delta}</div>}<p className="mt-1 text-slate-500">{e.recommendation||e.note||'等待下一轮评估。'}</p></div><div className="mt-2 grid gap-2 text-xs md:grid-cols-2"><div className="rounded-xl bg-slate-900 p-2"><b className="text-slate-400">Changed</b><div className="mt-1 text-slate-300">{(s.changed||[]).join(', ')||'-'}</div></div><div className="rounded-xl bg-slate-900 p-2"><b className="text-slate-400">After</b><pre className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap text-slate-300">{JSON.stringify(s.after||{},null,2)}</pre></div></div>{s.rolled_back&&<p className="mt-2 text-xs text-rose-300">已回滚：{s.rolled_back_at}</p>}</div>})}</div></section>
    <section className="panel"><div className="space-y-4">{rows.map(r=><div key={r.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4"><div className="flex justify-between"><b>#{r.id} {r.kind}</b><span className={r.status==='ok'?'badge badge-action':r.status==='running'?'badge':'badge badge-reject'}>{r.status}</span></div><div className="mt-2 text-xs text-slate-500">{r.started_at} → {r.finished_at||'running'}</div><Funnel summary={r.summary}/></div>)}</div></section>
  </div>
}
