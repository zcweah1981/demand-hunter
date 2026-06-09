'use client'
import {useEffect, useMemo, useState} from 'react'
import {usePathname} from 'next/navigation'
import {api, authToken} from '../lib/api'

type Section = 'overview' | 'conditions' | 'sources' | 'records'
type Tone = 'slate' | 'green' | 'blue' | 'amber' | 'purple' | 'red'

const sectionItems:{id:Section; label:string; desc:string}[] = [
 {id:'overview', label:'总览', desc:'结果、风险、下一步'},
 {id:'conditions', label:'搜索条件', desc:'系统依据什么继续找'},
 {id:'sources', label:'发现来源', desc:'每种来源发现什么'},
 {id:'records', label:'抓取记录', desc:'每次抓取结果'},
]

const sourceLabels:any={
 sitemap:'Sitemap 站点监控',
 domain_web:'网页内容识别',
 suggest:'搜索联想扩展',
 advanced_search:'搜索结果挖掘',
 alternatives:'替代品/对比挖掘',
 hot_topic:'热点任务补充',
 source_radar:'一手信号雷达',
}
const segmentLabels:any={winner:'高价值',promising:'可继续观察',new:'新搜索条件',noisy:'噪音高',cooldown:'已暂停',exhausted:'暂无价值'}
const sourceCatalog = [
 {id:'sitemap', name:'Sitemap 站点监控', group:'看竞品网站', look:'竞品 sitemap / 新页面', find:'新工具页、模板页、对比页'},
 {id:'domain_web', name:'网页内容识别', group:'看竞品网站', look:'页面标题、H1、Meta', find:'页面表达出来的任务需求'},
 {id:'suggest', name:'搜索联想扩展', group:'看搜索词', look:'已有搜索词的联想结果', find:'更长尾、更具体的搜索需求'},
 {id:'advanced_search', name:'搜索结果挖掘', group:'看搜索结果', look:'标题、站点、时间范围组合查询', find:'已有页面缺口和新页面主题'},
 {id:'alternatives', name:'替代品/对比挖掘', group:'看竞品缺口', look:'替代品、对比、迁移相关搜索', find:'用户准备替换或比较工具的机会'},
 {id:'hot_topic', name:'热点任务补充', group:'看近期趋势', look:'近期主题和有效搜索条件', find:'近期出现的任务型线索'},
 {id:'source_radar', name:'一手信号雷达', group:'看早期信号', look:'HN / GitHub / arXiv 等源头', find:'新技术、新词、新需求苗头'},
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
  const conditionCount=Object.values(selected).reduce((acc:any,items:any)=>acc+(Array.isArray(items)?items.length:0),0)
  return (s.source_results||[]).map((r:any,i:number)=>{
   const leads=Number(r.saved||0), looked=Number(r.seen||0), problems=Number(r.errors||0)
   const st=statusFor(leads, problems)
   return {id:`${run.id}-${i}`, batch:run.id, time:run.started_at, source:r.source||'unknown', sourceLabel:sourceName(r.source), leads, looked, problems, status:st, verified:s.import?.imported||0, selected:s.import?.selected||0, filtered:s.clean?.rejected||0, paused:s.target_health?.cooled||0, conditionCount, selectedBySegment:selected, raw:r}
  })
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
   const [h,seg,bg,rs,cs,repairs,repairAutos,mx]=await Promise.all([
    api<any>('/api/collectors/health'),
    api<any>('/api/collectors/targets/segments'),
    api<any>('/api/collectors/budget/next?limit=24'),
    api<any[]>('/api/collectors/runs?limit=8'),
    api<any[]>('/api/collectors/candidates?limit=80&status=new'),
    api<any[]>('/api/collectors/repairs?limit=8'),
    api<any[]>('/api/collectors/repairs/autopilot/runs?limit=6'),
    api<any>('/api/collectors/matrix?limit=400'),
   ])
   setHealth(h); setSegments(seg); setBudget(bg); setRuns(rs); setCandidates(cs); setRepairRuns(repairs); setRepairAutoRuns(repairAutos); setMatrix(mx)
  }catch(e:any){setMsg(`加载失败：${e.message}`)}
 }
 useEffect(()=>{load()},[])

 async function runDiscovery(){setBusy(true);setMsg('正在抓取机会线索...');try{const r=await api<any>('/api/collectors/autopilot/run',{method:'POST',body:JSON.stringify({limit:24})});setMsg(`抓取完成：${r.import?.imported||0}/${r.import?.selected||0} 条进入验证，过滤 ${r.clean?.rejected||0} 条噪音`);await load()}catch(e:any){setMsg(`运行失败：${e.message}`)}finally{setBusy(false)}}
 async function refreshConditions(){setBusy(true);setMsg('正在从机会判断更新搜索条件...');try{const r=await api<any>('/api/collectors/targets/refresh',{method:'POST'});setMsg(`已更新：搜索词 ${r.keyword_targets||0}，网站 ${r.domain_targets||0}`);await load()}catch(e:any){setMsg(`更新失败：${e.message}`)}finally{setBusy(false)}}
 async function tidyConditions(){setBusy(true);try{const r=await api<any>('/api/collectors/targets/health',{method:'POST'});setMsg(`整理完成：暂停 ${r.cooled||0}，恢复 ${r.promoted||0}`);await load()}catch(e:any){setMsg(`整理失败：${e.message}`)}finally{setBusy(false)}}
 async function inspectRejected(){setBusy(true);try{const r=await api<any>('/api/collectors/rejected-reasons?limit=800');setRejectedReasons(r); setShowLog(true)}catch(e:any){setMsg(`检查失败：${e.message}`)}finally{setBusy(false)}}
 async function downloadDigest(){setBusy(true);try{const token=authToken(); const res=await fetch('/api/reports/download/latest',{headers:token?{Authorization:`Bearer ${token}`}:{}}); if(!res.ok) throw new Error(`${res.status} ${await res.text()}`); const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='demand_cards_latest.md'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)}catch(e:any){setMsg(`下载失败：${e.message}`)}finally{setBusy(false)}}

 const records=useMemo(()=>normalizeRecords(runs),[runs])
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
   {section==='sources'&&<Sources sourceRows={sourceRows} matrix={matrix}/>} 
   {section==='records'&&<Records records={visibleRecords} allRecords={records} sources={sources} sourceFilter={recordSource} statusFilter={recordStatus} setSourceFilter={setRecordSource} setStatusFilter={setRecordStatus}/>} 
  </main>
  {trace&&<TraceModal trace={trace} onClose={()=>setTrace(null)}/>} {showLog&&<OptimizationLog onClose={()=>setShowLog(false)} repairRuns={repairRuns} repairAutoRuns={repairAutoRuns} rejectedReasons={rejectedReasons} inspectRejected={inspectRejected} busy={busy}/>} 
 </div>
}

