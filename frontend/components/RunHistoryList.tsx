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
function unique(xs:any[]){const seen=new Set(); const out:any[]=[]; for(const x of xs.filter(Boolean)){const key=typeof x==='string'?x:(x.label||x.href||JSON.stringify(x)); if(seen.has(key)) continue; seen.add(key); out.push(x)} return out.slice(0,30)}
function runLists(r:any){const s=r.summary||{}; if(typeof s==='string') return {opportunities:[], imported:[], skipped:[], sources:[]}
 const opportunities=unique([
  ...arr(s.verified).map((x:any)=>{const q=x.query||x.keyword||x.title; return {label:q, href:`/hunter/opportunities?verdict=All${x.card_id?`&card=${x.card_id}`:''}${q?`&q=${encodeURIComponent(q)}`:''}`}}),
  ...arr(s.auto_verify?.verified).map((x:any)=>{const q=x.query||x.keyword||x.title; return {label:q, href:`/hunter/opportunities?verdict=All${x.card_id?`&card=${x.card_id}`:''}${q?`&q=${encodeURIComponent(q)}`:''}`}}),
  ...arr(s.created_cards).map((x:any)=>{const q=x.query||x.keyword||x.title; return {label:q, href:`/hunter/opportunities?verdict=All${(x.card_id||x.id)?`&card=${x.card_id||x.id}`:''}${q?`&q=${encodeURIComponent(q)}`:''}`}}),
 ])
 const imported=unique([
  ...arr(s.import?.imported_keywords).map((x:any)=>typeof x==='string'?x:x.query||x.keyword),
  ...arr(s.import?.keywords).map((x:any)=>typeof x==='string'?x:x.query||x.keyword),
  ...arr(s.clean?.selected).map((x:any)=>x.keyword||x.query),
  ...arr(s.summary?.top_new).map((x:any)=>x.keyword||x.query),
 ])
 const skipped=unique([
  ...arr(s.skipped).map((x:any)=>`${x.query||x.keyword||'-'}：${x.reason||x.noise||'跳过'}`),
  ...arr(s.auto_verify?.skipped).map((x:any)=>`${x.query||x.keyword||'-'}：${x.reason||x.noise||'跳过'}`),
 ])
 const sources:string[]=[]
 if(s.results&&typeof s.results==='object') for(const [source,rows] of Object.entries(s.results)){const count=arr(rows).reduce((a:any,x:any)=>a+Number(x?.saved||x?.leads||0),0); sources.push(`${source}: ${count} 条线索`)}
 return {opportunities, imported, skipped:skipped.slice(0,20), sources:sources.slice(0,12)}
}
function runTime(r:any){const d=new Date(r.started_at||r.created_at||0); return Number.isNaN(d.getTime())?0:d.getTime()}
function groupRuns(runs:any[]){const sorted=[...(runs||[])].sort((a,b)=>runTime(b)-runTime(a)); const batches:any[]=[]; for(const r of sorted){const last=batches[batches.length-1]; if(last && Math.abs(runTime(last.runs[last.runs.length-1])-runTime(r))<=5*60*1000){last.runs.push(r); last.end_at=r.started_at||r.created_at}else batches.push({id:`batch-${r.id}`,started_at:r.started_at||r.created_at,end_at:r.finished_at||r.started_at||r.created_at,runs:[r]})} return batches}
function describeBatch(b:any){const runs=b.runs||[]; const ds=runs.map(describeRun); const inputs=unique(ds.flatMap((d:any)=>d.inputs)); const outputs=unique(ds.flatMap((d:any)=>d.outputs)); const highlights=unique(ds.flatMap((d:any)=>d.highlights)); const types=unique(runs.map((r:any)=>runType(r.kind))); const work=runs.length>1?`一次自动任务，包含 ${types.join('、')} ${runs.length} 个步骤`:(ds[0]?.work||'-'); return {work,inputs,outputs,highlights,types}}
function batchLists(b:any){const all=(b.runs||[]).map(runLists); return {opportunities:unique(all.flatMap((x:any)=>x.opportunities)), imported:unique(all.flatMap((x:any)=>x.imported)), skipped:unique(all.flatMap((x:any)=>x.skipped)).slice(0,30), sources:unique(all.flatMap((x:any)=>x.sources))}}

