import {api, Card} from '../../lib/api'
import {OpportunityList} from '../../components/OpportunityList'

export default async function Page(){
 const rows=(await api<Card[]>('/api/cards')).filter(c=>!c.feedback_label)
 return <div className="space-y-6">
  <div>
   <h1 className="text-3xl font-bold">复核队列</h1>
   <p className="mt-2 text-slate-400">默认显示摘要列表。点击标题打开右侧详情抽屉，再做行动 / 观察 / 拒绝 / 屏蔽反馈。</p>
  </div>
  <OpportunityList cards={rows} empty="暂无待复核卡片。" />
 </div>
}
