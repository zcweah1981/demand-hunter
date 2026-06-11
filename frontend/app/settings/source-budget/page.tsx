import {api} from '../../../lib/api'
import {SettingsForm} from '../../../components/SettingsForm'
import {SettingsHeader} from '../../../components/SettingsHeader'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const [rows, roi] = await Promise.all([
    api<any[]>('/api/settings'),
    api<any>('/api/collectors/source-roi').catch(() => null),
  ])
  const items = Array.isArray(roi) ? roi : (roi?.items || [])
  return (
    <div className="space-y-6">
      <SettingsHeader group="source-budget"/>
      <section className="panel">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-xl font-bold">来源表现</h2>
          <span className="badge">{items.length}</span>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.slice(0, 12).map((item:any, index:number) => (
            <div key={item.source || item.name || index} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="font-semibold text-slate-100">{item.source || item.name || `来源 #${index + 1}`}</div>
              <div className="mt-2 text-sm text-slate-400">success {item.success_count ?? item.success ?? 0} · reject {item.reject_count ?? item.reject ?? 0}</div>
            </div>
          ))}
          {!items.length && <p className="text-sm text-slate-400">暂无来源 ROI 数据。</p>}
        </div>
      </section>
      <SettingsForm rows={rows} initialGroup="source-budget"/>
    </div>
  )
}
