'use client'
import {Fragment, useEffect, useMemo, useState} from 'react'
import {usePathname} from 'next/navigation'
import {api, authToken} from '../lib/api'

type Section = 'overview' | 'conditions' | 'sources' | 'records'
type Tone = 'slate' | 'green' | 'blue' | 'amber' | 'purple' | 'red'

const sectionItems:{id:Section; label:string; desc:string}[] = [
 {id:'overview', label:'总览', desc:'结果、风险、下一步'},
 {id:'conditions', label:'搜索条件', desc:'系统依据什么继续找'},
 {id:'sources', label:'线索模型库', desc:'每个模型如何产出线索'},
 {id:'records', label:'抓取记录', desc:'每次抓取结果'},
]

const sourceLabels:any={
 sitemap:'Sitemap',
 domain_web:'Domain Web',
 suggest:'Google Suggest',
 google_suggest:'Google Suggest',
 duckduckgo:'DuckDuckGo Suggest',
 short_tail_rewrite:'Short Tail Rewrite',
 root_combo:'Root Combo',
 advanced_search:'SERP Search',
 alternatives:'Alternative',
 hot_topic:'Hot Topic',
 source_radar:'Source Radar',
 hn_algolia:'HN Algolia',
 arxiv:'arXiv',
 social:'Social',
 forum:'Forum',
 review:'Review',
 docs:'Docs',
 changelog:'Changelog',
 pricing_pages:'Pricing Pages',
 keyword_to_keyword:'词找词',
 keyword_to_site:'词找站',
 site_to_keyword:'站找词',
 site_to_site:'站找站',
}
const segmentLabels:any={winner:'高价值',promising:'可继续观察',new:'新搜索条件',noisy:'噪音高',cooldown:'已暂停',exhausted:'暂无价值'}

type ClueModel = {
 id:string
 category:string
 name:string
 status:'connected'|'planned'
 sources:string[]
 description:string
 input:string
 output:string
 endpoint?:string
 inputKind?:'domains'|'seeds'|'advanced'
}

const clueModelGroups = ['搜索扩展类','SERP 类','站点类','热点 / 早期信号类','社交 / 论坛 / 评论类','文档 / 更新 / 定价类','四找闭环类']

const clueModels:ClueModel[]=[
 {id:'google_suggest',category:'搜索扩展类',name:'Google Suggest',status:'connected',sources:['google_suggest','duckduckgo','suggest'],description:'从搜索联想里扩展用户已经开始表达的搜索需求。',input:'seed keyword / 搜索条件',output:'长尾搜索词线索',endpoint:'/api/collectors/suggest/run',inputKind:'seeds'},
 {id:'short_tail_rewrite',category:'搜索扩展类',name:'Short Tail Rewrite',status:'connected',sources:['short_tail_rewrite'],description:'把过短或泛化的词改写成更具体的任务型搜索词。',input:'短词 / 被拒绝候选词',output:'改写后的搜索词线索'},
 {id:'root_combo',category:'搜索扩展类',name:'Root Combo',status:'connected',sources:['root_combo'],description:'用词根和业务修饰词组合出可验证的搜索需求。',input:'词根库 / 修饰词',output:'组合搜索词线索'},
 {id:'serp_search',category:'SERP 类',name:'SERP Search',status:'connected',sources:['advanced_search','serp'],description:'从搜索结果标题、站点和时间范围组合中发现新页面和内容缺口。',input:'搜索词 / 域名 / 时间范围',output:'页面、竞品和搜索词线索',endpoint:'/api/collectors/advanced-search/run',inputKind:'advanced'},
 {id:'sitemap',category:'站点类',name:'Sitemap',status:'connected',sources:['sitemap'],description:'从网站 sitemap 发现新工具页、模板页、对比页和功能页。',input:'域名 / sitemap URL',output:'新页面和可转译的搜索词线索',endpoint:'/api/collectors/sitemap/run',inputKind:'domains'},
 {id:'domain_web',category:'站点类',name:'Domain Web',status:'connected',sources:['domain_web'],description:'抓取网页标题、H1、Meta，识别页面表达的任务需求。',input:'域名 / 页面 URL',output:'页面内容中的需求线索',endpoint:'/api/collectors/domain-web/run',inputKind:'domains'},
 {id:'alternatives',category:'站点类',name:'Alternative',status:'connected',sources:['alternatives'],description:'通过替代品、对比、迁移相关查询发现竞品缺口和替代机会。',input:'竞品域名 / 产品名',output:'替代品、相邻站点和对比需求线索',endpoint:'/api/collectors/alternatives/run',inputKind:'domains'},
 {id:'hot_topic',category:'热点 / 早期信号类',name:'Hot Topic',status:'connected',sources:['hot_topic'],description:'围绕活跃主题和年份/监管/AI 等修饰词发现近期任务线索。',input:'主题 / 搜索条件',output:'近期热点搜索线索',endpoint:'/api/collectors/hot-topic/run',inputKind:'seeds'},
 {id:'hn_algolia',category:'热点 / 早期信号类',name:'HN Algolia',status:'connected',sources:['hn_algolia','source_radar'],description:'从 HN 等早期信号中捕捉新工具、新项目和新需求苗头。',input:'seed / 技术主题',output:'早期趋势线索',endpoint:'/api/collectors/source-radar/run',inputKind:'seeds'},
 {id:'github_trending',category:'热点 / 早期信号类',name:'GitHub Trending',status:'planned',sources:['github_trending'],description:'发现快速增长的新项目和开发者工具机会。',input:'语言 / 主题 / 时间窗口',output:'项目和趋势实体线索'},
 {id:'product_hunt',category:'热点 / 早期信号类',name:'Product Hunt',status:'planned',sources:['product_hunt'],description:'发现新发布的工具、产品和细分需求方向。',input:'榜单 / 分类',output:'产品和趋势实体线索'},
 {id:'steam',category:'热点 / 早期信号类',name:'Steam',status:'planned',sources:['steam'],description:'发现新游戏、游戏机制和玩家工具机会。',input:'游戏榜单 / 标签',output:'游戏与玩家需求线索'},
 {id:'arxiv',category:'热点 / 早期信号类',name:'arXiv',status:'planned',sources:['arxiv'],description:'发现研究热点、新模型和可工具化技术趋势。',input:'主题 / 论文分类',output:'模型和技术趋势线索'},
 {id:'social',category:'社交 / 论坛 / 评论类',name:'Social / Forum / Review',status:'planned',sources:['social','forum','review','reddit','community'],description:'从讨论、抱怨、评价和论坛帖子中发现真实痛点。',input:'社区 / 关键词 / 产品名',output:'痛点、场景和用户语言线索'},
 {id:'docs',category:'文档 / 更新 / 定价类',name:'Docs / Changelog',status:'planned',sources:['docs','changelog'],description:'从文档和更新日志中发现平台变化、新功能和生态机会。',input:'文档页 / changelog',output:'平台更新和功能变化线索'},
 {id:'pricing_pages',category:'文档 / 更新 / 定价类',name:'Pricing Pages',status:'planned',sources:['pricing_pages','pricing_page'],description:'从定价页变化中发现商业模式、套餐和竞品动作。',input:'定价页 URL',output:'商业化变化线索'},
 {id:'keyword_to_keyword',category:'四找闭环类',name:'词找词',status:'connected',sources:['four_find:related','four_find:modifier','four_find:business_modifier','google_suggest','duckduckgo','suggest'],description:'从一个 seed keyword 扩展更多搜索表达。',input:'seed keyword',output:'扩展词线索'},
 {id:'keyword_to_site',category:'四找闭环类',name:'词找站',status:'planned',sources:['four_find:keyword_to_site'],description:'用关键词找到承接需求的网站、竞品和内容占位。',input:'搜索词',output:'竞品站点和页面线索'},
 {id:'site_to_keyword',category:'四找闭环类',name:'站找词',status:'connected',sources:['four_find:site_to_keyword','sitemap','domain_web'],description:'从竞品站、sitemap 和页面内容反查需求词。',input:'域名 / 页面',output:'站点反查关键词线索'},
 {id:'site_to_site',category:'四找闭环类',name:'站找站',status:'planned',sources:['four_find:site_to_site'],description:'从竞品和替代品扩展相邻站点与赛道。',input:'竞品域名',output:'相邻站点和替代机会线索'},
]
function fmtTime(s?:string){if(!s)return '-'; const d=new Date(s); if(Number.isNaN(d.getTime()))return '-'; return d.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}
function sourceName(x?:string){return sourceLabels[x||''] || x || '未知来源'}
function segmentName(x?:string){return segmentLabels[x||''] || x || '其他'}
function statusFor(leads:number, problems:number){if(leads>0)return {icon:'✅',label:'有发现',tone:'green' as Tone}; if(problems>0)return {icon:'⚠️',label:'需检查',tone:'amber' as Tone}; return {icon:'—',label:'暂无发现',tone:'slate' as Tone}}
function toneText(tone:Tone){return {slate:'text-white',green:'text-emerald-300',blue:'text-blue-300',amber:'text-amber-300',purple:'text-purple-300',red:'text-red-300'}[tone]}
function toneBorder(tone:Tone){return {slate:'hover:ring-slate-500/30',green:'hover:ring-emerald-500/40',blue:'hover:ring-blue-500/40',amber:'hover:ring-amber-500/40',purple:'hover:ring-purple-500/40',red:'hover:ring-red-500/40'}[tone]}

