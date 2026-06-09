import {api} from '../../lib/api'
import {AutopilotPanel} from '../../components/AutopilotPanel'

function fmtDate(s:string){if(!s) return '-'; const d=new Date(s); if(Number.isNaN(d.getTime())) return s; return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}
function runSummary(r:any){const s=r.summary||{}; if(typeof s==='string') return s.slice(0,120); const parts=[]; if(s.cards!==undefined) parts.push(`cards ${s.cards}`); if(s.keywords!==undefined) parts.push(`keywords ${s.keywords}`); if(s.import?.imported!==undefined) parts.push(`import ${s.import.imported}`); if(s.auto_verify?.verified) parts.push(`verify ${s.auto_verify.verified.length}`); if(s.quality_gate?.status) parts.push(`quality ${s.quality_gate.status}`); return parts.join(' · ')||'-'}
function runNarrative(r:any){const s=r.summary||{}; if(typeof s==='string') return s.slice(0,220); if(r.kind==='collector_autopilot'){const seeds=(s.seeds||[]).slice(0,5).join('、'); const domains=(s.domains||[]).slice(0,4).join('、'); const imported=s.import?.imported??0; const verified=s.auto_verify?.verified?.length??0; return `采集器自动跑了一轮：使用 ${seeds||domains||'自动预算条件'}，导入 ${imported} 条线索，自动验证 ${verified} 条机会。`} if(r.kind==='daily'){return `机会猎手日常运行：检查关键词/搜索结果/机会卡，生成 ${s.cards??'-'} 张卡，关键词 ${s.keywords??'-'} 个。`} return runSummary(r)}

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
   <div className="overflow-hidden rounded-2xl border border-slate-800">
    <div className="grid grid-cols-[90px_150px_110px_1fr] gap-3 border-b border-slate-800 bg-slate-900/70 px-4 py-3 text-xs font-semibold text-slate-500"><div>ID</div><div>时间</div><div>类型</div><div>摘要</div></div>
    {merged.length?merged.map((r:any)=><details key={`${r.kind}-${r.id}`} className="border-b border-slate-800 last:border-b-0"><summary className="grid cursor-pointer grid-cols-[90px_150px_110px_1fr] gap-3 px-4 py-3 text-sm hover:bg-slate-900/60"><div className="text-slate-500">#{r.id}</div><div className="text-slate-400">{fmtDate(r.started_at||r.created_at)}</div><div className="text-blue-300">{r.kind||'run'}</div><div className="safe-text text-slate-300">{runNarrative(r)}</div></summary><div className="bg-slate-950/80 p-4"><div className="mb-2 text-xs font-semibold text-slate-500">本轮明细</div><pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-900 p-4 text-xs text-slate-300">{JSON.stringify(r.summary||{},null,2)}</pre></div></details>):<div className="p-6 text-sm text-slate-500">暂无运行记录。</div>}
   </div>
  </section>
 </div>
}
