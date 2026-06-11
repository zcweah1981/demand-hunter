import Link from 'next/link'
import {automationCycleApi, discoveryApi, evidenceApi} from '../../../lib/api'
import {ContextActions} from '../../../components/ContextActions'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const [entries, evidence, due] = await Promise.all([
    discoveryApi.entries('?limit=40').catch(() => []),
    evidenceApi.list('?limit=40').catch(() => []),
    automationCycleApi.due().catch(() => []),
  ])
  const demandEntries = entries.filter(row => row.entry_type === 'demand')
  const trendEntries = entries.filter(row => row.entry_type === 'trend')
  const needsEvidence = entries.filter(row => row.status === 'needs_evidence')

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-7 shadow-2xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Opportunity Discovery</p>
            <h1 className="mt-3 text-4xl font-black text-white">机会发现</h1>
            <p className="mt-3 max-w-3xl text-slate-300">入口先进入候选池；需求入口和趋势入口分开评分，达标后再进入关键词库。</p>
          </div>
          <ContextActions actions={[{label:'运行一轮', actionType:'automation.run', targetType:'system', targetId:'automation_cycle'}]} />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="card"><div className="text-sm text-slate-400">入口池</div><div className="mt-2 text-3xl font-black text-white">{entries.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">需求入口</div><div className="mt-2 text-3xl font-black text-white">{demandEntries.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">趋势入口</div><div className="mt-2 text-3xl font-black text-white">{trendEntries.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">待补证</div><div className="mt-2 text-3xl font-black text-white">{needsEvidence.length}</div></div>
      </section>

      <section className="grid gap-5 xl:grid-cols-3">
        <Link className="panel no-underline transition hover:border-blue-500/50" href="/discovery/entries">
          <h2 className="text-xl font-bold text-white">入口池</h2>
          <p className="mt-2 text-sm text-slate-400">承接搜索需求、趋势实体、来源监控产生的新入口。</p>
        </Link>
        <Link className="panel no-underline transition hover:border-blue-500/50" href="/discovery/candidate-keywords">
          <h2 className="text-xl font-bold text-white">候选关键词</h2>
          <p className="mt-2 text-sm text-slate-400">趋势转译后的关键词和需求入口在这里进入质量门。</p>
        </Link>
        <Link className="panel no-underline transition hover:border-blue-500/50" href="/evidence">
          <h2 className="text-xl font-bold text-white">证据系统</h2>
          <p className="mt-2 text-sm text-slate-400">证据保持客观，通过关联关系服务入口、关键词和机会。</p>
        </Link>
      </section>

      <section className="panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-bold">本轮待执行</h2>
          <span className="badge">{due.length} 项</span>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {due.slice(0, 8).map((item, index) => (
            <div key={`${item.kind}-${item.target_type}-${item.target_id}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="text-sm font-semibold text-slate-100">{item.action}</div>
              <div className="mt-1 text-xs text-slate-500">{item.target_type} #{item.target_id}</div>
            </div>
          ))}
          {!due.length && <p className="text-sm text-slate-400">暂无到期动作。</p>}
        </div>
      </section>

      <section className="panel">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-xl font-bold">最新客观证据</h2>
          <span className="badge">{evidence.length}</span>
        </div>
        <div className="space-y-3">
          {evidence.slice(0, 5).map(item => (
            <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="text-sm font-semibold text-slate-100">{item.title || item.source_name || `证据 #${item.id}`}</div>
              <p className="mt-1 text-sm text-slate-400">{item.summary || item.raw_excerpt || '暂无摘要'}</p>
            </div>
          ))}
          {!evidence.length && <p className="text-sm text-slate-400">暂无证据。</p>}
        </div>
      </section>
    </div>
  )
}
