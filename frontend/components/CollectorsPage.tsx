'use client'
import {useEffect, useState} from 'react'
import Link from 'next/link'
import {usePathname} from 'next/navigation'
import {api, authToken} from '../lib/api'

type Tab = 'overview' | 'flow' | 'conditions' | 'modules' | 'results'

const collectorModules = [
 {id:'sitemap', name:'Sitemap 站点监控', layer:'站找词', goal:'发现竞品新增页面、工具页、模板页', input:'竞品域名 / sitemap.xml', output:'新页面 → 机会线索', status:'已接入'},
 {id:'domain_web', name:'网页标题/Meta 抽取', layer:'站找词', goal:'从竞品页面标题、H1、Meta 中提取任务词', input:'竞品域名', output:'页面主题 → 机会线索', status:'已接入'},
 {id:'suggest', name:'搜索联想扩词', layer:'词找词', goal:'围绕已知关键词扩展长尾词', input:'搜索词', output:'长尾搜索词 → 机会线索', status:'已接入'},
 {id:'advanced_search', name:'高级搜索 / 搜索结果变体', layer:'搜索结果找缺口', goal:'用标题/站点/时间范围查询发现页面缺口', input:'任务词 + 竞品域名', output:'搜索结果标题/页面 → 机会线索', status:'已接入'},
 {id:'alternatives', name:'Alternatives / Compare', layer:'竞品缺口', goal:'发现替代品、对比、迁移相关机会', input:'竞品域名', output:'替代品/对比类线索', status:'已接入'},
 {id:'hot_topic', name:'热点任务补充', layer:'趋势补充', goal:'从近期主题中补充可执行任务词', input:'有效搜索条件', output:'任务型机会线索', status:'已接入'},
 {id:'source_radar', name:'一手信息源雷达', layer:'早期信号', goal:'从 HN/arXiv/GitHub 等捕捉新词源头', input:'技术/趋势 seed', output:'早期信号线索', status:'已接入'},
]

function fmtTime(s?:string){if(!s)return '-'; const d=new Date(s); if(Number.isNaN(d.getTime()))return '-'; return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}

const sourceLabels:any={
 sitemap:'Sitemap 站点监控', domain_web:'网页标题/Meta 抽取', suggest:'搜索联想扩词', advanced_search:'高级搜索/搜索结果', alternatives:'替代品/对比挖掘', hot_topic:'热点任务补充', source_radar:'一手信息源雷达'
}
const segmentLabels:any={winner:'高价值',promising:'可继续观察',new:'新搜索条件',noisy:'噪音高',cooldown:'已暂停',exhausted:'暂无价值'}
function sourceName(x?:string){return sourceLabels[x||''] || x || '未知来源'}
function segmentName(x?:string){return segmentLabels[x||''] || x || '其他'}
function resultStatus(saved:number, errors:number){if(saved>0)return {icon:'✅',label:'有发现',cls:'text-emerald-300'}; if(errors>0)return {icon:'⚠️',label:'需检查',cls:'text-amber-300'}; return {icon:'—',label:'暂无发现',cls:'text-slate-500'}}
function MetricBlock({label,value,hint,tone='slate'}:{label:string;value:any;hint?:string;tone?:'slate'|'green'|'blue'|'amber'|'purple'|'red'}){const color:any={slate:'text-white',green:'text-emerald-300',blue:'text-blue-300',amber:'text-amber-300',purple:'text-purple-300',red:'text-red-300'}; return <div className="rounded-xl bg-slate-950 p-3"><div className="text-xs text-slate-500">{label}</div><b className={`text-2xl ${color[tone]}`}>{value}</b>{hint&&<div className="mt-1 text-xs text-slate-500">{hint}</div>}</div>}

function clsStatus(status?:string){return status==='healthy'?'text-emerald-300':status==='watch'?'text-amber-300':'text-red-300'}