export function RunHistoryList({runs}:{runs:any[]}){
 const [selected,setSelected]=useState<any|null>(null)
 const batches=groupRuns(runs)
 return <>
  <div className="overflow-hidden rounded-2xl border border-slate-800">
   <div className="grid grid-cols-[120px_150px_1.2fr_1fr_90px] gap-3 border-b border-slate-800 bg-slate-900/70 px-4 py-3 text-xs font-semibold text-slate-500"><div>时间</div><div>运行类型</div><div>本轮做了什么</div><div>结果重点</div><div>明细</div></div>
   {batches.length?batches.map((b:any)=>{const d=describeBatch(b); return <div key={b.id} className="grid grid-cols-[120px_150px_1.2fr_1fr_90px] gap-3 border-b border-slate-800 px-4 py-3 text-sm last:border-b-0"><div className="text-slate-400">{fmtDate(b.started_at)}{b.runs.length>1&&<div className="text-xs text-slate-600">{b.runs.length} 步</div>}</div><div className="text-blue-300">{d.types.join(' + ')}</div><div className="safe-text text-slate-300"><b>{d.work}</b>{d.inputs.length>0&&<div className="mt-1 text-xs text-slate-500">{d.inputs.join(' · ')}</div>}</div><div className="safe-text text-slate-300">{d.outputs.length?d.outputs.join(' · '):'暂无产出'}{d.highlights.length>0&&<div className="mt-1 text-xs text-slate-500">{d.highlights.join(' · ')}</div>}</div><button className="btn-secondary" onClick={()=>setSelected(b)}>明细</button></div>}):<div className="p-6 text-sm text-slate-500">暂无运行记录。</div>}
  </div>
  {selected&&<div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/60" onClick={()=>setSelected(null)} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-4 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">运行明细</div><h2 className="mt-1 text-xl font-bold text-white">{fmtDate(selected.started_at)} · 自动任务</h2><p className="mt-1 text-sm text-slate-400">包含 {(selected.runs||[]).length} 个步骤：{(selected.runs||[]).map((r:any)=>`#${r.id}`).join('、')}</p></div><button className="btn-secondary" onClick={()=>setSelected(null)}>关闭</button></div>{(()=>{const d=describeBatch(selected); const l=batchLists(selected); return <div className="space-y-4"><section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className="font-bold text-white">这一轮做了什么</h3><p className="mt-2 text-sm text-slate-300">{d.work}</p>{d.inputs.length>0&&<p className="mt-2 text-sm text-slate-400">输入：{d.inputs.join(' · ')}</p>}{d.outputs.length>0&&<p className="mt-2 text-sm text-slate-400">结果：{d.outputs.join(' · ')}</p>}{d.highlights.length>0&&<p className="mt-2 text-sm text-slate-400">重点：{d.highlights.join(' · ')}</p>}</section><RunListBlock title="抓到 / 验证出的机会" items={l.opportunities} empty="这一轮没有形成新机会卡。" tone="text-emerald-300"/><RunListBlock title="导入验证的线索" items={l.imported} empty="这一轮没有新的导入线索。" tone="text-blue-300"/><RunListBlock title="来源产出" items={l.sources} empty="这一轮没有可展示的来源产出。" tone="text-purple-300"/><RunListBlock title="跳过 / 拦截的线索" items={l.skipped} empty="这一轮没有明显低质量线索。" tone="text-amber-300"/></div>})()}</aside></div>}
 </>
}

function RunListBlock({title,items,empty,tone}:{title:string;items:any[];empty:string;tone:string}){return <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className={`font-bold ${tone}`}>{title}</h3>{items.length?<ul className="mt-3 space-y-2 text-sm text-slate-300">{items.map((x:any,i:number)=>{const label=typeof x==='string'?x:x.label; const href=typeof x==='string'?null:x.href; return <li key={`${label}-${i}`} className="rounded-xl bg-slate-950 px-3 py-2">{href?<a className="text-blue-300 hover:text-blue-200" href={href}>{label} <span className="text-xs text-slate-500">→ 查看机会</span></a>:label}</li>})}</ul>:<p className="mt-3 text-sm text-slate-500">{empty}</p>}</section>}
