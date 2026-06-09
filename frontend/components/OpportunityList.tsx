'use client'

import {useEffect, useMemo, useState} from 'react'
import {useRouter} from 'next/navigation'
import {OpportunityCardView, verdictClass, verdictLabel} from './OpportunityCard'
import {Feedback} from './Actions'
import {api} from '../lib/api'

function firstBusiness(card:any){return (card.evidence_json||[]).find((e:any)=>e.type==='business')||{}}
function shortText(s:string, n=90){s=(s||'').replace(/\s+/g,' ').trim(); return s.length>n?s.slice(0,n)+'…':s}
function fmtDate(s:string){if(!s) return '-'; const d=new Date(s); if(Number.isNaN(d.getTime())) return s; return d.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}

const SORTS:any={newest:'最新优先',oldest:'最早优先',score_desc:'分数高到低',score_asc:'分数低到高',verdict:'按判断分类'}
const VERDICTS=['全部','Adopted','Action','Watch','Reject','Block']

type Props={cards:any[]; empty?:string; showVerdictFilter?:boolean; mode?:'review'|'opportunity'; enableBulk?:boolean; currentFilter?:string}
export function OpportunityList({cards, empty='暂无卡片', showVerdictFilter=true, mode='review', enableBulk=false, currentFilter='All'}:Props){
 const router=useRouter()
 const [localCards,setLocalCards]=useState<any[]>(cards||[])
 const [reviewedCount,setReviewedCount]=useState(0)
 const [initialCount,setInitialCount]=useState((cards||[]).length)
 const [selected,setSelected]=useState<any|null>(null)
 const [sort,setSort]=useState('newest')
 const [verdict,setVerdict]=useState('全部')
 const [sourceKeyword,setSourceKeyword]=useState('全部')
 const [learning,setLearning]=useState<any|null>(null)
 const [selectedIds,setSelectedIds]=useState<Set<number>>(new Set())
 useEffect(()=>{setLocalCards(cards||[]); setInitialCount((cards||[]).length); setReviewedCount(0)},[cards])
 const sourceOptions=useMemo(()=>['全部',...Array.from(new Set((localCards||[]).map(c=>c.source_keyword||'').filter(Boolean))).sort()], [localCards])
 const rows=useMemo(()=>{
  let xs=[...(localCards||[])]
  if(showVerdictFilter&&verdict!=='全部') xs=xs.filter(c=>c.verdict===verdict)
  if(sourceKeyword!=='全部') xs=xs.filter(c=>(c.source_keyword||'')===sourceKeyword)
  const rank:any={Adopted:0,Action:1,Watch:2,Reject:3,Block:4}
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
  const updated:any=await api(`/api/cards/${card.id}/feedback`,{method:'POST',body:JSON.stringify({label})})
  const cf=(updated.evidence_json||[]).slice().reverse().find((e:any)=>e.type==='collector_feedback')?.data
  if(cf?.applied){setLearning({label, source:cf.source, weight:cf.source_weight, effect:cf.target_effect, targets:cf.affected_targets||[], matched:cf.matched_candidates})}
  setReviewedCount(n=>n+1)
  setSelected(null)
  router.refresh()
 }
 async function applyBulk(label:string){
  if(!enableBulk||!selectedIds.size) return
  if(!confirm(`批量标记 ${selectedIds.size} 个机会为 ${label}？`)) return
  const res:any=await api('/api/cards/bulk-feedback',{method:'POST',body:JSON.stringify({card_ids:Array.from(selectedIds),label,note:'bulk review from opportunities page'})})
  setSelectedIds(new Set())
  setSelected(null)
  router.refresh()
  setReviewedCount(n=>n+(res.updated||selectedIds.size))
 }
 useEffect(()=>{
  const id=new URLSearchParams(location.search).get('card')
  const q=new URLSearchParams(location.search).get('q')?.toLowerCase()
  if(id){const found=(localCards||[]).find(c=>String(c.id)===id); if(found){setSelected(found); return}}
  if(q){const found=(localCards||[]).find(c=>`${c.source_keyword||''} ${c.title||''} ${c.opportunity_group?.canonical_keyword||''}`.toLowerCase().includes(q)); if(found) setSelected(found)}
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
   const map:any={a:'Action',w:'Watch',d:'Adopted',r:'Reject',b:'Block'}
   if(map[k]&&selected&&mode==='review'){
    e.preventDefault()
    if(confirm(`快捷键 ${k.toUpperCase()}：将 #${selected.id} 标记为 ${map[k]}？`)) sendFeedback(map[k])
   }
  }
  window.addEventListener('keydown', onKey)
  return ()=>window.removeEventListener('keydown', onKey)
 },[rows,selected,mode])
 const processed=mode==='review'?reviewedCount:Math.max(0, initialCount-localCards.length)
 const remaining=localCards.length
 const progress=initialCount?Math.round(processed*100/initialCount):100
 return <>
  <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
   <div className="min-w-[260px] flex-1 text-sm text-slate-400"><div>机会数 <b className="text-slate-100">{initialCount}</b> · 本次改状态 <b className="text-emerald-300">{processed}</b>{mode==='review'&&<span className="ml-3 text-xs text-slate-500">快捷键：J/K · D/A/W/R/B · Esc</span>}</div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-emerald-500" style={{width:`${progress}%`}} /></div></div>
   <div className="flex flex-wrap gap-2">
    {enableBulk&&<><button className="btn-secondary" onClick={()=>setSelectedIds(new Set(rows.map((r:any)=>r.id)))}>全选当前</button><button className="btn-secondary" onClick={()=>setSelectedIds(new Set())}>清空选择</button>{['Adopted','Action','Watch','Reject','Block'].map(x=><button key={x} className={feedbackButtonClass(x)} disabled={!selectedIds.size} onClick={()=>applyBulk(x)}>批量{({Adopted:'采纳',Action:'行动',Watch:'观察',Reject:'拒绝',Block:'屏蔽'} as any)[x]} {selectedIds.size?`(${selectedIds.size})`:''}</button>)}</>}
    {showVerdictFilter&&<select className="input h-9 w-36 py-1 text-sm" value={verdict} onChange={e=>setVerdict(e.target.value)}>{VERDICTS.map(v=><option key={v} value={v}>{v==='全部'?'全部判断':verdictLabel(v)}</option>)}</select>}
    <select className="input h-9 w-52 py-1 text-sm" value={sourceKeyword} onChange={e=>setSourceKeyword(e.target.value)}>{sourceOptions.map(v=><option key={v} value={v}>{v==='全部'?'全部来源词':v}</option>)}</select>
    <select className="input h-9 w-36 py-1 text-sm" value={sort} onChange={e=>setSort(e.target.value)}>{Object.entries(SORTS).map(([k,v])=><option key={k} value={k}>{v as string}</option>)}</select>
   </div>
  </div>
  {learning&&<div className="mb-3 rounded-2xl border border-purple-500/30 bg-purple-500/10 p-3 text-sm text-purple-100"><div className="flex flex-wrap items-center justify-between gap-2"><b>采集器学习已应用</b><button className="text-xs text-purple-200 hover:text-white" onClick={()=>setLearning(null)}>关闭</button></div><div className="mt-1 text-purple-100/80">{learning.label} → {learning.effect==='reward'?'奖励':'惩罚'} source <b>{learning.source}</b>，source weight={learning.weight}，匹配 candidates={learning.matched}</div>{learning.targets?.length>0&&<div className="mt-2 flex flex-wrap gap-2">{learning.targets.slice(0,6).map((t:any)=><span key={t.id} className="rounded-lg bg-slate-950/70 px-2 py-1 text-xs text-slate-200">#{t.id} {t.value} · S{t.success_count||0}/R{t.reject_count||0} · P{Math.round(t.priority||0)}</span>)}</div>}</div>}

  <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70">
   <div className={`hidden gap-3 border-b border-slate-800 px-4 py-3 text-xs font-semibold text-slate-500 md:grid ${mode==='review'?'grid-cols-[56px_110px_1.1fr_1fr_100px_70px_1fr_170px]':'grid-cols-[56px_110px_1.1fr_1fr_100px_70px_1fr_110px]'}`}>
    <div>{enableBulk?'选择':'序号'}</div><div>日期</div><div>机会组</div><div>标题</div><div>判断</div><div>分数</div><div>摘要</div><div>{mode==='review'?'复核':'操作'}</div>
   </div>
   {rows.length?rows.map((card,idx)=>{const biz=firstBusiness(card); return <div key={card.id} role="button" tabIndex={0} onClick={()=>setSelected(card)} onKeyDown={(e)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault(); setSelected(card)}}} className={`grid cursor-pointer gap-3 border-b border-slate-800 px-4 py-4 transition hover:bg-slate-900/60 focus:outline-none focus:ring-2 focus:ring-blue-500/60 last:border-b-0 md:items-center ${mode==='review'?'md:grid-cols-[56px_110px_1.1fr_1fr_100px_70px_1fr_170px]':'md:grid-cols-[56px_110px_1.1fr_1fr_100px_70px_1fr_110px]'}`}>
    <div className="text-sm text-slate-500" onClick={(e)=>e.stopPropagation()}>{enableBulk?<input type="checkbox" checked={selectedIds.has(card.id)} onChange={e=>setSelectedIds(prev=>{const n=new Set(prev); e.target.checked?n.add(card.id):n.delete(card.id); return n})}/>:`#${idx+1}`}</div>
    <div className="text-xs text-slate-500">{fmtDate(card.created_at)}</div>
    <div className="safe-text text-xs text-slate-400"><button className="text-left hover:text-blue-200" onClick={(e)=>{e.stopPropagation(); setSourceKeyword(card.source_keyword||'全部')}}>{card.opportunity_group?.canonical_keyword||card.source_keyword||'-'}</button><div className="mt-1 text-slate-600">组概率 {Math.round((card.opportunity_group?.probability||0)*100)}% · {card.opportunity_group?.variant_count||0} 变体</div></div>
    <button className="safe-text text-left font-semibold text-blue-200 hover:text-blue-100" onClick={(e)=>{e.stopPropagation(); setSelected(card)}}>{card.title}</button>
    <div><span className={verdictClass(card.verdict)}>{verdictLabel(card.verdict)}</span></div>
    <div className="text-sm text-slate-300">{card.score}</div>
    <div className="safe-text text-sm text-slate-400">{shortText(biz.verdict_reason||card.mvp_plan||biz.pain||card.monetization_type)}</div>
    <div onClick={(e)=>e.stopPropagation()}>{mode==='review'?<InlineRowFeedback onFeedback={(label)=>applyFeedback(card,label)}/>:<span className="text-xs text-slate-500">点整行查看</span>}</div>
   </div>}):mode==='review'&&initialCount>0?<ReviewComplete processed={processed}/>:<div className="p-6 text-sm text-slate-500">{empty}</div>}
  </div>

  {selected&&<div className="fixed inset-0 z-50">
   <button className="absolute inset-0 bg-black/60" aria-label="关闭详情" onClick={()=>setSelected(null)} />
   <aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl">
    <div className="mb-4 flex items-center justify-between gap-3">
     <div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">机会详情</div><h2 className="mt-1 text-xl font-bold text-white">{selected.title}</h2><p className="mt-1 text-xs text-slate-500">创建时间：{fmtDate(selected.created_at)} · 来源词：{selected.source_keyword||'-'} · {verdictLabel(selected.verdict)} · 分数 {selected.score}{mode==='review'&&' · 快捷键 D/A/W/R/B'}</p></div>
     <button className="btn-secondary" onClick={()=>setSelected(null)}>关闭</button>
    </div>
    <OpportunityCardView card={selected} showFeedback={mode==='review'} mode={mode==='opportunity'?'execute':'review'} onFeedback={mode==='review'?(label)=>applyFeedback(selected,label):undefined}/>
    {mode==='opportunity'&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><a className="btn" href={`/review?card=${selected.id}`}>去复核模块处理这张卡</a></div>}
   </aside>
  </div>}
 </>
}

function feedbackButtonClass(x:string){const m:any={Watch:'border-blue-500/40 bg-blue-500/10 text-blue-200 hover:bg-blue-500/20',Action:'border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20',Adopted:'border-purple-500/40 bg-purple-500/10 text-purple-200 hover:bg-purple-500/20',Reject:'border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20',Block:'border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20'}; return `rounded border px-2 py-1 text-xs disabled:opacity-40 ${m[x]||'border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700'}`}
function InlineRowFeedback({onFeedback}:{onFeedback:(label:string)=>void}){const labels:any={Adopted:'采纳',Action:'行动',Watch:'观察',Reject:'拒绝',Block:'屏蔽'}; return <div className="flex flex-wrap gap-2">{['Adopted','Action','Watch','Reject','Block'].map(x=><button key={x} title={x} className={feedbackButtonClass(x)} onClick={()=>onFeedback(x)}>{labels[x]}</button>)}</div>}

function ReviewComplete({processed}:{processed:number}){return <div className="p-8"><div className="rounded-3xl border border-emerald-500/30 bg-emerald-500/10 p-6 text-center"><div className="text-sm font-semibold uppercase tracking-[0.25em] text-emerald-300">Review Complete</div><h3 className="mt-3 text-2xl font-black text-white">本次复核完成</h3><p className="mt-2 text-slate-300">已处理 {processed} 张卡片。系统会用你的反馈更新后续采集和评分。</p><div className="mt-5 flex flex-wrap justify-center gap-2"><a className="btn" href="/">返回首页</a><a className="btn-secondary" href="/cards?verdict=Action">看 Action 候选</a><button className="btn-secondary" onClick={async()=>{await api('/api/auto/tick',{method:'POST',body:JSON.stringify({force:true})}); location.href='/runs'}}>运行下一轮</button></div></div></div>}
