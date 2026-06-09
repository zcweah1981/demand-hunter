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
 async function savePrd(content?:string){if(!selected) return; const bodyContent=content ?? prd; setBusy(true); try{const r:any=await api(`/api/progress/${selected.project.id}/prd`,{method:'POST',body:JSON.stringify({content:bodyContent})}); setSelected(r); setPrd(r.project.prd_content||bodyContent); await refresh()}finally{setBusy(false)}}
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
  setPrd(text)
  setUploadName(name)
  setUploadSize(file.size)
  await savePrd(text)
 }
 useEffect(()=>{const id=new URLSearchParams(location.search).get('project'); if(id) open(Number(id))},[])
 return <div className="space-y-6">
  <section className="rounded-3xl border border-purple-500/20 bg-gradient-to-br from-purple-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl"><p className="text-sm font-semibold uppercase tracking-[0.3em] text-purple-300">Opportunity Progress</p><h1 className="mt-3 text-4xl font-black text-white">机会推进</h1><p className="mt-3 max-w-3xl text-slate-300">只有已采纳机会可以进入推进；上传 PRD 后，系统才开始竞品、Sitemap、SERP、商业策略、定价、SEO、推广和迭代验证。</p></section>
  <section className="panel"><h2 className="text-xl font-bold">从已采纳机会创建推进项目</h2><p className="mt-1 text-sm text-slate-400">未采纳机会不会进入这里，避免过早消耗验证资源。</p><div className="mt-4 grid gap-3 md:grid-cols-2">{adoptedCards.length?adoptedCards.map((c:any)=><div key={c.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-white">{c.opportunity_group?.canonical_keyword||c.title}</b><p className="mt-1 text-sm text-slate-400">score {c.score} · card #{c.id}</p><button disabled={busy} className="btn mt-3" onClick={()=>create(c.id)}>创建 / 打开推进项目</button></div>):<p className="text-sm text-slate-500">暂无已采纳机会。</p>}</div></section>
  <section className="panel"><h2 className="text-xl font-bold">推进项目</h2><div className="mt-4 overflow-hidden rounded-2xl border border-slate-800"><div className="grid grid-cols-[1fr_110px_110px_1fr_110px] gap-3 border-b border-slate-800 bg-slate-900/70 px-4 py-3 text-xs font-semibold text-slate-500"><div>机会</div><div>状态</div><div>可行性</div><div>下一步</div><div>操作</div></div>{projects.length?projects.map((p:any)=><div key={p.id} className="grid grid-cols-[1fr_110px_110px_1fr_110px] gap-3 border-b border-slate-800 px-4 py-3 text-sm last:border-b-0"><b className="text-blue-200">{p.canonical_keyword}</b><span className="text-slate-300">{p.status}</span><span className="text-purple-300">{Math.round(p.feasibility_score||0)}</span><span className="text-slate-400">{p.next_action||'-'}</span><button className="btn-secondary" onClick={()=>open(p.id)}>打开</button></div>):<div className="p-6 text-sm text-slate-500">暂无推进项目。</div>}</div></section>
  {selected&&<div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/60" onClick={()=>setSelected(null)}/><aside className="absolute right-0 top-0 h-full w-full max-w-5xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-purple-300">Progress Project</div><h2 className="mt-1 text-2xl font-bold text-white">{selected.project.canonical_keyword}</h2><p className="mt-1 text-sm text-slate-400">状态 {selected.project.status} · 可行性 {Math.round(selected.project.feasibility_score||0)} · 风险 {selected.project.risk_level}</p></div><button className="btn-secondary" onClick={()=>setSelected(null)}>关闭</button></div><div className="grid gap-4 xl:grid-cols-2"><section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold text-white">PRD.md</h3><p className="mt-1 text-xs text-slate-500">上传 Markdown 文档作为推进边界。上传后会直接保存到项目 PRD 文件。</p></div><div className="flex flex-wrap gap-2"><input ref={fileInputRef} type="file" accept=".md,.markdown,text/markdown,text/plain" className="hidden" onChange={e=>uploadPrdFile(e.target.files?.[0]||null)}/><button className="btn" disabled={busy} onClick={()=>fileInputRef.current?.click()}>{selected.project.prd_content?'重新上传 Markdown':'上传 Markdown'}</button></div></div>{uploadName&&<p className="mt-3 rounded-xl border border-emerald-500/20 bg-emerald-950/30 px-3 py-2 text-xs text-emerald-200">已上传并保存：{uploadName} · {formatBytes(uploadSize)} · {prd.trim().length} 字符</p>}{uploadError&&<p className="mt-3 rounded-xl border border-amber-500/20 bg-amber-950/30 px-3 py-2 text-xs text-amber-200">{uploadError}</p>}<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm"><div className="flex items-center justify-between gap-3"><span className="text-slate-400">当前 PRD</span><span className={selected.project.prd_content?'text-emerald-300':'text-slate-500'}>{selected.project.prd_content?'已保存':'未上传'}</span></div><div className="mt-3 grid gap-2 text-xs text-slate-500"><div>保存路径：{selected.project.prd_path||'上传后生成 prds/<slug>/PRD.md'}</div><div>当前内容长度：{(selected.project.prd_content||prd||'').trim().length} 字符</div></div></div><div className="mt-3 flex flex-wrap gap-2"><button className="btn-secondary" disabled={busy||!selected.project.prd_content} onClick={validate}>启动完整验证</button></div></section><section className="space-y-4"><Info title="下一步" text={selected.project.next_action}/><List title="竞品追踪" rows={selected.competitors.map((c:any)=>`${c.domain} · ${c.notes||''}`)}/><List title="策略建议" rows={selected.recommendations.map((r:any)=>`${r.title}: ${r.content}`)}/><List title="验证记录" rows={selected.runs.map((r:any)=>`#${r.id} ${r.status} · competitors=${r.summary?.competitors||0} · sitemap=${r.summary?.sitemap_snapshots||0}`)}/></section></div></aside></div>}
 </div>
}
function Info({title,text}:{title:string;text:string}){return <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className="font-bold text-white">{title}</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-300">{text||'暂无'}</p></div>}
function List({title,rows}:{title:string;rows:string[]}){return <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h3 className="font-bold text-white">{title}</h3>{rows.length?<ul className="mt-2 space-y-2 text-sm text-slate-300">{rows.map((x,i)=><li key={i} className="rounded-xl bg-slate-950 p-2">{x}</li>)}</ul>:<p className="mt-2 text-sm text-slate-500">暂无。</p>}</div>}
function formatBytes(size:number){if(!size) return '0 B'; const units=['B','KB','MB','GB']; let n=size; let i=0; while(n>=1024&&i<units.length-1){n/=1024; i++} return `${n.toFixed(n>=10||i===0?0:1)} ${units[i]}`}
