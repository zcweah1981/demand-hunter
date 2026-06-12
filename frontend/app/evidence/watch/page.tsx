import {automationCycleApi} from '../../../lib/api'
import {ContextActions} from '../../../components/ContextActions'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const due = await automationCycleApi.due().catch(() => [])
  const watchItems = due.filter(item => item.target_type.includes('watch') || item.kind.includes('watch'))

  return (
    <div className="space-y-6">
      <section className="panel">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Watch Targets</p>
            <h1 className="mt-2 text-3xl font-black text-white">监控对象</h1>
            <p className="mt-2 text-sm text-slate-400">竞品、趋势实体、定价页、changelog、社区和 sitemap 都作为监控对象进入统一周期。</p>
          </div>
          <ContextActions actions={[{label:'重新验证', actionType:'watch.verify', targetType:'watch_target', targetId:'all'}]} />
        </div>
      </section>
      <section className="panel">
        <div className="space-y-3">
          {watchItems.map((item, index) => (
            <div key={`${item.target_type}-${item.target_id}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="font-semibold text-slate-100">{item.target_type} #{item.target_id}</div>
              <p className="mt-1 text-sm text-slate-400">{item.reason || item.action}</p>
            </div>
          ))}
          {!watchItems.length && <p className="text-sm text-slate-400">暂无到期监控对象。</p>}
        </div>
      </section>
    </div>
  )
}
