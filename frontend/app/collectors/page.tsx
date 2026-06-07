'use client'
import {useEffect, useState} from 'react'
import {api} from '../../lib/api'

const collectors = [
 {id:'sitemap',name:'Sitemap 监控',tag:'站找词',status:'已接入·免费',desc:'监控竞品 sitemap 新增 URL，从路径抽取新页面、新工具、新长尾词。',feeds:['robots.txt','sitemap.xml','sitemap index'],output:'new URL/page → candidate pool → keyword → SEO 验证'},
 {id:'suggest',name:'搜索联想 / 相关搜索',tag:'词找词',status:'已接入·免费',desc:'从公开 suggest 接口扩展长尾搜索词。后续可接 PAA/Related Search 付费增强。',feeds:['Google Suggest','DuckDuckGo Suggest'],output:'suggest query → candidate pool → Four-Find'},
 {id:'advanced',name:'高级搜索找需求',tag:'SERP 变体',status:'下一步',desc:'allintitle/site/date 变体，用于发现新页面和竞品内容缺口。',feeds:['SearXNG','SerpApi/Zenserp/ScaleSERP'],output:'SERP URL/title → candidate pool'},
 {id:'source-radar',name:'一手信息源雷达',tag:'信息溯源',status:'下一步',desc:'监控 HN、arXiv、GitHub、HuggingFace 等源头，捕捉新模型/新技术/新词。',feeds:['HN Algolia','arXiv','GitHub','Hugging Face'],output:'early signal → candidate pool'},
 {id:'extensions',name:'插件差评挖掘',tag:'抱怨找需求',status:'计划中',desc:'找高下载、低评分、差评多的插件，从用户抱怨抽取具体需求词。',feeds:['Firefox Add-ons','Chrome Web Store'],output:'complaint topic → candidate pool'},
 {id:'requests',name:'AI 工具请求',tag:'请求找需求',status:'计划中',desc:'抓取 AI 工具请求/愿望单，按最新、投票数、重复诉求提取候选词。',feeds:['TheresAnAIForThat','ProductHunt'],output:'request text → candidate pool'},
 {id:'similarweb',name:'SimilarWeb / Landing Pages',tag:'站找词 / 站找站',status:'付费增强',desc:'获取站点关键词、相似站、出站流量、着陆页新点击量。',feeds:['SimilarWeb keywords','Similar sites','Landing pages'],output:'site/page/keyword → Four-Find'},
]

