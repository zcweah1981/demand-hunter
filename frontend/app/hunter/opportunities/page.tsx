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
 const filtered = rows.filter((r:any)=>{
  const finalVerdict = r.feedback_label || r.verdict
  if(verdict==='All') return true
  if(verdict==='Pending') return !r.feedback_label
  if(finalVerdict!==verdict) return false
  if(verdict==='Action') return Number(r.score||0) >= minAction
  return true
 }).map((r:any)=>r.feedback_label ? {...r, verdict:r.feedback_label} : r)
 const byGroup=new Map<string,any>()
 for(const r of filtered){
  const g=r.opportunity_group?.group_id || `card-${r.id}`
  const prev=byGroup.get(g)
  const rank=(x:any)=>((x.feedback_label||x.verdict)==='Action'?4:(x.feedback_label||x.verdict)==='Watch'?3:1)*1000 + Number(x.score||0) + Number(x.opportunity_group?.probability||0)*100
  if(!prev || rank(r)>rank(prev)) byGroup.set(g,r)
 }
 const cards=Array.from(byGroup.values()).sort((a:any,b:any)=>Number(b.opportunity_group?.probability||0)-Number(a.opportunity_group?.probability||0) || Number(b.score||0)-Number(a.score||0))
 const title=verdict==='All'?'全部机会':verdict==='Pending'?'待复核机会':verdictLabel(verdict)
 return <div className="space-y-6">
  <div className="flex flex-wrap items-start justify-between gap-3">
   <div>
    <h1 className="text-3xl font-bold">机会</h1>
    <p className="mt-2 text-slate-400">机会、复核、行动候选合并到这里。列表按“机会组”去重展示：相同/相似关键词作为一个机会的证据链，不再并列成多条机会。</p>
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
