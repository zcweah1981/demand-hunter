import {api, Card} from '../../lib/api'
import {OpportunityList} from '../../components/OpportunityList'
import {verdictLabel} from '../../components/OpportunityCard'

export default async function Page(){
 const rows=await api<Card[]>('/api/cards')
 const groups=['Action','Watch','Reject']
 return <div className="space-y-6">
  <div>
   <h1 className="text-3xl font-bold">机会卡</h1>
   <p className="mt-2 text-slate-400">默认按判断结果分组显示摘要列表。点击标题打开右侧抽屉查看完整分析。</p>
  </div>
  {groups.map(g=>{const list=rows.filter(r=>r.verdict===g);return <section className="panel" key={g}>
   <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">{verdictLabel(g)}</h2><span className="badge">{list.length}</span></div>
   <OpportunityList cards={list} empty={`暂无${verdictLabel(g)}卡片。`} showVerdictFilter={false} />
  </section>})}
 </div>
}