export function CollectorsPage({initialSection='overview'}:{initialSection?:string}){
 const pathname=usePathname()
 const routeSection=(pathname.split('/').pop() || initialSection) as Tab
 const tab:Tab = ['overview','flow','conditions','modules','results'].includes(routeSection) ? routeSection : 'overview'
 const [busy,setBusy]=useState(false)
 const [msg,setMsg]=useState('')
 const [showLog,setShowLog]=useState(false)
 const [health,setHealth]=useState<any|null>(null)
 const [targets,setTargets]=useState<any[]>([])
 const [segments,setSegments]=useState<any|null>(null)
 const [budget,setBudget]=useState<any|null>(null)
 const [runs,setRuns]=useState<any[]>([])
 const [report,setReport]=useState<any|null>(null)
 const [repairRuns,setRepairRuns]=useState<any[]>([])
 const [repairAutoRuns,setRepairAutoRuns]=useState<any[]>([])
 const [rejectedReasons,setRejectedReasons]=useState<any|null>(null)
 const [candidates,setCandidates]=useState<any[]>([])
 const [trace,setTrace]=useState<any|null>(null)

 async function load(){
  try{
   const [h,ts,seg,bg,rs,rep,repairs,repairAutos,cs]=await Promise.all([
    api<any>('/api/collectors/health'),
    api<any[]>('/api/collectors/targets?limit=120&status='),
    api<any>('/api/collectors/targets/segments'),
    api<any>('/api/collectors/budget/next?limit=24'),
    api<any[]>('/api/collectors/runs?limit=8'),
    api<any>('/api/reports/daily-digest').catch(()=>null),
    api<any[]>('/api/collectors/repairs?limit=8'),
    api<any[]>('/api/collectors/repairs/autopilot/runs?limit=6'),
    api<any[]>('/api/collectors/candidates?limit=80&status=new'),
   ])
   setHealth(h); setTargets(ts); setSegments(seg); setBudget(bg); setRuns(rs); setReport(rep); setRepairRuns(repairs); setRepairAutoRuns(repairAutos); setCandidates(cs)
  }catch(e:any){setMsg(`加载失败：${e.message}`)}
 }
 useEffect(()=>{load()},[])

 async function runCollectorAuto(){setBusy(true);setMsg('正在开始抓取流程...');try{const r=await api<any>('/api/collectors/autopilot/run',{method:'POST',body:JSON.stringify({limit:24})});setMsg(`抓取完成：进入验证 ${r.import?.imported||0}/${r.import?.selected||0}，过滤噪音 ${r.clean?.rejected||0}`);await load()}catch(e:any){setMsg(`运行失败：${e.message}`)}finally{setBusy(false)}}
 async function refreshTargets(){setBusy(true);setMsg('正在从机会判断刷新搜索条件...');try{const r=await api<any>('/api/collectors/targets/refresh',{method:'POST'});setMsg(`已刷新：搜索词条件 ${r.keyword_targets||0}，网站条件 ${r.domain_targets||0}`);await load()}catch(e:any){setMsg(`刷新失败：${e.message}`)}finally{setBusy(false)}}
 async function applyTargetHealth(){setBusy(true);try{const r=await api<any>('/api/collectors/targets/health',{method:'POST'});setMsg(`条件整理完成：已暂停 ${r.cooled||0}，恢复 ${r.promoted||0}`);await load()}catch(e:any){setMsg(`整理失败：${e.message}`)}finally{setBusy(false)}}
 async function inspectRejected(){setBusy(true);try{const r=await api<any>('/api/collectors/rejected-reasons?limit=800');setRejectedReasons(r); setShowLog(true)}catch(e:any){setMsg(`检查失败：${e.message}`)}finally{setBusy(false)}}
 async function downloadDigest(){setBusy(true);try{const token=authToken(); const res=await fetch('/api/reports/download/latest',{headers:token?{Authorization:`Bearer ${token}`}:{}}); if(!res.ok) throw new Error(`${res.status} ${await res.text()}`); const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='demand_cards_latest.md'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)}catch(e:any){setMsg(`下载失败：${e.message}`)}finally{setBusy(false)}}

 const summary=health?.summary||{}
 const seg=segments?.summary||{}
 const latest=runs?.[0]?.summary||{}
 const sourceRows=latest.source_results||[]
 const goodTargets=[...(segments?.segments?.winner||[]),...(segments?.segments?.promising||[]),...(segments?.segments?.new||[])].slice(0,24)
 const weakTargets=[...(segments?.segments?.noisy||[]),...(segments?.segments?.cooldown||[]),...(segments?.segments?.exhausted||[])].slice(0,16)

 return <div className="space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl">
   <div className="flex flex-wrap items-start justify-between gap-4">
    <div>
     <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Opportunity Sources</p>
     <h1 className="mt-3 text-4xl font-black text-white">机会发现中心</h1>
     <p className="mt-3 max-w-3xl text-slate-300">关注用户能判断的结果：发现了多少机会线索、哪些进入验证、依据哪些搜索条件继续找。</p>
    </div>
    <div className="flex flex-wrap gap-2">
     <button className="btn" disabled={busy} onClick={runCollectorAuto}>开始抓取</button>
     <button className="btn-secondary" disabled={busy} onClick={downloadDigest}>下载报告</button>
     <button className="btn-secondary" disabled={busy} onClick={()=>setShowLog(true)}>优化记录</button>
    </div>
   </div>
  </section>

  {msg&&<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}

  <div className="grid gap-6 xl:grid-cols-[220px_1fr]">
   <aside className="rounded-3xl border border-slate-800 bg-slate-950/70 p-3 xl:sticky xl:top-4 xl:h-fit">
    {[
     ['overview','总览','发现结果、风险、下一步'],
     ['flow','发现流程','从搜索条件到机会线索'],
     ['conditions','搜索条件','系统依据什么继续找'],
     ['modules','发现来源','每种来源发现什么'],
     ['results','抓取记录','每次抓取结果'],
    ].map(([id,label,desc]:any)=><Link key={id} href={`/collectors/${id}`} className={`mb-2 block w-full rounded-2xl px-4 py-3 text-left no-underline transition ${tab===id?'bg-blue-600 text-white':'bg-slate-900/70 text-slate-300 hover:bg-slate-800'}`}><b>{label}</b><div className="mt-1 text-xs opacity-70">{desc}</div></Link>)}
   </aside>

   <main className="space-y-6">
    {tab==='overview'&&<Overview health={health} summary={summary} latest={latest} report={report} goodTargets={goodTargets} sourceRows={sourceRows} candidates={candidates} openTrace={setTrace}/>} 
    {tab==='flow'&&<Flow/>}
    {tab==='conditions'&&<Conditions seg={seg} segments={segments?.segments||{}} goodTargets={goodTargets} weakTargets={weakTargets} budget={budget} busy={busy} refreshTargets={refreshTargets} applyTargetHealth={applyTargetHealth} openTrace={setTrace}/>} 
    {tab==='modules'&&<Modules sourceRows={sourceRows}/>} 
    {tab==='results'&&<Results runs={runs} runCollectorAuto={runCollectorAuto} busy={busy}/>} 
   </main>
  </div>

  {trace&&<TraceModal trace={trace} onClose={()=>setTrace(null)}/>}
  {showLog&&<OptimizationLog onClose={()=>setShowLog(false)} repairRuns={repairRuns} repairAutoRuns={repairAutoRuns} rejectedReasons={rejectedReasons} inspectRejected={inspectRejected} busy={busy}/>} 
 </div>
}

