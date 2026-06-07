'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {api} from '../lib/api'
import {useLang} from '../lib/i18n'

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

  async function start(){
    setError('')
    startTransition(async()=>{
      try{
        await api('/api/autopilot/start',{method:'POST',body:JSON.stringify({})})
        router.refresh()
      }catch(e:any){setError(e.message||'failed')}
    })
  }
  async function runOnce(){
    setError('')
    startTransition(async()=>{
      try{
        await api('/api/auto/tick',{method:'POST',body:JSON.stringify({force:true})})
        router.refresh()
      }catch(e:any){setError(e.message||'failed')}
    })
  }

  return <section className="rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-slate-950 via-slate-950 to-emerald-950/40 p-6 shadow-2xl">
    <div className="flex flex-wrap items-start justify-between gap-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-emerald-300">Autopilot</p>
        <h2 className="mt-2 text-3xl font-black text-white">{lang==='en'?'Automatic Opportunity Hunter':'自动机会猎手'}</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-300">{lang==='en'?'Default mode: the system discovers keywords, checks SERP gaps, generates cards, and learns from your review. You mainly review results.':'默认模式：系统自动找词、查 SERP 缺口、生成机会卡，并根据你的复核反馈学习。你主要只需要看结果。'}</p>
      </div>
      <span className={status.ready?'badge badge-action':'badge badge-watch'}>{status.ready?(lang==='en'?'Autopilot ready':'自动运行就绪'):(lang==='en'?'Needs setup':'需要初始化')}</span>
    </div>

    <div className="mt-5 grid gap-4 md:grid-cols-5">
      <div className="card"><div className="kpi-label">Discoveries</div><b className="text-2xl">{status.counts.discoveries}</b></div>
      <div className="card"><div className="kpi-label">Cards</div><b className="text-2xl">{status.counts.cards}</b></div>
      <div className="card"><div className="kpi-label">Pending Review</div><b className="text-2xl text-amber-300">{status.counts.pending_review}</b></div>
      <div className="card"><div className="kpi-label">Action</div><b className="text-2xl text-emerald-300">{status.counts.action}</b></div>
      <div className="card"><div className="kpi-label">Running</div><b className={running?'text-blue-300':'text-slate-300'}>{running?(lang==='en'?'Yes':'运行中'):(lang==='en'?'No':'空闲')}</b></div>
    </div>

    <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-500">{lang==='en'?'Recommended next action':'推荐下一步'}</div>
          <div className="mt-1 font-semibold text-white">{status.next_action}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          {!status.ready&&<button className="btn" disabled={pending} onClick={start}>{pending?(lang==='en'?'Starting...':'启动中...'):(lang==='en'?'Start Autopilot':'开启自动猎手')}</button>}
          {status.ready&&<button className="btn" disabled={pending||running} onClick={runOnce}>{pending?(lang==='en'?'Starting...':'启动中...'):(lang==='en'?'Run One Cycle':'手动跑一轮')}</button>}
          {status.counts.pending_review>0&&<a className="btn-secondary" href="/review">{lang==='en'?'Review Cards':'去复核卡片'}</a>}
        </div>
      </div>
      {error&&<p className="mt-3 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
      {last&&<div className="mt-4">
        <div className="mb-2 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-blue-500" style={{width:`${progress}%`}} /></div>
        <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-400"><span>Last run #{last.id} · {last.status}</span><span>{progress}%</span></div>
        {running&&summary.keyword&&<div className="mt-2 text-sm text-blue-200">{lang==='en'?'Current keyword':'当前关键词'}：{summary.keyword}</div>}
      </div>}
    </div>

    <div className="mt-5 grid gap-3 lg:grid-cols-4">
      {status.checks.map(c=><div key={c.key} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
        <div className="flex items-center justify-between gap-2"><b className="text-sm text-slate-200">{c.label}</b><span className={c.ok?'badge badge-action':'badge badge-reject'}>{c.ok?'OK':'Fix'}</span></div>
        <p className="mt-2 text-xs text-slate-500">{c.detail}</p>
      </div>)}
    </div>

    <details className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-400">
      <summary className="cursor-pointer font-semibold text-slate-300">{lang==='en'?'Advanced details':'高级细节'}</summary>
      <div className="mt-3 grid gap-3 md:grid-cols-3"><div><b>Providers</b><p>{status.providers.join(', ')||'none'}</p></div><div><b>Seeds</b><p>{status.seeds.slice(0,8).join(', ')||'none'}</p></div><div><b>Domains</b><p>{status.domains.slice(0,8).join(', ')||'none'}</p></div></div>
    </details>
  </section>
}
