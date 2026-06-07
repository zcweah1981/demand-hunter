import {api} from '../../lib/api'
import {StatCard} from '../../components/StatCard'
import {OpportunityCardView} from '../../components/OpportunityCard'
import {AutopilotPanel} from '../../components/AutopilotPanel'
import {I18nText} from '../../components/I18nText'

export default async function Overview(){
 const [health,cards,runs,autopilot] = await Promise.all([
  api<any>('/api/health'),
  api<any[]>('/api/cards'),
  api<any[]>('/api/runs'),
  api<any>('/api/autopilot/status').catch(()=>null),
 ])
 const counts={Action:cards.filter(c=>c.verdict==='Action').length,Watch:cards.filter(c=>c.verdict==='Watch').length,Reject:cards.filter(c=>c.verdict==='Reject').length,Reviewed:cards.filter(c=>c.feedback_label).length}
 const pending=cards.filter(c=>!c.feedback_label&&c.verdict!=='Reject').slice(0,4)
 const topAction=cards.filter(c=>c.verdict==='Action').slice(0,3)
 const latest=runs[0]
 return <div className="space-y-8">
  <section className="rounded-3xl border border-blue-500/30 bg-gradient-to-br from-blue-950/70 via-slate-950 to-slate-950 p-8 shadow-2xl">
   <div className="flex flex-wrap items-start justify-between gap-6">
    <div>
     <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Overview</p>
     <h1 className="mt-3 text-4xl font-black text-white"><I18nText zh='自动机会发现' en='Automatic Opportunity Discovery'/></h1>
     <p className="mt-3 max-w-3xl text-slate-300"><I18nText zh='这里是主控台：默认自动运转。复杂的四找、导入、跑 SERP、生成卡片都放到后台；你只需要看 Action/Watch，并用复核结果训练下一轮。' en='This is the control center. Four-Find, import, SERP checks, and card generation run in the background; you mainly review Action/Watch results.'/></p>
    </div>
    <a className="btn-secondary" href="/settings"><I18nText zh='高级设置' en='Advanced Settings'/></a>
   </div>
  </section>

  {autopilot&&<AutopilotPanel status={autopilot}/>} 

  <div className="grid gap-4 md:grid-cols-6"><StatCard label="Keywords" value={health.keywords} tone="blue"/><StatCard label="Cards" value={health.cards}/><StatCard label="Action" value={counts.Action} tone="green"/><StatCard label="Watch" value={counts.Watch} tone="amber"/><StatCard label="Reject" value={counts.Reject} tone="rose"/><StatCard label="Reviewed" value={counts.Reviewed} hint={`${cards.length-counts.Reviewed} pending`}/></div>

  <section className="grid gap-6 xl:grid-cols-2">
   <div className="panel"><div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold"><I18nText zh='待复核：只需判断' en='Pending review: just decide'/></h2><a href="/review" className="btn-secondary">Review</a></div><div className="space-y-4">{pending.length?pending.map(c=><OpportunityCardView key={c.id} card={c} compact/>):<p className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">暂无待复核 Action/Watch。系统会继续自动寻找。</p>}</div></div>
   <div className="panel"><div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold"><I18nText zh='Action 候选' en='Action Candidates'/></h2><a href="/cards" className="btn-secondary">All cards</a></div><div className="space-y-4">{topAction.length?topAction.map(c=><OpportunityCardView key={c.id} card={c} compact/>):<p className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">暂无 Action。保持严格是对的，系统会继续跑；你可以从 Watch 里筛。</p>}</div></div>
  </section>

  <section className="panel"><h2 className="mb-4 text-xl font-bold"><I18nText zh='最近一次后台运行' en='Latest background run'/></h2>{latest?<pre className="rounded-2xl bg-slate-950 p-4 text-xs text-slate-300">{JSON.stringify(latest,null,2)}</pre>:<p className="text-slate-400">还没有运行记录。</p>}</section>
 </div>
}