function normalizeRecords(runs:any[]){
 return (runs||[]).flatMap((run:any)=>{
  const s=run.summary||{}
  const selected=s.selected_by_segment||{}
  const inputObjects=Object.entries(selected).flatMap(([segment,items]:any)=>(items||[]).map((item:any)=>({...item,segment})))
  const conditionCount=inputObjects.length
  return (s.source_results||[]).map((r:any,i:number)=>{
   const leads=Number(r.saved||0), looked=Number(r.seen||0), problems=Number(r.errors||0)
   const st=statusFor(leads, problems)
   const verifiedItems=[...(s.auto_verify?.verified||[]),...(s.auto_verify?.skipped||[])]
   return {id:`${run.id}-${i}`, batch:run.id, time:run.started_at, source:r.source||'unknown', sourceLabel:sourceName(r.source), trigger:s.trigger||'automation', leads, looked, problems, status:st, verified:s.import?.imported||0, selected:s.import?.selected||0, filtered:s.clean?.rejected||0, paused:s.target_health?.cooled||0, conditionCount, inputObjects, verifiedItems, selectedBySegment:selected, generatedClues:[], raw:r}
  })
 })
}

function normalizeSourceRuns(rows:any[]){
 return (rows||[]).map((row:any)=>{
  const outputs=row.outputs||{}
  const inputs=row.inputs||{}
  const errors=Array.isArray(row.errors)?row.errors:[]
  const inputItems=[
   ...((inputs.seeds||[]).map((value:string,i:number)=>({id:`seed-${row.id}-${i}`,type:'keyword',value,segment:'manual'}))),
   ...((inputs.topics||[]).map((value:string,i:number)=>({id:`topic-${row.id}-${i}`,type:'keyword',value,segment:'manual'}))),
   ...((inputs.roots||[]).map((value:string,i:number)=>({id:`root-${row.id}-${i}`,type:'keyword',value,segment:'manual'}))),
   ...((inputs.domains||[]).map((value:string,i:number)=>({id:`domain-${row.id}-${i}`,type:'domain',value,segment:'manual'}))),
  ]
  const leads=Number(row.candidates_created??outputs.saved??outputs.imported??0)
  const looked=Number(outputs.seen??outputs.urls_seen??outputs.pages_seen??outputs.candidates_seen??0)
  const problems=errors.length
  return {
   id:`source-run-${row.id}`,
   batch:`M${row.id}`,
   time:row.started_at,
   source:row.source||'unknown',
   sourceLabel:sourceName(row.source),
   trigger:row.run_kind||'manual',
   leads,
   looked,
   problems,
   status:statusFor(leads, problems),
   verified:Number(row.keywords_promoted||0),
   selected:0,
   filtered:Number(row.rejects_created||0),
   paused:0,
   conditionCount:inputItems.length,
   inputObjects:inputItems,
   verifiedItems:[],
   selectedBySegment:{manual:inputItems},
   generatedClues:outputs.generatedClues||outputs.candidates||outputs.keywords||outputs.items||[],
   raw:outputs,
  }
 })
}

export function CollectorsPage({initialSection='overview'}:{initialSection?:string}){
 const pathname=usePathname()
 const current=(pathname.split('/').pop() || initialSection) as Section
 const section:Section = sectionItems.some(x=>x.id===current) ? current : 'overview'
 const [busy,setBusy]=useState(false)
 const [msg,setMsg]=useState('')
 const [health,setHealth]=useState<any|null>(null)
 const [segments,setSegments]=useState<any|null>(null)
 const [budget,setBudget]=useState<any|null>(null)
 const [runs,setRuns]=useState<any[]>([])
 const [sourceRuns,setSourceRuns]=useState<any[]>([])
 const [sourceRunStats,setSourceRunStats]=useState<any|null>(null)
 const [candidates,setCandidates]=useState<any[]>([])
 const [repairRuns,setRepairRuns]=useState<any[]>([])
 const [repairAutoRuns,setRepairAutoRuns]=useState<any[]>([])
 const [matrix,setMatrix]=useState<any|null>(null)
 const [rejectedReasons,setRejectedReasons]=useState<any|null>(null)
 const [trace,setTrace]=useState<any|null>(null)
 const [showLog,setShowLog]=useState(false)
 const [recordSource,setRecordSource]=useState('all')
 const [recordStatus,setRecordStatus]=useState('all')

 async function load(){
  try{
   const [h,seg,bg,rs,srs,srsStats,cs,repairs,repairAutos,mx]=await Promise.all([
    api<any>('/api/collectors/health'),
    api<any>('/api/collectors/targets/segments'),
    api<any>('/api/collectors/budget/next?limit=24'),
    api<any[]>('/api/collectors/runs?limit=8'),
    api<any[]>('/api/collectors/source-runs?limit=80').catch(()=>[]),
    api<any>('/api/collectors/source-runs/stats').catch(()=>null),
    api<any[]>('/api/collectors/candidates?limit=80&status=new'),
    api<any[]>('/api/collectors/repairs?limit=8'),
    api<any[]>('/api/collectors/repairs/autopilot/runs?limit=6'),
    api<any>('/api/collectors/matrix?limit=400'),
   ])
   setHealth(h); setSegments(seg); setBudget(bg); setRuns(rs); setSourceRuns(srs); setSourceRunStats(srsStats); setCandidates(cs); setRepairRuns(repairs); setRepairAutoRuns(repairAutos); setMatrix(mx)
  }catch(e:any){setMsg(`加载失败：${e.message}`)}
 }
 useEffect(()=>{load()},[])

 async function runDiscovery(){setBusy(true);setMsg('正在抓取机会线索...');try{const r=await api<any>('/api/collectors/autopilot/run',{method:'POST',body:JSON.stringify({limit:24})});setMsg(`抓取完成：${r.import?.imported||0}/${r.import?.selected||0} 条进入验证，过滤 ${r.clean?.rejected||0} 条噪音`);await load()}catch(e:any){setMsg(`运行失败：${e.message}`)}finally{setBusy(false)}}
 async function refreshConditions(){setBusy(true);setMsg('正在从机会判断更新搜索条件...');try{const r=await api<any>('/api/collectors/targets/refresh',{method:'POST'});setMsg(`已更新：搜索词 ${r.keyword_targets||0}，网站 ${r.domain_targets||0}`);await load()}catch(e:any){setMsg(`更新失败：${e.message}`)}finally{setBusy(false)}}
 async function tidyConditions(){setBusy(true);try{const r=await api<any>('/api/collectors/targets/health',{method:'POST'});setMsg(`整理完成：暂停 ${r.cooled||0}，恢复 ${r.promoted||0}`);await load()}catch(e:any){setMsg(`整理失败：${e.message}`)}finally{setBusy(false)}}
 async function inspectRejected(){setBusy(true);try{const r=await api<any>('/api/collectors/rejected-reasons?limit=800');setRejectedReasons(r); setShowLog(true)}catch(e:any){setMsg(`检查失败：${e.message}`)}finally{setBusy(false)}}
 async function downloadDigest(){setBusy(true);try{const token=authToken(); const res=await fetch('/api/reports/download/latest',{headers:token?{Authorization:`Bearer ${token}`}:{}}); if(!res.ok) throw new Error(`${res.status} ${await res.text()}`); const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='demand_cards_latest.md'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)}catch(e:any){setMsg(`下载失败：${e.message}`)}finally{setBusy(false)}}

 const records=useMemo(()=>[...normalizeRecords(runs),...normalizeSourceRuns(sourceRuns)],[runs,sourceRuns])
 const latest=runs?.[0]?.summary||{}
 const sourceRows=latest.source_results||[]
 const segSummary=segments?.summary||{}
 const segMap=segments?.segments||{}
 const highValue=[...(segMap.winner||[]),...(segMap.promising||[]),...(segMap.new||[])]
 const weak=[...(segMap.noisy||[]),...(segMap.cooldown||[]),...(segMap.exhausted||[])]
 const totalLeads=records.reduce((a,r)=>a+r.leads,0)
 const totalLooked=records.reduce((a,r)=>a+r.looked,0)
 const problemSources=records.filter(r=>r.problems>0)
 const sources=['all',...Array.from(new Set(records.map(r=>r.source)))]
 const visibleRecords=records.filter(r=>(recordSource==='all'||r.source===recordSource)&&(recordStatus==='all'||r.status.label===recordStatus))

 return <div className="space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl">
   <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Opportunity Discovery</p><h1 className="mt-3 text-4xl font-black text-white">机会发现中心</h1><p className="mt-3 max-w-3xl text-slate-300">用用户视角看结果：发现了多少线索、哪些进入验证、依据哪些搜索条件继续找。</p></div><div className="flex flex-wrap gap-2"><button className="btn" disabled={busy} onClick={runDiscovery}>开始抓取</button><button className="btn-secondary" disabled={busy} onClick={downloadDigest}>下载报告</button><button className="btn-secondary" disabled={busy} onClick={()=>setShowLog(true)}>优化记录</button></div></div>
  </section>
  {msg&&<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}
  <main className="space-y-6">
   {section==='overview'&&<Overview health={health} latest={latest} totalLeads={totalLeads} totalLooked={totalLooked} problemSources={problemSources} highValue={highValue} candidates={candidates} sourceRows={sourceRows} openTrace={setTrace}/>}
   {section==='conditions'&&<Conditions segSummary={segSummary} segMap={segMap} highValue={highValue} weak={weak} budget={budget} busy={busy} refreshConditions={refreshConditions} tidyConditions={tidyConditions} openTrace={setTrace}/>}
   {section==='sources'&&<Sources sourceRows={sourceRows} sourceRunStats={sourceRunStats} matrix={matrix} records={records} onRefresh={load}/>}
   {section==='records'&&<Records records={visibleRecords} allRecords={records} sources={sources} sourceFilter={recordSource} statusFilter={recordStatus} setSourceFilter={setRecordSource} setStatusFilter={setRecordStatus}/>}
  </main>
  {trace&&<TraceModal trace={trace} onClose={()=>setTrace(null)}/>} {showLog&&<OptimizationLog onClose={()=>setShowLog(false)} repairRuns={repairRuns} repairAutoRuns={repairAutoRuns} rejectedReasons={rejectedReasons} inspectRejected={inspectRejected} busy={busy}/>}
 </div>
}

