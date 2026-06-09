'use client'
import {useEffect, useRef, useState} from 'react'
import {api} from '../lib/api'

export function ProgressPage({initialProjects, adoptedCards}:{initialProjects:any[]; adoptedCards:any[]}){
 const [projects,setProjects]=useState(initialProjects||[])
 const [selected,setSelected]=useState<any|null>(null)
 const [prd,setPrd]=useState('')
 const [busy,setBusy]=useState(false)
 const [uploadName,setUploadName]=useState('')
 const [uploadSize,setUploadSize]=useState(0)
 const [uploadError,setUploadError]=useState('')
 const fileInputRef=useRef<HTMLInputElement|null>(null)
 async function refresh(){setProjects(await api('/api/progress'))}
 async function create(cardId:number){setBusy(true); try{const r:any=await api(`/api/progress/from-card/${cardId}`,{method:'POST'}); setSelected(r); setPrd(r.project.prd_content||''); setUploadName(''); setUploadSize(0); setUploadError(''); await refresh()}finally{setBusy(false)}}
 async function open(id:number){const r:any=await api(`/api/progress/${id}`); setSelected(r); setPrd(r.project.prd_content||''); setUploadName(''); setUploadSize(0); setUploadError('')}
 async function savePrdAndValidate(content:string){if(!selected) return; setBusy(true); try{const saved:any=await api(`/api/progress/${selected.project.id}/prd`,{method:'POST',body:JSON.stringify({content})}); setSelected(saved); setPrd(saved.project.prd_content||content); const validated:any=await api(`/api/progress/${saved.project.id}/validate`,{method:'POST'}); setSelected(validated); await refresh()}finally{setBusy(false)}}
 async function validate(){if(!selected) return; setBusy(true); try{const r:any=await api(`/api/progress/${selected.project.id}/validate`,{method:'POST'}); setSelected(r); await refresh()}finally{setBusy(false)}}
 async function uploadPrdFile(file:File|null){
  setUploadError('')
  if(!file) return
  const name=file.name||''
  const lower=name.toLowerCase()
  const isMarkdown=lower.endsWith('.md')||lower.endsWith('.markdown')||file.type==='text/markdown'||file.type==='text/plain'||file.type==='' 
  if(!isMarkdown){setUploadError('只支持上传 .md / .markdown Markdown 文档。'); return}
  const text=await file.text()
  if(!text.trim()){setUploadError('Markdown 文档为空，无法保存。'); return}
  setPrd(text); setUploadName(name); setUploadSize(file.size)
  await savePrdAndValidate(text)
 }
 useEffect(()=>{const id=new URLSearchParams(location.search).get('project'); if(id) open(Number(id))},[])
 const existingByCard=new Map(projects.map((p:any)=>[p.representative_card_id,p]))
 return <div className="space-y-6">
  <section className="rounded-3xl border border-purple-500/20 bg-gradient-to-br from-purple-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl"><p className="text-sm font-semibold uppercase tracking-[0.3em] text-purple-300">Opportunity Progress</p><h1 className="mt-3 text-4xl font-black text-white">机会推进</h1><p className="mt-3 max-w-4xl text-slate-300">流程：采纳机会 → 带入原机会卡信息 → 上传 PRD.md → Phase 1 证据验证。系统会用 LLM 分析 PRD、原机会证据、竞品、潜在客户和 SERP/Sitemap 证据，重新判断可行性并调整评分。</p></section>
  <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
   <section className="panel"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-bold">采纳机会列表</h2><p className="mt-1 text-sm text-slate-400">这里保留原采纳页面的信息，推进必须从已采纳机会开始。</p></div><span className="badge">{adoptedCards.length} adopted</span></div><div className="mt-4 space-y-3">{adoptedCards.length?adoptedCards.map((c:any)=>{const p=existingByCard.get(c.id) as any; const biz=(c.evidence_json||[]).find((e:any)=>e.type==='business')||{}; return <article key={c.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><h3 className="text-lg font-bold text-white">{c.opportunity_group?.canonical_keyword||c.title}</h3><p className="mt-1 text-sm text-slate-400">原评分 {c.score} · {biz.business_type||c.monetization_type||'未标注变现'} · card #{c.id}</p></div><button disabled={busy} className={p?'btn-secondary':'btn'} onClick={()=>p?open(p.id):create(c.id)}>{p?'打开推进':'开始推进'}</button></div><div className="mt-3 grid gap-2 text-xs md:grid-cols-4"><Metric label="需求" value={c.demand_score}/><Metric label="SERP缺口" value={c.serp_gap_score}/><Metric label="竞品弱点" value={c.competitor_weakness_score}/><Metric label="商业" value={c.mvp_score}/></div>{biz.commercial_mvp&&<p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-300"><b className="text-slate-100">原 MVP：</b>{biz.commercial_mvp}</p>}{c.risks?.length>0&&<p className="mt-2 line-clamp-1 text-xs text-amber-200">风险：{c.risks.slice(0,3).join('；')}</p>}{p&&<div className="mt-3 rounded-xl border border-purple-500/20 bg-purple-500/10 px-3 py-2 text-xs text-purple-100">推进状态：{p.status} · Phase 1 评分 {Math.round(p.feasibility_score||0)} · Δ {p.score_delta>0?'+':''}{p.score_delta}</div>}</article>}):<p className="text-sm text-slate-500">暂无已采纳机会。先在机会页把高质量机会标为 Adopted。</p>}</div></section>
   <section className="panel"><h2 className="text-xl font-bold">推进项目</h2><p className="mt-1 text-sm text-slate-400">上传 PRD 后会自动开始 Phase 1，不是直接进入开发。</p><div className="mt-4 overflow-hidden rounded-2xl border border-slate-800"><div className="grid grid-cols-[1fr_105px_90px_80px] gap-3 border-b border-slate-800 bg-slate-900/70 px-4 py-3 text-xs font-semibold text-slate-500"><div>机会</div><div>状态</div><div>评分</div><div>操作</div></div>{projects.length?projects.map((p:any)=><div key={p.id} className="grid grid-cols-[1fr_105px_90px_80px] gap-3 border-b border-slate-800 px-4 py-3 text-sm last:border-b-0"><b className="truncate text-blue-200">{p.canonical_keyword}</b><span className="truncate text-slate-300">{p.status}</span><span className={p.score_delta>0?'text-emerald-300':p.score_delta<0?'text-rose-300':'text-purple-300'}>{Math.round(p.feasibility_score||0)} {p.score_delta?`(${p.score_delta>0?'+':''}${p.score_delta})`:''}</span><button className="btn-secondary" onClick={()=>open(p.id)}>打开</button></div>):<div className="p-6 text-sm text-slate-500">暂无推进项目。</div>}</div></section>
  </div>
  {selected&&<ProgressDrawer selected={selected} busy={busy} prd={prd} uploadName={uploadName} uploadSize={uploadSize} uploadError={uploadError} fileInputRef={fileInputRef} onClose={()=>setSelected(null)} onUpload={uploadPrdFile} onValidate={validate}/>} 
 </div>
}

