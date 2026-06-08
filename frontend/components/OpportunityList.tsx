'use client'

import {useEffect, useMemo, useState} from 'react'
import {OpportunityCardView, verdictClass, verdictLabel} from './OpportunityCard'
import {Feedback} from './Actions'
import {api} from '../lib/api'

function firstBusiness(card:any){return (card.evidence_json||[]).find((e:any)=>e.type==='business')||{}}
function shortText(s:string, n=90){s=(s||'').replace(/\s+/g,' ').trim(); return s.length>n?s.slice(0,n)+'…':s}
function fmtDate(s:string){if(!s) return '-'; const d=new Date(s); if(Number.isNaN(d.getTime())) return s; return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}

const SORTS:any={newest:'最新优先',oldest:'最早优先',score_desc:'分数高到低',score_asc:'分数低到高',verdict:'按判断分类'}
const VERDICTS=['全部','Action','Watch','Reject','Block']

type Props={cards:any[]; empty?:string; showVerdictFilter?:boolean; mode?:'review'|'opportunity'}
export function OpportunityList({cards, empty='暂无卡片', showVerdictFilter=true, mode='review'}:Props){
 const [localCards,setLocalCards]=useState<any[]>(cards||[])
 const [initialCount,setInitialCount]=useState((cards||[]).length)
 const [selected,setSelected]=useState<any|null>(null)
 const [sort,setSort]=useState('newest')
 const [verdict,setVerdict]=useState('全部')
 const [sourceKeyword,setSourceKeyword]=useState('全部')
 useEffect(()=>{setLocalCards(cards||[]); setInitialCount((cards||[]).length)},[cards])
 const sourceOptions=useMemo(()=>['全部',...Array.from(new Set((localCards||[]).map(c=>c.source_keyword||'').filter(Boolean))).sort()], [localCards])
 const rows=useMemo(()=>{
  let xs=[...(localCards||[])]
  if(showVerdictFilter&&verdict!=='全部') xs=xs.filter(c=>c.verdict===verdict)
  if(sourceKeyword!=='全部') xs=xs.filter(c=>(c.source_keyword||'')===sourceKeyword)
  const rank:any={Action:0,Watch:1,Reject:2,Block:3}
  xs.sort((a,b)=>{
   if(sort==='oldest') return new Date(a.created_at||0).getTime()-new Date(b.created_at||0).getTime()
   if(sort==='score_desc') return (b.score||0)-(a.score||0)
   if(sort==='score_asc') return (a.score||0)-(b.score||0)
   if(sort==='verdict') return (rank[a.verdict]??9)-(rank[b.verdict]??9) || (b.score||0)-(a.score||0)
   return new Date(b.created_at||0).getTime()-new Date(a.created_at||0).getTime()
  })
  return xs
 },[localCards,sort,verdict,sourceKeyword,showVerdictFilter])
 async function applyFeedback(card:any,label:string){
  if(!card||mode!=='review') return
  const idx=rows.findIndex(x=>x.id===card.id)
  await api(`/api/cards/${card.id}/feedback`,{method:'POST',body:JSON.stringify({label})})
  const remaining=rows.filter(x=>x.id!==card.id)
  setLocalCards(prev=>prev.filter(x=>x.id!==card.id))
  if(selected?.id===card.id){
   const next=remaining[Math.min(idx, remaining.length-1)] || null
   setSelected(next)
  }
 }
 useEffect(()=>{
  const id=new URLSearchParams(location.search).get('card')
  if(id){const found=(localCards||[]).find(c=>String(c.id)===id); if(found) setSelected(found)}
 },[localCards])
 useEffect(()=>{
  function isTypingTarget(t:any){const tag=(t?.tagName||'').toLowerCase(); return tag==='input'||tag==='textarea'||tag==='select'||t?.isContentEditable}
  async function sendFeedback(label:string){if(!selected||mode!=='review') return; await applyFeedback(selected,label)}
  function move(delta:number){if(!rows.length) return; const cur=selected?rows.findIndex(x=>x.id===selected.id):-1; const next=rows[Math.max(0, Math.min(rows.length-1, (cur<0?0:cur)+delta))]; if(next) setSelected(next)}
  function onKey(e:KeyboardEvent){
   if(isTypingTarget(e.target)||e.metaKey||e.ctrlKey||e.altKey) return
   const k=e.key.toLowerCase()
   if(k==='escape'&&selected){e.preventDefault(); setSelected(null); return}
   if(k==='j'){e.preventDefault(); move(1); return}
   if(k==='k'){e.preventDefault(); move(-1); return}
   const map:any={a:'Action',w:'Watch',r:'Reject',b:'Block'}
   if(map[k]&&selected&&mode==='review'){
    e.preventDefault()
    if(confirm(`快捷键 ${k.toUpperCase()}：将 #${selected.id} 标记为 ${map[k]}？`)) sendFeedback(map[k])
   }
  }
  window.addEventListener('keydown', onKey)
  return ()=>window.removeEventListener('keydown', onKey)
 },[rows,selected,mode])
 const processed=Math.max(0, initialCount-localCards.length)
 const remaining=localCards.length
 const progress=initialCount?Math.round(processed*100/initialCount):100
 return <>
  <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
   <div className="min-w-[260px] flex-1 text-sm text-slate-400"><div>本次队列：已处理 <b className="text-emerald-300">{processed}</b> / <b className="text-slate-100">{initialCount}</b> · 剩余 <b className="text-amber-300">{remaining}</b>{mode==='review'&&<span className="ml-3 text-xs text-slate-500">快捷键：J/K · A/W/R/B · Esc</span>}</div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-emerald-500" style={{width:`${progress}%`}} /></div></div>
   <div className="flex flex-wrap gap-2">
    {showVerdictFilter&&<select className="input h-9 w-36 py-1 text-sm" value={verdict} onChange={e=>setVerdict(e.target.value)}>{VERDICTS.map(v=><option key={v} value={v}>{v==='全部'?'全部判断':verdictLabel(v)}</option>)}</select>}
    <select className="input h-9 w-52 py-1 text-sm" value={sourceKeyword} onChange={e=>setSourceKeyword(e.target.value)}>{sourceOptions.map(v=><option key={v} value={v}>{v==='全部'?'全部来源词':v}</option>)}</select>
    <select className="input h-9 w-36 py-1 text-sm" value={sort} onChange={e=>setSort(e.target.value)}>{Object.entries(SORTS).map(([k,v])=><option key={k} value={k}>{v as string}</option>)}</select>
   </div>
  </div>

  <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70">
   <div className={`hidden gap-3 border-b border-slate-800 px-4 py-3 text-xs font-semibold text-slate-500 md:grid ${mode==='review'?'grid-cols-[56px_110px_1.1fr_1fr_100px_70px_1fr_170px]':'grid-cols-[56px_110px_1.1fr_1fr_100px_70px_1fr_110px]'}`}>
    <div>序号</div><div>日期</div><div>来源词</div><div>标题</div><div>判断</div><div>分数</div><div>摘要</div><div>{mode==='review'?'复核':'操作'}</div>
   </div>
   {rows.length?rows.map((card,idx)=>{const biz=firstBusiness(card); return <div key={card.id} className={`grid gap-3 border-b border-slate-800 px-4 py-4 last:border-b-0 md:items-center ${mode==='review'?'md:grid-cols-[56px_110px_1.1fr_1fr_100px_70px_1fr_170px]':'md:grid-cols-[56px_110px_1.1fr_1fr_100px_70px_1fr_110px]'}`}>
    <div className="text-sm text-slate-500">#{idx+1}</div>
    <div className="text-xs text-slate-500">{fmtDate(card.created_at)}</div>
    <div className="safe-text text-xs text-slate-400"><button className="text-left hover:text-blue-200" onClick={()=>setSourceKeyword(card.source_keyword||'全部')}>{card.source_keyword||'-'}</button><div className="mt-1 text-slate-600">{card.keyword_source||''}</div></div>
    <button className="safe-text text-left font-semibold text-blue-200 hover:text-blue-100" onClick={()=>setSelected(card)}>{card.title}</button>
    <div><span className={verdictClass(card.verdict)}>{verdictLabel(card.verdict)}</span></div>
    <div className="text-sm text-slate-300">{card.score}</div>
    <div className="safe-text text-sm text-slate-400">{shortText(biz.verdict_reason||card.mvp_plan||biz.pain||card.monetization_type)}</div>
    <div>{mode==='review'?<InlineRowFeedback onFeedback={(label)=>applyFeedback(card,label)}/>:<a className="btn-secondary" href={`/review?card=${card.id}`}>去复核</a>}</div>
   </div>}):<div className="p-6 text-sm text-slate-500">{empty}</div>}
  </div>

  {selected&&<div className="fixed inset-0 z-50">
   <button className="absolute inset-0 bg-black/60" aria-label="关闭详情" onClick={()=>setSelected(null)} />
   <aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl">
    <div className="mb-4 flex items-center justify-between gap-3">
     <div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">机会详情</div><h2 className="mt-1 text-xl font-bold text-white">{selected.title}</h2><p className="mt-1 text-xs text-slate-500">创建时间：{fmtDate(selected.created_at)} · 来源词：{selected.source_keyword||'-'} · {verdictLabel(selected.verdict)} · 分数 {selected.score}{mode==='review'&&' · 快捷键 A/W/R/B'}</p></div>
     <button className="btn-secondary" onClick={()=>setSelected(null)}>关闭</button>
    </div>
    <OpportunityCardView card={selected} showFeedback={mode==='review'} onFeedback={mode==='review'?(label)=>applyFeedback(selected,label):undefined}/>
    {mode==='opportunity'&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><a className="btn" href={`/review?card=${selected.id}`}>去复核模块处理这张卡</a></div>}
   </aside>
  </div>}
 </>
}

function InlineRowFeedback({onFeedback}:{onFeedback:(label:string)=>void}){const labels:any={Action:'行动',Watch:'观察',Reject:'拒绝',Block:'屏蔽'}; return <div className="flex flex-wrap gap-2">{['Action','Watch','Reject','Block'].map(x=><button key={x} title={x} className="rounded bg-slate-800 px-2 py-1 text-xs hover:bg-slate-700" onClick={()=>onFeedback(x)}>{labels[x]} <span className="text-slate-500">{x}</span></button>)}</div>}
