import Link from 'next/link'
import {notFound} from 'next/navigation'
import {evidenceApi} from '../../../../lib/api'

export const dynamic = 'force-dynamic'

function fmtTime(s?:string){
  if(!s) return '-'
  const d = new Date(s)
  if(Number.isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN', {timeZone:'Asia/Shanghai', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit'})
}

function Stat({label,value}:{label:string;value:any}){
  return <div className="rounded-xl bg-slate-950 p-3"><div className="text-xs text-slate-500">{label}</div><b className="text-2xl text-white">{value}</b></div>
}

function Empty({text}:{text:string}) {
  return <p className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-500">{text}</p>
}

export default async function Page({params}:{params:Promise<{modelId:string}>}) {
  const {modelId} = await params
  const model = await evidenceApi.model(modelId).catch(() => null)
  if (!model) notFound()

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-7 shadow-2xl">
        <Link href="/evidence/models" className="text-sm text-blue-300 no-underline hover:text-blue-200">返回证据模型</Link>
        <p className="mt-5 text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">{model.group}</p>
        <h1 className="mt-3 text-4xl font-black text-white">{model.name}</h1>
        <p className="mt-3 max-w-4xl text-slate-300">{model.purpose}</p>
        <p className="mt-2 max-w-4xl text-sm text-slate-500">{model.loop}</p>
      </section>

      <section className="grid gap-4 md:grid-cols-6">
        <Stat label="运行" value={model.stats.runs} />
        <Stat label="证据" value={model.stats.evidence} />
        <Stat label="入口" value={model.stats.entries} />
        <Stat label="候选词" value={model.stats.candidate_keywords} />
        <Stat label="关键词" value={model.stats.keywords} />
        <Stat label="机会" value={model.stats.cards} />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="panel">
          <h2 className="text-xl font-bold">模型使用的来源</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {(model.sources || []).map(source => <span key={source} className="rounded-lg bg-slate-950 px-3 py-2 text-sm text-slate-300">{source}</span>)}
          </div>
        </div>
        <div className="panel">
          <h2 className="text-xl font-bold">识别方法</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {(model.methods || []).map(method => <span key={method} className="rounded-lg bg-slate-950 px-3 py-2 text-sm text-slate-300">{method}</span>)}
            {!model.methods?.length && <span className="text-sm text-slate-500">暂无独立方法标签。</span>}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <div className="panel">
          <h2 className="mb-4 text-xl font-bold">最新证据</h2>
          <div className="space-y-3">
            {(model.evidence || []).slice(0, 10).map(item => (
              <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold text-slate-100">{item.title || item.source_name || `证据 #${item.id}`}</h3>
                  <span className="badge">{item.source_type}</span>
                </div>
                <p className="mt-2 text-sm text-slate-400">{item.summary || item.raw_excerpt || '暂无摘要'}</p>
              </div>
            ))}
            {!model.evidence?.length && <Empty text="暂无证据。" />}
          </div>
        </div>

        <div className="panel">
          <h2 className="mb-4 text-xl font-bold">模型产生的入口</h2>
          <div className="space-y-3">
            {(model.entries || []).slice(0, 10).map(item => (
              <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold text-slate-100">{item.name}</h3>
                  <span className="badge">{item.entry_type}</span>
                </div>
                <p className="mt-2 text-sm text-slate-400">状态 {item.status} · 来源 {item.source || '-'}</p>
              </div>
            ))}
            {!model.entries?.length && <Empty text="暂无入口。" />}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <div className="panel">
          <h2 className="mb-4 text-xl font-bold">候选关键词</h2>
          <div className="space-y-2">
            {(model.candidate_keywords || []).slice(0, 12).map((item:any) => (
              <div key={item.id} className="rounded-xl bg-slate-950 p-3 text-sm">
                <b className="text-slate-100">{item.keyword}</b>
                <div className="mt-1 text-slate-500">{item.method || item.source} · score {Number(item.score || 0).toFixed(2)} · {item.status}</div>
              </div>
            ))}
            {!model.candidate_keywords?.length && <Empty text="暂无候选关键词。" />}
          </div>
        </div>

        <div className="panel">
          <h2 className="mb-4 text-xl font-bold">运行记录</h2>
          <div className="space-y-2">
            {(model.runs || []).slice(0, 12).map((item:any) => (
              <div key={item.id} className="rounded-xl bg-slate-950 p-3 text-sm">
                <b className="text-slate-100">#{item.id} {item.source}</b>
                <div className="mt-1 text-slate-500">{fmtTime(item.started_at)} · {item.status} · 入口 {item.candidates_created || 0} · 证据 {item.evidence_created || 0}</div>
              </div>
            ))}
            {!model.runs?.length && <Empty text="暂无运行记录。" />}
          </div>
        </div>
      </section>
    </div>
  )
}
