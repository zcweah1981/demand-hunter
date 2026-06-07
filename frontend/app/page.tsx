import {api} from '../lib/api'
import {OpportunityCardView} from '../components/OpportunityCard'
import {AutopilotPanel} from '../components/AutopilotPanel'
import {I18nText} from '../components/I18nText'

export default async function Page(){
 const [cards,autopilot] = await Promise.all([
  api<any[]>('/api/cards'),
  api<any>('/api/autopilot/status').catch(()=>null),
 ])
 const review=cards.filter(c=>!c.feedback_label&&c.verdict!=='Reject').slice(0,4)
 const actions=cards.filter(c=>c.verdict==='Action').slice(0,4)
 return <div className="space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl">
   <div className="flex flex-wrap items-start justify-between gap-4">
    <div>
     <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Demand Hunter</p>
     <h1 className="mt-3 text-4xl font-black text-white"><I18nText zh='自动机会猎手' en='Autopilot Opportunity Hunter'/></h1>
     <p className="mt-3 max-w-2xl text-slate-300"><I18nText zh='系统自动找机会。你只需要看结果、做复核。' en='The system hunts automatically. You only review results.'/></p>
    </div>
    <a href="/settings" className="btn-secondary"><I18nText zh='设置' en='Settings'/></a>
   </div>
  </section>

  {autopilot&&<AutopilotPanel status={autopilot}/>} 

  <section className="grid gap-6 xl:grid-cols-2">
   <div className="panel">
    <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold"><I18nText zh='待复核' en='To review'/></h2><a href="/review" className="btn-secondary"><I18nText zh='全部复核' en='Review all'/></a></div>
    <div className="space-y-4">{review.length?review.map(c=><OpportunityCardView key={c.id} card={c} compact/>):<p className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">暂无待复核卡片。</p>}</div>
   </div>
   <div className="panel">
    <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">Action</h2><a href="/cards" className="btn-secondary"><I18nText zh='全部卡片' en='All cards'/></a></div>
    <div className="space-y-4">{actions.length?actions.map(c=><OpportunityCardView key={c.id} card={c} compact/>):<p className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">暂无 Action。保持严格，系统会继续找。</p>}</div>
   </div>
  </section>
 </div>
}