function Overview({health,summary,latest,report,goodTargets,sourceRows,candidates,openTrace}:any){
 const totalSignals=(sourceRows||[]).reduce((a:any,r:any)=>a+Number(r.saved||0),0)
 const totalFetched=(sourceRows||[]).reduce((a:any,r:any)=>a+Number(r.seen||0),0)
 const errorSources=(sourceRows||[]).filter((r:any)=>Number(r.errors||0)>0)
 return <div className="space-y-6">
 <section className="grid gap-4 md:grid-cols-5">
  <TraceCard label="健康度" value={`${health?.score??'-'}/100`} hint={health?.status||'-'} tone={health?.status==='healthy'?'green':health?.status==='watch'?'amber':'red'} onClick={()=>openTrace({title:'健康度追溯',type:'issues',items:health?.issues||[],empty:'暂无健康风险。'})}/>
  <TraceCard label="有效搜索条件" value={summary.usable_targets??0} hint="点击查看条件" tone="green" onClick={()=>openTrace({title:'有效搜索条件',type:'targets',items:goodTargets,empty:'暂无有效搜索条件。'})}/>
  <TraceCard label="待验证线索" value={summary.new_candidates??0} hint="点击查看线索" tone="blue" onClick={()=>openTrace({title:'待验证机会线索',type:'candidates',items:candidates,empty:'暂无待验证线索。'})}/>
  <TraceCard label="进入验证" value={`${latest.import?.imported??0}/${latest.import?.selected??0}`} hint="最近一轮" tone="purple" onClick={()=>openTrace({title:'进入验证追溯',type:'run',items:[latest],empty:'暂无进入验证记录。'})}/>
  <TraceCard label="需关注问题" value={health?.issues?.length||0} hint="点击查看风险" tone="amber" onClick={()=>openTrace({title:'需关注问题',type:'issues',items:health?.issues||[],empty:'暂无需关注问题。'})}/>
 </section>
 {report?.collector_audit&&<section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">最近一次抓取结论</h2><p className="mt-1 text-sm text-slate-400">每个数字都可以点开追溯来源。</p></div><span className="badge">抓取 #{report.collector_audit.run_id}</span></div><div className="mt-4 grid gap-3 md:grid-cols-4"><TraceCard label="进入验证" value={`${latest.import?.imported??0}/${latest.import?.selected??0}`} tone="purple" onClick={()=>openTrace({title:'进入验证追溯',type:'run',items:[latest]})}/><TraceCard label="机会线索" value={totalSignals} tone="green" onClick={()=>openTrace({title:'机会线索来源',type:'sources',items:sourceRows})}/><TraceCard label="抓取结果" value={totalFetched||'-'} tone="blue" onClick={()=>openTrace({title:'抓取结果来源',type:'sources',items:sourceRows})}/><TraceCard label="异常来源" value={errorSources.length} tone="amber" onClick={()=>openTrace({title:'异常来源',type:'sources',items:errorSources,empty:'暂无异常来源。'})}/></div>{health?.issues?.length>0&&<button className="mt-4 block w-full rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-left text-sm text-amber-100 hover:bg-amber-500/20" onClick={()=>openTrace({title:'下一轮关注',type:'issues',items:health.issues})}><b>下一轮关注：</b>{health.issues.slice(0,3).map((x:any)=>x.text).join('；')}</button>}</section>}
 <section className="grid gap-4 xl:grid-cols-2"><TargetPreview title="当前优先搜索条件" items={goodTargets}/><SourcePreview rows={sourceRows}/></section>
 </div>}


function Flow(){const steps=[['1','搜索条件','来自 Action/Watch 机会判断、人工搜索词、竞品网站'],['2','发现来源','Sitemap / 网页 / Suggest / SERP / Alternatives / Hot topic'],['3','线索池','保留具体可验证线索，过滤泛词、博客路径和噪音高结果'],['4','验证队列','把可用线索送入搜索验证'],['5','机会判断','形成 Action / Watch / Reject，反馈再更新搜索条件']]; return <section className="panel"><h2 className="text-xl font-bold">发现流程</h2><p className="mt-1 text-sm text-slate-400">这是用户需要理解的主流程，不展示内部实现细节。</p><div className="mt-5 grid gap-4 md:grid-cols-5">{steps.map(([n,t,d])=><div key={n} className="rounded-3xl border border-slate-800 bg-slate-950 p-4"><div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 font-black text-white">{n}</div><h3 className="font-bold text-white">{t}</h3><p className="mt-2 text-sm leading-6 text-slate-400">{d}</p></div>)}</div></section>}

function Conditions({seg,segments,goodTargets,weakTargets,budget,busy,refreshTargets,applyTargetHealth,openTrace}:any){
 const cats=[['winner','高价值'],['promising','可继续观察'],['new','新搜索条件'],['noisy','噪音高'],['cooldown','已暂停'],['exhausted','暂无价值']]
 return <div className="space-y-6"><section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">搜索条件分类</h2><p className="mt-1 text-sm text-slate-400">数字可点击追溯：点开就能看到对应的搜索条件列表。</p></div><div className="flex gap-2"><button className="btn-secondary" disabled={busy} onClick={applyTargetHealth}>整理搜索条件</button><button className="btn" disabled={busy} onClick={refreshTargets}>从机会卡更新</button></div></div><div className="mt-4 grid gap-3 md:grid-cols-6">{cats.map(([k,l])=><button key={k} onClick={()=>openTrace({title:l,type:'targets',items:segments?.[k]||[],empty:`暂无${l}。`})} className="rounded-xl bg-slate-950 p-3 text-left hover:bg-slate-900"><div className="text-xs text-slate-500">{l}</div><b className="text-2xl text-white">{seg[k]||0}</b><div className="mt-1 text-xs text-blue-300">查看 →</div></button>)}</div></section><section className="grid gap-4 xl:grid-cols-2"><TargetPreview title="有效搜索条件" items={goodTargets}/><TargetPreview title="暂停/低价值条件" items={weakTargets}/></section><section className="panel"><h2 className="text-xl font-bold">下一轮投入</h2><div className="mt-4 grid gap-3 md:grid-cols-4">{(budget?.allocation||[]).map((row:any)=><button key={row.segment} onClick={()=>openTrace({title:`${row.label} 投入条件`,type:'targets',items:row.targets||[],empty:'暂无条件。'})} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-left hover:bg-slate-900"><div className="text-sm font-semibold text-slate-200">{row.label}</div><div className="mt-2 text-2xl font-black text-emerald-300">{row.budget}</div><div className="mt-1 text-xs text-slate-500">可用 {row.available} · 点击追溯</div></button>)}</div></section></div>}


function Modules({sourceRows}:any){const perf=Object.fromEntries((sourceRows||[]).map((r:any)=>[r.source,r])); return <section className="panel"><h2 className="text-xl font-bold">发现来源</h2><p className="mt-1 text-sm text-slate-400">每个来源负责一种发现机会的方法。这里只展示它看哪里、产出什么、最近是否有效。</p><div className="mt-5 grid gap-4 xl:grid-cols-2">{collectorModules.map(m=>{const p=perf[m.id]||{}; return <article key={m.id} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">{m.layer}</div><h3 className="mt-2 text-lg font-bold text-white">{m.name}</h3></div><span className="badge badge-action">{m.status}</span></div><p className="mt-3 text-sm leading-6 text-slate-300">{m.goal}</p><div className="mt-4 grid gap-2 text-xs md:grid-cols-2"><div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-300">看哪里</b><div className="mt-1 text-slate-500">{m.input}</div></div><div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-300">发现什么</b><div className="mt-1 text-slate-500">{m.output}</div></div></div><div className="mt-4 rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-300">最近效果：</b><span className="ml-2 text-emerald-300">机会线索 {p.saved??'-'}</span><span className="ml-2 text-blue-300">抓取结果 {p.seen??'-'}</span><span className="ml-2 text-slate-500">异常 {p.errors??'-'}</span></div></article>})}</div></section>}

function Results({runs,runCollectorAuto,busy}:any){
 const [sourceFilter,setSourceFilter]=useState('all')
 const [statusFilter,setStatusFilter]=useState('all')
 const rows=(runs||[]).flatMap((run:any)=>{
  const s=run.summary||{}
  const selected=s.selected_by_segment||{}
  const selectedCount=Object.values(selected).reduce((acc:any,items:any)=>acc+(Array.isArray(items)?items.length:0),0)
  return (s.source_results||[]).map((r:any,i:number)=>{
   const saved=Number(r.saved||0), seen=Number(r.seen||0), errors=Number(r.errors||0)
   const st=resultStatus(saved, errors)
   return {id:`${run.id}-${i}`,runId:run.id,time:run.started_at,source:r.source||'unknown',sourceLabel:sourceName(r.source),saved,seen,errors,status:st.label,statusIcon:st.icon,statusCls:st.cls,imported:s.import?.imported||0,selected:s.import?.selected||0,cleanRejected:s.clean?.rejected||0,targetCooled:s.target_health?.cooled||0,selectedCount,summary:s,raw:r}
  })
 })
 const sources=['all',...Array.from(new Set(rows.map((r:any)=>r.source)))]
 const filtered=rows.filter((r:any)=>(sourceFilter==='all'||r.source===sourceFilter)&&(statusFilter==='all'||r.status===statusFilter))
 const totalSaved=filtered.reduce((a:number,r:any)=>a+r.saved,0)
 const totalSeen=filtered.reduce((a:number,r:any)=>a+r.seen,0)
 const totalErrors=filtered.reduce((a:number,r:any)=>a+r.errors,0)
 return <section className="panel">
  <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">抓取记录</h2><p className="mt-1 text-sm text-slate-400">每次自动抓取的结果列表。可筛选来源、查看状态，并追溯使用了哪些搜索条件。</p></div><button className="btn" disabled={busy} onClick={runCollectorAuto}>开始抓取</button></div>
  <div className="mt-4 grid gap-3 md:grid-cols-4"><MetricBlock label="记录数" value={filtered.length}/><MetricBlock label="机会线索" value={totalSaved} tone="green"/><MetricBlock label="抓取结果" value={totalSeen||'-'} tone="blue"/><MetricBlock label="异常" value={totalErrors} tone={totalErrors?'amber':'slate'}/></div>
  <div className="mt-4 flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3">
   <label className="text-sm text-slate-300">发现来源 <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={sourceFilter} onChange={e=>setSourceFilter(e.target.value)}>{sources.map((x:any)=><option key={x} value={x}>{x==='all'?'全部':sourceName(x)}</option>)}</select></label>
   <label className="text-sm text-slate-300">状态 <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>{['all','有发现','暂无发现','需检查'].map(x=><option key={x} value={x}>{x==='all'?'全部':x}</option>)}</select></label>
  </div>
  <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800">
   <div className="grid grid-cols-[82px_112px_1fr_96px_96px_80px_110px_110px] gap-2 border-b border-slate-800 bg-slate-900/70 px-3 py-2 text-xs font-semibold text-slate-500"><div>抓取批次</div><div>时间</div><div>发现来源</div><div>机会线索</div><div>抓取结果</div><div>异常</div><div>进入验证</div><div>状态</div></div>
   {filtered.length?filtered.map((r:any)=><details key={r.id} className="border-b border-slate-800 last:border-b-0">
    <summary className="grid cursor-pointer grid-cols-[82px_112px_1fr_96px_96px_80px_110px_110px] gap-2 px-3 py-3 text-sm hover:bg-slate-900/50">
     <b className="text-blue-300">#{r.runId}</b><span className="text-slate-400">{fmtTime(r.time)}</span><span className="font-semibold text-slate-100">{r.sourceLabel}</span><span className="text-emerald-300">{r.saved}</span><span className="text-blue-300">{r.seen||'-'}</span><span className={r.errors?'text-amber-300':'text-slate-500'}>{r.errors}</span><span className="text-purple-300">{r.imported}/{r.selected}</span><span className={r.statusCls}>{r.statusIcon} {r.status}</span>
    </summary>
    <div className="grid gap-4 bg-slate-950/70 p-4 text-sm xl:grid-cols-3">
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">本次处理</b><div className="mt-2 text-slate-400">过滤噪音高：{r.cleanRejected}</div><div className="text-slate-400">暂停条件：{r.targetCooled}</div><div className="text-slate-400">使用条件：{r.selectedCount}</div></div>
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">追溯信息</b><div className="mt-2 text-slate-400">抓取批次：#{r.runId}</div><div className="text-slate-400">发现来源：{r.sourceLabel}</div><div className="text-slate-400">机会线索 {r.saved} / 抓取结果 {r.seen||'-'} / 异常 {r.errors}</div></div>
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">原始记录</b><pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(r.raw,null,2)}</pre></div>
     <div className="xl:col-span-3 rounded-xl bg-slate-900 p-3"><b className="text-slate-200">本次使用的搜索条件</b><div className="mt-2 flex flex-wrap gap-2">{Object.entries(r.summary.selected_by_segment||{}).flatMap(([seg,items]:any)=>(items||[]).slice(0,8).map((t:any)=><span key={`${r.id}-${seg}-${t.id}`} className="rounded-lg bg-slate-950 px-2 py-1 text-xs text-slate-300">{segmentName(seg)}：{t.value}</span>))}</div></div>
    </div>
   </details>):<div className="px-4 py-6 text-sm text-slate-500">暂无符合筛选条件的抓取记录。</div>}
  </div>
 </section>
}

function TraceCard({label,value,hint,tone='slate',onClick}:any){const color:any={slate:'text-white',green:'text-emerald-300',blue:'text-blue-300',amber:'text-amber-300',purple:'text-purple-300',red:'text-red-300'}; return <button onClick={onClick} className="rounded-xl bg-slate-950 p-3 text-left transition hover:bg-slate-900 hover:ring-1 hover:ring-blue-500/40"><div className="text-xs text-slate-500">{label}</div><b className={`text-2xl ${color[tone]}`}>{value}</b><div className="mt-1 text-xs text-blue-300">{hint||'点击追溯'} →</div></button>}
function TraceModal({trace,onClose}:any){return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">Trace</div><h2 className="mt-1 text-2xl font-bold text-white">{trace.title}</h2><p className="mt-1 text-sm text-slate-400">这里显示这个数字背后的具体数据。</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><TraceList trace={trace}/></aside></div>}
function TraceList({trace}:any){const items=trace.items||[]; if(!items.length)return <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-sm text-slate-400">{trace.empty||'暂无数据。'}</div>; if(trace.type==='targets')return <div className="space-y-2">{items.map((t:any)=><div key={t.id||t.value} className="rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-100">{t.value}</b><div className="mt-1 text-slate-500">类型：{t.target_type==='domain'?'网站':'搜索词'} · 状态：{segmentName(t.status)} · 优先级：{Math.round(t.priority||0)} · 成功/拒绝：{t.success_count||0}/{t.reject_count||0}</div></div>)}</div>; if(trace.type==='sources')return <div className="space-y-2">{items.map((r:any,i:number)=>{const st=resultStatus(Number(r.saved||0),Number(r.errors||0)); return <div key={i} className="rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-100">{sourceName(r.source)}</b><div className="mt-1 text-slate-400">机会线索 {r.saved||0} · 抓取结果 {r.seen??'-'} · 异常 {r.errors||0} · <span className={st.cls}>{st.icon} {st.label}</span></div></div>})}</div>; if(trace.type==='candidates')return <div className="space-y-2">{items.map((c:any)=><div key={c.id} className="rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-100">{c.keyword}</b><div className="mt-1 text-slate-500">来源：{sourceName(c.source)} · 分数：{Number(c.score||0).toFixed(2)}</div></div>)}</div>; if(trace.type==='issues')return <div className="space-y-2">{items.map((x:any,i:number)=><div key={x.code||i} className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100"><b>{x.severity||'关注'}</b><div className="mt-1">{x.text||JSON.stringify(x)}</div></div>)}</div>; return <pre className="rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(items,null,2)}</pre>}
function TargetPreview({title,items}:{title:string;items:any[]}){return <section className="panel"><h2 className="text-xl font-bold">{title}</h2><div className="mt-4 space-y-2">{items.length?items.map((t:any)=><div key={t.id} className="rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{t.value}</b><span className="ml-2 text-slate-500">{t.target_type} · {t.status} · P{Math.round(t.priority||0)} · S{t.success_count||0}/R{t.reject_count||0}</span></div>):<p className="text-sm text-slate-500">暂无</p>}</div></section>}
function SourcePreview({rows}:{rows:any[]}){return <section className="panel"><h2 className="text-xl font-bold">最近来源表现</h2><div className="mt-4 space-y-2">{rows?.length?rows.map((r:any,i:number)=>{const st=resultStatus(Number(r.saved||0),Number(r.errors||0)); return <div key={i} className="grid grid-cols-[1fr_88px_88px_88px_96px] gap-2 rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{sourceName(r.source)}</b><span className="text-emerald-300">线索 {r.saved||0}</span><span className="text-blue-300">结果 {r.seen??'-'}</span><span className={r.errors?'text-amber-300':'text-slate-500'}>异常 {r.errors||0}</span><span className={st.cls}>{st.icon} {st.label}</span></div>}) : <p className="text-sm text-slate-500">暂无抓取记录。</p>}</div></section>}

function OptimizationLog({onClose,repairRuns,repairAutoRuns,rejectedReasons,inspectRejected,busy}:any){return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-4xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-amber-300">Optimization Records</div><h2 className="mt-1 text-2xl font-bold text-white">优化记录</h2><p className="mt-1 text-sm text-slate-400">仅用于维护者排查系统为什么调整策略，不属于主流程。</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><div className="mb-4"><button className="btn-secondary" disabled={busy} onClick={inspectRejected}>刷新过滤原因</button></div>{rejectedReasons&&<section className="mb-5 rounded-2xl border border-slate-800 bg-slate-900/50 p-4"><h3 className="font-bold text-white">过滤原因</h3><div className="mt-3 grid gap-4 xl:grid-cols-2"><ReasonList rows={rejectedReasons.by_reason} keyName="reason"/><ReasonList rows={rejectedReasons.by_source} keyName="source"/></div></section>}<section className="grid gap-4 xl:grid-cols-2"><Replay title="自动优化记录" rows={repairAutoRuns}/><Replay title="单次优化记录" rows={repairRuns}/></section></aside></div>}
function ReasonList({rows,keyName}:{rows:any[];keyName:string}){return <div className="space-y-2">{(rows||[]).slice(0,12).map((r:any)=><div key={r[keyName]} className="flex justify-between rounded-xl bg-slate-950 p-3 text-sm"><span className="text-slate-300">{r[keyName]}</span><b className="text-amber-300">{r.count}</b></div>)}</div>}
function Replay({title,rows}:{title:string;rows:any[]}){return <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4"><h3 className="font-bold text-white">{title}</h3><div className="mt-3 space-y-2">{rows.length?rows.map((r:any)=><details key={r.id} className="rounded-xl bg-slate-950 p-3 text-sm"><summary className="cursor-pointer text-slate-200">#{r.id} · {fmtTime(r.started_at)} · {r.status}</summary><pre className="mt-3 max-h-72 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(r.summary||{},null,2)}</pre></details>):<p className="text-sm text-slate-500">暂无</p>}</div></section>}
