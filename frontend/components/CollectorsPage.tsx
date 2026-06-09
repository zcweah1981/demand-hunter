'use client'
import {useEffect, useState} from 'react'
import Link from 'next/link'
import {usePathname} from 'next/navigation'
import {api, authToken} from '../lib/api'

type Tab = 'overview' | 'flow' | 'conditions' | 'modules' | 'results'

const collectorModules = [
 {id:'sitemap', name:'Sitemap 站点监控', layer:'站找词', goal:'发现竞品新增页面、工具页、模板页', input:'竞品域名 / sitemap.xml', output:'新页面 URL → 候选关键词', status:'已接入'},
 {id:'domain_web', name:'网页标题/Meta 抽取', layer:'站找词', goal:'从竞品页面标题、H1、Meta 中提取任务词', input:'竞品域名', output:'页面主题 → 候选关键词', status:'已接入'},
 {id:'suggest', name:'搜索联想扩词', layer:'词找词', goal:'围绕已知关键词扩展长尾词', input:'seed keyword', output:'长尾 query → 候选关键词', status:'已接入'},
 {id:'advanced_search', name:'高级搜索 / SERP 变体', layer:'SERP 找缺口', goal:'用 allintitle/site/date 查询发现页面缺口', input:'任务词 + 竞品域名', output:'SERP 标题/URL → 候选关键词', status:'已接入'},
 {id:'alternatives', name:'Alternatives / Compare', layer:'竞品缺口', goal:'发现替代品、对比、迁移相关机会', input:'竞品域名', output:'alternative/compare 词', status:'已接入'},
 {id:'hot_topic', name:'热点任务补充', layer:'趋势补充', goal:'从近期主题中补充可执行任务词', input:'有效条件', output:'任务型候选词', status:'已接入'},
 {id:'source_radar', name:'一手信息源雷达', layer:'早期信号', goal:'从 HN/arXiv/GitHub 等捕捉新词源头', input:'技术/趋势 seed', output:'早期信号候选', status:'已接入'},
]

function fmtTime(s?:string){if(!s)return '-'; const d=new Date(s); if(Number.isNaN(d.getTime()))return '-'; return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}

