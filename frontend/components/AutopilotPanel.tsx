'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {api} from '../lib/api'
import {useLang} from '../lib/i18n'
import {ExperimentRepairButton, RecommendedExperimentButton, RepairActionButton, RollbackRepairButton} from './Actions'

type AutopilotStatus = {
  ready:boolean
  running:boolean
  mode:string
  next_action:string
  checks:{key:string;label:string;ok:boolean;detail:string}[]
  counts:{discoveries:number;cards:number;pending_review:number;action:number;watch:number}
  auto:any
  providers:string[]
  seeds:string[]
  domains:string[]
  diagnosis?:{severity?:string;issues?:any[];recommended_actions?:string[];repair_actions?:any[];manual_repair_actions?:any[];recommended_experiment?:any;repair_recommendation_fallback?:string;repair_recommendation_meta?:any;next_action?:string}|null
  active_experiment?:any|null
  latest_experiment?:any|null
  collectors?:{by_status?:Record<string,number>;by_source?:Record<string,number>;source_weights?:Record<string,any>;budget_plan?:{active?:any[];paused?:any[]};top_new?:any[]}
}

export function AutopilotPanel({status}:{status:AutopilotStatus}){
  const router = useRouter()
  const {lang}=useLang()
  const [error,setError]=useState('')
  const [pending,startTransition]=useTransition()
  const last=status.auto?.last_run
  const summary=last?.summary||{}
  const running=status.running || last?.status==='running'
  const progress=running&&summary.total?Math.round((summary.current||0)*100/summary.total):last?.status==='ok'?100:0
  const healthy=status.ready && !running
  const collectorStatus=status.collectors?.by_status||{}
  const collectorTop=status.collectors?.top_new||[]
  const collectorWeights=status.collectors?.source_weights||{}
  const budgetPlan=status.collectors?.budget_plan||{}
  const diagnosis=status.diagnosis
  const bestExperiment=diagnosis?.recommended_experiment
  const manualRepairActions=diagnosis?.manual_repair_actions||diagnosis?.repair_actions||[]
  const activeExperiment=status.active_experiment
  const latestExperiment=status.latest_experiment
  const severityClass=diagnosis?.severity==='critical'?'border-rose-500/40 bg-rose-500/10 text-rose-100':diagnosis?.severity==='warning'?'border-amber-500/40 bg-amber-500/10 text-amber-100':'border-slate-800 bg-slate-900/60 text-slate-200'

  async function call(path:string){
    setError('')
    startTransition(async()=>{
      try{
        await api(path,{method:'POST',body:JSON.stringify(path.includes('autopilot')?{}:{force:true})})
        router.refresh()
      }catch(e:any){setError(e.message||'failed')}
    })
  }

  return <section className="rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-2xl">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-2xl font-black text-white">{lang==='en'?'Autopilot':'自动猎手'}</h2>
          <span className={running?'badge badge-watch':status.ready?'badge badge-action':'badge badge-reject'}>{running?(lang==='en'?'Running':'运行中'):status.ready?(lang==='en'?'Ready':'就绪'):(lang==='en'?'Setup needed':'需初始化')}</span>
        </div>
        <p className="mt-2 max-w-3xl text-sm font-semibold text-slate-200">{status.next_action}</p>
        {running&&summary.keyword&&<p className="mt-2 text-sm text-blue-200">{lang==='en'?'Now checking':'正在检查'}：{summary.keyword}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {!status.ready&&<button className="btn" disabled={pending} onClick={()=>call('/api/autopilot/start')}>{pending?(lang==='en'?'Starting...':'启动中...'):(lang==='en'?'Start':'开启')}</button>}
        {status.ready&&<button className="btn" disabled={pending||running} onClick={()=>call('/api/auto/tick')}>{pending?(lang==='en'?'Starting...':'启动中...'):(lang==='en'?'Run now':'现在跑一轮')}</button>}
        {status.counts.pending_review>0&&<a className="btn-secondary" href="/review">{lang==='en'?'Review':'去复核'}</a>}
      </div>
    </div>

    {last&&<div className="mt-5">
      <div className="mb-2 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-blue-500" style={{width:`${progress}%`}} /></div>
      <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>#{last.id} · {last.status}</span><span>{progress}%</span></div>
    </div>}

    {diagnosis&&<div className={`mt-4 rounded-2xl border p-4 ${severityClass}`}><div className="flex flex-wrap justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-[0.2em] opacity-70">自动诊断</div><b className="mt-1 block">{diagnosis.issues?.[0]?.title||'诊断完成'}</b><p className="mt-1 text-sm opacity-90">{diagnosis.next_action}</p></div><span className="badge">{diagnosis.severity}</span></div>{!!diagnosis.issues?.length&&<div className="mt-3 flex flex-wrap gap-2">{diagnosis.issues.slice(0,3).map((i:any)=><span key={i.code} className="rounded-lg bg-slate-950/70 px-2 py-1 text-xs">{i.code}</span>)}</div>}{bestExperiment&&<div className="mt-4 rounded-2xl border border-blue-500/30 bg-blue-950/30 p-3"><div className="mb-2 text-xs font-semibold opacity-70">推荐实验</div><div className="flex flex-wrap items-center justify-between gap-3"><div><b>运行系统推荐的下一步实验</b><p className="mt-1 text-xs opacity-80">推荐项：{bestExperiment.label}</p></div><RecommendedExperimentButton action={bestExperiment}/></div></div>}{!bestExperiment&&diagnosis.repair_recommendation_fallback&&<div className="mt-4 rounded-2xl border border-slate-700 bg-slate-950/60 p-3 text-sm text-slate-300"><b>暂无推荐实验</b><p className="mt-1 text-xs text-slate-500">{diagnosis.repair_recommendation_fallback}{diagnosis.repair_recommendation_meta?.cooldown_until?` 冷却最早结束：${diagnosis.repair_recommendation_meta.cooldown_until}`:''}</p></div>}{!!manualRepairActions.length&&<details className="mt-3"><summary className="cursor-pointer text-xs opacity-70 hover:opacity-100">其它修复动作</summary><div className="mt-2 flex flex-wrap gap-2">{manualRepairActions.slice(0,4).map((a:any)=><span key={a.id||a.action} className="flex gap-1"><RepairActionButton action={a}/><ExperimentRepairButton action={a}/></span>)}</div></details>}</div>}

    {activeExperiment&&<div className="mt-4 rounded-2xl border border-blue-500/30 bg-blue-500/10 p-4 text-blue-100"><div className="text-xs font-semibold uppercase tracking-[0.2em] opacity-70">实验队列</div><b className="mt-1 block">已有实验等待评估：#{activeExperiment.id} {activeExperiment.summary?.action}</b><p className="mt-1 text-sm opacity-90">为避免变量污染，新实验会被阻止，直到当前实验完成或处理。</p></div>}

    {latestExperiment&&!activeExperiment&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">上次实验结果</div><div className="mt-1 flex flex-wrap items-center justify-between gap-3"><div><b className={latestExperiment.effect?.status==='improved'?'text-emerald-300':latestExperiment.effect?.status==='regressed'?'text-rose-300':'text-slate-200'}>{latestExperiment.effect?.guard?.label||latestExperiment.effect?.status||latestExperiment.status}</b><p className="mt-1 text-sm text-slate-400">#{latestExperiment.id} {latestExperiment.summary?.action} · {latestExperiment.effect?.guard?.recommendation||latestExperiment.effect?.recommendation||latestExperiment.effect?.note||'暂无摘要'}</p>{typeof latestExperiment.effect?.delta==='number'&&<p className="mt-1 text-xs text-slate-500">health score Δ {latestExperiment.effect.delta}</p>}</div>{latestExperiment.effect?.guard?.rollback_recommended&&latestExperiment.summary?.repair_id&&<RollbackRepairButton id={latestExperiment.summary.repair_id}/>}</div></div>}

    <div className="mt-5 grid gap-3 md:grid-cols-3">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="kpi-label">待复核</div><b className="text-3xl text-amber-300">{status.counts.pending_review}</b></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="kpi-label">行动 Action</div><b className="text-3xl text-emerald-300">{status.counts.action}</b></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="kpi-label">观察 Watch</div><b className="text-3xl text-blue-300">{status.counts.watch}</b></div>
    </div>

    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h3 className="font-bold text-slate-100">采集器候选池</h3><p className="mt-1 text-xs text-slate-500">采集器只发现候选；自动清洗后进入 Four-Find / SEO / LLM。</p></div>
        <div className="flex gap-3 text-sm"><span className="text-blue-300">New {collectorStatus.new||0}</span><span className="text-emerald-300">Imported {collectorStatus.imported||0}</span><span className="text-rose-300">Rejected {collectorStatus.rejected||0}</span></div>
      </div>
      {collectorTop.length>0&&<div className="mt-3 grid gap-2 md:grid-cols-2">{collectorTop.slice(0,4).map((c:any)=><div key={c.id} className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs"><div className="flex justify-between gap-2"><b className="truncate text-slate-200">{c.keyword}</b><span className="text-blue-300">{Number(c.score||0).toFixed(2)}</span></div><p className="mt-1 truncate text-slate-500">{c.source} · {c.method}</p></div>)}</div>}
      {Object.keys(collectorWeights).length>0&&<div className="mt-3 flex flex-wrap gap-2">{Object.entries(collectorWeights).slice(0,8).map(([source,row]:any)=><span key={source} className="rounded-lg bg-slate-950 px-2 py-1 text-xs text-slate-400">{source} ×{Number(row?.weight||1).toFixed(2)}</span>)}</div>}
      {!!budgetPlan.active?.length&&<div className="mt-3 rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="mb-2 text-xs font-semibold text-slate-500">本轮采集预算</div><div className="flex flex-wrap gap-2">{budgetPlan.active.map((row:any)=><span key={row.key} className="rounded-lg bg-slate-900 px-2 py-1 text-xs text-slate-300">{row.key}: {Math.round((row.share||0)*100)}% · {row.item_limit}</span>)}{!!budgetPlan.paused?.length&&<span className="rounded-lg bg-rose-950/40 px-2 py-1 text-xs text-rose-300">paused {budgetPlan.paused.length}</span>}</div></div>}
    </div>

    {error&&<p className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}

    <details className="mt-4 text-sm text-slate-400">
      <summary className="cursor-pointer text-slate-500 hover:text-slate-300">{lang==='en'?'System details':'系统细节'}</summary>
      <div className="mt-3 grid gap-3 md:grid-cols-4">
        {status.checks.map(c=><div key={c.key} className="rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="flex justify-between gap-2"><b className="text-slate-300">{c.label}</b><span className={c.ok?'text-emerald-300':'text-rose-300'}>{c.ok?'正常':'需处理'}</span></div><p className="mt-1 text-xs text-slate-500">{c.detail}</p></div>)}
      </div>
      <div className="mt-3 text-xs text-slate-500">搜索源：{status.providers.join(', ')||'无'} · 种子词：{status.seeds.slice(0,5).join(', ')||'无'}</div>
    </details>
  </section>
}
