'use client'

import {useEffect, useMemo, useState} from 'react'
import {OpportunityCardView, verdictClass, verdictLabel} from './OpportunityCard'
import {Feedback} from './Actions'

function firstBusiness(card:any){return (card.evidence_json||[]).find((e:any)=>e.type==='business')||{}}
function shortText(s:string, n=90){s=(s||'').replace(/\s+/g,' ').trim(); return s.length>n?s.slice(0,n)+'…':s}
function fmtDate(s:string){if(!s) return '-'; const d=new Date(s); if(Number.isNaN(d.getTime())) return s; return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}

const SORTS:any={newest:'最新优先',oldest:'最早优先',score_desc:'分数高到低',score_asc:'分数低到高',verdict:'按判断分类'}
const VERDICTS=['全部','Action','Watch','Reject','Block']

type Props={cards:any[]; empty?:string; showVerdictFilter?:boolean; mode?:'review'|'opportunity'}
export function OpportunityList({cards, empty='暂无卡片', showVerdictFilter=true, mode='review'}:Props){
 const [selected,setSelected]=useState<any|null>(null)
 const [sort,setSort]=useState('newest')
 const [verdict,setVerdict]=useState('全部')
 const rows=useMemo(()=>{
  let xs=[...(cards||[])]
  if(showVerdictFilter&&verdict!=='全部') xs=xs.filter(c=>c.verdict===verdict)
  const rank:any={Action:0,Watch:1,Reject:2,Block:3}
  xs.sort((a,b)=>{
   if(sort==='oldest') return new Date(a.created_at||0).getTime()-new Date(b.created_at||0).getTime()
   if(sort==='score_desc') return (b.score||0)-(a.score||0)
   if(sort==='score_asc') return (a.score||0)-(b.score||0)
   if(sort==='verdict') return (rank[a.verdict]??9)-(rank[b.verdict]??9) || (b.score||0)-(a.score||0)
   return new Date(b.created_at||0).getTime()-new Date(a.created_at||0).getTime()
  })
  return xs
 },[cards,sort,verdict,showVerdictFilter])
 useEffect(()=>{
  const id=new URLSearchParams(location.search).get('card')
  if(id){const found=(cards||[]).find(c=>String(c.id)===id); if(found) setSelected(found)}
 },[cards])
 return <>
  <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
   <div className="text-sm text-slate-400">共 <b className="text-slate-100">{rows.length}</b> 条</div>
   <div className="flex flex-wrap gap-2">
    {showVerdictFilter&&<select className="input h-9 w-36 py-1 text-sm" value={verdict} onChange={e=>setVerdict(e.target.value)}>{VERDICTS.map(v=><option key={v} value={v}>{v==='全部'?'全部判断':verdictLabel(v)}</option>)}</select>}
    <select className="input h-9 w-36 py-1 text-sm" value={sort} onChange={e=>setSort(e.target.value)}>{Object.entries(SORTS).map(([k,v])=><option key={k} value={k}>{v as string}</option>)}</select>
   </div>
  </div>

  <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70">
   <div className={`hidden gap-3 border-b border-slate-800 px-4 py-3 text-xs font-semibold text-slate-500 md:grid ${mode==='review'?'grid-cols-[56px_120px_1.35fr_110px_80px_1fr_180px]':'grid-cols-[56px_120px_1.45fr_110px_80px_1fr_110px]'}`}>
    <div>序号</div><div>日期</div><div>标题</div><div>判断</div><div>分数</div><div>摘要</div><div>{mode==='review'?'复核':'操作'}</div>
   </div>
   {rows.length?rows.map((card,idx)=>{const biz=firstBusiness(card); return <div key={card.id} className={`grid gap-3 border-b border-slate-800 px-4 py-4 last:border-b-0 md:items-center ${mode==='review'?'md:grid-cols-[56px_120px_1.35fr_110px_80px_1fr_180px]':'md:grid-cols-[56px_120px_1.45fr_110px_80px_1fr_110px]'}`}>
    <div className="text-sm text-slate-500">#{idx+1}</div>
    <div className="text-xs text-slate-500">{fmtDate(card.created_at)}</div>
    <button className="safe-text text-left font-semibold text-blue-200 hover:text-blue-100" onClick={()=>setSelected(card)}>{card.title}</button>
    <div><span className={verdictClass(card.verdict)}>{verdictLabel(card.verdict)}</span></div>
    <div className="text-sm text-slate-300">{card.score}</div>
    <div className="safe-text text-sm text-slate-400">{shortText(biz.verdict_reason||card.mvp_plan||biz.pain||card.monetization_type)}</div>
    <div>{mode==='review'?<Feedback id={card.id}/>:<a className="btn-secondary" href={`/review?card=${card.id}`}>去复核</a>}</div>
   </div>}):<div className="p-6 text-sm text-slate-500">{empty}</div>}
  </div>

  {selected&&<div className="fixed inset-0 z-50">
   <button className="absolute inset-0 bg-black/60" aria-label="关闭详情" onClick={()=>setSelected(null)} />
   <aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl">
    <div className="mb-4 flex items-center justify-between gap-3">
     <div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">机会详情</div><h2 className="mt-1 text-xl font-bold text-white">{selected.title}</h2><p className="mt-1 text-xs text-slate-500">创建时间：{fmtDate(selected.created_at)} · {verdictLabel(selected.verdict)} · 分数 {selected.score}</p></div>
     <button className="btn-secondary" onClick={()=>setSelected(null)}>关闭</button>
    </div>
    <OpportunityCardView card={selected} showFeedback={mode==='review'}/>
    {mode==='opportunity'&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><a className="btn" href={`/review?card=${selected.id}`}>去复核模块处理这张卡</a></div>}
   </aside>
  </div>}
 </>
}