const sourceLabels:any={
 sitemap:'Sitemap 站点监控', domain_web:'网页标题/Meta 抽取', suggest:'搜索联想扩词', advanced_search:'高级搜索/SERP', alternatives:'替代品/对比挖掘', hot_topic:'热点任务补充', source_radar:'一手信息源雷达'
}
const segmentLabels:any={winner:'高产出',promising:'有潜力',new:'新条件',noisy:'噪音',cooldown:'冷却',exhausted:'耗尽'}
function sourceName(x?:string){return sourceLabels[x||''] || x || '未知采集器'}
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

 async function load(){
  try{
   const [h,ts,seg,bg,rs,rep,repairs,repairAutos]=await Promise.all([
    api<any>('/api/collectors/health'),
    api<any[]>('/api/collectors/targets?limit=120&status='),
    api<any>('/api/collectors/targets/segments'),
    api<any>('/api/collectors/budget/next?limit=24'),
    api<any[]>('/api/collectors/runs?limit=8'),
    api<any>('/api/reports/daily-digest').catch(()=>null),
    api<any[]>('/api/collectors/repairs?limit=8'),
    api<any[]>('/api/collectors/repairs/autopilot/runs?limit=6'),
   ])
   setHealth(h); setTargets(ts); setSegments(seg); setBudget(bg); setRuns(rs); setReport(rep); setRepairRuns(repairs); setRepairAutoRuns(repairAutos)
  }catch(e:any){setMsg(`加载失败：${e.message}`)}
 }
 useEffect(()=>{load()},[])

 async function runCollectorAuto(){setBusy(true);setMsg('正在运行采集流程...');try{const r=await api<any>('/api/collectors/autopilot/run',{method:'POST',body:JSON.stringify({limit:24})});setMsg(`采集完成：导入 ${r.import?.imported||0}/${r.import?.selected||0}，清洗拒绝 ${r.clean?.rejected||0}`);await load()}catch(e:any){setMsg(`运行失败：${e.message}`)}finally{setBusy(false)}}
 async function refreshTargets(){setBusy(true);setMsg('正在从机会卡刷新已知条件...');try{const r=await api<any>('/api/collectors/targets/refresh',{method:'POST'});setMsg(`已刷新：关键词条件 ${r.keyword_targets||0}，域名条件 ${r.domain_targets||0}`);await load()}catch(e:any){setMsg(`刷新失败：${e.message}`)}finally{setBusy(false)}}
 async function applyTargetHealth(){setBusy(true);try{const r=await api<any>('/api/collectors/targets/health',{method:'POST'});setMsg(`条件整理完成：冷却 ${r.cooled||0}，恢复 ${r.promoted||0}`);await load()}catch(e:any){setMsg(`整理失败：${e.message}`)}finally{setBusy(false)}}
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
     <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Collector Center</p>
     <h1 className="mt-3 text-4xl font-black text-white">采集中心</h1>
     <p className="mt-3 max-w-3xl text-slate-300">关注结果和已知条件：系统发现了什么、依据什么继续找、哪些采集模块在工作。</p>
    </div>
    <div className="flex flex-wrap gap-2">
     <button className="btn" disabled={busy} onClick={runCollectorAuto}>运行采集</button>
     <button className="btn-secondary" disabled={busy} onClick={downloadDigest}>下载日报</button>
     <button className="btn-secondary" disabled={busy} onClick={()=>setShowLog(true)}>优化日志</button>
    </div>
   </div>
  </section>

  {msg&&<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}

  <div className="grid gap-6 xl:grid-cols-[220px_1fr]">
   <aside className="rounded-3xl border border-slate-800 bg-slate-950/70 p-3 xl:sticky xl:top-4 xl:h-fit">
    {[
     ['overview','总览','结果、风险、下一步'],
     ['flow','采集流程','从条件到机会'],
     ['conditions','已知条件','系统依据什么找'],
     ['modules','采集模块','每个采集器做什么'],
     ['results','运行结果','历史产出'],
    ].map(([id,label,desc]:any)=><Link key={id} href={`/collectors/${id}`} className={`mb-2 block w-full rounded-2xl px-4 py-3 text-left no-underline transition ${tab===id?'bg-blue-600 text-white':'bg-slate-900/70 text-slate-300 hover:bg-slate-800'}`}><b>{label}</b><div className="mt-1 text-xs opacity-70">{desc}</div></Link>)}
   </aside>

   <main className="space-y-6">
    {tab==='overview'&&<Overview health={health} summary={summary} latest={latest} report={report} goodTargets={goodTargets} sourceRows={sourceRows}/>} 
    {tab==='flow'&&<Flow/>}
    {tab==='conditions'&&<Conditions seg={seg} goodTargets={goodTargets} weakTargets={weakTargets} budget={budget} busy={busy} refreshTargets={refreshTargets} applyTargetHealth={applyTargetHealth}/>} 
    {tab==='modules'&&<Modules sourceRows={sourceRows}/>} 
    {tab==='results'&&<Results runs={runs} runCollectorAuto={runCollectorAuto} busy={busy}/>} 
   </main>
  </div>

  {showLog&&<OptimizationLog onClose={()=>setShowLog(false)} repairRuns={repairRuns} repairAutoRuns={repairAutoRuns} rejectedReasons={rejectedReasons} inspectRejected={inspectRejected} busy={busy}/>} 
 </div>
}

