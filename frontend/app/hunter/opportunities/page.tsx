import {api, Card} from '../../../lib/api'
import {OpportunityList} from '../../../components/OpportunityList'
import {verdictLabel} from '../../../components/OpportunityCard'
import {ExportActionsButton} from '../../../components/Actions'

const VERDICTS=['All','Adopted','Action','Watch','Reject','Block']
function tabClass(v:string, active:boolean){const tone:any={All:'border-slate-700 bg-slate-800 text-slate-100',Adopted:'border-purple-500/50 bg-purple-500/10 text-purple-200',Action:'border-emerald-500/50 bg-emerald-500/10 text-emerald-200',Watch:'border-blue-500/50 bg-blue-500/10 text-blue-200',Reject:'border-amber-500/50 bg-amber-500/10 text-amber-200',Block:'border-rose-500/50 bg-rose-500/10 text-rose-200'}; return `rounded-xl border px-3 py-2 text-sm no-underline transition ${tone[v]||tone.All} ${active?'ring-2 ring-white/30':'opacity-80 hover:opacity-100'}`}

export default async function Page({searchParams}:{searchParams?:Promise<Record<string,string|string[]|undefined>>}){
 const params=(await (searchParams||Promise.resolve({}))) as Record<string,string|string[]|undefined>
 const raw=Array.isArray(params.verdict)?params.verdict[0]:params.verdict
 const verdict=VERDICTS.includes(raw||'') ? (raw as string) : 'All'
 const [cards, settings] = await Promise.all([
 api<Card[]>(`/api/cards/groups?verdict=${verdict}`),
  api<any[]>('/api/settings').catch(()=>[]),
 ])
 const minAction = Number(settings.find((s:any)=>s.key==='MIN_ACTION_SCORE')?.value || 74)
 const title=verdict==='All'?'全部机会':verdictLabel(verdict)
 return <div className="space-y-6">
  <div className="flex flex-wrap items-start justify-between gap-3">
   <div>
    <h1 className="text-3xl font-bold">机会</h1>
    <p className="mt-2 text-slate-400">这里不再是“复核队列”，而是机会状态管理。每个机会组可以在 Watch / Action / Adopted / Reject / Block 之间切换。</p>
    <p className="mt-1 text-xs text-slate-500">当前 Action 分数门槛：{minAction}</p>
   </div>
   <div className="flex flex-wrap gap-2">
    <ExportActionsButton/>
    {VERDICTS.map(v=><a key={v} className={tabClass(v, verdict===v)} href={`/hunter/opportunities?verdict=${v}`}>{v==='All'?'全部':verdictLabel(v)}</a>)}
   </div>
  </div>
  <section className="panel">
   <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">{title}</h2><span className="badge">{cards.length}</span></div>
   <details className="mb-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400">
    <summary className="cursor-pointer font-semibold text-slate-300 hover:text-white">机会组规则 / 为什么有些关键词会合并</summary>
    <div className="mt-3 grid gap-3 md:grid-cols-3">
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-100">同组</b><p className="mt-1">同一个用户任务和商业入口，例如 compliance cost calculator 与 ai compliance cost calculator。</p></div>
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-100">不同组</b><p className="mt-1">不同工作流/ICP/购买触发，例如 compliance cost calculator 与 call center compliance tracker。</p></div>
     <div className="rounded-xl bg-slate-900 p-3"><b className="text-slate-100">组概率</b><p className="mt-1">综合变体数、来源数、正向/负向卡和人工状态；概率越高，说明证据链越集中。</p></div>
    </div>
   </details>
   <OpportunityList cards={cards} empty={`暂无${title}。`} showVerdictFilter={false} mode="review" enableBulk currentFilter={verdict}/>
  </section>
 </div>
}
