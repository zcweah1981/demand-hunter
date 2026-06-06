import {api} from '../../lib/api'
import {StatCard} from '../../components/StatCard'
import {DiscoverySeedForm} from '../../components/DiscoverySeedForm'
import {DiscoveryDomainForm} from '../../components/DiscoveryDomainForm'
import {FullPipelineForm} from '../../components/FullPipelineForm'
import {DiscoveryImportButton} from '../../components/DiscoveryImportButton'

export default async function Discovery(){
  const [expansions, competitorKws, similarSites] = await Promise.all([
    api<any[]>('/api/discovery/expansions').catch(()=>[]),
    api<any[]>('/api/discovery/competitor-keywords').catch(()=>[]),
    api<any[]>('/api/discovery/similar-sites').catch(()=>[]),
  ])
  const loop = await api<any>('/api/discovery/loop-status').catch(()=>null)

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-violet-500/30 bg-gradient-to-br from-violet-950/70 via-slate-950 to-blue-950/60 p-8 shadow-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-violet-300">Four-Find Discovery</p>
        <h1 className="mt-3 text-4xl font-black text-white">四找发现引擎</h1>
        <p className="mt-3 max-w-3xl text-slate-300">
          基于「词找词 → 词找站 → 站找词 → 站找站」的完整找词链路。从一个 seed keyword 出发，发现更多搜索入口、竞品、和机会。
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="panel">
          <h2 className="text-xl font-bold">词找词 / 词找站</h2>
          <p className="mt-2 text-sm text-slate-400">输入一个 seed keyword，系统会自动扩展相关搜索词，并发现 SERP 上的竞品站。</p>
          <DiscoverySeedForm />
        </div>
        <div className="panel">
          <h2 className="text-xl font-bold">站找词 / 站找站</h2>
          <p className="mt-2 text-sm text-slate-400">输入一个竞品域名，系统会反查它的关键词，并找到类似站。</p>
          <DiscoveryDomainForm />
        </div>
      </section>

      <section className="panel">
        <h2 className="text-xl font-bold">完整四找流水线</h2>
        <p className="mt-2 text-sm text-slate-400">一键执行：词找词 → 词找站 → 站找词 → 站找站</p>
        <FullPipelineForm />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <StatCard label="Expanded Keywords" value={expansions.length} tone="violet"/>
        <StatCard label="Competitor Keywords" value={competitorKws.length} tone="blue"/>
        <StatCard label="Similar Sites" value={similarSites.length} tone="cyan"/>
      </section>

      {loop&&<section className="panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold">四找闭环状态</h2>
            <p className="mt-1 text-sm text-slate-400">Discovery → Import → SERP/Card → Review Feedback → 下一轮 seeds/domains。</p>
          </div>
          <span className="badge badge-action">API closed loop</span>
        </div>
        <div className="grid gap-4 md:grid-cols-6">
          <StatCard label="Discovered" value={loop.funnel?.expansions||0} tone="violet"/>
          <StatCard label="Imported" value={loop.funnel?.imported_keywords||0} tone="green"/>
          <StatCard label="Cards" value={loop.funnel?.cards||0} />
          <StatCard label="Reviewed" value={loop.funnel?.reviewed_cards||0} tone="blue"/>
          <StatCard label="Action" value={loop.card_verdicts?.Action||0} tone="green"/>
          <StatCard label="Reject" value={loop.card_verdicts?.Reject||0} tone="rose"/>
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <h3 className="font-semibold text-slate-200">Top Seeds</h3>
            <div className="mt-3 space-y-2 text-sm">{(loop.seed_scores||[]).slice(0,6).map((s:any)=><div key={s.seed} className="flex justify-between gap-4"><span className="text-slate-300">{s.seed}</span><span className="text-slate-500">expanded {s.expanded} · imported {s.imported}</span></div>)}</div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <h3 className="font-semibold text-slate-200">Top Competitor Domains</h3>
            <div className="mt-3 space-y-2 text-sm">{(loop.top_competitor_domains||[]).slice(0,6).map((d:any)=><div key={d.domain} className="flex justify-between gap-4"><span className="text-slate-300">{d.domain}</span><span className="text-slate-500">{d.keywords} keywords</span></div>)}</div>
          </div>
        </div>
      </section>}

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="panel overflow-x-auto">
          <h2 className="mb-4 text-xl font-bold">词找词结果</h2>
          {expansions.length ? (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-slate-500"><th className="pb-2">Seed</th><th className="pb-2">Expanded</th><th className="pb-2">Type</th><th className="pb-2">Action</th></tr></thead>
              <tbody>
              {expansions.slice(0,30).map((e:any)=>(
                <tr key={e.id} className="border-t border-slate-800">
                  <td className="py-2 text-slate-400">{e.seed_keyword}</td>
                  <td className="py-2 font-medium text-white">{e.expanded_keyword}</td>
                  <td className="py-2"><span className="badge">{e.expansion_type}</span></td>
                  <td className="py-2">
                    {e.status === 'new' ? <DiscoveryImportButton id={e.id} type="expansion"/> : <span className="text-xs text-emerald-400">{e.status}</span>}
                  </td>
                </tr>
              ))}
              </tbody>
            </table>
          ) : <p className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">还没有词找词结果。输入 seed keyword 开始。</p>}
        </div>

        <div className="panel overflow-x-auto">
          <h2 className="mb-4 text-xl font-bold">站找词结果</h2>
          {competitorKws.length ? (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-slate-500"><th className="pb-2">Domain</th><th className="pb-2">Keyword</th><th className="pb-2">Source</th><th className="pb-2">Action</th></tr></thead>
              <tbody>
              {competitorKws.slice(0,30).map((e:any)=>(
                <tr key={e.id} className="border-t border-slate-800">
                  <td className="py-2 text-slate-400">{e.competitor_domain}</td>
                  <td className="py-2 font-medium text-white">{e.discovered_keyword}</td>
                  <td className="py-2"><span className="badge">{e.source}</span></td>
                  <td className="py-2">
                    {e.status === 'new' ? <DiscoveryImportButton id={e.id} type="competitor-keyword"/> : <span className="text-xs text-emerald-400">{e.status}</span>}
                  </td>
                </tr>
              ))}
              </tbody>
            </table>
          ) : <p className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">还没有站找词结果。</p>}
        </div>
      </section>

      <section className="panel overflow-x-auto">
        <h2 className="mb-4 text-xl font-bold">站找站结果</h2>
        {similarSites.length ? (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-slate-500"><th className="pb-2">From</th><th className="pb-2">Similar Domain</th><th className="pb-2">Title</th></tr></thead>
            <tbody>
            {similarSites.slice(0,30).map((e:any)=>(
              <tr key={e.id} className="border-t border-slate-800">
                <td className="py-2 text-slate-400">{e.seed_domain}</td>
                <td className="py-2 font-medium text-white">{e.similar_domain}</td>
                <td className="py-2 text-slate-300">{e.title}</td>
              </tr>
            ))}
            </tbody>
          </table>
        ) : <p className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">还没有站找站结果。</p>}
      </section>

      <section className="panel">
        <h2 className="text-xl font-bold">方法论</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-violet-500/30 bg-violet-950/30 p-4">
            <div className="text-2xl">🔍</div>
            <h3 className="mt-2 font-bold text-violet-300">词找词</h3>
            <p className="mt-1 text-xs text-slate-400">从 seed keyword 出发，通过 SERP title modifiers、related searches、"vs" pattern 扩展更多搜索词。</p>
          </div>
          <div className="rounded-2xl border border-blue-500/30 bg-blue-950/30 p-4">
            <div className="text-2xl">🌐</div>
            <h3 className="mt-2 font-bold text-blue-300">词找站</h3>
            <p className="mt-1 text-xs text-slate-400">搜索关键词，发现 SERP 前排站，按类型分类：tool / saas / content / forum / directory。</p>
          </div>
          <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/30 p-4">
            <div className="text-2xl">🔎</div>
            <h3 className="mt-2 font-bold text-cyan-300">站找词</h3>
            <p className="mt-1 text-xs text-slate-400">用 site:domain 搜索反查竞品页面，从 title 和 URL path 提取它覆盖的关键词。</p>
          </div>
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/30 p-4">
            <div className="text-2xl">🔗</div>
            <h3 className="mt-2 font-bold text-emerald-300">站找站</h3>
            <p className="mt-1 text-xs text-slate-400">搜索 "alternative to X"、"sites like X"，从一个竞品发现更多同类站和替代品。</p>
          </div>
        </div>
      </section>
    </div>
  )
}
