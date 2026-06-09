import {api, Card} from '../../../lib/api'
import {OpportunityList} from '../../../components/OpportunityList'
import {verdictLabel} from '../../../components/OpportunityCard'
import {ExportActionsButton} from '../../../components/Actions'

const VERDICTS=['All','Pending','Action','Watch','Reject','Block']

export default async function Page({searchParams}:{searchParams?:Promise<Record<string,string|string[]|undefined>>}){
 const params=(await (searchParams||Promise.resolve({}))) as Record<string,string|string[]|undefined>
 const raw=Array.isArray(params.verdict)?params.verdict[0]:params.verdict
 const verdict=VERDICTS.includes(raw||'') ? (raw as string) : 'Pending'
 const [rows, settings] = await Promise.all([
  api<Card[]>('/api/cards'),
  api<any[]>('/api/settings').catch(()=>[]),
 ])
 const minAction = Number(settings.find((s:any)=>s.key==='MIN_ACTION_SCORE')?.value || 74)
 const cards = rows.filter((r:any)=>{
  const finalVerdict = r.feedback_label || r.verdict
  if(verdict==='All') return true
  if(verdict==='Pending') return !r.feedback_label
  if(finalVerdict!==verdict) return false
  if(verdict==='Action') return Number(r.score||0) >= minAction
  return true
 }).map((r:any)=>r.feedback_label ? {...r, verdict:r.feedback_label} : r)
 const title=verdict==='All'?'全部机会':verdict==='Pending'?'待复核机会':verdictLabel(verdict)
 return <div className="space-y-6">
  <div className="flex flex-wrap items-start justify-between gap-3">
   <div>
    <h1 className="text-3xl font-bold">机会</h1>
    <p className="mt-2 text-slate-400">机会、复核、行动候选合并到这里。每张卡按“相似机会组”展示证据链和组概率，可单条或批量复核。</p>
    <p className="mt-1 text-xs text-slate-500">当前 Action 分数门槛：{minAction}</p>
   </div>
   <div className="flex flex-wrap gap-2">
    <ExportActionsButton/>
    {VERDICTS.map(v=><a key={v} className={verdict===v?'btn':'btn-secondary'} href={`/hunter/opportunities?verdict=${v}`}>{v==='All'?'全部':v==='Pending'?'待复核':verdictLabel(v)}</a>)}
   </div>
  </div>
  <section className="panel">
   <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">{title}</h2><span className="badge">{cards.length}</span></div>
   <OpportunityList cards={cards} empty={`暂无${title}。`} showVerdictFilter={false} mode="review" enableBulk />
  </section>
 </div>
}