function Overview({health,latest,totalLeads,totalLooked,problemSources,highValue,candidates,sourceRows,openTrace}:any){return <div className="space-y-6"><section className="grid gap-4 md:grid-cols-5"><TraceCard label="系统状态" value={`${health?.score??'-'}/100`} hint="查看风险" tone={health?.status==='healthy'?'green':health?.status==='watch'?'amber':'red'} onClick={()=>openTrace({title:'系统状态',type:'issues',items:health?.issues||[],empty:'暂无风险。'})}/><TraceCard label="有效搜索条件" value={highValue.length} hint="查看条件" tone="green" onClick={()=>openTrace({title:'有效搜索条件',type:'targets',items:highValue})}/><TraceCard label="待验证线索" value={candidates.length} hint="查看线索" tone="blue" onClick={()=>openTrace({title:'待验证线索',type:'candidates',items:candidates})}/><TraceCard label="进入验证" value={`${latest.import?.imported??0}/${latest.import?.selected??0}`} hint="查看最近一轮" tone="purple" onClick={()=>openTrace({title:'进入验证',type:'run',items:[latest]})}/><TraceCard label="需检查来源" value={problemSources.length} hint="查看来源" tone="amber" onClick={()=>openTrace({title:'需检查来源',type:'records',items:problemSources})}/></section><FlowCompact/><section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">最近一次抓取</h2><p className="mt-1 text-sm text-slate-400">点击任意数字查看它背后的数据。</p></div></div><div className="mt-4 grid gap-3 md:grid-cols-4"><TraceCard label="机会线索" value={totalLeads} tone="green" onClick={()=>openTrace({title:'机会线索来源',type:'sources',items:sourceRows})}/><TraceCard label="抓取结果" value={totalLooked||'-'} tone="blue" onClick={()=>openTrace({title:'抓取结果来源',type:'sources',items:sourceRows})}/><TraceCard label="异常来源" value={problemSources.length} tone="amber" onClick={()=>openTrace({title:'异常来源',type:'records',items:problemSources})}/><TraceCard label="进入验证" value={`${latest.import?.imported??0}/${latest.import?.selected??0}`} tone="purple" onClick={()=>openTrace({title:'进入验证',type:'run',items:[latest]})}/></div></section><section className="grid gap-4 xl:grid-cols-2"><TargetList title="当前优先搜索条件" items={highValue.slice(0,12)}/><SourceList rows={sourceRows}/></section></div>}
function FlowCompact(){const steps=[['搜索条件','机会卡/人工词/竞品网站'],['发现来源','网站/搜索结果/联想/热点'],['机会线索','过滤噪音后进入线索池'],['进入验证','可用线索进入搜索验证'],['机会判断','Action / Watch / Reject 回流条件']]; return <section className="panel"><h2 className="text-xl font-bold">系统如何找机会</h2><p className="mt-1 text-sm text-slate-400">这是背景说明，不单独占菜单入口。</p><div className="mt-4 grid gap-3 md:grid-cols-5">{steps.map(([t,d],i)=><div key={t} className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="mb-2 flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-black text-white">{i+1}</div><b className="text-sm text-white">{t}</b><p className="mt-1 text-xs leading-5 text-slate-400">{d}</p></div>)}</div></section>}
function Conditions({segSummary,segMap,highValue,weak,budget,busy,refreshConditions,tidyConditions,openTrace}:any){const cats=[['winner','高价值'],['promising','可继续观察'],['new','新搜索条件'],['noisy','噪音高'],['cooldown','已暂停'],['exhausted','暂无价值']]; return <div className="space-y-6"><section className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">搜索条件分类</h2><p className="mt-1 text-sm text-slate-400">点击数字，查看对应条件。</p></div><div className="flex gap-2"><button className="btn-secondary" disabled={busy} onClick={tidyConditions}>整理搜索条件</button><button className="btn" disabled={busy} onClick={refreshConditions}>从机会卡更新</button></div></div><div className="mt-4 grid gap-3 md:grid-cols-6">{cats.map(([k,l])=><TraceCard key={k} label={l} value={segSummary[k]||0} onClick={()=>openTrace({title:l,type:'targets',items:segMap[k]||[],empty:`暂无${l}`})}/>)}</div></section><section className="grid gap-4 xl:grid-cols-2"><TargetList title="有效搜索条件" items={highValue}/><TargetList title="暂停/低价值条件" items={weak}/></section><section className="panel"><h2 className="text-xl font-bold">下一轮投入</h2><div className="mt-4 grid gap-3 md:grid-cols-4">{(budget?.allocation||[]).map((row:any)=><TraceCard key={row.segment} label={row.label} value={row.budget} hint={`可用 ${row.available}`} tone="green" onClick={()=>openTrace({title:`${row.label} 投入条件`,type:'targets',items:row.targets||[]})}/>)}</div></section></div>}
function Sources({sourceRows,matrix}:any){const perf=Object.fromEntries((sourceRows||[]).map((r:any)=>[normalizeSourceKey(r.source),r])); const sourceMatrix=matrix?.by_source||[]; return <div className="space-y-6"><section className="panel"><h2 className="text-xl font-bold">发现来源</h2><p className="mt-1 text-sm text-slate-400">每种来源看哪里、发现什么、最近是否有效。</p><div className="mt-5 grid gap-4 xl:grid-cols-2">{sourceCatalog.map(m=>{const p=perf[m.id]||{}; const st=statusFor(Number(p.saved||0),Number(p.errors||0)); const mx=sourceMatrix.find((x:any)=>x.source===m.id)||{}; return <article key={m.id} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-xs text-blue-300">{m.group}</div><h3 className="mt-2 text-lg font-bold text-white">{m.name}</h3></div><span className={`${toneText(st.tone)} text-sm`}>{st.icon} {st.label}</span></div><div className="mt-4 grid gap-2 text-xs md:grid-cols-2"><div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-300">看哪里</b><div className="mt-1 text-slate-500">{m.look}</div></div><div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-300">发现什么</b><div className="mt-1 text-slate-500">{m.find}</div></div></div><div className="mt-4 grid grid-cols-3 gap-2 text-sm"><MetricBlock label="线索" value={p.saved??'-'} tone="green"/><MetricBlock label="结果" value={p.seen??'-'} tone="blue"/><MetricBlock label="异常" value={p.errors??'-'} tone={p.errors?'amber':'slate'}/></div><div className="mt-3 rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-200">条件效果</b><div className="mt-1 text-slate-400">有效条件 {mx.effective||0} · 噪音条件 {mx.noisy||0} · 总有效/拒绝 {mx.success||0}/{mx.reject||0}</div></div></article>})}</div></section><MatrixTable rows={matrix?.rows||[]}/></div>}
function normalizeSourceKey(x?:string){return x==='google_suggest'||x==='duckduckgo'||x==='short_tail_rewrite'?'suggest':x==='hn_algolia'||x==='arxiv'?'source_radar':(x||'unknown')}
function MatrixTable({rows}:{rows:any[]}){const [source,setSource]=useState('all'); const [verdict,setVerdict]=useState('all'); const sources=Array.from(new Set((rows||[]).map((r:any)=>r.source))); const visible=(rows||[]).filter((r:any)=>(source==='all'||r.source===source)&&(verdict==='all'||r.verdict===verdict)).slice(0,120); return <section className="panel"><h2 className="text-xl font-bold">来源 × 搜索条件效果矩阵</h2><p className="mt-1 text-sm text-slate-400">判断哪个来源对哪个搜索条件有效，哪个来源制造噪音。</p><div className="mt-4 flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3"><Select label="来源" value={source} setValue={setSource} options={[['all','全部'],...sources.map((x:any)=>[x,sourceName(x)])]}/><Select label="效果" value={verdict} setValue={setVerdict} options={[['all','全部'],['有效','有效'],['噪音偏高','噪音偏高'],['观察','观察'],['暂无来源反馈','暂无来源反馈']]}/><div className="ml-auto text-sm text-slate-400">显示 {visible.length}/{rows?.length||0}</div></div><div className="mt-4 overflow-hidden rounded-2xl border border-slate-800"><div className="grid grid-cols-[1fr_160px_90px_90px_90px_100px] gap-2 border-b border-slate-800 bg-slate-900/70 px-3 py-2 text-xs font-semibold text-slate-500"><div>搜索条件</div><div>发现来源</div><div>线索</div><div>有效</div><div>拒绝</div><div>判断</div></div>{visible.length?visible.map((r:any,i:number)=><div key={`${r.target_id}-${r.source}-${i}`} className="grid grid-cols-[1fr_160px_90px_90px_90px_100px] gap-2 border-b border-slate-800 px-3 py-3 text-sm last:border-b-0"><b className="text-slate-100">{r.condition}</b><span className="text-blue-300">{r.source_label}</span><span className="text-slate-300">{r.leads}</span><span className="text-emerald-300">{r.success}</span><span className={(r.reject||0)>(r.success||0)?'text-amber-300':'text-slate-400'}>{r.reject}</span><span className={r.verdict==='有效'?'text-emerald-300':r.verdict==='噪音偏高'?'text-amber-300':'text-slate-400'}>{r.verdict}</span></div>):<div className="px-4 py-6 text-sm text-slate-500">暂无矩阵数据。</div>}</div></section>}
function Records({records,allRecords,sources,sourceFilter,statusFilter,setSourceFilter,setStatusFilter}:any){const totalLeads=records.reduce((a:any,r:any)=>a+r.leads,0), totalLooked=records.reduce((a:any,r:any)=>a+r.looked,0), totalProblems=records.reduce((a:any,r:any)=>a+r.problems,0); return <section className="panel"><div><h2 className="text-xl font-bold">抓取记录</h2><p className="mt-1 text-sm text-slate-400">每条记录都能追到抓取批次、发现来源和使用的搜索条件。</p></div><div className="mt-4 grid gap-3 md:grid-cols-4"><MetricBlock label="记录数" value={records.length}/><MetricBlock label="机会线索" value={totalLeads} tone="green"/><MetricBlock label="抓取结果" value={totalLooked||'-'} tone="blue"/><MetricBlock label="异常" value={totalProblems} tone={totalProblems?'amber':'slate'}/></div><div className="mt-4 flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-3"><label className="text-sm text-slate-300">发现来源 <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={sourceFilter} onChange={e=>setSourceFilter(e.target.value)}>{sources.map((x:any)=><option key={x} value={x}>{x==='all'?'全部':sourceName(x)}</option>)}</select></label><label className="text-sm text-slate-300">状态 <select className="ml-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>{['all','有发现','暂无发现','需检查'].map(x=><option key={x} value={x}>{x==='all'?'全部':x}</option>)}</select></label></div><div className="mt-4 overflow-hidden rounded-2xl border border-slate-800"><div className="grid grid-cols-[90px_112px_1fr_96px_96px_80px_110px_110px] gap-2 border-b border-slate-800 bg-slate-900/70 px-3 py-2 text-xs font-semibold text-slate-500"><div>抓取批次</div><div>时间</div><div>发现来源</div><div>机会线索</div><div>抓取结果</div><div>异常</div><div>进入验证</div><div>状态</div></div>{records.length?records.map((r:any)=><details key={r.id} className="border-b border-slate-800 last:border-b-0"><summary className="grid cursor-pointer grid-cols-[90px_112px_1fr_96px_96px_80px_110px_110px] gap-2 px-3 py-3 text-sm hover:bg-slate-900/50"><b className="text-blue-300">#{r.batch}</b><span className="text-slate-400">{fmtTime(r.time)}</span><span className="font-semibold text-slate-100">{r.sourceLabel}</span><span className="text-emerald-300">{r.leads}</span><span className="text-blue-300">{r.looked||'-'}</span><span className={r.problems?'text-amber-300':'text-slate-500'}>{r.problems}</span><span className="text-purple-300">{r.verified}/{r.selected}</span><span className={toneText(r.status.tone)}>{r.status.icon} {r.status.label}</span></summary><div className="grid gap-4 bg-slate-950/70 p-4 text-sm xl:grid-cols-3"><InfoCard title="本次处理" rows={[['过滤噪音',r.filtered],['暂停条件',r.paused],['使用条件',r.conditionCount]]}/><InfoCard title="追溯信息" rows={[['抓取批次',`#${r.batch}`],['发现来源',r.sourceLabel],['结果',`线索 ${r.leads} / 抓取 ${r.looked||'-'} / 异常 ${r.problems}`]]}/><div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-200">原始记录</b><pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(r.raw,null,2)}</pre></div><div className="xl:col-span-3 rounded-xl bg-slate-900 p-3"><b className="text-slate-200">本次使用的搜索条件</b><div className="mt-2 flex flex-wrap gap-2">{Object.entries(r.selectedBySegment||{}).flatMap(([seg,items]:any)=>(items||[]).slice(0,8).map((t:any)=><span key={`${r.id}-${seg}-${t.id}`} className="rounded-lg bg-slate-950 px-2 py-1 text-xs text-slate-300">{segmentName(seg)}：{t.value}</span>))}</div></div></div></details>):<div className="px-4 py-6 text-sm text-slate-500">暂无符合筛选条件的抓取记录。</div>}</div></section>}

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
function ConditionRow({t}:{t:any}){const sources=t.source_effectiveness||[]; const top=sources.slice(0,3); return <details className="border-b border-slate-800 last:border-b-0"><summary className="grid cursor-pointer grid-cols-[1fr_80px_90px_100px_120px_1.4fr] gap-2 px-3 py-3 text-sm hover:bg-slate-900/50"><b className="text-slate-100">{t.value}</b><span className="text-slate-400">{t.target_type==='domain'?'网站':'搜索词'}</span><span className="text-blue-300">{segmentName(t.status)}</span><span className="text-slate-300">{Math.round(t.priority||0)}</span><span className="text-slate-300">{t.success_count||0}/{t.reject_count||0}</span><span className="flex flex-wrap gap-1">{top.length?top.map((s:any)=><span key={s.source} className={(s.reject||0)>(s.success||0)?'rounded bg-amber-500/10 px-2 py-0.5 text-xs text-amber-200':'rounded bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-200'}>{sourceName(s.source)} {s.success||0}/{s.reject||0}</span>):<span className="text-slate-500">暂无来源反馈</span>}</span></summary><div className="bg-slate-950/70 p-4"><h4 className="mb-2 text-sm font-semibold text-slate-200">发现来源效果</h4>{sources.length?<div className="grid gap-2 md:grid-cols-2">{sources.map((s:any)=><div key={s.source} className="rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-100">{sourceName(s.source)}</b><div className="mt-1 text-slate-400">带来线索 {s.leads||0} · 有效 {s.success||0} · 拒绝 {s.reject||0}</div>{s.last_keyword&&<div className="mt-1 text-xs text-slate-500">最近：{s.last_label} · {s.last_keyword}</div>}</div>)}</div>:<p className="text-sm text-slate-500">暂无来源反馈。</p>}</div></details>}

function SourceList({rows}:{rows:any[]}){return <section className="panel"><h2 className="text-xl font-bold">最近来源表现</h2><div className="mt-4 space-y-2">{rows?.length?rows.map((r:any,i:number)=>{const st=statusFor(Number(r.saved||0),Number(r.errors||0)); return <div key={i} className="grid grid-cols-[1fr_88px_88px_88px_96px] gap-2 rounded-xl bg-slate-950 p-3 text-sm"><b className="text-slate-100">{sourceName(r.source)}</b><span className="text-emerald-300">线索 {r.saved||0}</span><span className="text-blue-300">结果 {r.seen??'-'}</span><span className={r.errors?'text-amber-300':'text-slate-500'}>异常 {r.errors||0}</span><span className={toneText(st.tone)}>{st.icon} {st.label}</span></div>}) : <p className="text-sm text-slate-500">暂无抓取记录。</p>}</div></section>}
function TraceModal({trace,onClose}:any){return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">Trace</div><h2 className="mt-1 text-2xl font-bold text-white">{trace.title}</h2><p className="mt-1 text-sm text-slate-400">这个数字背后的具体数据。</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><TraceList trace={trace}/></aside></div>}
function TraceList({trace}:any){const items=trace.items||[]; if(!items.length)return <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-sm text-slate-400">{trace.empty||'暂无数据。'}</div>; if(trace.type==='targets')return <ConditionTable items={items}/>; if(trace.type==='sources')return <SourceList rows={items}/>; if(trace.type==='records')return <div className="space-y-2">{items.map((r:any)=><div key={r.id} className="rounded-xl bg-slate-900 p-3 text-sm"><b>{r.sourceLabel}</b><div className="mt-1 text-slate-400">批次 #{r.batch} · 线索 {r.leads} · 抓取 {r.looked||'-'} · 异常 {r.problems}</div></div>)}</div>; if(trace.type==='candidates')return <div className="space-y-2">{items.map((c:any)=><div key={c.id} className="rounded-xl bg-slate-900 p-3 text-sm"><b className="text-slate-100">{c.keyword}</b><div className="mt-1 text-slate-500">来源：{sourceName(c.source)} · 分数：{Number(c.score||0).toFixed(2)}</div></div>)}</div>; if(trace.type==='issues')return <div className="space-y-2">{items.map((x:any,i:number)=><div key={x.code||i} className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100"><b>{x.severity||'关注'}</b><div className="mt-1">{x.text||JSON.stringify(x)}</div></div>)}</div>; return <pre className="rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(items,null,2)}</pre>}
function OptimizationLog({onClose,repairRuns,repairAutoRuns,rejectedReasons,inspectRejected,busy}:any){return <div className="fixed inset-0 z-50"><button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭"/><aside className="absolute right-0 top-0 h-full w-full max-w-4xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl"><div className="mb-5 flex items-start justify-between gap-3"><div><div className="text-xs uppercase tracking-[0.25em] text-amber-300">Optimization Records</div><h2 className="mt-1 text-2xl font-bold text-white">优化记录</h2><p className="mt-1 text-sm text-slate-400">仅用于维护者排查系统为什么调整策略，不属于主流程。</p></div><button className="btn-secondary" onClick={onClose}>关闭</button></div><div className="mb-4"><button className="btn-secondary" disabled={busy} onClick={inspectRejected}>刷新过滤原因</button></div>{rejectedReasons&&<section className="mb-5 rounded-2xl border border-slate-800 bg-slate-900/50 p-4"><h3 className="font-bold text-white">过滤原因</h3><div className="mt-3 grid gap-4 xl:grid-cols-2"><ReasonMini rows={rejectedReasons.by_reason} keyName="reason"/><ReasonMini rows={rejectedReasons.by_source} keyName="source"/></div></section>}<section className="grid gap-4 xl:grid-cols-2"><Replay title="自动优化记录" rows={repairAutoRuns}/><Replay title="单次优化记录" rows={repairRuns}/></section></aside></div>}
function ReasonMini({rows,keyName}:{rows:any[];keyName:string}){return <div className="space-y-2">{(rows||[]).slice(0,12).map((r:any)=><div key={r[keyName]} className="flex justify-between rounded-xl bg-slate-950 p-3 text-sm"><span className="text-slate-300">{r[keyName]}</span><b className="text-amber-300">{r.count}</b></div>)}</div>}
function Replay({title,rows}:{title:string;rows:any[]}){return <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4"><h3 className="font-bold text-white">{title}</h3><div className="mt-3 space-y-2">{rows.length?rows.map((r:any)=><details key={r.id} className="rounded-xl bg-slate-950 p-3 text-sm"><summary className="cursor-pointer text-slate-200">#{r.id} · {fmtTime(r.started_at)} · {r.status}</summary><pre className="mt-3 max-h-72 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(r.summary||{},null,2)}</pre></details>):<p className="text-sm text-slate-500">暂无</p>}</div></section>}
