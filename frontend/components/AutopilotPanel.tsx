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
  const healthy=status.ready && !running

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

    <div className="mt-5 grid gap-3 md:grid-cols-3">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="kpi-label">待复核</div><b className="text-3xl text-amber-300">{status.counts.pending_review}</b></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="kpi-label">行动 Action</div><b className="text-3xl text-emerald-300">{status.counts.action}</b></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="kpi-label">观察 Watch</div><b className="text-3xl text-blue-300">{status.counts.watch}</b></div>
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
