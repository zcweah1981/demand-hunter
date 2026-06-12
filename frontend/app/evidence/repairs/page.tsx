import {actionsApi} from '../../../lib/api'
import {ContextActions} from '../../../components/ContextActions'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const rows = await actionsApi.list('?limit=100').catch(() => [])
  const failed = rows.filter(row => row.status === 'failed')

  return (
    <div className="space-y-6">
      <section className="panel">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Repairs</p>
        <h1 className="mt-2 text-3xl font-black text-white">异常修复</h1>
        <p className="mt-2 text-sm text-slate-400">异常对象使用“修复”动作处理；不把排除和暂停混在一起。</p>
      </section>
      <section className="panel">
        <div className="space-y-3">
          {failed.map(row => (
            <div key={row.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="font-semibold text-slate-100">{row.action_type}</div>
                  <div className="mt-1 text-xs text-slate-500">{row.target_type} #{row.target_id}</div>
                  <p className="mt-2 text-sm text-slate-400">{row.reason || '暂无原因'}</p>
                </div>
                <ContextActions actions={[{label:'修复异常', actionType:'repair.action', targetType:row.target_type, targetId:row.target_id}]} />
              </div>
            </div>
          ))}
          {!failed.length && <p className="text-sm text-slate-400">暂无异常。</p>}
        </div>
      </section>
    </div>
  )
}
