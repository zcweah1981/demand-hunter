import {EvidenceTimeline} from '../../../components/EvidenceTimeline'
import {evidenceApi} from '../../../lib/api'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const derived = await evidenceApi.derived().catch(() => [])
  const first = derived[0]

  return (
    <div className="space-y-6">
      <section className="panel">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Evidence Timeline</p>
        <h1 className="mt-2 text-3xl font-black text-white">证据时间线</h1>
        <p className="mt-2 text-sm text-slate-400">每个对象看到的证据不同；时间线展示证据何时出现、为谁服务、为什么关联。</p>
      </section>
      <section className="panel">
        <h2 className="mb-4 text-xl font-bold">{first ? `入口 #${first.id} 的证据` : '示例时间线'}</h2>
        {first ? <EvidenceTimeline targetType="candidate_entry" targetId={first.id} /> : <p className="text-sm text-slate-400">暂无可展示的关联对象。</p>}
      </section>
    </div>
  )
}
