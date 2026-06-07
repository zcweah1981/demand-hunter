import {api, Card} from '../../lib/api'
import {OpportunityList} from '../../components/OpportunityList'

export default async function Page(){
 const [rows, settings] = await Promise.all([
  api<Card[]>('/api/cards'),
  api<any[]>('/api/settings').catch(()=>[]),
 ])
 const minAction = Number(settings.find((s:any)=>s.key==='MIN_ACTION_SCORE')?.value || 74)
 const opportunities = rows.filter(r=>r.verdict==='Action' && Number(r.score||0) >= minAction)
 return <div className="space-y-6">
  <div>
   <h1 className="text-3xl font-bold">机会</h1>
   <p className="mt-2 text-slate-400">这里只显示达到 Action 门槛的执行候选。观察 Watch、拒绝 Reject 和低于分数门槛的卡片只保留在复核队列里，不进入机会列表。</p>
   <p className="mt-1 text-xs text-slate-500">当前 Action 分数门槛：{minAction}</p>
  </div>
  <section className="panel">
   <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">行动机会 <span className="text-slate-500">Action</span></h2><span className="badge">{opportunities.length}</span></div>
   <OpportunityList cards={opportunities} empty="暂无达到 Action 门槛的机会。" showVerdictFilter={false} />
  </section>
 </div>
}
