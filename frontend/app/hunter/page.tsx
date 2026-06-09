import {api} from '../../lib/api'
import {AutopilotPanel} from '../../components/AutopilotPanel'
import {RunHistoryList} from '../../components/RunHistoryList'

export default async function Page(){
 const [autopilot,runs,collectorRuns] = await Promise.all([
  api<any>('/api/autopilot/status').catch(()=>null),
  api<any[]>('/api/runs').catch(()=>[]),
  api<any[]>('/api/collectors/runs?limit=20').catch(()=>[]),
 ])
 const merged=[...runs,...collectorRuns].sort((a:any,b:any)=>new Date(b.started_at||b.created_at||0).getTime()-new Date(a.started_at||a.created_at||0).getTime()).slice(0,30)
 return <div className="space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl">
   <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Opportunity Hunter</p>
   <h1 className="mt-3 text-4xl font-black text-white">机会猎手总览</h1>
   <p className="mt-3 max-w-2xl text-slate-300">这里只看自动系统是否在跑、最近每一轮跑了什么。机会判断和复核统一放到“机会”页面。</p>
  </section>
  {autopilot&&<AutopilotPanel status={autopilot}/>} 
  <section className="panel">
   <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">自动运行记录</h2><p className="mt-1 text-sm text-slate-400">每一轮自动任务都保留在这里，便于追溯系统为什么产生/没有产生机会。</p></div><span className="badge">{merged.length}</span></div>
   <RunHistoryList runs={merged}/>
  </section>
 </div>
}
