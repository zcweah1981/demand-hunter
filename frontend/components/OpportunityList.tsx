'use client'

import {useMemo, useState} from 'react'
import {OpportunityCardView, verdictClass, verdictLabel} from './OpportunityCard'
import {Feedback} from './Actions'

function firstBusiness(card:any){return (card.evidence_json||[]).find((e:any)=>e.type==='business')||{}}
function shortText(s:string, n=90){s=(s||'').replace(/\s+/g,' ').trim(); return s.length>n?s.slice(0,n)+'…':s}

export function OpportunityList({cards, empty='暂无卡片'}:{cards:any[]; empty?:string}){
 const [selected,setSelected]=useState<any|null>(null)
 const rows=useMemo(()=>cards||[],[cards])
 return <>
  <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70">
   <div className="hidden grid-cols-[1.4fr_110px_90px_1fr_180px] gap-3 border-b border-slate-800 px-4 py-3 text-xs font-semibold text-slate-500 md:grid">
    <div>标题</div><div>判断</div><div>分数</div><div>摘要</div><div>复核</div>
   </div>
   {rows.length?rows.map(card=>{const biz=firstBusiness(card); return <div key={card.id} className="grid gap-3 border-b border-slate-800 px-4 py-4 last:border-b-0 md:grid-cols-[1.4fr_110px_90px_1fr_180px] md:items-center">
    <button className="safe-text text-left font-semibold text-blue-200 hover:text-blue-100" onClick={()=>setSelected(card)}>{card.title}</button>
    <div><span className={verdictClass(card.verdict)}>{verdictLabel(card.verdict)}</span></div>
    <div className="text-sm text-slate-300">{card.score}</div>
    <div className="safe-text text-sm text-slate-400">{shortText(biz.verdict_reason||card.mvp_plan||biz.pain||card.monetization_type)}</div>
    <div><Feedback id={card.id}/></div>
   </div>}):<div className="p-6 text-sm text-slate-500">{empty}</div>}
  </div>

  {selected&&<div className="fixed inset-0 z-50">
   <button className="absolute inset-0 bg-black/60" aria-label="关闭详情" onClick={()=>setSelected(null)} />
   <aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl">
    <div className="mb-4 flex items-center justify-between gap-3">
     <div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">机会详情</div><h2 className="mt-1 text-xl font-bold text-white">{selected.title}</h2></div>
     <button className="btn-secondary" onClick={()=>setSelected(null)}>关闭</button>
    </div>
    <OpportunityCardView card={selected}/>
   </aside>
  </div>}
 </>
}
