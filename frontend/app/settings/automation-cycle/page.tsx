import {api} from '../../../lib/api'
import {automationCycleApi} from '../../../lib/api'
import {ContextActions} from '../../../components/ContextActions'
import {SettingsForm} from '../../../components/SettingsForm'
import {SettingsHeader} from '../../../components/SettingsHeader'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const [rows, due, runs] = await Promise.all([
    api<any[]>('/api/settings'),
    automationCycleApi.due().catch(() => []),
    automationCycleApi.runs().catch(() => []),
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
      <SettingsForm rows={rows} initialGroup="automation-cycle"/>
    </div>
  )
}
