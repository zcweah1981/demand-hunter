import {api, Card} from '../../lib/api'
import {OpportunityCardView, verdictLabel} from '../../components/OpportunityCard'

export default async function Page(){
 const rows=await api<Card[]>('/api/cards')
 const groups=['Action','Watch','Reject']
 return <div className="space-y-6">
  <div>
   <h1 className="text-3xl font-bold">机会卡</h1>
   <p className="mt-2 text-slate-400">按判断结果分组查看。行动 Action 才进入执行候选；观察 Watch 保留继续跟踪；拒绝 / 屏蔽会训练系统。</p>
  </div>
  {groups.map(g=>{const list=rows.filter(r=>r.verdict===g);return <section className="panel" key={g}>
   <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">{verdictLabel(g)}</h2><span className="badge">{list.length}</span></div>
   <div className="grid gap-4 lg:grid-cols-2">{list.length?list.map(c=><OpportunityCardView key={c.id} card={c}/>):<p className="text-sm text-slate-500">暂无{verdictLabel(g)}卡片。</p>}</div>
  </section>})}
 </div>
}
