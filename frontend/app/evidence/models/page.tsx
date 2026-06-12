import Link from 'next/link'
import {evidenceApi, EvidenceModel} from '../../../lib/api'

export const dynamic = 'force-dynamic'

const groups = ['四找模型', '趋势模型', '监控模型']

function stat(model:EvidenceModel, key:keyof EvidenceModel['stats']){
  return model.stats?.[key] ?? 0
}

function Stat({label,value}:{label:string;value:any}){
  return <div className="rounded-xl bg-slate-950 p-3"><div className="text-xs text-slate-500">{label}</div><b className="text-2xl text-white">{value}</b></div>
}

function ModelCard({model}:{model:EvidenceModel}){
  return (
    <Link href={`/evidence/models/${model.id}`} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 no-underline transition hover:border-blue-500/50">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-blue-300">{model.group}</div>
          <h3 className="mt-2 text-xl font-bold text-white">{model.name}</h3>
        </div>
        <span className="badge">{stat(model,'runs')} 轮</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-300">{model.purpose}</p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{model.loop}</p>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <Stat label="证据" value={stat(model,'evidence')} />
        <Stat label="入口" value={stat(model,'entries')} />
        <Stat label="候选词" value={stat(model,'candidate_keywords')} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <Stat label="关键词" value={stat(model,'keywords')} />
        <Stat label="机会" value={stat(model,'cards')} />
        <Stat label="异常" value={stat(model,'errors')} />
      </div>
    </Link>
  )
}

export default async function Page() {
  const data = await evidenceApi.models().catch(() => ({items: [], totals: {runs:0,evidence:0,entries:0,candidate_keywords:0,keywords:0,cards:0,errors:0}}))
  const items = data.items || []

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-7 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Evidence Models</p>
        <h1 className="mt-3 text-4xl font-black text-white">证据模型</h1>
        <p className="mt-3 max-w-4xl text-slate-300">先有模型，再按模型找证据；证据产生入口、候选关键词和机会，最后回到模型表现里形成闭环。</p>
      </section>

      <section className="grid gap-4 md:grid-cols-6">
        <Stat label="模型" value={items.length} />
        <Stat label="运行" value={data.totals.runs} />
        <Stat label="证据" value={data.totals.evidence} />
        <Stat label="入口" value={data.totals.entries} />
        <Stat label="候选词" value={data.totals.candidate_keywords} />
        <Stat label="机会" value={data.totals.cards} />
      </section>

      {groups.map(group => {
        const rows = items.filter(item => item.group === group)
        if (!rows.length) return null
        return (
          <section key={group} className="space-y-4">
            <h2 className="text-xl font-bold text-white">{group}</h2>
            <div className="grid gap-4 xl:grid-cols-2">
              {rows.map(model => <ModelCard key={model.id} model={model} />)}
            </div>
          </section>
        )
      })}
    </div>
  )
}
