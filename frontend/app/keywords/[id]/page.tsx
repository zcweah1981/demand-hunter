import {api} from '../../../lib/api'
import {SerpButton, CardButton} from '../../../components/Actions'
import {I18nText} from '../../../components/I18nText'
import {ContextActions} from '../../../components/ContextActions'
import {EvidenceTimeline} from '../../../components/EvidenceTimeline'
import {ScoreHistory} from '../../../components/ScoreHistory'

function gapBadge(tag: string) {
  return <span className="inline-block rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 text-xs text-cyan-200">{tag}</span>
}

function weaknessBadge(tag: string) {
  return <span className="inline-block rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-xs text-amber-200">{tag}</span>
}

const STATUS_MAP: Record<string, {label: string; tone: string}> = {
  adopted:  {label: '已采纳',  tone: 'border-purple-500/40 bg-purple-500/10 text-purple-200'},
  action:   {label: '待行动',  tone: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'},
  watch:    {label: '观察中',  tone: 'border-blue-500/40 bg-blue-500/10 text-blue-200'},
  reject:   {label: '已排除',  tone: 'border-amber-500/40 bg-amber-500/10 text-amber-200'},
  block:    {label: '已屏蔽',  tone: 'border-rose-500/40 bg-rose-500/10 text-rose-200'},
}

function intentLabel(raw: string) {
  if (!raw || raw === 'unknown') return '待分析'
  if (raw.startsWith('search_demand')) return '有搜索需求'
  if (raw.startsWith('evidence_for_card:')) return `补充证据 #${raw.split(':')[1]}`
  if (raw.startsWith('duplicate_card:')) return `关联卡片 #${raw.split(':')[1]}`
  return raw
}

export default async function Page({params}:{params:{id:string}}) {
  const d = await api<any>(`/api/keywords/${params.id}`)
  const kw = d.keyword
  const s = STATUS_MAP[kw.status] || {label: kw.status, tone: 'border-slate-600 bg-slate-800 text-slate-300'}

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Keyword Detail</p>
        <h1 className="mt-2 text-3xl font-black text-white">{kw.query}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <span className={`inline-block rounded border px-2.5 py-1 text-xs ${s.tone}`}>{s.label}</span>
          <span className="text-sm text-slate-400">意图：{intentLabel(kw.intent)}</span>
          <span className="font-mono text-sm text-blue-300">评分 {kw.score}</span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <SerpButton id={+params.id}/>
          <CardButton id={+params.id}/>
          <ContextActions actions={[
            {label:'重新计算', actionType:'keyword.rescore', targetType:'keyword', targetId:params.id, variant:'secondary'},
            {label:'补证据', actionType:'keyword.collect_evidence', targetType:'keyword', targetId:params.id},
          ]} />
        </div>
        <p className="mt-3 text-xs text-slate-500">
          <I18nText
            zh="运行 SERP = 用这个词去搜索，分析竞争对手弱点。生成卡片 = 判断这个方向是否值得做产品。"
            en="Run SERP = search this keyword and analyze competitor weaknesses. Generate Card = evaluate if this direction is worth building."
          />
        </p>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="panel">
          <h2 className="mb-4 text-xl font-bold">证据时间线</h2>
          <EvidenceTimeline targetType="keyword" targetId={params.id} />
        </div>
        <ScoreHistory title="关键词权重历史" events={d.weight_events || []} />
      </section>

      {/* SERP Results */}
      {d.serp?.length > 0 && (
        <section className="panel">
          <h2 className="text-xl font-bold">🔍 <I18nText zh="搜索结果分析" en="SERP Analysis"/></h2>
          <p className="mt-1 text-sm text-slate-400">
            <I18nText
              zh="Google 搜索这个词后，前 10 名长什么样。看他们做得好不好，有没有我们可以切入的空间。"
              en="Top 10 Google results for this keyword. See how well they cover the topic and where we can fit in."
            />
          </p>
          <div className="mt-4 space-y-3">
            {d.serp.map((s: any) => (
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3" key={s.id}>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="font-mono">#{s.rank}</span>
                  <span className="text-slate-400">{s.domain}</span>
                  {s.weakness_score != null && (
                    <span className="text-amber-300">弱点 {s.weakness_score}</span>
                  )}
                </div>
                <a className="mt-1 block text-sm font-medium text-blue-200 hover:underline" href={s.url} target="_blank">{s.title}</a>
                {s.snippet && <p className="mt-1 text-xs text-slate-400 line-clamp-2">{s.snippet}</p>}
                {s.gap_tags?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {s.gap_tags.map((t: string) => gapBadge(t))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Competitor Weakness */}
      {d.competitors?.length > 0 && (
        <section className="panel">
          <h2 className="text-xl font-bold">⚔️ <I18nText zh="竞争对手弱点" en="Competitor Weaknesses"/></h2>
          <p className="mt-1 text-sm text-slate-400">
            <I18nText
              zh="这些网站在哪些方面做得不够好，正是我们的切入点。"
              en="Where these sites fall short — exactly where we can step in."
            />
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {d.competitors.map((c: any) => (
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3" key={c.id}>
                <div className="font-medium text-slate-200">{c.domain}</div>
                {c.weakness_tags?.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {c.weakness_tags.map((t: string) => weaknessBadge(t))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Social Evidence */}
      {d.social?.length > 0 && (
        <section className="panel">
          <h2 className="text-xl font-bold">💬 <I18nText zh="社交讨论证据" en="Social Evidence"/></h2>
          <p className="mt-1 text-sm text-slate-400">
            <I18nText
              zh="来自论坛、社交媒体的真实用户讨论，证明这个词背后有真实需求。"
              en="Real user discussions from forums and social media, proving real demand behind this keyword."
            />
          </p>
          <div className="mt-4 space-y-2">
            {d.social.map((s: any) => (
              <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/50 p-3" key={s.id}>
                <span className="inline-block rounded border border-slate-600 bg-slate-800 px-2 py-0.5 text-xs text-slate-300">{s.platform}</span>
                <a className="flex-1 truncate text-sm text-blue-200 hover:underline" href={s.url} target="_blank">{s.title}</a>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Cards */}
      {d.cards?.length > 0 && (
        <section className="panel">
          <h2 className="text-xl font-bold">💡 <I18nText zh="已生成的机会卡" en="Generated Opportunity Cards"/></h2>
          <p className="mt-1 text-sm text-slate-400">
            <I18nText
              zh="基于这个关键词搜索分析后，系统判断出的产品机会。"
              en="Product opportunities the system identified based on search analysis of this keyword."
            />
          </p>
          <div className="mt-4 space-y-3">
            {d.cards.map((c: any) => (
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4" key={c.id}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-block rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-200">{c.verdict}</span>
                  <span className="font-mono text-sm text-blue-300">评分 {c.score}</span>
                  {c.monetization_type && (
                    <span className="text-xs text-slate-500">{c.monetization_type}</span>
                  )}
                </div>
                {c.mvp_plan && <p className="mt-2 text-sm text-slate-300 line-clamp-3">{c.mvp_plan}</p>}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Empty state */}
      {(!d.serp?.length && !d.competitors?.length && !d.social?.length && !d.cards?.length) && (
        <section className="panel text-center">
          <p className="text-lg text-slate-400">
            <I18nText
              zh="这个关键词还没有跑过分析。点击上方的「运行 SERP」开始搜索分析。"
              en={'This keyword hasn\'t been analyzed yet. Click "Run SERP" above to start.'}
            />
          </p>
        </section>
      )}
    </div>
  )
}
