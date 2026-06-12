import Link from 'next/link'
import {actionsApi, automationCycleApi, evidenceApi} from '../../lib/api'
import {ContextActions} from '../../components/ContextActions'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const [evidence, derived, actions, due] = await Promise.all([
    evidenceApi.list('?limit=80').catch(() => []),
    evidenceApi.derived().catch(() => []),
    actionsApi.list('?limit=80').catch(() => []),
    automationCycleApi.due().catch(() => []),
  ])
  const failed = actions.filter(row => row.status === 'failed')

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-7 shadow-2xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Evidence System</p>
            <h1 className="mt-3 text-4xl font-black text-white">证据系统</h1>
            <p className="mt-3 max-w-3xl text-slate-300">证据只保存客观事实；通过服务关系被入口、关键词、机会和推进项目复用。</p>
          </div>
          <ContextActions actions={[{label:'运行一轮', actionType:'automation.run', targetType:'system', targetId:'automation_cycle'}]} />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="card"><div className="text-sm text-slate-400">证据</div><div className="mt-2 text-3xl font-black text-white">{evidence.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">证据新词</div><div className="mt-2 text-3xl font-black text-white">{derived.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">待执行</div><div className="mt-2 text-3xl font-black text-white">{due.length}</div></div>
        <div className="card"><div className="text-sm text-slate-400">异常</div><div className="mt-2 text-3xl font-black text-white">{failed.length}</div></div>
      </section>

      <section className="grid gap-5 xl:grid-cols-3">
        <Link className="panel no-underline transition hover:border-blue-500/50" href="/evidence/models"><h2 className="text-xl font-bold text-white">证据模型</h2><p className="mt-2 text-sm text-slate-400">从四找、趋势和变化监控模型查看证据如何产生入口、关键词和机会。</p></Link>
        <Link className="panel no-underline transition hover:border-blue-500/50" href="/evidence/tasks"><h2 className="text-xl font-bold text-white">补证任务</h2><p className="mt-2 text-sm text-slate-400">为缺口对象补充来源、SERP、社区或变更证据。</p></Link>
        <Link className="panel no-underline transition hover:border-blue-500/50" href="/evidence/derived"><h2 className="text-xl font-bold text-white">证据新词</h2><p className="mt-2 text-sm text-slate-400">sitemap、changelog、社区变化产生的新机会词先回到入口池。</p></Link>
        <Link className="panel no-underline transition hover:border-blue-500/50" href="/evidence/repairs"><h2 className="text-xl font-bold text-white">异常修复</h2><p className="mt-2 text-sm text-slate-400">失败和关联错误使用修复动作，不隐藏问题。</p></Link>
      </section>

      <section className="panel">
        <h2 className="mb-4 text-xl font-bold">最新证据</h2>
        <div className="space-y-3">
          {evidence.slice(0, 8).map(item => (
            <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold text-slate-100">{item.title || item.source_name || `证据 #${item.id}`}</h3>
                <span className="badge">{item.source_type}</span>
              </div>
              <p className="mt-2 text-sm text-slate-400">{item.summary || item.raw_excerpt || '暂无摘要'}</p>
            </div>
          ))}
          {!evidence.length && <p className="text-sm text-slate-400">暂无证据。</p>}
        </div>
      </section>
    </div>
  )
}