export default function Page(){
 const [domains,setDomains]=useState('')
 const [seeds,setSeeds]=useState('')
 const [advRoots,setAdvRoots]=useState('')
 const [advDomains,setAdvDomains]=useState('')
 const [radarSeeds,setRadarSeeds]=useState('')
 const [msg,setMsg]=useState('')
 const [busy,setBusy]=useState(false)
 const [candidates,setCandidates]=useState<any[]>([])
 async function load(){try{setCandidates(await api<any[]>('/api/collectors/candidates?limit=50&status=new'))}catch{}}
 useEffect(()=>{load()},[])
 async function runSitemap(){setBusy(true);setMsg('运行 Sitemap Watcher...');try{const r=await api<any>('/api/collectors/sitemap/run',{method:'POST',body:JSON.stringify({domains:domains.split(/[\n,]+/).map(x=>x.trim()).filter(Boolean),max_urls_per_domain:80})});setMsg(`✅ Sitemap: saved=${r.saved}, seen=${r.candidates_seen}, errors=${r.errors?.length||0}`);await load()}catch(e:any){setMsg(`❌ ${e.message}`)}finally{setBusy(false)}}
 async function runSuggest(){setBusy(true);setMsg('运行 Suggest Collector...');try{const r=await api<any>('/api/collectors/suggest/run',{method:'POST',body:JSON.stringify({seeds:seeds.split(/[\n,]+/).map(x=>x.trim()).filter(Boolean)})});setMsg(`✅ Suggest: saved=${r.saved}, seen=${r.candidates_seen}`);await load()}catch(e:any){setMsg(`❌ ${e.message}`)}finally{setBusy(false)}}
 async function importCandidates(){setBusy(true);setMsg('导入关键词流...');try{const r=await api<any>('/api/collectors/candidates/import',{method:'POST',body:JSON.stringify({limit:30})});setMsg(`✅ 已导入 keyword：${r.imported}/${r.selected}`);await load()}catch(e:any){setMsg(`❌ ${e.message}`)}finally{setBusy(false)}}
 async function runAdvanced(){setBusy(true);setMsg('运行 Advanced Search Collector...');try{const r=await api<any>('/api/collectors/advanced-search/run',{method:'POST',body:JSON.stringify({roots:advRoots.split(/[\n,]+/).map(x=>x.trim()).filter(Boolean),domains:advDomains.split(/[\n,]+/).map(x=>x.trim()).filter(Boolean),days:30,limit_per_query:8})});setMsg(`✅ Advanced Search: saved=${r.saved}, seen=${r.candidates_seen}, queries=${r.queries}`);await load()}catch(e:any){setMsg(`❌ ${e.message}`)}finally{setBusy(false)}}
 async function runRadar(){setBusy(true);setMsg('运行 Source Radar...');try{const r=await api<any>('/api/collectors/source-radar/run',{method:'POST',body:JSON.stringify({seeds:radarSeeds.split(/[\n,]+/).map(x=>x.trim()).filter(Boolean),limit_per_seed:10})});setMsg(`✅ Source Radar: saved=${r.saved}, seen=${r.candidates_seen}`);await load()}catch(e:any){setMsg(`❌ ${e.message}`)}finally{setBusy(false)}}
 return <div className="space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl">
   <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Collectors</p>
   <h1 className="mt-3 text-4xl font-black text-white">采集器</h1>
   <p className="mt-3 max-w-3xl text-slate-300">文章组方法已经收敛成统一候选池：采集器只发现候选，不能直接产出机会；候选必须进入 Four-Find / SEO / LLM 机会判断。</p>
  </section>

  <section className="panel">
   <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">统一流转</h2><p className="mt-1 text-sm text-slate-400">词根 → 扩词 → 找站 → 反查词 → 监控新页面/新词 → SEO 验证 → 机会卡</p></div><button className="btn" disabled={busy||!candidates.length} onClick={importCandidates}>导入候选到关键词流</button></div>
   <div className="mt-4 grid gap-3 md:grid-cols-5">{['采集源','候选池','Four-Find 扩展','SEO 验证','机会卡'].map((x,i)=><div key={x} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-center"><div className="text-xs text-slate-500">Step {i+1}</div><b className="text-slate-100">{x}</b></div>)}</div>
   {msg&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}
  </section>

  <section className="grid gap-4 xl:grid-cols-2">
   <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl"><div className="flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">P0 · 站找词</div><h2 className="mt-2 text-xl font-bold text-white">Sitemap Watcher</h2></div><span className="badge badge-action">免费</span></div><p className="mt-3 text-sm text-slate-300">每行一个竞品域名，自动读取 robots.txt / sitemap.xml，抽取 URL 长尾词进入候选池。</p><textarea className="input mt-4 min-h-28 w-full font-mono text-sm" value={domains} onChange={e=>setDomains(e.target.value)} placeholder={'example.com\ncompetitor.com'}/><button className="btn mt-3" disabled={busy||!domains.trim()} onClick={runSitemap}>运行 Sitemap Watcher</button></div>
   <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl"><div className="flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">P0 · 词找词</div><h2 className="mt-2 text-xl font-bold text-white">Suggest Collector</h2></div><span className="badge badge-action">免费</span></div><p className="mt-3 text-sm text-slate-300">每行一个 seed keyword，调用公开 Suggest 接口扩展长尾搜索词进入候选池。</p><textarea className="input mt-4 min-h-28 w-full font-mono text-sm" value={seeds} onChange={e=>setSeeds(e.target.value)} placeholder={'invoice calculator\nai image generator\nshopify tax app'}/><button className="btn mt-3" disabled={busy||!seeds.trim()} onClick={runSuggest}>运行 Suggest Collector</button></div>
   <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl"><div className="flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">P1 · 高级搜索</div><h2 className="mt-2 text-xl font-bold text-white">Advanced Search Collector</h2></div><span className="badge badge-action">轮询 SERP</span></div><p className="mt-3 text-sm text-slate-300">allintitle / site / after 变体，从 SERP title 和 URL 抽候选。</p><textarea className="input mt-4 min-h-20 w-full font-mono text-sm" value={advRoots} onChange={e=>setAdvRoots(e.target.value)} placeholder={'calculator\ngenerator\ntemplate'}/><textarea className="input mt-3 min-h-20 w-full font-mono text-sm" value={advDomains} onChange={e=>setAdvDomains(e.target.value)} placeholder={'可选竞品域名：example.com\ncompetitor.com'}/><button className="btn mt-3" disabled={busy||!advRoots.trim()} onClick={runAdvanced}>运行 Advanced Search</button></div>
   <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl"><div className="flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">P1 · 信息溯源</div><h2 className="mt-2 text-xl font-bold text-white">Source Radar</h2></div><span className="badge badge-action">免费</span></div><p className="mt-3 text-sm text-slate-300">从 HN Algolia 和 arXiv 抓早期讨论/论文标题，捕捉新词源头。</p><textarea className="input mt-4 min-h-28 w-full font-mono text-sm" value={radarSeeds} onChange={e=>setRadarSeeds(e.target.value)} placeholder={'ai agent\nrag evaluation\nmcp server'}/><button className="btn mt-3" disabled={busy||!radarSeeds.trim()} onClick={runRadar}>运行 Source Radar</button></div>
  </section>

  <section className="grid gap-4 xl:grid-cols-2">{collectors.map(c=><article key={c.id} id={c.id} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">{c.tag}</div><h2 className="mt-2 text-xl font-bold text-white">{c.name}</h2></div><span className={c.status.includes('已接入')?'badge badge-action':c.status.includes('付费')?'badge badge-watch':'badge'}>{c.status}</span></div><p className="mt-3 text-sm leading-6 text-slate-300">{c.desc}</p><div className="mt-4"><div className="mb-2 text-xs font-semibold text-slate-500">数据源</div><div className="flex flex-wrap gap-2">{c.feeds.map(f=><span key={f} className="rounded-lg bg-slate-900 px-2 py-1 text-xs text-slate-300">{f}</span>)}</div></div><div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-3 text-xs text-slate-400"><b className="text-slate-300">输出：</b>{c.output}</div></article>)}</section>

  <section className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70 shadow-xl"><div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/70 px-5 py-3"><h2 className="font-bold">候选池 New Candidates</h2><span className="text-sm text-slate-500">{candidates.length} 条</span></div><div className="divide-y divide-slate-800">{candidates.length?candidates.map(c=><div key={c.id} className="grid gap-2 px-5 py-3 text-sm md:grid-cols-[1.2fr_0.7fr_0.7fr_1.4fr]"><b className="text-slate-100">{c.keyword}</b><span className="text-slate-400">{c.method}</span><span className="text-slate-500">{c.source}</span><span className="truncate text-slate-500">{c.source_url||JSON.stringify(c.evidence||{})}</span></div>):<div className="px-5 py-6 text-sm text-slate-500">暂无候选。先运行 Sitemap 或 Suggest。</div>}</div></section>
 </div>
}
