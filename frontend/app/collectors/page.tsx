'use client'
import {useEffect, useState} from 'react'
import {api, authToken} from '../../lib/api'

type Tab = 'overview' | 'targets' | 'runs' | 'maintenance'

function fmtTime(s?:string){if(!s)return '-'; const d=new Date(s); if(Number.isNaN(d.getTime()))return '-'; return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}
function n(v:any){return Number(v||0)}
function clsStatus(status?:string){return status==='healthy'?'text-emerald-300':status==='watch'?'text-amber-300':'text-red-300'}

export default function Page(){
 const [tab,setTab]=useState<Tab>('overview')
 const [busy,setBusy]=useState(false)
 const [msg,setMsg]=useState('')
 const [health,setHealth]=useState<any|null>(null)
 const [targets,setTargets]=useState<any[]>([])
 const [segments,setSegments]=useState<any|null>(null)
 const [budget,setBudget]=useState<any|null>(null)
 const [runs,setRuns]=useState<any[]>([])
 const [report,setReport]=useState<any|null>(null)
 const [candidates,setCandidates]=useState<any[]>([])
 const [repairRuns,setRepairRuns]=useState<any[]>([])
 const [repairAutoRuns,setRepairAutoRuns]=useState<any[]>([])
 const [rejectedReasons,setRejectedReasons]=useState<any|null>(null)

 async function load(){
  try{
   const [h,ts,seg,bg,rs,rep,cs,repairs,repairAutos]=await Promise.all([
    api<any>('/api/collectors/health'),
    api<any[]>('/api/collectors/targets?limit=120&status='),
    api<any>('/api/collectors/targets/segments'),
    api<any>('/api/collectors/budget/next?limit=24'),
    api<any[]>('/api/collectors/runs?limit=8'),
    api<any>('/api/reports/daily-digest').catch(()=>null),
    api<any[]>('/api/collectors/candidates?limit=30&status=new'),
    api<any[]>('/api/collectors/repairs?limit=8'),
    api<any[]>('/api/collectors/repairs/autopilot/runs?limit=6'),
   ])
   setHealth(h); setTargets(ts); setSegments(seg); setBudget(bg); setRuns(rs); setReport(rep); setCandidates(cs); setRepairRuns(repairs); setRepairAutoRuns(repairAutos)
  }catch(e:any){setMsg(`加载失败：${e.message}`)}
 }
 useEffect(()=>{load()},[])

 async function runCollectorAuto(){setBusy(true);setMsg('正在运行采集器...');try{const r=await api<any>('/api/collectors/autopilot/run',{method:'POST',body:JSON.stringify({limit:24})});setMsg(`采集完成：导入 ${r.import?.imported||0}/${r.import?.selected||0}，清洗拒绝 ${r.clean?.rejected||0}，安全自修复 ${r.safe_repair?.applied_count??0}`);await load()}catch(e:any){setMsg(`运行失败：${e.message}`)}finally{setBusy(false)}}
 async function refreshTargets(){setBusy(true);setMsg('正在从机会卡刷新采集条件...');try{const r=await api<any>('/api/collectors/targets/refresh',{method:'POST'});setMsg(`已刷新条件：关键词 ${r.keyword_targets||0}，域名 ${r.domain_targets||0}`);await load()}catch(e:any){setMsg(`刷新失败：${e.message}`)}finally{setBusy(false)}}
 async function applyTargetHealth(){setBusy(true);try{const r=await api<any>('/api/collectors/targets/health',{method:'POST'});setMsg(`条件健康检查完成：cooled=${r.cooled||0}, promoted=${r.promoted||0}`);await load()}catch(e:any){setMsg(`健康检查失败：${e.message}`)}finally{setBusy(false)}}
 async function runSafeRepair(){setBusy(true);try{const r=await api<any>('/api/collectors/repairs/autopilot',{method:'POST',body:JSON.stringify({allow_cleanup:false,force:false})});setMsg(`系统维护完成：safe applied=${r.applied_count||0}, blocked=${r.blocked_count||0}`);await load()}catch(e:any){setMsg(`系统维护失败：${e.message}`)}finally{setBusy(false)}}
 async function inspectRejected(){setBusy(true);try{const r=await api<any>('/api/collectors/rejected-reasons?limit=800');setRejectedReasons(r)}catch(e:any){setMsg(`检查失败：${e.message}`)}finally{setBusy(false)}}
 async function downloadDigest(){setBusy(true);try{const token=authToken(); const res=await fetch('/api/reports/download/latest',{headers:token?{Authorization:`Bearer ${token}`}:{}}); if(!res.ok) throw new Error(`${res.status} ${await res.text()}`); const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='demand_cards_latest.md'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)}catch(e:any){setMsg(`下载失败：${e.message}`)}finally{setBusy(false)}}

 const summary=health?.summary||{}
 const seg=segments?.summary||{}
 const latest=runs?.[0]?.summary||{}
 const sourceRows=latest.source_results||[]
 const goodTargets=[...(segments?.segments?.winner||[]),...(segments?.segments?.promising||[]),...(segments?.segments?.new||[])].slice(0,18)
 const noisyTargets=[...(segments?.segments?.noisy||[]),...(segments?.segments?.cooldown||[]),...(segments?.segments?.exhausted||[])].slice(0,12)

 return <div className="space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl">
   <div className="flex flex-wrap items-start justify-between gap-4">
    <div>
     <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Collector Center</p>
     <h1 className="mt-3 text-4xl font-black text-white">采集中心</h1>
     <p className="mt-3 max-w-3xl text-slate-300">这里只回答三个问题：现在发现了什么、系统依据哪些条件继续找、下一步该做什么。内部修复和日志放到“系统维护”。</p>
    </div>
    <div className="flex flex-wrap gap-2"><button className="btn" disabled={busy} onClick={runCollectorAuto}>运行采集</button><button className="btn-secondary" disabled={busy} onClick={downloadDigest}>下载日报</button></div>
   </div>
  </section>

  {msg&&<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}

  <nav className="flex flex-wrap gap-2 rounded-2xl border border-slate-800 bg-slate-950/70 p-2">
   {[
    ['overview','核心概览'],['targets','已知条件'],['runs','运行记录'],['maintenance','系统维护']
   ].map(([id,label]:any)=><button key={id} className={tab===id?'btn':'btn-secondary'} onClick={()=>setTab(id)}>{label}</button>)}
  </nav>

  {tab==='overview'&&<div className="space-y-6">
   <section className="grid gap-4 md:grid-cols-5">
    <div className="card"><div className="kpi-label">健康度</div><b className={`text-2xl ${clsStatus(health?.status)}`}>{health?.score??'-'}/100</b><div className="mt-1 text-xs text-slate-500">{health?.status||'-'}</div></div>
    <div className="card"><div className="kpi-label">可用条件</div><b className="text-2xl text-emerald-300">{summary.usable_targets??0}</b><div className="mt-1 text-xs text-slate-500">winner/promising/new</div></div>
    <div className="card"><div className="kpi-label">待处理候选</div><b className="text-2xl text-blue-300">{summary.new_candidates??0}</b><div className="mt-1 text-xs text-slate-500">new candidates</div></div>
    <div className="card"><div className="kpi-label">最近导入</div><b className="text-2xl text-purple-300">{latest.import?.imported??0}/{latest.import?.selected??0}</b><div className="mt-1 text-xs text-slate-500">keyword import</div></div>
    <div className="card"><div className="kpi-label">安全自修复</div><b className="text-2xl text-amber-300">{latest.safe_repair?.applied_count??'-'}</b><div className="mt-1 text-xs text-slate-500">最近一轮 applied</div></div>
   </section>

   {report?.collector_audit?.report&&<section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">最近一轮结果摘要</h2><p className="mt-1 text-sm text-slate-400">给用户看的结论：产出、导入、风险点。</p></div><span className="badge">run #{report.collector_audit.run_id}</span></div><pre className="mt-4 whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-200">{report.collector_audit.report}</pre></section>}

   <section className="grid gap-4 xl:grid-cols-2">
    <div className="panel"><h2 className="text-xl font-bold">当前有效条件</h2><p className="mt-1 text-sm text-slate-400">系统下一轮优先依据这些关键词/域名继续找。</p><div className="mt-4 space-y-2">{goodTargets.length?goodTargets.map((t:any)=><div key={t.id} className="rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{t.value}</b><span className="ml-2 text-slate-500">{t.target_type} · P{Math.round(t.priority||0)} · S{t.success_count||0}/R{t.reject_count||0}</span></div>):<p className="text-sm text-slate-500">暂无有效条件。先从机会卡刷新目标池。</p>}</div></div>
    <div className="panel"><h2 className="text-xl font-bold">最近采集源表现</h2><p className="mt-1 text-sm text-slate-400">只看结果，不展示内部过程。</p><div className="mt-4 space-y-2">{sourceRows.length?sourceRows.map((r:any,i:number)=><div key={i} className="grid grid-cols-[1fr_80px_80px_80px] gap-2 rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{r.source}</b><span className="text-emerald-300">saved {r.saved||0}</span><span className="text-blue-300">seen {r.seen??'-'}</span><span className={r.errors?'text-amber-300':'text-slate-500'}>err {r.errors||0}</span></div>):<p className="text-sm text-slate-500">暂无运行记录。</p>}</div></div>
   </section>
  </div>}

  {tab==='targets'&&<div className="space-y-6">
   <section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">已知条件分类</h2><p className="mt-1 text-sm text-slate-400">这是系统继续找机会的依据。只保留有用条件；噪音条件会冷却或屏蔽。</p></div><div className="flex gap-2"><button className="btn-secondary" disabled={busy} onClick={applyTargetHealth}>整理条件</button><button className="btn" disabled={busy} onClick={refreshTargets}>从机会卡刷新</button></div></div><div className="mt-4 grid gap-3 md:grid-cols-6">{[['winner','高产出'],['promising','有潜力'],['new','新条件'],['noisy','噪音'],['cooldown','冷却'],['exhausted','耗尽']].map(([k,l])=><div key={k} className="rounded-xl bg-slate-950 p-3"><div className="text-xs text-slate-500">{l}</div><b className="text-2xl text-white">{seg[k]||0}</b></div>)}</div></section>
   <section className="grid gap-4 xl:grid-cols-2"><TargetList title="有效条件" items={goodTargets}/><TargetList title="需要降温/屏蔽" items={noisyTargets}/></section>
   <section className="panel"><h2 className="text-xl font-bold">下一轮预算</h2><div className="mt-4 grid gap-3 md:grid-cols-4">{(budget?.allocation||[]).map((row:any)=><div key={row.segment} className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><div className="text-sm font-semibold text-slate-200">{row.label}</div><div className="mt-2 text-2xl font-black text-emerald-300">{row.budget}</div><div className="mt-1 text-xs text-slate-500">available {row.available}</div></div>)}</div></section>
  </div>}

  {tab==='runs'&&<section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">运行记录</h2><p className="mt-1 text-sm text-slate-400">只展示每轮结果，内部修复细节不在这里干扰判断。</p></div><button className="btn" disabled={busy} onClick={runCollectorAuto}>运行采集</button></div><div className="mt-4 space-y-3">{runs.length?runs.map(run=>{const s=run.summary||{}; return <details key={run.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4"><summary className="cursor-pointer text-sm font-semibold text-slate-200">#{run.id} · {fmtTime(run.started_at)} · imported {s.import?.imported||0}/{s.import?.selected||0} · clean rejected {s.clean?.rejected||0} · safe repair {s.safe_repair?.applied_count??'-'}</summary><pre className="mt-3 max-h-80 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(s,null,2)}</pre></details>}):<p className="text-sm text-slate-500">暂无运行记录。</p>}</div></section>}

  {tab==='maintenance'&&<div className="space-y-6">
   <section className="rounded-3xl border border-amber-500/30 bg-amber-500/10 p-5"><h2 className="text-xl font-bold text-amber-100">系统维护（二级菜单）</h2><p className="mt-2 text-sm text-amber-100/80">这里是给维护者看的：修复动作、回放、rejected reason。普通判断只看“核心概览”和“已知条件”。</p><div className="mt-4 flex flex-wrap gap-2"><button className="btn-secondary" disabled={busy} onClick={runSafeRepair}>执行 Safe Repair</button><button className="btn-secondary" disabled={busy} onClick={inspectRejected}>查看 rejected reason</button></div></section>
   {rejectedReasons&&<section className="panel"><h2 className="text-xl font-bold">Rejected reason</h2><div className="mt-4 grid gap-4 xl:grid-cols-2"><ReasonList rows={rejectedReasons.by_reason} keyName="reason"/><ReasonList rows={rejectedReasons.by_source} keyName="source"/></div></section>}
   <section className="grid gap-4 xl:grid-cols-2"><Replay title="Safe Repair Autopilot 回放" rows={repairAutoRuns}/><Replay title="修复动作回放" rows={repairRuns}/></section>
   <section className="panel"><h2 className="text-xl font-bold">New candidates 调试</h2><div className="mt-4 space-y-2">{candidates.map((c:any)=><div key={c.id} className="rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{c.keyword}</b><span className="ml-2 text-slate-500">{c.source} · {Number(c.score||0).toFixed(2)}</span></div>)}</div></section>
  </div>}
 </div>
}

function TargetList({title,items}:{title:string;items:any[]}){return <section className="panel"><h2 className="text-xl font-bold">{title}</h2><div className="mt-4 space-y-2">{items.length?items.map((t:any)=><div key={t.id} className="rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{t.value}</b><span className="ml-2 text-slate-500">{t.target_type} · {t.status} · P{Math.round(t.priority||0)} · S{t.success_count||0}/R{t.reject_count||0}</span></div>):<p className="text-sm text-slate-500">暂无</p>}</div></section>}
function ReasonList({rows,keyName}:{rows:any[];keyName:string}){return <div className="space-y-2">{(rows||[]).slice(0,12).map((r:any)=><div key={r[keyName]} className="flex justify-between rounded-xl bg-slate-950 p-3 text-sm"><span className="text-slate-300">{r[keyName]}</span><b className="text-amber-300">{r.count}</b></div>)}</div>}
function Replay({title,rows}:{title:string;rows:any[]}){return <section className="panel"><h2 className="text-xl font-bold">{title}</h2><div className="mt-4 space-y-2">{rows.length?rows.map((r:any)=><details key={r.id} className="rounded-xl bg-slate-950 p-3 text-sm"><summary className="cursor-pointer text-slate-200">#{r.id} · {fmtTime(r.started_at)} · {r.status}</summary><pre className="mt-3 max-h-72 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(r.summary||{},null,2)}</pre></details>):<p className="text-sm text-slate-500">暂无</p>}</div></section>}