function ProgressDrawer({selected,busy,prd,uploadName,uploadSize,uploadError,fileInputRef,onClose,onUpload,onValidate}:any){
 const opp=selected.project.opportunity||{}
 const biz=opp.business||{}
 const latest=selected.runs?.[0]
 const analysis=latest?.summary?.analysis||{}
 return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/60" onClick={onClose}/><aside className="absolute right-0 top-0 h-full w-full max-w-6xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-purple-300">Progress Project</div><h2 className="mt-1 text-2xl font-bold text-white">{selected.project.canonical_keyword}</h2><p className="mt-1 text-sm text-slate-400">状态 {selected.project.status} · 原评分 {Math.round(selected.project.original_score||0)} → Phase 1 {Math.round(selected.project.feasibility_score||0)} · Δ {selected.project.score_delta>0?'+':''}{selected.project.score_delta} · 风险 {selected.project.risk_level}</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div>
  <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
   <section className="space-y-4">
    <Info title="原采纳机会" text={`${opp.title||selected.project.canonical_keyword}\n关键词：${opp.keyword||'-'}\n变现：${biz.business_type||opp.monetization_type||'-'}\n原判断：${biz.verdict_reason||biz.go_no_go||'-'}`}/>
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className="font-bold text-white">原机会评分</h3><div className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-3"><Metric label="总分" value={opp.score}/><Metric label="需求" value={opp.demand_score}/><Metric label="SERP" value={opp.serp_gap_score}/><Metric label="竞品弱点" value={opp.competitor_weakness_score}/><Metric label="商业" value={opp.commercial_score}/><Metric label="变现" value={opp.monetization_score}/></div></div>
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold text-white">上传 PRD.md 开始 Phase 1</h3><p className="mt-1 text-xs text-slate-500">上传后自动保存，并立即用 LLM 进行证据验证和重新评分。</p></div><input ref={fileInputRef} type="file" accept=".md,.markdown,text/markdown,text/plain" className="hidden" onChange={(e:any)=>onUpload(e.target.files?.[0]||null)}/><button className="btn" disabled={busy} onClick={()=>fileInputRef.current?.click()}>{selected.project.prd_content?'重新上传并分析':'上传 PRD 并分析'}</button></div>{busy&&<p className="mt-3 rounded-xl border border-blue-500/20 bg-blue-950/30 px-3 py-2 text-xs text-blue-200">正在执行 Phase 1：搜索竞品/证据，并调用 LLM 重新评分...</p>}{uploadName&&<p className="mt-3 rounded-xl border border-emerald-500/20 bg-emerald-950/30 px-3 py-2 text-xs text-emerald-200">已上传并分析：{uploadName} · {formatBytes(uploadSize)} · {prd.trim().length} 字符</p>}{uploadError&&<p className="mt-3 rounded-xl border border-amber-500/20 bg-amber-950/30 px-3 py-2 text-xs text-amber-200">{uploadError}</p>}<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm"><div className="flex items-center justify-between gap-3"><span className="text-slate-400">当前 PRD</span><span className={selected.project.prd_content?'text-emerald-300':'text-slate-500'}>{selected.project.prd_content?'已保存':'未上传'}</span></div><div className="mt-3 grid gap-2 text-xs text-slate-500"><div>保存路径：{selected.project.prd_path||'上传后生成 prds/<slug>/PRD.md'}</div><div>当前内容长度：{(selected.project.prd_content||prd||'').trim().length} 字符</div></div></div><div className="mt-3"><button className="btn-secondary" disabled={busy||!selected.project.prd_content} onClick={onValidate}>重新运行 Phase 1</button></div></section>
   </section>
   <section className="space-y-4"><Info title="Phase 1 结论 / 下一步" text={selected.project.next_action}/>{analysis.notification&&<Info title="LLM 简短结论" text={analysis.notification}/>}<div className="grid gap-4 md:grid-cols-2"><Info title="评分变化原因" text={analysis.score_change_reason}/><Info title="突破口 / 差异化" text={analysis.wedge}/></div><List title="潜在客户 / 需求入口" rows={arr(analysis.customer_evidence)}/><List title="竞品判断" rows={selected.competitors.map((c:any)=>`${c.domain} · ${c.notes||''}`).concat(arr(analysis.competitor_findings))}/><List title="PRD 待补强" rows={arr(analysis.prd_gaps)}/><List title="下一步补证" rows={arr(analysis.evidence_to_collect_next)}/><List title="策略建议" rows={selected.recommendations.map((r:any)=>`${r.title}: ${r.content}`)}/><List title="验证记录" rows={selected.runs.map((r:any)=>`#${r.id} ${r.kind} ${r.status} · ${r.summary?.old_score??'-'} → ${r.summary?.new_score??'-'} · competitors=${r.summary?.competitors||0}`)}/></section>
  </div></aside></div>
}
function arr(x:any){return Array.isArray(x)?x.filter(Boolean):x?[String(x)]:[]}
function Metric({label,value}:{label:string;value:any}){return <div className="rounded-xl bg-slate-950/80 p-2"><div className="text-slate-500">{label}</div><b className="text-slate-100">{value??'-'}</b></div>}
function Info({title,text}:{title:string;text?:string}){return <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className="font-bold text-white">{title}</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-300">{text||'暂无'}</p></div>}
function List({title,rows}:{title:string;rows:string[]}){return <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className="font-bold text-white">{title}</h3>{rows.length?<ul className="mt-2 space-y-2 text-sm text-slate-300">{rows.map((x,i)=><li key={i} className="whitespace-pre-wrap rounded-xl bg-slate-950 p-2">{x}</li>)}</ul>:<p className="mt-2 text-sm text-slate-500">暂无。</p>}</div>}
function formatBytes(size:number){if(!size) return '0 B'; const units=['B','KB','MB','GB']; let n=size; let i=0; while(n>=1024&&i<units.length-1){n/=1024; i++} return `${n.toFixed(n>=10||i===0?0:1)} ${units[i]}`}
