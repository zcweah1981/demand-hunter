import {api} from '../lib/api'
import {StatCard} from '../components/StatCard'
import {OpportunityCardView} from '../components/OpportunityCard'
import {AutopilotPanel} from '../components/AutopilotPanel'
import {I18nText} from '../components/I18nText'

export default async function Page(){
 const [health,cards,autopilot] = await Promise.all([
  api<any>('/api/health'),
  api<any[]>('/api/cards'),
  api<any>('/api/autopilot/status').catch(()=>null),
 ])
 const counts={Action:cards.filter(c=>c.verdict==='Action').length,Watch:cards.filter(c=>c.verdict==='Watch').length,Reject:cards.filter(c=>c.verdict==='Reject').length}
 const top=cards.filter(c=>c.verdict!=='Reject').slice(0,6)
 return <div className="space-y-8">
  <section className="rounded-3xl border border-blue-500/30 bg-gradient-to-br from-blue-950/80 via-slate-950 to-slate-950 p-8 shadow-2xl"><div className="flex flex-wrap items-start justify-between gap-5"><div><p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Demand Hunter</p><h1 className="mt-3 text-4xl font-black text-white"><I18nText zh='自动机会猎手' en='Automatic Opportunity Hunter'/></h1><p className="mt-3 max-w-2xl text-slate-300"><I18nText zh='目标不是让你操作流程，而是让系统自己循环发现机会；你只看结果、做少量复核。' en='The goal is not workflow operation. The system should discover opportunities by itself; you review results.'/></p></div><a href="/settings" className="btn-secondary"><I18nText zh='高级设置' en='Advanced Settings'/></a></div></section>
  {autopilot&&<AutopilotPanel status={autopilot}/>} 
  <div className="grid gap-4 md:grid-cols-5"><StatCard label="Keywords" value={health.keywords} tone="blue"/><StatCard label="Cards" value={health.cards}/><StatCard label="Action" value={counts.Action} tone="green"/><StatCard label="Watch" value={counts.Watch} tone="amber"/><StatCard label="Reject" value={counts.Reject} tone="rose"/></div>
  <section className="panel"><div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold"><I18nText zh='当前最值得看的机会' en='Current top opportunities'/></h2><a href="/cards" className="btn-secondary"><I18nText zh='查看全部' en='View all'/></a></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{top.length?top.map(c=><OpportunityCardView key={c.id} card={c} compact/>):<div className="rounded-2xl border border-slate-800 bg-slate-950 p-6 text-slate-400"><I18nText zh='还没有 Action/Watch 卡片。开启自动猎手后，系统会自动跑第一轮。' en='No Action/Watch cards yet. Start Autopilot to run the first cycle.'/></div>}</div></section>
 </div>
}
