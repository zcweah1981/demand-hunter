import {actionsApi, api, automationCycleApi} from '../../../lib/api'
import {ContextActions} from '../../../components/ContextActions'
import {SettingsForm} from '../../../components/SettingsForm'
import {SettingsHeader} from '../../../components/SettingsHeader'

export const dynamic = 'force-dynamic'

function statusText(status: string) {
  if (status === 'running') return '运行中'
  if (status === 'pending') return '排队中'
  if (status === 'success') return '完成'
  if (status === 'failed') return '失败'
  if (status === 'needs_confirmation') return '需确认'
  if (status === 'cancelled') return '已取消'
  return status || '未知'
}

function timeText(value?: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function errorText(row: any) {
  const err = row.error_json
  if (!err || (typeof err === 'object' && !Object.keys(err).length)) return '-'
  if (typeof err === 'string') return err
  if (Array.isArray(err.errors) && err.errors.length) return err.errors.map((item: any) => item.message || item.error || String(item)).join('；')
  return err.summary || err.reason || '-'
}

function runSummary(row: any) {
  const summary = row.summary || {}
  return {
    stage: summary.stage || row.status || 'unknown',
    processed: summary.processed ?? summary.executed ?? 0,
    total: summary.actions_collected ?? 0,
    success: summary.executed ?? 0,
    failed: summary.failed ?? 0,
  }
}

export default async function Page() {
  const [rows, due, runs, actions] = await Promise.all([
    api<any[]>('/api/settings'),
    automationCycleApi.due().catch(() => []),
    automationCycleApi.runs().catch(() => []),
    actionsApi.list('?limit=20').catch(() => []),
  ])
  return (
    <div className="space-y-6">
      <SettingsHeader group="automation-cycle"/>
      <section className="grid gap-4 md:grid-cols-3">
        <div className="card"><div className="text-sm text-slate-400">待执行动作</div><div className="mt-2 text-3xl font-black text-white">{due.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">最近运行</div><div className="mt-2 text-3xl font-black text-white">{runs.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">周期模式</div><div className="mt-2 text-lg font-bold text-white">统一周期</div></div>
      </section>
      <section className="panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="text-xl font-bold">手动运行</h2><p className="mt-1 text-sm text-slate-400">自动周期会执行所有到期动作；人工按钮只用于立即触发一轮。</p></div>
          <ContextActions actions={[{label:'运行一轮', actionType:'automation.run', targetType:'system', targetId:'automation_cycle'}]} />
        </div>
      </section>
      <section className="panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold">最近周期</h2>
            <p className="mt-1 text-sm text-slate-400">这里展示自动和手动触发的统一周期进度。</p>
          </div>
          <span className="badge">{runs.length} 轮</span>
        </div>
        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/80 text-slate-500">
              <tr>
                <th className="px-4 py-3">批次</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">阶段</th>
                <th className="px-4 py-3">进度</th>
                <th className="px-4 py-3">成功</th>
                <th className="px-4 py-3">失败</th>
                <th className="px-4 py-3">开始 / 结束</th>
              </tr>
            </thead>
            <tbody>
              {runs.slice(0, 8).map(row => {
                const summary = runSummary(row)
                return (
                  <tr key={row.id} className="border-t border-slate-800">
                    <td className="px-4 py-3 font-semibold text-slate-100">#{row.id}</td>
                    <td className="px-4 py-3"><span className="badge">{statusText(row.status)}</span></td>
                    <td className="px-4 py-3 text-slate-300">{summary.stage}</td>
                    <td className="px-4 py-3 text-slate-300">{summary.processed}/{summary.total}</td>
                    <td className="px-4 py-3 text-emerald-300">{summary.success}</td>
                    <td className="px-4 py-3 text-amber-300">{summary.failed}</td>
                    <td className="px-4 py-3 text-slate-400">{timeText(row.started_at)} / {timeText(row.finished_at)}</td>
                  </tr>
                )
              })}
              {!runs.length && (
                <tr>
                  <td className="px-4 py-6 text-slate-400" colSpan={7}>暂无周期记录。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold">最近动作</h2>
            <p className="mt-1 text-sm text-slate-400">手动和自动都会写入同一套动作状态。</p>
          </div>
          <span className="badge">{actions.length} 项</span>
        </div>
        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/80 text-slate-500">
              <tr>
                <th className="px-4 py-3">动作</th>
                <th className="px-4 py-3">对象</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">运行归属</th>
                <th className="px-4 py-3">来源</th>
                <th className="px-4 py-3">开始 / 结束</th>
                <th className="px-4 py-3">异常</th>
              </tr>
            </thead>
            <tbody>
              {actions.map(row => (
                <tr key={row.id} className="border-t border-slate-800">
                  <td className="px-4 py-3 font-semibold text-slate-100">{row.action_type}</td>
                  <td className="px-4 py-3 text-slate-300">{row.target_type} #{row.target_id}</td>
                  <td className="px-4 py-3"><span className="badge">{statusText(row.status)}</span></td>
                  <td className="px-4 py-3 text-slate-400">{row.run_id ? `#${row.run_id}` : '-'}</td>
                  <td className="px-4 py-3 text-slate-400">{row.requested_by || 'system'}</td>
                  <td className="px-4 py-3 text-slate-400">{timeText(row.started_at || row.created_at)} / {timeText(row.finished_at || row.executed_at)}</td>
                  <td className="max-w-sm truncate px-4 py-3 text-slate-400">{errorText(row)}</td>
                </tr>
              ))}
              {!actions.length && (
                <tr>
                  <td className="px-4 py-6 text-slate-400" colSpan={7}>暂无动作记录。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <SettingsForm rows={rows} initialGroup="automation-cycle"/>
    </div>
  )
}
