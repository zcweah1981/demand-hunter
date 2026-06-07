import {api, Card} from '../../lib/api'
import {OpportunityCardView} from '../../components/OpportunityCard'

export default async function Page(){
 const rows=(await api<Card[]>('/api/cards')).filter(c=>!c.feedback_label)
 return <div className="space-y-6">
  <div>
   <h1 className="text-3xl font-bold">复核队列</h1>
   <p className="mt-2 text-slate-400">这是训练入口。不要放过垃圾卡：点“拒绝 / 屏蔽”会影响下一轮找词和过滤。</p>
  </div>
  <div className="grid gap-4 lg:grid-cols-2">{rows.length?rows.map(c=><OpportunityCardView card={c} key={c.id}/>):<div className="panel text-slate-400">暂无待复核卡片。</div>}</div>
 </div>
}
