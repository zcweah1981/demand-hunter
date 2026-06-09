'use client'
import {useState} from 'react'

function fmtDate(s:string){if(!s) return '-'; const d=new Date(s); if(Number.isNaN(d.getTime())) return s; return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}
function arr(x:any){return Array.isArray(x)?x:[]}
function runType(kind:string){const m:any={daily:'日常机会扫描',collector_autopilot:'采集器自动抓取',collector_auto_verify:'线索自动验证',collector_repair_autopilot:'自动优化检查',collector_repair:'单次优化'}; return m[kind]||kind||'运行'}
function describeRun(r:any){const s=r.summary||{}; if(typeof s==='string') return {work:s.slice(0,160), inputs:[], outputs:[], highlights:[]}
 const inputs:string[]=[]; const outputs:string[]=[]; const highlights:string[]=[]
 if(s.seeds?.length) inputs.push(`关键词：${arr(s.seeds).slice(0,6).join('、')}`)
 if(s.domains?.length) inputs.push(`网站：${arr(s.domains).slice(0,4).join('、')}`)
 if(s.auto_targets?.keywords?.length) inputs.push(`优先条件：${arr(s.auto_targets.keywords).slice(0,5).join('、')}`)
 if(s.verified?.length) outputs.push(`生成/验证机会 ${s.verified.length} 条`)
 if(s.import?.imported!==undefined) outputs.push(`导入线索 ${s.import.imported} 条`)
 if(s.auto_verify?.verified?.length) outputs.push(`自动成卡 ${s.auto_verify.verified.length} 条`)
 if(s.results){const vals=Object.values(s.results as any).flat() as any[]; const saved=vals.reduce((a:any,x:any)=>a+Number(x?.saved||x?.leads||0),0); if(saved) outputs.push(`发现线索 ${saved} 条`)}
 if(s.skipped?.length) highlights.push(`跳过 ${s.skipped.length} 条低质量线索`)
 if(s.verified?.length) highlights.push(`重点：${arr(s.verified).slice(0,3).map((x:any)=>x.query).filter(Boolean).join('、')}`)
 if(s.auto_verify?.verified?.length) highlights.push(`重点：${arr(s.auto_verify.verified).slice(0,3).map((x:any)=>x.query).filter(Boolean).join('、')}`)
 if(s.repair) highlights.push(`优化：${s.repair}`)
 if(s.applied_count!==undefined) outputs.push(`自动优化应用 ${s.applied_count} 项，阻止 ${s.blocked_count||0} 项`)
 const work = r.kind==='collector_auto_verify'?'把已导入线索跑验证，判断是否形成机会卡':r.kind==='collector_autopilot'?'按当前预算抓取来源、清洗线索、导入关键词并自动验证':r.kind==='daily'?'运行完整机会猎手：关键词、SERP、竞品和机会卡':r.kind==='collector_repair_autopilot'?'检查采集器健康并执行安全优化':'执行系统维护/优化'
 return {work, inputs, outputs, highlights}
}

export function RunHistoryList({runs}:{runs:any[]}){
 const [selected,setSelected]=useState<any|null>(null)
 return <>
  <div className="overflow-hidden rounded-2xl border border-slate-800">
   <div className="grid grid-cols-[120px_150px_1.2fr_1fr_90px] gap-3 border-b border-slate-800 bg-slate-900/70 px-4 py-3 text-xs font-semibold text-slate-500"><div>时间</div><div>运行类型</div><div>本轮做了什么</div><div>结果重点</div><div>明细</div></div>
   {runs.length?runs.map((r:any)=>{const d=describeRun(r); return <div key={`${r.kind}-${r.id}`} className="grid grid-cols-[120px_150px_1.2fr_1fr_90px] gap-3 border-b border-slate-800 px-4 py-3 text-sm last:border-b-0"><div className="text-slate-400">{fmtDate(r.started_at||r.created_at)}</div><div className="text-blue-300">{runType(r.kind)}</div><div className="safe-text text-slate-300"><b>{d.work}</b>{d.inputs.length>0&&<div className="mt-1 text-xs text-slate-500">{d.inputs.join(' · ')}</div>}</div><div className="safe-text text-slate-300">{d.outputs.length?d.outputs.join(' · '):'暂无产出'}{d.highlights.length>0&&<div className="mt-1 text-xs text-slate-500">{d.highlights.join(' · ')}</div>}</div><button className="btn-secondary" onClick={()=>setSelected(r)}>明细</button></div>}):<div className="p-6 text-sm text-slate-500">暂无运行记录。</div>}
  </div>
  {selected&&<div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/60" onClick={()=>setSelected(null)} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-4 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">Run Detail</div><h2 className="mt-1 text-xl font-bold text-white">{fmtDate(selected.started_at)} · {runType(selected.kind)}</h2><p className="mt-1 text-sm text-slate-400">#{selected.id} · {selected.status}</p></div><button className="btn-secondary" onClick={()=>setSelected(null)}>关闭</button></div>{(()=>{const d=describeRun(selected); return <section className="mb-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className="font-bold text-white">客户视角摘要</h3><p className="mt-2 text-sm text-slate-300">{d.work}</p>{d.inputs.length>0&&<p className="mt-2 text-sm text-slate-400">输入：{d.inputs.join(' · ')}</p>}{d.outputs.length>0&&<p className="mt-2 text-sm text-slate-400">结果：{d.outputs.join(' · ')}</p>}{d.highlights.length>0&&<p className="mt-2 text-sm text-slate-400">重点：{d.highlights.join(' · ')}</p>}</section>})()}<section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className="font-bold text-white">技术明细</h3><pre className="mt-3 max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-2xl bg-slate-950 p-4 text-xs text-slate-300">{JSON.stringify(selected.summary||{},null,2)}</pre></section></aside></div>}
 </>
}
