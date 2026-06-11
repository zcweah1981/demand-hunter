import {ContextActions} from '../../../components/ContextActions'
import {discoveryApi} from '../../../lib/api'

export const dynamic = 'force-dynamic'

function score(value?: number) {
  if (typeof value !== 'number') return '-'
  return value.toFixed(1)
}

export default async function Page() {
  const rows = await discoveryApi.entries('?limit=100').catch(() => [])

  return (
    <div className="space-y-6">
      <section className="panel">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Candidate Entries</p>
            <h1 className="mt-2 text-3xl font-black text-white">入口池</h1>
            <p className="mt-2 text-sm text-slate-400">采集器、监控和证据系统只产生入口；入口需要评分、补证和转译后才进入关键词库。</p>
          </div>
          <ContextActions actions={[{label:'手动抓取', actionType:'manual.collect', targetType:'entry_pool', targetId:'all'}]} />
        </div>
      </section>

      <section className="panel">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="table-head">
              <tr>
                <th className="py-3 text-left">入口</th>
                <th className="py-3 text-left">类型</th>
                <th className="py-3 text-left">来源</th>
                <th className="py-3 text-left">状态</th>
                <th className="py-3 text-left">趋势分</th>
                <th className="py-3 text-left">需求分</th>
                <th className="py-3 text-left">操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.id} className="border-t border-slate-800">
                  <td className="max-w-[260px] truncate py-3 font-medium text-slate-100">{row.name}</td>
                  <td className="py-3"><span className="badge">{row.entry_type}</span></td>
                  <td className="max-w-[180px] truncate py-3 text-slate-400">{row.source_role || row.source || '-'}</td>
                  <td className="py-3 text-slate-400">{row.status}</td>
                  <td className="py-3 font-mono text-blue-200">{score(row.trend_score)}</td>
                  <td className="py-3 font-mono text-blue-200">{score(row.demand_score)}</td>
                  <td className="py-3">
                    <ContextActions actions={[{label:'推送到候选词', actionType:'entry.push', targetType:'candidate_entry', targetId:row.id, variant:'secondary'}]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && <p className="py-6 text-sm text-slate-400">暂无入口。</p>}
        </div>
      </section>
    </div>
  )
}
