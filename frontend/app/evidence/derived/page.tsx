import {evidenceApi} from '../../../lib/api'
import {ContextActions} from '../../../components/ContextActions'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const rows = await evidenceApi.derived().catch(() => [])

  return (
    <div className="space-y-6">
      <section className="panel">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Derived Entries</p>
        <h1 className="mt-2 text-3xl font-black text-white">证据新词</h1>
        <p className="mt-2 text-sm text-slate-400">证据系统发现的新词不直接进入关键词库，而是回到入口池重新走质量门。</p>
      </section>
      <section className="panel">
        <div className="space-y-3">
          {rows.map(row => (
            <div key={row.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="font-semibold text-slate-100">{row.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{row.entry_type} · {row.source_role} · {row.status}</div>
                </div>
                <ContextActions actions={[{label:'推送到候选词', actionType:'entry.push', targetType:'candidate_entry', targetId:row.id}]} />
              </div>
            </div>
          ))}
          {!rows.length && <p className="text-sm text-slate-400">暂无证据新词。</p>}
        </div>
      </section>
    </div>
  )
}
