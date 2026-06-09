import {api} from '../../lib/api'
import {AutopilotPanel} from '../../components/AutopilotPanel'
import {RunHistoryList} from '../../components/RunHistoryList'

function fmtNextRun(s?:string){if(!s) return '暂无预计时间'; const d=new Date(s); if(Number.isNaN(d.getTime())) return s; return `${d.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})} 北京时间`}
function runTime(r:any){const d=new Date(r.started_at||r.created_at||0); return Number.isNaN(d.getTime())?0:d.getTime()}
function mergedTaskCount(runs:any[]){const sorted=[...(runs||[])].sort((a,b)=>runTime(b)-runTime(a)); let count=0; let last=0; for(const r of sorted){const t=runTime(r); if(!last||Math.abs(last-t)>5*60*1000) count++; last=t} return count}

export default async function Page(){
 const [autopilot,runs] = await Promise.all([
  api<any>('/api/autopilot/status').catch(()=>null),
  api<any[]>('/api/runs').catch(()=>[]),
 ])
 const merged=[...runs].sort((a:any,b:any)=>new Date(b.started_at||b.created_at||0).getTime()-new Date(a.started_at||a.created_at||0).getTime()).slice(0,30)
 const taskCount=mergedTaskCount(merged)
 return <div className="space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl">
   <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Opportunity Hunter</p>
   <h1 className="mt-3 text-4xl font-black text-white">机会猎手总览</h1>
   <p className="mt-3 max-w-2xl text-slate-300">这里只看自动系统是否在跑、最近每一轮跑了什么。机会判断和复核统一放到“机会”页面。</p>
  </section>
  {autopilot&&<AutopilotPanel status={autopilot}/>} 
  <section className="panel">
   <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">自动运行记录</h2><p className="mt-1 text-sm text-slate-400">每一轮自动任务都保留在这里，便于追溯系统为什么产生/没有产生机会。</p></div><div className="flex flex-wrap items-center gap-2"><span className="rounded-xl border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-sm text-blue-100">下次预计自动运行：{autopilot?.auto?.enabled?fmtNextRun(autopilot?.auto?.next_run_at):'自动化未开启'}</span><span className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-300">间隔 {autopilot?.auto?.interval_minutes??'-'} 分钟</span><span className="badge">{taskCount} 个任务</span><span className="badge">{merged.length} 个步骤</span></div></div>
   <RunHistoryList runs={merged}/>
  </section>
 </div>
}