function Overview({health,latest,totalLeads,totalLooked,problemSources,highValue,candidates,sourceRows,openTrace}:any){return <div className="space-y-6"><section className="grid gap-4 md:grid-cols-5"><TraceCard label="系统状态" value={`${health?.score??'-'}/100`} hint="查看风险" tone={health?.status==='healthy'?'green':health?.status==='watch'?'amber':'red'} onClick={()=>openTrace({title:'系统状态',type:'issues',items:health?.issues||[],empty:'暂无风险。'})}/><TraceCard label="有效搜索条件" value={highValue.length} hint="查看条件" tone="green" onClick={()=>openTrace({title:'有效搜索条件',type:'targets',items:highValue})}/><TraceCard label="待验证线索" value={candidates.length} hint="查看线索" tone="blue" onClick={()=>openTrace({title:'待验证线索',type:'candidates',items:candidates})}/><TraceCard label="进入验证" value={`${latest.import?.imported??0}/${latest.import?.selected??0}`} hint="查看最近一轮" tone="purple" onClick={()=>openTrace({title:'进入验证',type:'run',items:[latest]})}/><TraceCard label="需检查来源" value={problemSources.length} hint="查看来源" tone="amber" onClick={()=>openTrace({title:'需检查来源',type:'records',items:problemSources})}/></section><FlowCompact/><section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">最近一次抓取</h2><p className="mt-1 text-sm text-slate-400">点击任意数字查看它背后的数据。</p></div></div><div className="mt-4 grid gap-3 md:grid-cols-4"><TraceCard label="机会线索" value={totalLeads} tone="green" onClick={()=>openTrace({title:'机会线索来源',type:'sources',items:sourceRows})}/><TraceCard label="抓取结果" value={totalLooked||'-'} tone="blue" onClick={()=>openTrace({title:'抓取结果来源',type:'sources',items:sourceRows})}/><TraceCard label="异常来源" value={problemSources.length} tone="amber" onClick={()=>openTrace({title:'异常来源',type:'records',items:problemSources})}/><TraceCard label="进入验证" value={`${latest.import?.imported??0}/${latest.import?.selected??0}`} tone="purple" onClick={()=>openTrace({title:'进入验证',type:'run',items:[latest]})}/></div></section><section className="space-y-4"><TargetList title="当前优先搜索条件" items={highValue.slice(0,12)}/><SourceList rows={sourceRows}/></section></div>}
function FlowCompact(){const steps=[['搜索条件','机会卡/人工词/竞品网站'],['线索模型','网站/搜索结果/联想/热点'],['机会线索','过滤噪音后进入线索池'],['进入验证','可用线索进入搜索验证'],['机会判断','Action / Watch / Reject 回流条件']]; return <section className="panel"><h2 className="text-xl font-bold">系统如何找机会</h2><p className="mt-1 text-sm text-slate-400">这是背景说明，不单独占菜单入口。</p><div className="mt-4 grid gap-3 md:grid-cols-5">{steps.map(([t,d],i)=><div key={t} className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="mb-2 flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-black text-white">{i+1}</div><b className="text-sm text-white">{t}</b><p className="mt-1 text-xs leading-5 text-slate-400">{d}</p></div>)}</div></section>}
function Conditions({segSummary,segMap,highValue,weak,budget,busy,refreshConditions,tidyConditions,openTrace}:any){const cats=[['winner','高价值'],['promising','可继续观察'],['new','新搜索条件'],['noisy','噪音高'],['cooldown','已暂停'],['exhausted','暂无价值']]; return <div className="space-y-6"><section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">搜索条件分类</h2><p className="mt-1 text-sm text-slate-400">点击数字，查看对应条件。</p></div><div className="flex gap-2"><button className="btn-secondary" disabled={busy} onClick={tidyConditions}>整理搜索条件</button><button className="btn" disabled={busy} onClick={refreshConditions}>从机会卡更新</button></div></div><div className="mt-4 grid gap-3 md:grid-cols-6">{cats.map(([k,l])=><TraceCard key={k} label={l} value={segSummary[k]||0} onClick={()=>openTrace({title:l,type:'targets',items:segMap[k]||[],empty:`暂无${l}`})}/>)}</div></section><section className="grid gap-4 xl:grid-cols-2"><TargetList title="有效搜索条件" items={highValue}/><TargetList title="暂停/低价值条件" items={weak}/></section><section className="panel"><h2 className="text-xl font-bold">下一轮投入</h2><div className="mt-4 grid gap-3 md:grid-cols-4">{(budget?.allocation||[]).map((row:any)=><TraceCard key={row.segment} label={row.label} value={row.budget} hint={`可用 ${row.available}`} tone="green" onClick={()=>openTrace({title:`${row.label} 投入条件`,type:'targets',items:row.targets||[]})}/>)}</div></section></div>}
function Sources({sourceRows,sourceRunStats,matrix,records,onRefresh}:any){
 const [selected,setSelected]=useState<ClueModel|null>(null)
 const [openGroups,setOpenGroups]=useState<Record<string,boolean>>({'搜索扩展类':true})
 const models=clueModels.map(model=>withModelStats(model, sourceRows||[], matrix?.rows||[], records||[], sourceRunStats?.by_source||null))
 const totals=models.reduce((acc:any,item:any)=>({runs:acc.runs+item.stats.runs,leads:acc.leads+item.stats.leads,seen:acc.seen+item.stats.seen,errors:acc.errors+item.stats.errors,connected:acc.connected+(item.status==='connected'?1:0)}),{runs:0,leads:0,seen:0,errors:0,connected:0})
 return <div className="space-y-6">
  <section className="panel">
   <div className="flex flex-wrap items-start justify-between gap-4">
    <div>
     <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Clue Model Library</p>
     <h2 className="mt-2 text-3xl font-black text-white">线索模型库</h2>
     <p className="mt-2 max-w-4xl text-sm text-slate-400">这里是机会发现的第一个口：查看哪些模型正在产生机会线索、每个模型贡献多少、哪些模型还未接入。点击模型查看运行明细和输入对象效果。</p>
    </div>
    <span className="badge">{totals.connected}/{models.length} 已接入</span>
   </div>
   <div className="mt-5 grid gap-3 md:grid-cols-4">
    <MetricBlock label="运行批次" value={totals.runs}/>
    <MetricBlock label="抓取结果" value={totals.seen} tone="blue"/>
    <MetricBlock label="贡献线索" value={totals.leads} tone="green"/>
    <MetricBlock label="异常" value={totals.errors} tone={totals.errors?'amber':'slate'}/>
   </div>
  </section>
  {clueModelGroups.map(group=>{
   const groupModels=models.filter(item=>item.category===group)
   const opened=openGroups[group] ?? false
   return <section key={group} className="space-y-3">
    <button type="button" onClick={()=>setOpenGroups({...openGroups,[group]:!opened})} className="flex w-full items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-left transition hover:border-blue-500/40">
     <div className="flex items-center gap-3"><span className="text-sm text-blue-300">{opened?'▾':'▸'}</span><h3 className="text-xl font-bold text-white">{group}</h3></div>
     <span className="text-sm text-slate-500">{groupModels.filter(m=>m.status==='connected').length}/{groupModels.length} 已接入</span>
    </button>
    {opened&&<div className="grid gap-4 xl:grid-cols-2">
     {groupModels.map(model=><ModelCard key={model.id} model={model} onOpen={()=>setSelected(model)}/>)}
    </div>}
   </section>
  })}
  {selected&&<ModelDrawer model={selected} records={records||[]} matrixRows={matrix?.rows||[]} onRefresh={onRefresh} onClose={()=>setSelected(null)}/>}
 </div>
}

function normalizeSourceKey(x?:string){return (x||'unknown').toLowerCase()}
function modelMatchesSource(model:ClueModel, source?:string){const raw=normalizeSourceKey(source); return model.sources.some(s=>normalizeSourceKey(s)===raw)}
function sourceStatsForModel(model:ClueModel, statsBySource:any){
 if(!statsBySource)return null
 const sources=Object.keys(statsBySource).filter(source=>modelMatchesSource(model,source))
 if(!sources.length)return {runs:0,seen:0,leads:0,errors:0}
 return sources.reduce((acc:any,source:string)=>{
  const row=statsBySource[source]||{}
  acc.runs+=Number(row.runs||0)
  acc.seen+=Number(row.seen||0)
  acc.leads+=Number(row.leads||0)
  acc.errors+=Number(row.errors||0)
  return acc
 },{runs:0,seen:0,leads:0,errors:0})
}
function withModelStats(model:ClueModel, sourceRows:any[], matrixRows:any[], records:any[], statsBySource?:any){
 if(model.status==='planned'){
  const stats={runs:0,seen:0,leads:0,errors:0,effective:0,rejected:0,inputs:0}
  return {...model,stats,sourceRows:[],matrixRows:[],runRows:[]}
 }
 const perf=sourceRows.filter(row=>modelMatchesSource(model,row.source))
 const runRows=records.filter((row:any)=>modelMatchesSource(model,row.source))
 const matrixMatches=matrixRows.filter(row=>modelMatchesSource(model,row.source))
 const manualRows=runRows
  .filter((row:any)=>row.trigger==='manual'&&row.inputObjects?.length)
  .flatMap((row:any)=>row.inputObjects.map((item:any)=>({
   target_id:`${row.id}-${item.id||item.value}`,
   condition:item.value,
   type:item.type,
   segment:item.segment,
   source:row.source,
   leads:row.leads,
   success:0,
   reject:0,
    verdict:'暂无判断',
   priority:0,
   runId:row.batch,
   latestAt:row.time,
 })))
 const rows=[...manualRows,...matrixMatches]
 const aggregateStats=sourceStatsForModel(model, statsBySource)
  const stats={
   runs: aggregateStats?.runs ?? runRows.length,
   seen: aggregateStats?.seen ?? runRows.reduce((a:number,row:any)=>a+Number(row.looked||0),0),
   leads: aggregateStats?.leads ?? runRows.reduce((a:number,row:any)=>a+Number(row.leads||0),0),
   errors: aggregateStats?.errors ?? runRows.reduce((a:number,row:any)=>a+Number(row.problems||0),0),
  effective: rows.reduce((a,row)=>a+Number(row.success||0),0),
  rejected: rows.reduce((a,row)=>a+Number(row.reject||0),0),
  inputs: new Set(rows.map(row=>row.condition).filter(Boolean)).size,
 }
 return {...model,stats,sourceRows:perf,matrixRows:rows,runRows}
}
function modelStatus(model:any){if(model.status==='planned')return {label:'未接入',tone:'slate' as Tone}; if(model.stats.errors>0)return {label:'需检查',tone:'amber' as Tone}; if(model.stats.leads>0||model.stats.seen>0||model.stats.runs>0)return {label:'有数据',tone:'green' as Tone}; return {label:'已接入',tone:'blue' as Tone}}
function noiseRate(model:any){const total=Number(model.stats.effective||0)+Number(model.stats.rejected||0); if(!total)return '-'; return `${Math.round((Number(model.stats.rejected||0)/total)*100)}%`}
function ModelCard({model,onOpen}:{model:any;onOpen:()=>void}){const st=modelStatus(model); return <button type="button" onClick={onOpen} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 text-left transition hover:border-blue-500/50"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs text-blue-300">{model.category}</div><h4 className="mt-2 text-xl font-bold text-white">{model.name}</h4></div><span className={`${toneText(st.tone)} rounded-xl border border-slate-700 bg-slate-900 px-3 py-1 text-xs`}>{st.label}</span></div><p className="mt-3 min-h-10 text-sm leading-5 text-slate-400">{model.description}</p><div className="mt-4 grid grid-cols-3 gap-2"><MetricBlock label="运行" value={model.stats.runs}/><MetricBlock label="结果" value={model.stats.seen} tone="blue"/><MetricBlock label="线索" value={model.stats.leads} tone="green"/></div><div className="mt-3 grid grid-cols-3 gap-2"><MetricBlock label="有效" value={model.stats.effective} tone="green"/><MetricBlock label="拒绝" value={model.stats.rejected} tone={model.stats.rejected?'amber':'slate'}/><MetricBlock label="噪音率" value={noiseRate(model)} tone={model.stats.rejected?'amber':'slate'}/></div></button>}
function ModelDrawer({model,records,matrixRows,onRefresh,onClose}:{model:any;records:any[];matrixRows:any[];onRefresh:()=>Promise<void>;onClose:()=>void}){const [manualRuns,setManualRuns]=useState<any[]>([]); const [manualEffects,setManualEffects]=useState<any[]>([]); const rows=[...(manualEffects||[]),...(model.matrixRows||[])]; const runRows=[...(manualRuns||[]),...(model.runRows||[])]; const manualStats=manualRuns.reduce((acc:any,r:any)=>({runs:acc.runs+1,seen:acc.seen+Number(r.looked||0),leads:acc.leads+Number(r.leads||0),errors:acc.errors+Number(r.problems||0)}),{runs:0,seen:0,leads:0,errors:0}); const liveStats={...model.stats,runs:Number(model.stats.runs||0)+manualStats.runs,seen:Number(model.stats.seen||0)+manualStats.seen,leads:Number(model.stats.leads||0)+manualStats.leads,errors:Number(model.stats.errors||0)+manualStats.errors}; const liveModel={...model,stats:liveStats}; return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-6xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">线索模型</div><h2 className="mt-1 text-3xl font-black text-white">{model.name}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{model.description}</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><section className="grid gap-3 md:grid-cols-6"><MetricBlock label="运行" value={liveStats.runs}/><MetricBlock label="结果" value={liveStats.seen} tone="blue"/><MetricBlock label="线索" value={liveStats.leads} tone="green"/><MetricBlock label="有效" value={liveStats.effective} tone="green"/><MetricBlock label="拒绝" value={liveStats.rejected} tone={liveStats.rejected?'amber':'slate'}/><MetricBlock label="异常" value={liveStats.errors} tone={liveStats.errors?'amber':'slate'}/></section><section className="mt-5 grid gap-4 xl:grid-cols-2"><ModelExplanation model={liveModel}/><ManualRunPanel model={model} onRun={async (run:any,effect:any)=>{setManualRuns([run,...manualRuns]); setManualEffects([effect,...manualEffects]); await onRefresh()}}/></section><section className="mt-5 panel"><h3 className="text-xl font-bold">运行记录</h3><p className="mt-1 text-sm text-slate-400">每一行是一轮自动化或人工触发；点击批次展开输入对象和本轮产生线索。异常通过“处理异常”单独查看。</p><RunRecordsTable rows={runRows}/></section><section className="mt-5 panel"><h3 className="text-xl font-bold">输入对象效果</h3><p className="mt-1 text-sm text-slate-400">这里展示模型围绕哪些输入对象产生了可进入线索池的对象。有效高的对象应继续推进，拒绝偏高的对象需要降权或暂停。</p><EffectRows rows={rows}/></section></aside></div>}
function modelSteps(model:any){const input=model.inputKind==='domains'?'读取域名、页面或 sitemap URL':model.inputKind==='advanced'?'组合搜索词、站点和时间范围':'读取 seed、主题或搜索条件'; return [input,'执行对应采集逻辑并生成候选对象','清洗噪音、去重并记录本轮数量','把可用对象送入线索池或后续质量门','把有效、拒绝、异常结果回写到模型效果中']}
function ModelExplanation({model}:{model:any}){const status=modelStatus(model); return <div className="rounded-xl border border-slate-800 bg-slate-900 p-4"><b className="text-slate-100">模型说明</b><p className="mt-2 text-sm leading-6 text-slate-400">{model.name} 的作用是：{model.description}</p><div className="mt-3 grid gap-2 text-sm md:grid-cols-2"><div className="rounded-xl bg-slate-950 p-3"><span className="text-slate-500">输入</span><div className="mt-1 text-slate-200">{model.input}</div></div><div className="rounded-xl bg-slate-950 p-3"><span className="text-slate-500">输出</span><div className="mt-1 text-slate-200">{model.output}</div></div><div className="rounded-xl bg-slate-950 p-3"><span className="text-slate-500">状态</span><div className={`mt-1 ${toneText(status.tone)}`}>{status.label}</div></div><div className="rounded-xl bg-slate-950 p-3"><span className="text-slate-500">来源标识</span><div className="mt-1 break-words font-mono text-xs text-slate-300">{model.sources.join(', ')}</div></div></div><div className="mt-3 rounded-xl bg-slate-950 p-3"><span className="text-sm font-semibold text-slate-200">运行逻辑</span><ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-slate-400">{modelSteps(model).map((step:string)=><li key={step}>{step}</li>)}</ol></div></div>}
function RunRecordsTable({rows}:{rows:any[]}){
 const [status,setStatus]=useState('all')
 const [sort,setSort]=useState('time_desc')
 const [open,setOpen]=useState<string|null>(null)
 const [errorRow,setErrorRow]=useState<any|null>(null)
 const filtered=(rows||[]).filter((r:any)=>status==='all'||(status==='has_leads'&&r.leads>0)||(status==='problem'&&r.problems>0)||(status==='verified'&&r.verified>0))
 const sorted=[...filtered].sort((a:any,b:any)=>{if(sort==='time_asc')return new Date(a.time||0).getTime()-new Date(b.time||0).getTime(); if(sort==='leads_desc')return Number(b.leads||0)-Number(a.leads||0); if(sort==='verified_desc')return Number(b.verified||0)-Number(a.verified||0); if(sort==='problems_desc')return Number(b.problems||0)-Number(a.problems||0); return new Date(b.time||0).getTime()-new Date(a.time||0).getTime()})
 return <div className="mt-4 space-y-3">
  <div className="flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3"><Select label="分类" value={status} setValue={setStatus} options={[['all','全部'],['has_leads','产生线索'],['verified','进入验证'],['problem','有异常']]}/><Select label="排序" value={sort} setValue={setSort} options={[['time_desc','时间新到旧'],['time_asc','时间旧到新'],['leads_desc','线索最多'],['verified_desc','进入验证最多'],['problems_desc','异常最多']]}/><span className="ml-auto text-sm text-slate-500">显示 {sorted.length}/{rows.length}</span></div>
  <div className="overflow-x-auto rounded-2xl border border-slate-800">
   <table className="w-full min-w-[920px] text-sm">
    <thead className="table-head"><tr><th className="py-3 text-left">批次</th><th className="py-3 text-left">触发</th><th className="py-3 text-left">时间</th><th className="py-3 text-left">线索</th><th className="py-3 text-left">抓取结果</th><th className="py-3 text-left">进入验证</th><th className="py-3 text-left">过滤噪音</th><th className="py-3 text-left">使用对象</th><th className="py-3 text-left">异常</th><th className="py-3 text-left">判断</th></tr></thead>
    <tbody>{sorted.length?sorted.map((r:any)=><Fragment key={r.id}><tr className="border-t border-slate-800"><td className="py-3"><button className="font-mono text-blue-300" onClick={()=>setOpen(open===r.id?null:r.id)}>{open===r.id?'▾':'▸'} #{r.batch}</button></td><td className="py-3 text-slate-400">{r.trigger==='manual'?'人工':'自动'}</td><td className="py-3 text-slate-400">{fmtTime(r.time)}</td><td className="py-3 font-semibold text-emerald-300">{r.leads}</td><td className="py-3 text-blue-300">{r.looked||'-'}</td><td className="py-3 text-purple-300">{r.verified}/{r.selected}</td><td className="py-3 text-slate-300">{r.filtered}</td><td className="py-3 text-slate-300">{r.conditionCount}</td><td className="py-3">{r.problems?<button className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-500/20" onClick={()=>setErrorRow(r)}>处理异常 {r.problems}</button>:<span className="text-slate-500">0</span>}</td><td className={toneText(r.status.tone)}>{r.status.label}</td></tr>{open===r.id&&<tr className="border-t border-slate-800 bg-slate-950/70"><td colSpan={10} className="p-4"><RunRecordDetails row={r}/></td></tr>}</Fragment>):<tr><td colSpan={10} className="py-6 text-slate-500">暂无符合条件的运行记录。</td></tr>}</tbody>
   </table>
  </div>
  {errorRow&&<RunErrorModal row={errorRow} onClose={()=>setErrorRow(null)}/>}
 </div>
}
function clueName(x:any){return x?.keyword||x?.name||x?.value||x?.query||''}
function clueEvidence(x:any){return x?.evidence||x?.raw_context||{}}
function clueInputValue(x:any){const ev=clueEvidence(x); return ev.seed||ev.root||ev.domain||ev.query||ev.source_domain||''}
function inputTypeLabel(type?:string){return type==='domain'?'网站':'搜索词'}
function candidateStatusLabel(status?:string){return {new:'待处理',imported:'已入关键词库',rejected:'已过滤'}[status||'']||status||'待观察'}
function normalizeEffectKey(value:any,type?:string){return `${type||objectTypeLabel(value)}::${String(value||'').trim().toLowerCase()}`}
function readableError(item:any){if(!item)return ''; if(typeof item==='string'||typeof item==='number')return String(item); const target=item.seed||item.domain||item.query||item.url||item.source||''; const msg=item.error||item.reason||item.message||item.detail||JSON.stringify(item); return target?`${target}：${msg}`:msg}
function runErrorItems(row:any){const raw=row.raw||{}; const rawErrors=raw.errors; let items:any[]=[]; if(Array.isArray(rawErrors))items=rawErrors; else if(typeof rawErrors==='string'&&rawErrors)items=[rawErrors]; else if(typeof rawErrors==='number'&&rawErrors>0)items=[`记录异常 ${rawErrors} 个`]; if(raw.error)items.push(raw.error); const clean=items.map(readableError).filter(Boolean); if(clean.length)return clean; if(Number(row.problems||0)>0)return [`本轮记录异常 ${row.problems} 个，但历史记录未保存具体异常明细。`]; return []}
function RunRecordDetails({row}:{row:any}){
 const inputs=row.inputObjects||[]
 const clues=row.generatedClues||[]
 const inputRows=inputs.length?inputs:[{id:'unknown',type:'keyword',value:'本轮未记录输入对象',segment:'unknown'}]
 const cluesByInput=new Map<string,any[]>()
 clues.forEach((clue:any)=>{const input=clueInputValue(clue); const key=normalizeEffectKey(input||inputRows[0]?.value,inputRows[0]?.type); cluesByInput.set(key,[...(cluesByInput.get(key)||[]),clue])})
  return <div className="space-y-4">
  <div className="grid gap-3 md:grid-cols-3"><MetricBlock label="输入对象" value={row.conditionCount||inputs.length}/><MetricBlock label="产生线索" value={row.leads} tone="green"/><MetricBlock label="抓取结果" value={row.looked||'-'} tone="blue"/></div>
  <div className="overflow-x-auto rounded-2xl border border-slate-800">
   <table className="w-full min-w-[860px] text-sm">
    <thead className="table-head"><tr><th className="py-3 text-left">输入对象</th><th className="py-3 text-left">类型</th><th className="py-3 text-left">本轮产生线索</th></tr></thead>
    <tbody>{inputRows.map((input:any,i:number)=>{const key=normalizeEffectKey(input.value,input.type); const matched=cluesByInput.get(key)||(!i&&clues.length&&!cluesByInput.size?clues:[]); return <tr key={`${row.id}-input-${input.id||input.value||i}`} className="border-t border-slate-800 align-top"><td className="max-w-[260px] py-3 font-semibold text-slate-100">{input.value}</td><td className="py-3"><span className="badge">{inputTypeLabel(input.type)}</span></td><td className="py-3"><div className="max-h-44 space-y-1 overflow-auto pr-1">{matched.length?matched.slice(0,40).map((clue:any,idx:number)=><div key={`${row.id}-clue-${idx}`} className="rounded-lg bg-slate-950 px-2 py-1 text-xs text-slate-300"><b className="text-slate-100">{clueName(clue)}</b><span className="ml-2 text-slate-500">状态：{candidateStatusLabel(clue.status)}</span></div>):<span className="text-slate-500">{row.trigger==='manual'?'本轮未产生新线索或历史记录缺少明细':'历史自动批次暂未记录具体线索明细'}</span>}</div></td></tr>})}</tbody>
   </table>
  </div>
 </div>
}
function RunErrorModal({row,onClose}:{row:any;onClose:()=>void}){const errors=runErrorItems(row); return <div className="fixed inset-0 z-[60]"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭异常窗口"/><section className="absolute right-6 top-6 max-h-[calc(100vh-48px)] w-full max-w-2xl overflow-y-auto rounded-3xl border border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-amber-300">Run Exceptions</div><h3 className="mt-1 text-2xl font-black text-white">运行异常</h3><p className="mt-2 text-sm text-slate-400">这里单独查看本轮异常，不混入输入对象和线索明细。</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><div className="mt-4 grid gap-3 md:grid-cols-4"><MetricBlock label="批次" value={`#${row.batch}`}/><MetricBlock label="线索模型" value={row.sourceLabel||sourceName(row.source)} tone="blue"/><MetricBlock label="时间" value={fmtTime(row.time)}/><MetricBlock label="异常" value={row.problems} tone="amber"/></div><div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h4 className="font-bold text-slate-100">异常内容</h4><div className="mt-3 space-y-2">{errors.length?errors.map((err:string,i:number)=><div key={`${row.id}-modal-error-${i}`} className="rounded-xl bg-slate-950 px-3 py-2 text-sm text-amber-100">{err}</div>):<p className="text-sm text-slate-500">当前只有异常数量，没有保存具体异常明细。后续需要在采集器里接入异常明细记录，才能定位到具体输入对象和错误原因。</p>}</div></div><div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4"><h4 className="font-bold text-slate-100">处理建议</h4><p className="mt-2 text-sm leading-6 text-slate-400">{errors.length?'优先检查上面的输入对象、请求返回、超时或解析错误；处理后重新运行该模型。':'这是历史批次的汇总异常，当前无法直接定位原因。建议先补充异常明细记录，再处理具体错误。'}</p><div className="mt-3 flex flex-wrap gap-2"><button className="btn" onClick={onClose}>我知道了</button><button className="btn-secondary" onClick={()=>navigator.clipboard?.writeText(JSON.stringify({batch:row.batch,source:row.source,time:row.time,errors},null,2))}>复制异常信息</button></div></div></section></div>}
function objectTypeLabel(v:any){const s=String(v||''); if(s.includes('.'))return '网站'; if(s.split(/\s+/).length>2)return '长尾词'; return '搜索词'}
function aggregateEffectRows(rows:any[]){const byKey=new Map<string,any>(); (rows||[]).forEach((r:any)=>{const key=normalizeEffectKey(r.condition,r.type); const current=byKey.get(key)||{...r,runCount:0,runIds:[],latestAt:'',leads:0,success:0,reject:0}; current.leads+=Number(r.leads||0); current.success+=Number(r.success||0); current.reject+=Number(r.reject||0); current.runCount+=1; if(r.runId||r.batch)current.runIds.push(r.runId||r.batch); if(r.latestAt&&(!current.latestAt||new Date(r.latestAt)>new Date(current.latestAt)))current.latestAt=r.latestAt; current.verdict=current.success>0?'有效':current.reject>current.success?'噪音偏高':r.verdict||'暂无判断'; byKey.set(key,current)}); return Array.from(byKey.values())}
function EffectRows({rows}:{rows:any[]}){const [verdict,setVerdict]=useState('all'); const [sort,setSort]=useState('leads_desc'); const aggregated=aggregateEffectRows(rows); const filtered=aggregated.filter((r:any)=>verdict==='all'||(verdict==='effective'&&Number(r.success||0)>0)||(verdict==='noisy'&&Number(r.reject||0)>Number(r.success||0))||(verdict==='unknown'&&!Number(r.success||0)&&!Number(r.reject||0))); const sorted=[...filtered].sort((a:any,b:any)=>{if(sort==='success_desc')return Number(b.success||0)-Number(a.success||0); if(sort==='reject_desc')return Number(b.reject||0)-Number(a.reject||0); if(sort==='condition_asc')return String(a.condition||'').localeCompare(String(b.condition||'')); return Number(b.leads||0)-Number(a.leads||0)}); return <div className="mt-4 space-y-3"><div className="flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3"><Select label="分类" value={verdict} setValue={setVerdict} options={[['all','全部'],['effective','可推进'],['noisy','噪音偏高'],['unknown','暂无反馈']]}/><Select label="排序" value={sort} setValue={setSort} options={[['leads_desc','线索最多'],['success_desc','有效最多'],['reject_desc','拒绝最多'],['condition_asc','名称 A-Z']]}/><span className="ml-auto text-sm text-slate-500">显示 {sorted.length}/{aggregated.length}</span></div><div className="overflow-x-auto rounded-2xl border border-slate-800"><table className="w-full min-w-[940px] text-sm"><thead className="table-head"><tr><th className="py-3 text-left">线索对象</th><th className="py-3 text-left">类型</th><th className="py-3 text-left">运行</th><th className="py-3 text-left">线索</th><th className="py-3 text-left">有效</th><th className="py-3 text-left">拒绝</th><th className="py-3 text-left">判断</th><th className="py-3 text-left">关联批次</th><th className="py-3 text-left">去向</th></tr></thead><tbody>{sorted.length?sorted.map((r:any,i:number)=><tr key={`${r.target_id}-${r.source}-${i}`} className="border-t border-slate-800"><td className="max-w-[260px] truncate py-3 font-semibold text-slate-100">{r.condition}</td><td className="py-3"><span className="badge">{r.type==='domain'?'网站':objectTypeLabel(r.condition)}</span></td><td className="py-3 text-slate-300">{r.runCount||1}</td><td className="py-3 text-slate-300">{r.leads||0}</td><td className="py-3 text-emerald-300">{r.success||0}</td><td className={(r.reject||0)>(r.success||0)?'py-3 text-amber-300':'py-3 text-slate-400'}>{r.reject||0}</td><td className={r.verdict==='有效'?'py-3 text-emerald-300':r.verdict==='噪音偏高'?'py-3 text-amber-300':'py-3 text-slate-400'}>{r.verdict||'暂无反馈'}</td><td className="py-3 text-blue-300">{(r.runIds||[]).slice(0,4).map((x:any)=>`#${x}`).join(' ')||'-'}</td><td className="py-3 text-slate-400">{Number(r.success||0)>0?'可进入线索池 / 继续推进':Number(r.reject||0)>Number(r.success||0)?'降权或暂停':'等待更多运行'}</td></tr>):<tr><td colSpan={9} className="py-6 text-slate-500">暂无输入对象效果数据。</td></tr>}</tbody></table></div></div>}
function ManualRunPanel({model,onRun}:{model:any;onRun?:(run:any,effect:any)=>Promise<void>|void}){const [value,setValue]=useState(''), [busy,setBusy]=useState(false), [msg,setMsg]=useState(''); async function run(){if(!model.endpoint||!model.inputKind||!value.trim())return; const items=value.split(/[\n,]+/).map(x=>x.trim()).filter(Boolean); if(!items.length)return; const payload=model.inputKind==='domains'?{domains:items,max_urls_per_domain:80,only_new:false}:model.inputKind==='advanced'?{roots:items,domains:[],days:30,limit_per_query:8}:{seeds:items,limit_per_seed:10}; setBusy(true); setMsg(''); try{const r=await api<any>(model.endpoint,{method:'POST',body:JSON.stringify(payload)}); const saved=Number(r.saved??r.imported??0), seen=Number(r.seen??r.urls_seen??r.pages_seen??r.candidates_seen??0), errors=Array.isArray(r.errors)?r.errors.length:Number(r.errors||0); const now=new Date().toISOString(); const runRow={id:`manual-${model.id}-${Date.now()}`,batch:'manual',time:now,source:r.source||model.sources[0]||model.id,sourceLabel:model.name,trigger:'manual',leads:saved,looked:seen,problems:errors,status:statusFor(saved,errors),verified:0,selected:0,filtered:0,paused:0,conditionCount:items.length,inputObjects:items.map((item,i)=>({id:`manual-${i}`,type:model.inputKind==='domains'?'domain':'keyword',value:item,segment:'manual'})),verifiedItems:[],generatedClues:r.candidates||r.keywords||r.items||[],raw:r}; const effect={target_id:`manual-${model.id}-${Date.now()}`,condition:items.join(', '),type:model.inputKind==='domains'?'domain':'keyword',segment:'manual',source:r.source||model.sources[0]||model.id,leads:saved,success:0,reject:0,verdict:'暂无判断',priority:0}; await onRun?.(runRow,effect); setMsg(`已运行：保存线索 ${saved}，结果 ${seen||'-'}，异常 ${errors}`)}catch(e:any){setMsg(`运行失败：${e.message}`)}finally{setBusy(false)}} if(!model.endpoint)return <div className="rounded-xl border border-slate-800 bg-slate-900 p-3"><b className="text-slate-200">人工入口</b><p className="mt-2 text-sm text-slate-500">{model.status==='planned'?'该模型尚未接入，暂不能人工运行。':'该模型当前没有独立人工运行入口。'}</p></div>; return <div className="rounded-xl border border-slate-800 bg-slate-900 p-3"><div className="flex flex-wrap items-center justify-between gap-3"><b className="text-slate-200">人工入口</b><button className="btn" disabled={busy||!value.trim()} onClick={run}>{busy?'运行中...':'立即运行'}</button></div><p className="mt-2 text-xs text-slate-500">输入 {model.inputKind==='domains'?'域名或 sitemap URL':'seed / 主题'}，多个值可换行或用逗号分隔。人工触发会先显示在当前抽屉；若后端没有返回具体线索名，明细只显示数量。</p><textarea className="mt-3 min-h-24 w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm text-slate-100 outline-none focus:border-blue-500" value={value} onChange={e=>setValue(e.target.value)} placeholder={model.inputKind==='domains'?'example.com\nhttps://example.com/sitemap.xml':'ai tools\ninvoice automation'} />{msg&&<p className="mt-2 text-sm text-slate-400">{msg}</p>}</div>}
function Records({records,allRecords,sources,sourceFilter,statusFilter,setSourceFilter,setStatusFilter}:any){const totalLeads=records.reduce((a:any,r:any)=>a+r.leads,0), totalLooked=records.reduce((a:any,r:any)=>a+r.looked,0), totalProblems=records.reduce((a:any,r:any)=>a+r.problems,0); return <section className="panel"><div><h2 className="text-xl font-bold">抓取记录</h2><p className="mt-1 text-sm text-slate-400">每条记录都能追到抓取批次、线索模型和使用的搜索条件。</p></div><div className="mt-4 grid gap-3 md:grid-cols-4"><MetricBlock label="记录数" value={records.length}/><MetricBlock label="机会线索" value={totalLeads} tone="green"/><MetricBlock label="抓取结果" value={totalLooked||'-'} tone="blue"/><MetricBlock label="异常" value={totalProblems} tone={totalProblems?'amber':'slate'}/></div><div className="mt-4 flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3"><label className="text-sm text-slate-300">线索模型 <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={sourceFilter} onChange={e=>setSourceFilter(e.target.value)}>{sources.map((x:any)=><option key={x} value={x}>{x==='all'?'全部':sourceName(x)}</option>)}</select></label><label className="text-sm text-slate-300">状态 <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>{['all','有发现','暂无发现','需检查'].map(x=><option key={x} value={x}>{x==='all'?'全部':x}</option>)}</select></label></div><div className="mt-4 overflow-hidden rounded-2xl border border-slate-800"><div className="grid grid-cols-[90px_112px_1fr_96px_96px_80px_110px_110px] gap-2 border-b border-slate-800 bg-slate-900/70 px-3 py-2 text-xs font-semibold text-slate-500"><div>抓取批次</div><div>时间</div><div>线索模型</div><div>机会线索</div><div>抓取结果</div><div>异常</div><div>进入验证</div><div>状态</div></div>{records.length?records.map((r:any)=><details key={r.id} className="border-b border-slate-800 last:border-b-0"><summary className="grid cursor-pointer grid-cols-[90px_112px_1fr_96px_96px_80px_110px_110px] gap-2 px-3 py-3 text-sm hover:bg-slate-900/50"><b className="text-blue-300">#{r.batch}</b><span className="text-slate-400">{fmtTime(r.time)}</span><span className="font-semibold text-slate-100">{r.sourceLabel}</span><span className="text-emerald-300">{r.leads}</span><span className="text-blue-300">{r.looked||'-'}</span><span className={r.problems?'text-amber-300':'text-slate-500'}>{r.problems}</span><span className="text-purple-300">{r.verified}/{r.selected}</span><span className={toneText(r.status.tone)}>{r.status.icon} {r.status.label}</span></summary><div className="grid gap-4 bg-slate-950/70 p-4 text-sm xl:grid-cols-3"><InfoCard title="本次处理" rows={[['过滤噪音',r.filtered],['暂停条件',r.paused],['使用条件',r.conditionCount]]}/><InfoCard title="追溯信息" rows={[['抓取批次',`#${r.batch}`],['线索模型',r.sourceLabel],['结果',`线索 ${r.leads} / 抓取 ${r.looked||'-'} / 异常 ${r.problems}`]]}/><div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">原始记录</b><pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(r.raw,null,2)}</pre></div><div className="xl:col-span-3 rounded-xl bg-slate-900 p-3"><b className="text-slate-200">本次使用的搜索条件</b><div className="mt-2 flex flex-wrap gap-2">{Object.entries(r.selectedBySegment||{}).flatMap(([seg,items]:any)=>(items||[]).slice(0,8).map((t:any)=><span key={`${r.id}-${seg}-${t.id}`} className="rounded-lg bg-slate-950 px-2 py-1 text-xs text-slate-300">{segmentName(seg)}：{t.value}</span>))}</div></div></div></details>):<div className="px-4 py-6 text-sm text-slate-500">暂无符合筛选条件的抓取记录。</div>}</div></section>}

function TraceCard({label,value,hint,tone='slate',onClick}:any){return <button onClick={onClick} className={`rounded-xl bg-slate-950 p-3 text-left transition hover:bg-slate-900 hover:ring-1 ${toneBorder(tone)}`}><div className="text-xs text-slate-500">{label}</div><b className={`text-2xl ${toneText(tone)}`}>{value}</b><div className="mt-1 text-xs text-blue-300">{hint||'点击追溯'} →</div></button>}
function MetricBlock({label,value,hint,tone='slate'}:{label:string;value:any;hint?:string;tone?:Tone}){return <div className="rounded-xl bg-slate-950 p-3"><div className="text-xs text-slate-500">{label}</div><b className={`text-2xl ${toneText(tone)}`}>{value}</b>{hint&&<div className="mt-1 text-xs text-slate-500">{hint}</div>}</div>}
function InfoCard({title,rows}:{title:string;rows:any[]}){return <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">{title}</b>{rows.map(([k,v])=><div key={k} className="mt-2 text-slate-400">{k}：{v}</div>)}</div>}
function TargetList({title,items}:{title:string;items:any[]}){return <section className="panel"><h2 className="text-xl font-bold">{title}</h2><ConditionTable items={items}/></section>}
function ConditionTable({items}:{items:any[]}){
 const [typeFilter,setTypeFilter]=useState('all')
 const [segmentFilter,setSegmentFilter]=useState('all')
 const [sourceFilter,setSourceFilter]=useState('all')
 const [effectFilter,setEffectFilter]=useState('all')
 const sources=Array.from(new Set((items||[]).flatMap((t:any)=>(t.source_effectiveness||[]).map((s:any)=>s.source))))
 const rows=(items||[]).filter((t:any)=>{
  const eff=t.source_effectiveness||[]
  const hasSource=sourceFilter==='all'||eff.some((s:any)=>s.source===sourceFilter)
  const sourceRows=sourceFilter==='all'?eff:eff.filter((s:any)=>s.source===sourceFilter)
  const success=sourceRows.reduce((a:number,s:any)=>a+Number(s.success||0),0)
  const reject=sourceRows.reduce((a:number,s:any)=>a+Number(s.reject||0),0)
  const effectOk=effectFilter==='all'||(effectFilter==='effective'&&success>0)||(effectFilter==='noisy'&&reject>success)||(effectFilter==='unknown'&&!success&&!reject)
  return (typeFilter==='all'||t.target_type===typeFilter)&&(segmentFilter==='all'||t.status===segmentFilter)&&hasSource&&effectOk
 })
 return <div className="mt-4 space-y-4">
  <div className="flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3">
   <Select label="类型" value={typeFilter} setValue={setTypeFilter} options={[['all','全部'],['keyword','搜索词'],['domain','网站']]}/>
   <Select label="分类" value={segmentFilter} setValue={setSegmentFilter} options={[['all','全部'],['active','有效'],['cooldown','已暂停'],['rejected','已拒绝'],['exhausted','暂无价值']]}/>
   <Select label="来源" value={sourceFilter} setValue={setSourceFilter} options={[['all','全部'],...sources.map((x:any)=>[x,sourceName(x)])]}/>
   <Select label="效果" value={effectFilter} setValue={setEffectFilter} options={[['all','全部'],['effective','有有效结果'],['noisy','拒绝偏多'],['unknown','暂无反馈']]}/>
   <div className="ml-auto text-sm text-slate-400">显示 {rows.length}/{items?.length||0}</div>
  </div>
  <div className="overflow-hidden rounded-2xl border border-slate-800">
   <div className="grid grid-cols-[1fr_80px_90px_100px_120px_1.4fr] gap-2 border-b border-slate-800 bg-slate-900/70 px-3 py-2 text-xs font-semibold text-slate-500"><div>搜索条件</div><div>类型</div><div>分类</div><div>优先级</div><div>成功/拒绝</div><div>来源效果</div></div>
   {rows.length?rows.map((t:any)=><ConditionRow key={t.id||t.value} t={t}/>):<div className="px-4 py-6 text-sm text-slate-500">暂无符合筛选条件的搜索条件。</div>}
  </div>
 </div>
}
function Select({label,value,setValue,options}:any){return <label className="text-sm text-slate-300">{label} <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={value} onChange={e=>setValue(e.target.value)}>{options.map(([v,l]:any)=><option key={v} value={v}>{l}</option>)}</select></label>}
function ConditionRow({t}:{t:any}){const sources=t.source_effectiveness||[]; const top=sources.slice(0,3); return <details className="border-b border-slate-800 last:border-b-0"><summary className="grid cursor-pointer grid-cols-[1fr_80px_90px_100px_120px_1.4fr] gap-2 px-3 py-3 text-sm hover:bg-slate-900/50"><b className="text-slate-100">{t.value}</b><span className="text-slate-400">{t.target_type==='domain'?'网站':'搜索词'}</span><span className="text-blue-300">{segmentName(t.status)}</span><span className="text-slate-300">{Math.round(t.priority||0)}</span><span className="text-slate-300">{t.success_count||0}/{t.reject_count||0}</span><span className="flex flex-wrap gap-1">{top.length?top.map((s:any)=><span key={s.source} className={(s.reject||0)>(s.success||0)?'rounded bg-amber-500/10 px-2 py-0.5 text-xs text-amber-200':'rounded bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-200'}>{sourceName(s.source)} {s.success||0}/{s.reject||0}</span>):<span className="text-slate-500">暂无模型反馈</span>}</span></summary><div className="bg-slate-950/70 p-4"><h4 className="mb-2 text-sm font-semibold text-slate-200">线索模型效果</h4>{sources.length?<div className="grid gap-2 md:grid-cols-2">{sources.map((s:any)=><div key={s.source} className="rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-100">{sourceName(s.source)}</b><div className="mt-1 text-slate-400">带来线索 {s.leads||0} · 有效 {s.success||0} · 拒绝 {s.reject||0}</div>{s.last_keyword&&<div className="mt-1 text-xs text-slate-500">最近：{s.last_label} · {s.last_keyword}</div>}</div>)}</div>:<p className="text-sm text-slate-500">暂无模型反馈。</p>}</div></details>}

function SourceList({rows}:{rows:any[]}){return <section className="panel"><div><h2 className="text-xl font-bold">最近线索模型</h2><p className="mt-1 text-sm text-slate-400">看每个模型最近贡献了多少线索、抓取结果和异常。不再挤成一行宽表。</p></div><div className="mt-4 grid gap-3 md:grid-cols-2 2xl:grid-cols-3">{rows?.length?rows.map((r:any,i:number)=>{const st=statusFor(Number(r.saved||0),Number(r.errors||0)); return <article key={i} className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><div className="flex items-start justify-between gap-3"><div><h3 className="font-bold text-slate-100">{sourceName(r.source)}</h3><p className="mt-1 text-xs text-slate-500">最近运行模型</p></div><span className={`${toneText(st.tone)} rounded-lg bg-slate-900 px-2 py-1 text-xs`}>{st.icon} {st.label}</span></div><div className="mt-4 grid grid-cols-3 gap-2"><MetricBlock label="线索" value={r.saved||0} tone="green"/><MetricBlock label="结果" value={r.seen??'-'} tone="blue"/><MetricBlock label="异常" value={r.errors||0} tone={r.errors?'amber':'slate'}/></div></article>}) : <p className="text-sm text-slate-500">暂无抓取记录。</p>}</div></section>}
function TraceModal({trace,onClose}:any){return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">Trace</div><h2 className="mt-1 text-2xl font-bold text-white">{trace.title}</h2><p className="mt-1 text-sm text-slate-400">这个数字背后的具体数据。</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><TraceList trace={trace}/></aside></div>}
function TraceList({trace}:any){const items=trace.items||[]; if(!items.length)return <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-sm text-slate-400">{trace.empty||'暂无数据。'}</div>; if(trace.type==='targets')return <ConditionTable items={items}/>; if(trace.type==='sources')return <SourceList rows={items}/>; if(trace.type==='records')return <div className="space-y-2">{items.map((r:any)=><div key={r.id} className="rounded-xl bg-slate-900 p-3 text-sm"><b>{r.sourceLabel}</b><div className="mt-1 text-slate-400">批次 #{r.batch} · 线索 {r.leads} · 抓取 {r.looked||'-'} · 异常 {r.problems}</div></div>)}</div>; if(trace.type==='candidates')return <div className="space-y-2">{items.map((c:any)=><div key={c.id} className="rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-100">{c.keyword}</b><div className="mt-1 text-slate-500">来源：{sourceName(c.source)} · 分数：{Number(c.score||0).toFixed(2)}</div></div>)}</div>; if(trace.type==='issues')return <div className="space-y-2">{items.map((x:any,i:number)=><div key={x.code||i} className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100"><b>{x.severity||'关注'}</b><div className="mt-1">{x.text||JSON.stringify(x)}</div></div>)}</div>; return <pre className="rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(items,null,2)}</pre>}
function OptimizationLog({onClose,repairRuns,repairAutoRuns,rejectedReasons,inspectRejected,busy}:any){return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-4xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-amber-300">Optimization Records</div><h2 className="mt-1 text-2xl font-bold text-white">优化记录</h2><p className="mt-1 text-sm text-slate-400">仅用于维护者排查系统为什么调整策略，不属于主流程。</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><div className="mb-4"><button className="btn-secondary" disabled={busy} onClick={inspectRejected}>刷新过滤原因</button></div>{rejectedReasons&&<section className="mb-5 rounded-2xl border border-slate-800 bg-slate-900/50 p-4"><h3 className="font-bold text-white">过滤原因</h3><div className="mt-3 grid gap-4 xl:grid-cols-2"><ReasonMini rows={rejectedReasons.by_reason} keyName="reason"/><ReasonMini rows={rejectedReasons.by_source} keyName="source"/></div></section>}<section className="grid gap-4 xl:grid-cols-2"><Replay title="自动优化记录" rows={repairAutoRuns}/><Replay title="单次优化记录" rows={repairRuns}/></section></aside></div>}
function ReasonMini({rows,keyName}:{rows:any[];keyName:string}){return <div className="space-y-2">{(rows||[]).slice(0,12).map((r:any)=><div key={r[keyName]} className="flex justify-between rounded-xl bg-slate-950 p-3 text-sm"><span className="text-slate-300">{r[keyName]}</span><b className="text-amber-300">{r.count}</b></div>)}</div>}
function Replay({title,rows}:{title:string;rows:any[]}){return <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4"><h3 className="font-bold text-white">{title}</h3><div className="mt-3 space-y-2">{rows.length?rows.map((r:any)=><details key={r.id} className="rounded-xl bg-slate-950 p-3 text-sm"><summary className="cursor-pointer text-slate-200">#{r.id} · {fmtTime(r.started_at)} · {r.status}</summary><pre className="mt-3 max-h-72 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(r.summary||{},null,2)}</pre></details>):<p className="text-sm text-slate-500">暂无</p>}</div></section>}
