import {ContextActions} from '../../../components/ContextActions'
import {discoveryApi} from '../../../lib/api'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const rows = await discoveryApi.entries('?limit=100').catch(() => [])
  const candidateRows = rows.filter(row => row.entry_type === 'demand' || row.entry_type === 'keyword' || row.status === 'scored')

  return (
    <div className="space-y-6">
      <section className="panel">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Candidate Keywords</p>
        <h1 className="mt-2 text-3xl font-black text-white">候选关键词</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">这里承接需求入口和趋势转译结果。需求质量分与趋势质量分分开计算，只有通过关键词质量门后才进入正式关键词库。</p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="card"><div className="text-sm text-slate-400">候选</div><div className="mt-2 text-3xl font-black text-white">{candidateRows.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">待补证</div><div className="mt-2 text-3xl font-black text-white">{candidateRows.filter(row => row.status === 'needs_evidence').length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">已评分</div><div className="mt-2 text-3xl font-black text-white">{candidateRows.filter(row => row.status === 'scored').length}</div></div>
      </section>

      <section className="panel">
        <div className="space-y-3">
          {candidateRows.map(row => (
            <div key={row.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-base font-semibold text-slate-100">{row.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{row.source_role || row.source || 'unknown'} · {row.status}</div>
                </div>
                <ContextActions actions={[
                  {label:'重新计算', actionType:'candidate.rescore', targetType:'candidate_entry', targetId:row.id, variant:'secondary'},
                  {label:'补证据', actionType:'candidate.collect_evidence', targetType:'candidate_entry', targetId:row.id},
                ]} />
              </div>
              <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3"><span className="text-slate-500">需求分</span><div className="mt-1 font-mono text-blue-200">{row.demand_score?.toFixed?.(1) ?? '-'}</div></div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3"><span className="text-slate-500">趋势分</span><div className="mt-1 font-mono text-blue-200">{row.trend_score?.toFixed?.(1) ?? '-'}</div></div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3"><span className="text-slate-500">质量分</span><div className="mt-1 font-mono text-blue-200">{row.quality_score?.toFixed?.(1) ?? '-'}</div></div>
              </div>
            </div>
          ))}
          {!candidateRows.length && <p className="text-sm text-slate-400">暂无候选关键词。</p>}
        </div>
      </section>
    </div>
  )
}