function Overview({health,summary,latest,report,goodTargets,sourceRows}:any){return <div className="space-y-6">
 <section className="grid gap-4 md:grid-cols-5">
  <div className="card"><div className="kpi-label">健康度</div><b className={`text-2xl ${clsStatus(health?.status)}`}>{health?.score??'-'}/100</b><div className="mt-1 text-xs text-slate-500">{health?.status||'-'}</div></div>
  <div className="card"><div className="kpi-label">有效条件</div><b className="text-2xl text-emerald-300">{summary.usable_targets??0}</b><div className="mt-1 text-xs text-slate-500">可继续追踪</div></div>
  <div className="card"><div className="kpi-label">待处理候选</div><b className="text-2xl text-blue-300">{summary.new_candidates??0}</b><div className="mt-1 text-xs text-slate-500">等待验证/入库</div></div>
  <div className="card"><div className="kpi-label">入库关键词</div><b className="text-2xl text-purple-300">{latest.import?.imported??0}/{latest.import?.selected??0}</b><div className="mt-1 text-xs text-slate-500">本轮筛选后入库</div></div>
  <div className="card"><div className="kpi-label">待关注项</div><b className="text-2xl text-amber-300">{health?.issues?.length||0}</b><div className="mt-1 text-xs text-slate-500">可能影响质量</div></div>
 </section>
 {report?.collector_audit&&<section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">最近一轮结论</h2><p className="mt-1 text-sm text-slate-400">只展示用户能判断的结果，不展示内部字段。</p></div><span className="badge">运行 #{report.collector_audit.run_id}</span></div><div className="mt-4 grid gap-3 md:grid-cols-4"><MetricBlock label="入库关键词" value={`${latest.import?.imported??0}/${latest.import?.selected??0}`} tone="purple"/><MetricBlock label="有效候选" value={(sourceRows||[]).reduce((a:any,r:any)=>a+Number(r.saved||0),0)} tone="green"/><MetricBlock label="抓取数量" value={(sourceRows||[]).reduce((a:any,r:any)=>a+Number(r.seen||0),0)||'-'} tone="blue"/><MetricBlock label="异常模块" value={(sourceRows||[]).filter((r:any)=>Number(r.errors||0)>0).length} tone="amber"/></div>{health?.issues?.length>0&&<div className="mt-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100"><b>下一轮关注：</b>{health.issues.slice(0,3).map((x:any)=>x.text).join('；')}</div>}</section>}
 <section className="grid gap-4 xl:grid-cols-2"><TargetPreview title="当前优先条件" items={goodTargets}/><SourcePreview rows={sourceRows}/></section>
 </div>}

function Flow(){const steps=[['1','输入条件','来自 Action/Watch 机会卡、人工 seed、竞品域名'],['2','采集模块','Sitemap / 网页 / Suggest / SERP / Alternatives / Hot topic'],['3','候选池','只保留具体任务词，过滤泛词、博客路径、噪音结果'],['4','关键词流','导入可验证关键词，进入 SEO/SERP 验证'],['5','机会卡','形成 Action / Watch / Reject，反馈再回流到条件库']]; return <section className="panel"><h2 className="text-xl font-bold">采集流程</h2><p className="mt-1 text-sm text-slate-400">这是用户需要理解的主流程，不展示内部修复细节。</p><div className="mt-5 grid gap-4 md:grid-cols-5">{steps.map(([n,t,d])=><div key={n} className="rounded-3xl border border-slate-800 bg-slate-950 p-4"><div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 font-black text-white">{n}</div><h3 className="font-bold text-white">{t}</h3><p className="mt-2 text-sm leading-6 text-slate-400">{d}</p></div>)}</div></section>}

function Conditions({seg,goodTargets,weakTargets,budget,busy,refreshTargets,applyTargetHealth}:any){return <div className="space-y-6"><section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">已知条件分类</h2><p className="mt-1 text-sm text-slate-400">这些是系统继续采集的依据。重点看哪些有效，哪些需要降温。</p></div><div className="flex gap-2"><button className="btn-secondary" disabled={busy} onClick={applyTargetHealth}>整理条件</button><button className="btn" disabled={busy} onClick={refreshTargets}>从机会卡刷新</button></div></div><div className="mt-4 grid gap-3 md:grid-cols-6">{[['winner','高产出'],['promising','有潜力'],['new','新条件'],['noisy','噪音'],['cooldown','冷却'],['exhausted','耗尽']].map(([k,l])=><div key={k} className="rounded-xl bg-slate-950 p-3"><div className="text-xs text-slate-500">{l}</div><b className="text-2xl text-white">{seg[k]||0}</b></div>)}</div></section><section className="grid gap-4 xl:grid-cols-2"><TargetPreview title="有效条件" items={goodTargets}/><TargetPreview title="降温/屏蔽条件" items={weakTargets}/></section><section className="panel"><h2 className="text-xl font-bold">下一轮预算</h2><div className="mt-4 grid gap-3 md:grid-cols-4">{(budget?.allocation||[]).map((row:any)=><div key={row.segment} className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><div className="text-sm font-semibold text-slate-200">{row.label}</div><div className="mt-2 text-2xl font-black text-emerald-300">{row.budget}</div><div className="mt-1 text-xs text-slate-500">available {row.available}</div></div>)}</div></section></div>}

function Modules({sourceRows}:any){const perf=Object.fromEntries((sourceRows||[]).map((r:any)=>[r.source,r])); return <section className="panel"><h2 className="text-xl font-bold">采集模块</h2><p className="mt-1 text-sm text-slate-400">每个模块负责一种找机会的方法。这里只展示输入、产出和最近表现。</p><div className="mt-5 grid gap-4 xl:grid-cols-2">{collectorModules.map(m=>{const p=perf[m.id]||{}; return <article key={m.id} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">{m.layer}</div><h3 className="mt-2 text-lg font-bold text-white">{m.name}</h3></div><span className="badge badge-action">{m.status}</span></div><p className="mt-3 text-sm leading-6 text-slate-300">{m.goal}</p><div className="mt-4 grid gap-2 text-xs md:grid-cols-2"><div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-300">输入</b><div className="mt-1 text-slate-500">{m.input}</div></div><div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-300">产出</b><div className="mt-1 text-slate-500">{m.output}</div></div></div><div className="mt-4 rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-300">最近表现：</b><span className="ml-2 text-emerald-300">有效候选 {p.saved??'-'}</span><span className="ml-2 text-blue-300">抓取数量 {p.seen??'-'}</span><span className="ml-2 text-slate-500">异常 {p.errors??'-'}</span></div></article>})}</div></section>}

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
  <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">运行结果</h2><p className="mt-1 text-sm text-slate-400">每次自动抓取的数据列表。用业务字段展示，可筛选、分类、追溯。</p></div><button className="btn" disabled={busy} onClick={runCollectorAuto}>运行采集</button></div>
  <div className="mt-4 grid gap-3 md:grid-cols-4"><MetricBlock label="结果记录" value={filtered.length}/><MetricBlock label="有效候选" value={totalSaved} tone="green"/><MetricBlock label="抓取数量" value={totalSeen||'-'} tone="blue"/><MetricBlock label="异常" value={totalErrors} tone={totalErrors?'amber':'slate'}/></div>
  <div className="mt-4 flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3">
   <label className="text-sm text-slate-300">采集模块 <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={sourceFilter} onChange={e=>setSourceFilter(e.target.value)}>{sources.map((x:any)=><option key={x} value={x}>{x==='all'?'全部':sourceName(x)}</option>)}</select></label>
   <label className="text-sm text-slate-300">状态 <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>{['all','有发现','暂无发现','需检查'].map(x=><option key={x} value={x}>{x==='all'?'全部':x}</option>)}</select></label>
  </div>
  <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800">
   <div className="grid grid-cols-[82px_112px_1fr_96px_96px_80px_110px_110px] gap-2 border-b border-slate-800 bg-slate-900/70 px-3 py-2 text-xs font-semibold text-slate-500"><div>批次</div><div>时间</div><div>采集模块</div><div>有效候选</div><div>抓取数量</div><div>异常</div><div>入库关键词</div><div>状态</div></div>
   {filtered.length?filtered.map((r:any)=><details key={r.id} className="border-b border-slate-800 last:border-b-0">
    <summary className="grid cursor-pointer grid-cols-[82px_112px_1fr_96px_96px_80px_110px_110px] gap-2 px-3 py-3 text-sm hover:bg-slate-900/50">
     <b className="text-blue-300">#{r.runId}</b><span className="text-slate-400">{fmtTime(r.time)}</span><span className="font-semibold text-slate-100">{r.sourceLabel}</span><span className="text-emerald-300">{r.saved}</span><span className="text-blue-300">{r.seen||'-'}</span><span className={r.errors?'text-amber-300':'text-slate-500'}>{r.errors}</span><span className="text-purple-300">{r.imported}/{r.selected}</span><span className={r.statusCls}>{r.statusIcon} {r.status}</span>
    </summary>
    <div className="grid gap-4 bg-slate-950/70 p-4 text-sm xl:grid-cols-3">
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">当轮结果</b><div className="mt-2 text-slate-400">过滤噪音：{r.cleanRejected}</div><div className="text-slate-400">暂停条件：{r.targetCooled}</div><div className="text-slate-400">使用条件：{r.selectedCount}</div></div>
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">追溯信息</b><div className="mt-2 text-slate-400">批次：#{r.runId}</div><div className="text-slate-400">采集模块：{r.sourceLabel}</div><div className="text-slate-400">有效候选 {r.saved} / 抓取 {r.seen||'-'} / 异常 {r.errors}</div></div>
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">技术摘要</b><pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(r.raw,null,2)}</pre></div>
     <div className="xl:col-span-3 rounded-xl bg-slate-900 p-3"><b className="text-slate-200">本轮使用的条件</b><div className="mt-2 flex flex-wrap gap-2">{Object.entries(r.summary.selected_by_segment||{}).flatMap(([seg,items]:any)=>(items||[]).slice(0,8).map((t:any)=><span key={`${r.id}-${seg}-${t.id}`} className="rounded-lg bg-slate-950 px-2 py-1 text-xs text-slate-300">{segmentName(seg)}：{t.value}</span>))}</div></div>
    </div>
   </details>):<div className="px-4 py-6 text-sm text-slate-500">暂无符合筛选条件的运行结果。</div>}
  </div>
 </section>
}

function TargetPreview({title,items}:{title:string;items:any[]}){return <section className="panel"><h2 className="text-xl font-bold">{title}</h2><div className="mt-4 space-y-2">{items.length?items.map((t:any)=><div key={t.id} className="rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{t.value}</b><span className="ml-2 text-slate-500">{t.target_type} · {t.status} · P{Math.round(t.priority||0)} · S{t.success_count||0}/R{t.reject_count||0}</span></div>):<p className="text-sm text-slate-500">暂无</p>}</div></section>}
function SourcePreview({rows}:{rows:any[]}){return <section className="panel"><h2 className="text-xl font-bold">最近采集表现</h2><div className="mt-4 space-y-2">{rows?.length?rows.map((r:any,i:number)=>{const st=resultStatus(Number(r.saved||0),Number(r.errors||0)); return <div key={i} className="grid grid-cols-[1fr_88px_88px_88px_96px] gap-2 rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{sourceName(r.source)}</b><span className="text-emerald-300">有效 {r.saved||0}</span><span className="text-blue-300">抓取 {r.seen??'-'}</span><span className={r.errors?'text-amber-300':'text-slate-500'}>异常 {r.errors||0}</span><span className={st.cls}>{st.icon} {st.label}</span></div>}) : <p className="text-sm text-slate-500">暂无运行记录。</p>}</div></section>}

function OptimizationLog({onClose,repairRuns,repairAutoRuns,rejectedReasons,inspectRejected,busy}:any){return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-4xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-amber-300">Optimization Log</div><h2 className="mt-1 text-2xl font-bold text-white">优化日志</h2><p className="mt-1 text-sm text-slate-400">仅用于排查系统为什么调整采集策略，不属于主流程。</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><div className="mb-4"><button className="btn-secondary" disabled={busy} onClick={inspectRejected}>刷新 rejected reason</button></div>{rejectedReasons&&<section className="mb-5 rounded-2xl border border-slate-800 bg-slate-900/50 p-4"><h3 className="font-bold text-white">Rejected reason</h3><div className="mt-3 grid gap-4 xl:grid-cols-2"><ReasonList rows={rejectedReasons.by_reason} keyName="reason"/><ReasonList rows={rejectedReasons.by_source} keyName="source"/></div></section>}<section className="grid gap-4 xl:grid-cols-2"><Replay title="Safe Repair Autopilot" rows={repairAutoRuns}/><Replay title="Repair Actions" rows={repairRuns}/></section></aside></div>}
function ReasonList({rows,keyName}:{rows:any[];keyName:string}){return <div className="space-y-2">{(rows||[]).slice(0,12).map((r:any)=><div key={r[keyName]} className="flex justify-between rounded-xl bg-slate-950 p-3 text-sm"><span className="text-slate-300">{r[keyName]}</span><b className="text-amber-300">{r.count}</b></div>)}</div>}
function Replay({title,rows}:{title:string;rows:any[]}){return <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4"><h3 className="font-bold text-white">{title}</h3><div className="mt-3 space-y-2">{rows.length?rows.map((r:any)=><details key={r.id} className="rounded-xl bg-slate-950 p-3 text-sm"><summary className="cursor-pointer text-slate-200">#{r.id} · {fmtTime(r.started_at)} · {r.status}</summary><pre className="mt-3 max-h-72 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(r.summary||{},null,2)}</pre></details>):<p className="text-sm text-slate-500">暂无</p>}</div></section>}
