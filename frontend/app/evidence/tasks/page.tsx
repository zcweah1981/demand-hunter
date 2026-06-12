import {actionsApi, automationCycleApi} from '../../../lib/api'
import {ContextActions} from '../../../components/ContextActions'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const [actions, due] = await Promise.all([
    actionsApi.list('?limit=100').catch(() => []),
    automationCycleApi.due().catch(() => []),
  ])
  const evidenceActions = actions.filter(row => row.action_type.includes('evidence') || row.reason.includes('证据'))

  return (
    <div className="space-y-6">
      <section className="panel">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Evidence Tasks</p>
            <h1 className="mt-2 text-3xl font-black text-white">补证任务</h1>
            <p className="mt-2 text-sm text-slate-400">补证动作按对象触发，页面只保留当前语境需要的操作。</p>
          </div>
          <ContextActions actions={[{label:'补证据', actionType:'evidence.collect', targetType:'evidence_task', targetId:'manual'}]} />
        </div>
      </section>
      <section className="panel">
        <h2 className="mb-4 text-xl font-bold">到期动作</h2>
        <div className="space-y-3">
          {due.map((item, index) => (
            <div key={`${item.action}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="font-semibold text-slate-100">{item.action}</div>
              <div className="mt-1 text-xs text-slate-500">{item.target_type} #{item.target_id}</div>
            </div>
          ))}
          {!due.length && <p className="text-sm text-slate-400">暂无到期动作。</p>}
        </div>
      </section>
      <section className="panel">
        <h2 className="mb-4 text-xl font-bold">已提交补证请求</h2>
        <div className="space-y-3">
          {evidenceActions.map(row => (
            <div key={row.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="font-semibold text-slate-100">{row.action_type}</span>
                <span className="badge">{row.status}</span>
              </div>
              <p className="mt-2 text-sm text-slate-400">{row.reason || `${row.target_type} #${row.target_id}`}</p>
            </div>
          ))}
          {!evidenceActions.length && <p className="text-sm text-slate-400">暂无补证请求。</p>}
        </div>
      </section>
    </div>
  )
}
